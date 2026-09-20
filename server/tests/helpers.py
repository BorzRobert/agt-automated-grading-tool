"""Synthetic answer-sheet generator used by the image_processor tests.

Builds a minimal grid image that exercises the same detection assumptions
as `ImageProcessor.detect_guided_boxes` (full-width title separator, row
"tick" marks confined to the left 15% of the page, and full-height vertical
column lines bracketed by an outer left/right frame border that the
algorithm strips), without depending on any real scanned template.
"""
from typing import List, Optional, Set, Tuple

import cv2
import numpy as np

WIDTH_MARGIN = 150
HEIGHT_MARGIN = 150

TITLE_RECT = (400, 80, 600, 110)  # x0, y0, x1, y1 - simulates title text
SEPARATOR_Y0 = 150
SEPARATOR_THICKNESS = 6

# Must match ImageProcessor.LEFT_FRACTION so tick marks land in the region
# actually inspected for horizontal lines, regardless of image width.
LEFT_FRACTION = 0.15
TICK_X0 = 10
TICK_THICKNESS = 2

ROW_TOP_MARGIN = 20
ROW_HEIGHT = 30
ROW_GAP = 30  # must stay comfortably above ImageProcessor.MINIMUM_LINE_GAP (20)

OUTER_LEFT_X = 240
COL_START_X = 300
COL_WIDTH = 60
COL_SPACING = 100
OUTER_RIGHT_PADDING = 40


def _row_top(crop_offset_y: int, row_index: int) -> int:
    return crop_offset_y + ROW_TOP_MARGIN + row_index * (ROW_HEIGHT + ROW_GAP)


def build_synthetic_sheet(
    question_count: int,
    choice_count: int,
    faint_row_indices: Optional[Set[int]] = None,
) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
    """Build a synthetic answer sheet image.

    Returns (image, expected_boxes). `expected_boxes` is only an exact
    regression baseline when `faint_row_indices` is empty/None (faint lines
    intentionally perturb detection to exercise the adaptive fallback).
    """
    faint_row_indices = faint_row_indices or set()

    separator_y = SEPARATOR_Y0  # matches what detect_guided_boxes should find
    crop_offset_y = separator_y + 10

    last_row_bottom = _row_top(crop_offset_y, question_count - 1) + ROW_HEIGHT
    outer_right_x = COL_START_X + (choice_count - 1) * COL_SPACING + COL_WIDTH + OUTER_RIGHT_PADDING

    width = outer_right_x + WIDTH_MARGIN
    height = last_row_bottom + HEIGHT_MARGIN

    # Size tick marks relative to the actually-inspected left region (15% of
    # width) so they remain valid signals regardless of the chosen width.
    valid_width = int(width * LEFT_FRACTION)
    normal_tick_x1 = TICK_X0 + max(20, int(valid_width * 0.6))
    faint_tick_x1 = TICK_X0 + max(8, int(valid_width * 0.2))
    assert OUTER_LEFT_X > valid_width, "outer frame line must stay outside the tick-detection region"

    image = np.full((height, width, 3), 255, dtype=np.uint8)

    # Title text placeholder (must not span enough width to look like a separator)
    cv2.rectangle(image, (TITLE_RECT[0], TITLE_RECT[1]), (TITLE_RECT[2], TITLE_RECT[3]), (0, 0, 0), -1)

    # Full-width title/answers separator line
    cv2.rectangle(image, (0, separator_y), (width, separator_y + SEPARATOR_THICKNESS), (0, 0, 0), -1)

    # Row tick marks (top & bottom edge of each row), confined to the left margin.
    # Only the bottom edge is weakened for "faint" rows, so a single faint
    # row perturbs the total line count to odd (unlike weakening both edges,
    # which would keep the count even and mask the detection gap).
    expected_boxes: List[Tuple[int, int, int, int]] = []
    for row_index in range(question_count):
        top = _row_top(crop_offset_y, row_index)
        bottom = top + ROW_HEIGHT

        bottom_tick_x1 = faint_tick_x1 if row_index in faint_row_indices else normal_tick_x1

        cv2.rectangle(image, (TICK_X0, top), (normal_tick_x1, top + TICK_THICKNESS), (0, 0, 0), -1)
        cv2.rectangle(image, (TICK_X0, bottom), (bottom_tick_x1, bottom + TICK_THICKNESS), (0, 0, 0), -1)

        for col_index in range(choice_count):
            x1 = COL_START_X + col_index * COL_SPACING
            expected_boxes.append((x1, top, COL_WIDTH, ROW_HEIGHT))

    # Vertical column lines + outer left/right frame (stripped by the detector)
    grid_top = crop_offset_y
    grid_bottom = last_row_bottom + 10

    cv2.rectangle(image, (OUTER_LEFT_X, grid_top), (OUTER_LEFT_X + TICK_THICKNESS, grid_bottom), (0, 0, 0), -1)
    cv2.rectangle(image, (outer_right_x, grid_top), (outer_right_x + TICK_THICKNESS, grid_bottom), (0, 0, 0), -1)

    for col_index in range(choice_count):
        x1 = COL_START_X + col_index * COL_SPACING
        x2 = x1 + COL_WIDTH
        cv2.rectangle(image, (x1, grid_top), (x1 + TICK_THICKNESS, grid_bottom), (0, 0, 0), -1)
        cv2.rectangle(image, (x2, grid_top), (x2 + TICK_THICKNESS, grid_bottom), (0, 0, 0), -1)

    return image, expected_boxes


def rotate_image(image: np.ndarray, angle_degrees: float) -> np.ndarray:
    """Rotate an image in place (same output size) around its center, white-filled borders."""
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (width, height),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )

