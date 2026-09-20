import cv2
import numpy as np
import pytest

from image_processor import GridDetectionError, ImageProcessor

from helpers import build_synthetic_sheet, rotate_image


class TestDetectGuidedBoxesBaseline:
    """Golden-path regression: a perfectly aligned grid must still produce
    the exact same boxes as the original (pre-refactor) algorithm."""

    def test_aligned_grid_matches_expected_boxes_exactly(self):
        image, expected_boxes = build_synthetic_sheet(question_count=20, choice_count=4)

        processor = ImageProcessor(debug=False)
        boxes, grayscale_image, number_of_questions, number_of_choices = processor.detect_guided_boxes(
            "baseline.png", image
        )

        assert number_of_questions == 20
        assert number_of_choices == 4
        assert boxes == expected_boxes
        assert grayscale_image.shape == image.shape[:2]

    @pytest.mark.parametrize("question_count,choice_count", [(5, 4), (30, 6), (8, 2)])
    def test_various_sizes_detected_correctly(self, question_count, choice_count):
        image, expected_boxes = build_synthetic_sheet(question_count, choice_count)

        processor = ImageProcessor(debug=False)
        boxes, _, number_of_questions, number_of_choices = processor.detect_guided_boxes("sheet.png", image)

        assert number_of_questions == question_count
        assert number_of_choices == choice_count
        assert boxes == expected_boxes


class TestDeskewRobustness:
    """Rotated scans should still yield the correct grid dimensions."""

    @pytest.mark.parametrize("angle_degrees", [3.0, 5.0, 8.0])
    def test_rotated_grid_still_detects_correct_counts(self, angle_degrees):
        image, _ = build_synthetic_sheet(question_count=10, choice_count=4)
        rotated_image = rotate_image(image, angle_degrees)

        processor = ImageProcessor(debug=False)
        boxes, _, number_of_questions, number_of_choices = processor.detect_guided_boxes(
            f"rotated_{angle_degrees}.png", rotated_image
        )

        assert number_of_questions == 10
        assert number_of_choices == 4
        assert len(boxes) == 40

    def test_well_aligned_image_is_not_modified_by_deskew(self):
        image, _ = build_synthetic_sheet(question_count=10, choice_count=4)
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(grayscale_image, (3, 3), 0)
        _, binary_image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        processor = ImageProcessor(debug=False)
        result_gray, result_binary, angle = processor._deskew(grayscale_image, binary_image)

        assert angle == 0.0
        assert np.array_equal(result_gray, grayscale_image)
        assert np.array_equal(result_binary, binary_image)


class TestAdaptiveThresholdFallback:
    """A single faint/broken guide line should be recovered by the adaptive
    threshold retry instead of producing an odd/incomplete line count."""

    def test_faint_row_line_recovered(self):
        image, _ = build_synthetic_sheet(question_count=10, choice_count=4, faint_row_indices={2})

        processor = ImageProcessor(debug=False)
        boxes, _, number_of_questions, number_of_choices = processor.detect_guided_boxes("faint.png", image)

        assert number_of_questions == 10
        assert number_of_choices == 4
        assert len(boxes) == 40

    def test_peaks_from_projection_adaptive_retry_via_find_horizontal_lines(self):
        # Craft a projection directly: 10 "rows", each pair (top,bottom) at
        # relative strength 1.0 except one line at 0.33 strength.
        # Positions are spaced 30px apart (> MINIMUM_LINE_GAP=20) so each is
        # detected as a distinct line rather than merged together.
        cropped_height = 350
        crop_offset_y = 100
        left_part_width = 5
        max_strength = 100

        line_positions = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300]
        strengths = [max_strength] * len(line_positions)
        strengths[5] = int(max_strength * 0.33)  # make one line faint (odd count at default threshold)

        cropped_image = np.zeros((cropped_height, left_part_width + 50), dtype=np.uint8)
        for y, strength in zip(line_positions, strengths):
            cropped_image[y, :left_part_width] = strength

        processor = ImageProcessor(debug=False)
        lines = processor._find_horizontal_lines(cropped_image, crop_offset_y)

        assert len(lines) == len(line_positions)
        assert len(lines) % 2 == 0


class TestErrorDiagnostics:
    def test_blank_image_raises_grid_detection_error_with_diagnostics(self):
        blank_image = np.full((400, 400, 3), 255, dtype=np.uint8)
        processor = ImageProcessor(debug=False)

        with pytest.raises(GridDetectionError) as exc_info:
            processor.detect_guided_boxes("blank.png", blank_image)

        assert exc_info.value.diagnostics["image_name"] == "blank.png"
        assert exc_info.value.diagnostics["stage"] == "separator_detection"

    def test_debug_visualization_is_saved_even_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "debug_results").mkdir()

        blank_image = np.full((400, 400, 3), 255, dtype=np.uint8)
        processor = ImageProcessor(debug=True)

        with pytest.raises(GridDetectionError):
            processor.detect_guided_boxes("failure_case.png", blank_image)

        assert (tmp_path / "debug_results" / "failure_case.png").exists()


class TestAdaptiveThresholdsHelper:
    def test_adaptive_thresholds_steps_down_to_floor_inclusive(self):
        thresholds = list(ImageProcessor._adaptive_thresholds(0.5, 0.2, 0.05))
        assert thresholds == [0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2]
