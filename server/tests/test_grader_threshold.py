import asyncio
from io import BytesIO

import numpy as np
import pytest
from fastapi import HTTPException, UploadFile

import grader
from grader import Grader
from main import grade_endpoint


def test_fill_threshold_controls_selection(monkeypatch):
    image = np.zeros((20, 20), dtype=np.uint8)

    monkeypatch.setattr(grader, "load_image_from_bytes", lambda _: image)

    processor = type(
        "Processor",
        (),
        {
            "detect_guided_boxes": lambda self, image_name, loaded_image: (
                [(0, 0, 10, 10)],
                loaded_image,
                1,
                1,
            )
        },
    )()
    monkeypatch.setattr(grader, "compute_fill_confidence", lambda _: 0.5)

    low_threshold_grader = Grader(debug=False)
    low_threshold_grader.image_processor = processor
    low_threshold_result = low_threshold_grader.grade(
        "sheet.png", b"image", {1: "A"}, fill_threshold=0.3
    )
    high_threshold_grader = Grader(debug=False)
    high_threshold_grader.image_processor = processor
    high_threshold_result = high_threshold_grader.grade(
        "sheet.png", b"image", {1: "A"}, fill_threshold=0.7
    )

    assert low_threshold_result.per_question[0].selected == ["A"]
    assert high_threshold_result.per_question[0].selected == []
    assert low_threshold_result.score_percent == 100.0
    assert high_threshold_result.score_percent == 0.0


@pytest.mark.parametrize("invalid_threshold", [-0.1, 1.1])
def test_grade_endpoint_rejects_out_of_range_threshold(invalid_threshold):
    config = UploadFile(filename="config.json", file=BytesIO(b"{}"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(grade_endpoint([], config, invalid_threshold))

    assert exc_info.value.status_code == 400
    