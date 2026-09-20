"""Opt-in regression check against a local folder of real scanned answer sheets.

Not run by default (see `manual_dataset` marker in pytest.ini). Point
AGT_MANUAL_DATASET_DIR at a folder of scanned images to run it:

    AGT_MANUAL_DATASET_DIR="/path/to/sheets" pytest -m manual_dataset -v

Verifies that the full Grader pipeline (grid detection + per-choice fill
confidence) identifies every expected row/column ("cell") on each sampled
sheet, without requiring a real answer key (a dummy config is used since
this test only cares about detection completeness, not scoring).
"""
import os
from pathlib import Path

import pytest

from grader import Grader

EXPECTED_QUESTIONS = int(os.environ.get("AGT_MANUAL_DATASET_QUESTIONS", 30))
EXPECTED_CHOICES = int(os.environ.get("AGT_MANUAL_DATASET_CHOICES", 4))
SAMPLE_SIZE = int(os.environ.get("AGT_MANUAL_DATASET_SAMPLE_SIZE", 12))

EXPECTED_LETTERS = ["A", "B", "C", "D", "E", "F"][:EXPECTED_CHOICES]


def _dataset_dir():
    dataset_dir = os.environ.get("AGT_MANUAL_DATASET_DIR")
    if not dataset_dir:
        return None
    path = Path(dataset_dir)
    return path if path.is_dir() else None


def _sample_images(dataset_dir: Path, count: int):
    """Pick `count` images evenly spread across the sorted directory listing."""
    images = sorted(
        p for p in dataset_dir.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )
    if len(images) <= count:
        return images
    step = len(images) / count
    return [images[int(i * step)] for i in range(count)]


@pytest.mark.manual_dataset
def test_full_grid_and_choices_detected_on_real_scanned_sheets():
    dataset_dir = _dataset_dir()
    if dataset_dir is None:
        pytest.skip("Set AGT_MANUAL_DATASET_DIR to a folder of scanned sheets to run this check.")

    sample_images = _sample_images(dataset_dir, SAMPLE_SIZE)
    assert len(sample_images) >= 10, "Need at least 10 sample images for this check."

    dummy_config = {i: "A" for i in range(1, EXPECTED_QUESTIONS + 1)}
    grader = Grader(debug=False)

    failures = []
    for image_path in sample_images:
        image_bytes = image_path.read_bytes()
        try:
            result = grader.grade(image_path.name, image_bytes, dummy_config)
        except Exception as exc:
            failures.append(f"{image_path.name}: raised {exc!r}")
            continue

        if result.total_questions != EXPECTED_QUESTIONS:
            failures.append(
                f"{image_path.name}: expected {EXPECTED_QUESTIONS} questions, got {result.total_questions}"
            )
        if len(result.per_question) != EXPECTED_QUESTIONS:
            failures.append(
                f"{image_path.name}: expected {EXPECTED_QUESTIONS} graded rows, got {len(result.per_question)}"
            )
        mismatched_questions = [
            box_result.question for box_result in result.per_question
            if set(box_result.confidences.keys()) != set(EXPECTED_LETTERS)
        ]
        if mismatched_questions:
            sample_found = sorted(result.per_question[0].confidences.keys())
            failures.append(
                f"{image_path.name}: {len(mismatched_questions)} question(s) with wrong choice count "
                f"(expected {EXPECTED_LETTERS}, e.g. found {sample_found}), questions={mismatched_questions[:5]}..."
            )

    assert not failures, "Cell/grid detection mismatches:\n" + "\n".join(failures)
