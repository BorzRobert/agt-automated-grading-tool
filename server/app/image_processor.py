import cv2
import numpy as np
from typing import List, Tuple


class ImageProcessor:
    """Detect guiding lines and extract answer boxes coordinates."""

    def __init__(self, debug):
        self.debug = debug
        self.debug_image = None

    def detect_guided_boxes(self, image: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray, int, int]:
        """Detect boxes using the guiding lines."""

        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(grayscale_image, (3, 3), 0)
        _, binary_image = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        height, width = binary_image.shape

        # Detect the horizontal line separating title area from the area containing the answers
        row_sum = np.sum(binary_image, axis=1)
        threshold = 0.5 * np.max(row_sum)
        separator_y = None
        for y, val in enumerate(row_sum):
            if val > threshold:
                separator_y = y
                break
        if separator_y is None:
            raise RuntimeError("Could not find title separator line")

        # Crop below separator line to obtain just the area containing the answers
        crop_offset_y = separator_y + 10
        cropped_image = binary_image[crop_offset_y : , :]
        cropped_image_height, cropped_image_width = cropped_image.shape

        minimum = 5  # pixels threshold between consecutive line detections

        # Detect the horizontal guiding lines present on the left side of the paper
        left_fraction = 0.15  # Use only left 15% of the image to detect horizontal lines
        valid_width = int(cropped_image_width * left_fraction)
        left_part = cropped_image[:, :valid_width]

        horizontal_sum = np.sum(left_part, axis=1)
        horizontal_lines = []
        for y in range(1, cropped_image_height - 1):
            if horizontal_sum[y] > 0.5 * np.max(horizontal_sum):  # strong horizontal line
                if not horizontal_lines or ((y + crop_offset_y) - horizontal_lines[-1])  > minimum:
                    horizontal_lines.append(y + crop_offset_y)

        # Detect vertical guiding lines present at the top of the area containing the answers
        vertical_sum = np.sum(cropped_image, axis=0)
        vertical_lines = []
        for x in range(1, cropped_image_width - 1):
            if vertical_sum[x] > 0.5 * np.max(vertical_sum): # strong vertical line
                if not vertical_lines or x - vertical_lines[-1] > minimum:
                    vertical_lines.append(x)

        # Drop the first and last vertical lines (outer borders)
        if len(vertical_lines) > 2:
            vertical_lines = vertical_lines[1:-1]

        # Construct boxes from intersections of vertical lines with horizontal lines
        boxes = []
        number_of_questions = int(len(horizontal_lines) / 2)
        number_of_choices = int(len(vertical_lines) / 2)

        for i in range(0, 2 * number_of_questions, 2):
            y1, y2 = horizontal_lines[i], horizontal_lines[i + 1]
            for j in range(0, 2 * number_of_choices, 2):
                x1, x2 = vertical_lines[j], vertical_lines[j + 1]
                boxes.append((x1, y1, x2 - x1, y2 - y1))

        if self.debug:
            debug_visualization_image = cv2.cvtColor(grayscale_image, cv2.COLOR_GRAY2BGR)

            # Draw each horizontal line on debug_visualization_image in red
            for y in horizontal_lines:
                cv2.line(debug_visualization_image, (0, y), (width, y), (0, 0, 255), 2)

            # Draw each vertical line on debug_visualization_image in blue
            for x in vertical_lines:
                cv2.line(debug_visualization_image, (x, crop_offset_y), (x, height), (255, 0, 0), 2)

            # Draw each box on debug_visualization_image in green
            for (x, y, width, height) in boxes:
                top_left = (x, y)
                bottom_right = (x + width, y + height)
                cv2.rectangle(debug_visualization_image, top_left, bottom_right, (0, 255, 0), 3)  # red box

            self.debug_image = debug_visualization_image
            self.save_debug_image("debug_results/debug_image.png")

        return boxes, grayscale_image, number_of_questions, number_of_choices

    def save_debug_image(self, output_path: str):
        """Save the image showing detected lines and boxes (if debug=True)."""
        if hasattr(self, "debug_image"):
            cv2.imwrite(output_path, self.debug_image)
            print(f"[DEBUG] Saved debug visualization to: {output_path}")
        else:
            print("[DEBUG] No debug image available. Make sure debug=True when detecting.")
