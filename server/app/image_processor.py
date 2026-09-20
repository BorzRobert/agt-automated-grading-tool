import os
import statistics

import cv2
import numpy as np
from typing import Iterator, List, Optional, Tuple


class GridDetectionError(RuntimeError):
    """Raised when the answer grid cannot be located on a sheet.

    Carries structured diagnostics (image name, failing stage, projection
    stats) in addition to the human-readable message, to speed up triage.
    """

    def __init__(self, message: str, **diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


class ImageProcessor:
    """Detect guiding lines and extract answer boxes coordinates."""

    # Relative-to-max thresholds used to decide whether a projection value
    # represents a guide line. Primary value matches the original hardcoded
    # behavior; the fallback values are only used if the primary attempt
    # yields an inconsistent (odd or zero) number of lines.
    SEPARATOR_RELATIVE_THRESHOLD = 0.4
    LINE_RELATIVE_THRESHOLD = 0.5
    ADAPTIVE_THRESHOLD_FLOOR = 0.2
    ADAPTIVE_THRESHOLD_STEP = 0.05

    # Real scanned sheets often register the same physical line twice, a few
    # pixels apart (ink bleed/double strokes); 20px comfortably merges those
    # duplicates while staying well below genuine row/column pitch (~35px+).
    MINIMUM_LINE_GAP = 20
    LEFT_FRACTION = 0.15  # Use only left 15% of the image to detect horizontal lines
    SEPARATOR_CROP_MARGIN = 10

    # A line whose gap to its neighbor exceeds this multiple of the median
    # gap is considered an isolated stray mark (e.g. a signature underline)
    # rather than part of the regular grid, and is trimmed from the ends.
    OUTLIER_GAP_RATIO = 3.0

    # Runs (contiguous above-threshold spans) in the vertical projection no
    # wider than this are a single thin guide line stroke (use its midpoint);
    # wider runs are a checkbox column whose left/right edges have visually
    # merged with interior fill ink, so both edges (run start/end) are used.
    LINE_MAX_THICKNESS = 26

    # Runs separated by less than this are coalesced into one (handles a
    # double-registered stroke, or a column's fill briefly dipping below
    # threshold and splitting what should be one run into two).
    RUN_MERGE_GAP = 25

    # Real scans sometimes have a thin dark shadow line right at the
    # physical page/scanner-bed edge; excluding this margin from vertical
    # line detection keeps it from being mistaken for the grid's outer
    # frame border (which sits well inside this margin in practice).
    PAGE_EDGE_MARGIN = 15

    # Deskew is skipped for angles smaller than this (already-aligned scans
    # are processed identically to before) and for angles larger than the
    # max (likely noise rather than a real skew, correcting could hurt).
    # Real-world testing showed sub-2-degree "corrections" tend to do more
    # harm than good (rotation interpolation adds noise around densely
    # packed guide marks), so only clearly skewed scans are corrected.
    MIN_SKEW_CORRECTION_DEGREES = 2.0
    MAX_SKEW_CORRECTION_DEGREES = 15.0

    def __init__(self, debug):
        self.debug = debug
        self.debug_image = None

    def detect_guided_boxes(self, image_name: str, image: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray, int, int]:
        """Detect boxes using the guiding lines."""

        grayscale_image, binary_image = self._binarize(image)

        separator_y: Optional[int] = None
        horizontal_lines: List[int] = []
        vertical_lines: List[int] = []
        boxes: List[Tuple[int, int, int, int]] = []
        crop_offset_y = 0
        skew_angle = 0.0

        try:
            grayscale_image, binary_image, skew_angle = self._deskew(grayscale_image, binary_image)

            separator_y = self._find_separator_row(binary_image)
            if separator_y is None:
                raise GridDetectionError(
                    "Could not find title separator line",
                    image_name=image_name,
                    stage="separator_detection",
                )

            crop_offset_y = separator_y + self.SEPARATOR_CROP_MARGIN
            cropped_image = binary_image[crop_offset_y:, :]

            horizontal_lines = self._find_horizontal_lines(cropped_image, crop_offset_y)
            vertical_lines = self._find_vertical_lines(cropped_image)

            number_of_questions = len(horizontal_lines) // 2
            number_of_choices = len(vertical_lines) // 2

            if number_of_questions == 0 or number_of_choices == 0:
                raise GridDetectionError(
                    "Could not detect a valid answer grid (no rows/columns found)",
                    image_name=image_name,
                    stage="line_detection",
                    horizontal_lines_found=len(horizontal_lines),
                    vertical_lines_found=len(vertical_lines),
                    skew_angle_deg=round(skew_angle, 3),
                )

            boxes = self._build_boxes(horizontal_lines, vertical_lines, number_of_questions, number_of_choices)

            return boxes, grayscale_image, number_of_questions, number_of_choices

        except GridDetectionError:
            raise
        except Exception as exc:
            raise GridDetectionError(
                f"Unexpected error while detecting the answer grid for '{image_name}': {exc}",
                image_name=image_name,
                stage="unknown",
            ) from exc
        finally:
            if self.debug:
                self._save_debug_visualization(
                    image_name,
                    grayscale_image,
                    horizontal_lines,
                    vertical_lines,
                    boxes,
                    crop_offset_y,
                )

    def _binarize(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(grayscale_image, (3, 3), 0)
        _, binary_image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return grayscale_image, binary_image

    def _deskew(self, grayscale_image: np.ndarray, binary_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """Estimate and correct small rotations before running line detection.

        No-op (returns inputs unchanged, angle=0) when the estimated skew is
        negligible or implausibly large, so already-aligned scans are
        processed identically to the original implementation.
        """
        coords = np.column_stack(np.where(binary_image > 0))
        if coords.size == 0:
            return grayscale_image, binary_image, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < self.MIN_SKEW_CORRECTION_DEGREES or abs(angle) > self.MAX_SKEW_CORRECTION_DEGREES:
            return grayscale_image, binary_image, 0.0

        height, width = binary_image.shape
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        rotated_grayscale = cv2.warpAffine(
            grayscale_image, rotation_matrix, (width, height),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )
        rotated_binary = cv2.warpAffine(
            binary_image, rotation_matrix, (width, height),
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )

        return rotated_grayscale, rotated_binary, angle

    @staticmethod
    def _adaptive_thresholds(start: float, floor: float, step: float) -> Iterator[float]:
        """Yield relative thresholds from `start` down to `floor` (inclusive)."""
        value = start
        while value >= floor - 1e-9:
            yield round(value, 4)
            value -= step

    def _find_separator_row(self, binary_image: np.ndarray) -> Optional[int]:
        """Find the horizontal line separating the title area from the grid."""
        row_sum = np.sum(binary_image, axis=1)
        max_row_sum = np.max(row_sum)
        if max_row_sum <= 0:
            return None

        for relative_threshold in self._adaptive_thresholds(
            self.SEPARATOR_RELATIVE_THRESHOLD, self.ADAPTIVE_THRESHOLD_FLOOR, self.ADAPTIVE_THRESHOLD_STEP
        ):
            threshold_value = relative_threshold * max_row_sum
            for y, val in enumerate(row_sum):
                if val > threshold_value:
                    return y
        return None

    def _peaks_from_projection(
        self,
        projection: np.ndarray,
        relative_threshold: float,
        offset: int,
        valid_range: Tuple[int, int],
    ) -> List[int]:
        max_value = np.max(projection)
        if max_value <= 0:
            return []
        threshold_value = relative_threshold * max_value
        lines: List[int] = []
        start, end = valid_range
        for i in range(start, end):
            if projection[i] > threshold_value:
                coordinate = i + offset
                if not lines or coordinate - lines[-1] > self.MINIMUM_LINE_GAP:
                    lines.append(coordinate)
        return lines

    def _find_horizontal_lines(self, cropped_image: np.ndarray, crop_offset_y: int) -> List[int]:
        """Detect the horizontal guiding lines present on the left side of the paper."""
        cropped_image_height, cropped_image_width = cropped_image.shape
        valid_width = int(cropped_image_width * self.LEFT_FRACTION)
        left_part = cropped_image[:, :valid_width]
        horizontal_sum = np.sum(left_part, axis=1)

        lines: List[int] = []
        for relative_threshold in self._adaptive_thresholds(
            self.LINE_RELATIVE_THRESHOLD, self.ADAPTIVE_THRESHOLD_FLOOR, self.ADAPTIVE_THRESHOLD_STEP
        ):
            lines = self._trim_outlier_lines(self._peaks_from_projection(
                horizontal_sum, relative_threshold, crop_offset_y, (1, cropped_image_height - 1)
            ))
            if lines and len(lines) % 2 == 0:
                return lines
        return lines

    def _find_vertical_lines(self, cropped_image: np.ndarray) -> List[int]:
        """Detect vertical guiding lines present across the area containing the answers.

        Real scans frequently have some choices filled in enough that a
        column's left/right box edges visually bridge into one contiguous
        "blob" in the projection (border + interior ink), while other,
        lightly-marked columns still show as two separate thin edges. Both
        shapes are handled uniformly via contiguous above-threshold runs:
        a thin run (~line stroke width) contributes its single midpoint,
        a wide run (~box width or more) contributes its start and end as
        the two edges. The outer left/right frame border is always the
        first/last run and is dropped. Because the "right" relative
        threshold varies per-image (too high starves faint columns, too
        low reintroduces noise), every threshold in the adaptive range is
        tried and the most common (most stable) resulting line count wins,
        preferring the highest threshold that achieves it.
        """
        _, cropped_image_width = cropped_image.shape
        vertical_sum = np.sum(cropped_image, axis=0)
        valid_range = (self.PAGE_EDGE_MARGIN, max(self.PAGE_EDGE_MARGIN + 1, cropped_image_width - self.PAGE_EDGE_MARGIN))

        candidates: dict[float, List[int]] = {}
        for relative_threshold in self._adaptive_thresholds(
            self.LINE_RELATIVE_THRESHOLD, self.ADAPTIVE_THRESHOLD_FLOOR, self.ADAPTIVE_THRESHOLD_STEP
        ):
            runs = self._merge_close_runs(
                self._contiguous_runs(vertical_sum, relative_threshold, 0, valid_range),
                self.RUN_MERGE_GAP,
            )
            if len(runs) < 3:
                continue
            lines = self._runs_to_lines(runs[1:-1])  # drop the outer frame border runs
            if lines and len(lines) % 2 == 0:
                candidates[relative_threshold] = lines

        if not candidates:
            return []

        vote_counts: dict[int, int] = {}
        for lines in candidates.values():
            vote_counts[len(lines)] = vote_counts.get(len(lines), 0) + 1
        best_length = max(vote_counts, key=lambda length: (vote_counts[length], length))

        for relative_threshold in sorted(candidates, reverse=True):
            if len(candidates[relative_threshold]) == best_length:
                return candidates[relative_threshold]
        return []

    def _contiguous_runs(
        self,
        projection: np.ndarray,
        relative_threshold: float,
        offset: int,
        valid_range: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """Find (start, end) ranges (inclusive, in original coordinates) where the projection exceeds the threshold."""
        max_value = np.max(projection)
        if max_value <= 0:
            return []
        threshold_value = relative_threshold * max_value
        start, end = valid_range
        runs: List[Tuple[int, int]] = []
        run_start: Optional[int] = None
        for i in range(start, end):
            if projection[i] > threshold_value:
                if run_start is None:
                    run_start = i
            elif run_start is not None:
                runs.append((run_start + offset, i - 1 + offset))
                run_start = None
        if run_start is not None:
            runs.append((run_start + offset, end - 1 + offset))
        return runs

    def _merge_close_runs(self, runs: List[Tuple[int, int]], max_gap: int) -> List[Tuple[int, int]]:
        """Coalesce runs separated by a small gap (double-registered strokes, or a column's fill briefly dipping below threshold)."""
        if not runs:
            return runs
        merged = [runs[0]]
        for start, end in runs[1:]:
            last_start, last_end = merged[-1]
            if start - last_end <= max_gap:
                merged[-1] = (last_start, end)
            else:
                merged.append((start, end))
        return merged

    def _runs_to_lines(self, runs: List[Tuple[int, int]]) -> List[int]:
        """Convert runs to line coordinates: a thin run is one edge (its start), a wide run is a box (its two edges)."""
        lines: List[int] = []
        for run_start, run_end in runs:
            if run_end - run_start <= self.LINE_MAX_THICKNESS:
                lines.append(run_start)
            else:
                lines.append(run_start)
                lines.append(run_end)
        return lines

    def _trim_outlier_lines(self, lines: List[int]) -> List[int]:
        """Drop leading/trailing lines whose gap dwarfs the regular grid pitch."""
        lines = list(lines)
        while len(lines) > 2:
            gaps = [b - a for a, b in zip(lines, lines[1:])]
            median_gap = statistics.median(gaps)
            if median_gap <= 0:
                break
            if gaps[0] > self.OUTLIER_GAP_RATIO * median_gap:
                lines.pop(0)
            elif gaps[-1] > self.OUTLIER_GAP_RATIO * median_gap:
                lines.pop()
            else:
                break
        return lines

    def _build_boxes(
        self,
        horizontal_lines: List[int],
        vertical_lines: List[int],
        number_of_questions: int,
        number_of_choices: int,
    ) -> List[Tuple[int, int, int, int]]:
        boxes = []
        for i in range(0, 2 * number_of_questions, 2):
            y1, y2 = horizontal_lines[i], horizontal_lines[i + 1]
            for j in range(0, 2 * number_of_choices, 2):
                x1, x2 = vertical_lines[j], vertical_lines[j + 1]
                boxes.append((x1, y1, x2 - x1, y2 - y1))
        return boxes

    def _save_debug_visualization(
        self,
        image_name: str,
        grayscale_image: Optional[np.ndarray],
        horizontal_lines: List[int],
        vertical_lines: List[int],
        boxes: List[Tuple[int, int, int, int]],
        crop_offset_y: int,
    ):
        """Build and persist the debug visualization, even for partial/failed detections."""
        if grayscale_image is None:
            return

        height, width = grayscale_image.shape
        debug_visualization_image = cv2.cvtColor(grayscale_image, cv2.COLOR_GRAY2BGR)

        # Draw each horizontal line on debug_visualization_image in red
        for y in horizontal_lines:
            cv2.line(debug_visualization_image, (0, y), (width, y), (0, 0, 255), 2)

        # Draw each vertical line on debug_visualization_image in blue
        for x in vertical_lines:
            cv2.line(debug_visualization_image, (x, crop_offset_y), (x, height), (255, 0, 0), 2)

        # Draw each box on debug_visualization_image in green
        for (x, y, box_width, box_height) in boxes:
            top_left = (x, y)
            bottom_right = (x + box_width, y + box_height)
            cv2.rectangle(debug_visualization_image, top_left, bottom_right, (0, 255, 0), 3)

        self.debug_image = debug_visualization_image
        self.save_debug_image(f"debug_results/{image_name}")

    def save_debug_image(self, output_path: str):
        """Save the image showing detected lines and boxes (if debug=True)."""
        if hasattr(self, "debug_image") and self.debug_image is not None:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            cv2.imwrite(output_path, self.debug_image)
            print(f"[DEBUG] Saved debug visualization to: {output_path}")
        else:
            print("[DEBUG] No debug image available. Make sure debug=True when detecting.")
