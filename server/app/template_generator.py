"""Generate blank answer-sheet templates compatible with `ImageProcessor`.

Mirrors the visual/geometric conventions of the checked-in reference
templates (`templates/20`, `templates/30`): a title area followed by a
full-width separator line, vertical "tick" marks bracketing each answer
column (reinforcing vertical-line detection on an otherwise blank sheet),
an outer grid frame with column letter headers, and per-question rows
made up of a left-margin horizontal tick "comb" plus one checkbox per
choice.

Every dimension is defined in inches and rendered at a fixed print DPI so
box/gap sizes stay comfortably above `ImageProcessor`'s detection
thresholds (`MINIMUM_LINE_GAP`, `LINE_MAX_THICKNESS`) regardless of
`question_count`. Nothing is written to disk - callers get raster bytes,
PDF bytes, or a ready-to-download ZIP, all built in-memory.
"""
import json
import zipfile
from io import BytesIO
from typing import Dict

import cv2
import numpy as np
from PIL import Image

MIN_QUESTIONS = 5
MAX_QUESTIONS = 30
MIN_CHOICES = 2
MAX_CHOICES = 6

LETTER_MAP = ["A", "B", "C", "D", "E", "F"]

DPI = 300
PAGE_WIDTH_IN = 8.5
PAGE_HEIGHT_IN = 11.0

# -- Geometry (inches). Chosen so that, at DPI above, the row gap and
# checkbox side both stay well clear of ImageProcessor.MINIMUM_LINE_GAP
# (20px) / LINE_MAX_THICKNESS (26px), and the full 30-question grid still
# fits within the Letter page height.
MARGIN_TOP_IN = 0.4
HEADER_TEXT_HEIGHT_IN = 0.6
HEADER_LEFT_MARGIN_IN = 4.75
GAP_BEFORE_SEPARATOR_IN = 0.15
SEPARATOR_THICKNESS_IN = 0.02
GAP_AFTER_SEPARATOR_IN = 0.15
TICK_HEIGHT_IN = 0.35
GAP_BEFORE_FRAME_IN = 0.08
HEADER_LETTERS_ZONE_IN = 0.35
ROW_START_PAD_IN = 0.05
ROW_PITCH_IN = 0.28
BOX_SIDE_IN = 0.18
FRAME_BOTTOM_PAD_IN = 0.1

FRAME_LEFT_X_IN = 1.7
NUMBERING_ZONE_WIDTH_IN = 0.5
COL_START_PAD_IN = 0.05
COL_PITCH_IN = 0.75
FRAME_RIGHT_PAD_IN = 0.15

# Small filled squares at the four page corners. Their only purpose is to
# pin the convex hull used by ImageProcessor._deskew's cv2.minAreaRect to
# the page's true (axis-aligned) bounding box: without them, a sparse
# grid of strokes can have a minimum-area rotated bounding rect that's
# slightly off-axis (a geometric artifact, not a real skew), causing a
# spurious "corrective" rotation on an already-straight generated sheet.
# Kept within ImageProcessor.PAGE_EDGE_MARGIN of each edge so they're
# excluded from vertical-line candidate search; any stray contribution to
# horizontal-line detection is cleaned up by ImageProcessor's own
# outlier-line trimming (they sit far past the last real grid row).
CORNER_MARK_MARGIN_IN = 0.02
CORNER_MARK_SIZE_IN = 0.03


def _px(inches: float) -> int:
    return int(round(inches * DPI))


def _validate(question_count: int, number_of_choices: int) -> None:
    if not (MIN_QUESTIONS <= question_count <= MAX_QUESTIONS):
        raise ValueError(
            f"question_count must be between {MIN_QUESTIONS} and {MAX_QUESTIONS} (got {question_count})."
        )
    if not (MIN_CHOICES <= number_of_choices <= MAX_CHOICES):
        raise ValueError(
            f"number_of_choices must be between {MIN_CHOICES} and {MAX_CHOICES} (got {number_of_choices})."
        )


def generate_template_image(
    question_count: int,
    number_of_choices: int = 4,
    exam_title: str = "Exam Title",
) -> np.ndarray:
    """Render a blank answer sheet as a BGR raster image."""
    _validate(question_count, number_of_choices)

    font = cv2.FONT_HERSHEY_SIMPLEX
    page_width = _px(PAGE_WIDTH_IN)
    page_height = _px(PAGE_HEIGHT_IN)
    image = np.full((page_height, page_width, 3), 255, dtype=np.uint8)

    # Corner registration marks (see constant docstring above).
    mark_margin = _px(CORNER_MARK_MARGIN_IN)
    mark_size = _px(CORNER_MARK_SIZE_IN)
    for corner_x in (mark_margin, page_width - mark_margin - mark_size):
        for corner_y in (mark_margin, page_height - mark_margin - mark_size):
            cv2.rectangle(
                image, (corner_x, corner_y), (corner_x + mark_size, corner_y + mark_size), (0, 0, 0), -1
            )

    # Header labels sit to the right of the page center.
    header_left_x = _px(HEADER_LEFT_MARGIN_IN)
    header_lines = ["Name:", exam_title]
    line_height = _px(HEADER_TEXT_HEIGHT_IN) // len(header_lines)
    for i, text in enumerate(header_lines):
        y = _px(MARGIN_TOP_IN) + (i + 1) * line_height
        cv2.putText(image, text, (header_left_x, y), font, 0.8, (0, 0, 0), 2, cv2.LINE_AA)

    # Full-width title/answers separator line.
    separator_y = _px(MARGIN_TOP_IN + HEADER_TEXT_HEIGHT_IN + GAP_BEFORE_SEPARATOR_IN)
    separator_thickness = max(2, _px(SEPARATOR_THICKNESS_IN))
    cv2.rectangle(image, (0, separator_y), (page_width, separator_y + separator_thickness), (0, 0, 0), -1)

    # Column boundary tick marks: reinforce vertical-line detection signal
    # for an otherwise-blank sheet (no fill ink to bridge box edges yet).
    tick_top_y = separator_y + separator_thickness
    frame_top_y = tick_top_y + _px(TICK_HEIGHT_IN)
    tick_bottom_y = frame_top_y
    frame_left_x = _px(FRAME_LEFT_X_IN)
    col_start_x = _px(FRAME_LEFT_X_IN + NUMBERING_ZONE_WIDTH_IN + COL_START_PAD_IN)
    col_pitch = _px(COL_PITCH_IN)
    box_side = _px(BOX_SIDE_IN)

    for j in range(number_of_choices):
        x_left = col_start_x + j * col_pitch
        x_right = x_left + box_side
        cv2.line(image, (x_left, tick_top_y), (x_left, tick_bottom_y), (0, 0, 0), 2)
        cv2.line(image, (x_right, tick_top_y), (x_right, tick_bottom_y), (0, 0, 0), 2)

    frame_right_x = col_start_x + (number_of_choices - 1) * col_pitch + box_side + _px(FRAME_RIGHT_PAD_IN)

    # Column letter headers (A, B, C, ...), centered above each column.
    header_letters_baseline_y = frame_top_y + int(_px(HEADER_LETTERS_ZONE_IN) * 0.75)
    for j in range(number_of_choices):
        letter = LETTER_MAP[j]
        (text_width, _), _ = cv2.getTextSize(letter, font, 0.9, 2)
        x_center = col_start_x + j * col_pitch + box_side // 2
        cv2.putText(
            image, letter, (x_center - text_width // 2, header_letters_baseline_y),
            font, 0.9, (0, 0, 0), 2, cv2.LINE_AA,
        )

    # Per-question rows: left-margin comb ticks, row number, and checkboxes.
    row_start_y = frame_top_y + _px(HEADER_LETTERS_ZONE_IN + ROW_START_PAD_IN)
    row_pitch = _px(ROW_PITCH_IN)
    comb_line_length = frame_left_x

    for i in range(question_count):
        row_top = row_start_y + i * row_pitch
        row_bottom = row_top + box_side

        cv2.line(image, (0, row_top), (comb_line_length, row_top), (0, 0, 0), 2)
        cv2.line(image, (0, row_bottom), (comb_line_length, row_bottom), (0, 0, 0), 2)

        label = f"{i + 1}."
        (_, label_height), _ = cv2.getTextSize(label, font, 0.7, 2)
        label_x = frame_left_x + _px(0.1)
        label_y = row_top + (box_side + label_height) // 2
        cv2.putText(image, label, (label_x, label_y), font, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

        for j in range(number_of_choices):
            x_left = col_start_x + j * col_pitch
            cv2.rectangle(image, (x_left, row_top), (x_left + box_side, row_bottom), (0, 0, 0), 2)

    frame_bottom_y = row_start_y + (question_count - 1) * row_pitch + box_side + _px(FRAME_BOTTOM_PAD_IN)

    # Outer grid frame.
    cv2.rectangle(image, (frame_left_x, frame_top_y), (frame_right_x, frame_bottom_y), (0, 0, 0), 4)

    return image


def generate_template_pdf_bytes(
    question_count: int,
    number_of_choices: int = 4,
    exam_title: str = "Exam Title",
) -> bytes:
    """Render the template and encode it as a print-ready, A4/Letter-scaled PDF."""
    image = generate_template_image(question_count, number_of_choices, exam_title)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)

    buffer = BytesIO()
    pil_image.save(buffer, format="PDF", resolution=DPI)
    return buffer.getvalue()


def generate_blank_config(question_count: int) -> Dict:
    """Blank config skeleton (question numbers 1..N), valid against `GradeRequestConfig` as-is."""
    return {"correct_answers": {str(i): "A" for i in range(1, question_count + 1)}}


def build_template_zip_bytes(
    question_count: int,
    number_of_choices: int = 4,
    exam_title: str = "Exam Title",
) -> bytes:
    """Build an in-memory ZIP containing the generated PDF plus a blank config skeleton."""
    pdf_bytes = generate_template_pdf_bytes(question_count, number_of_choices, exam_title)
    config_json = json.dumps(generate_blank_config(question_count), indent=2)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr(f"template_{question_count}.pdf", pdf_bytes)
        zipf.writestr("config.json", config_json)

    return zip_buffer.getvalue()
