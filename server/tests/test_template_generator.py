import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from image_processor import ImageProcessor
from main import app
from template_generator import (
    MAX_CHOICES,
    MAX_QUESTIONS,
    MIN_CHOICES,
    MIN_QUESTIONS,
    build_template_zip_bytes,
    generate_blank_config,
    generate_template_image,
    generate_template_pdf_bytes,
    _px,
    PAGE_WIDTH_IN,
    PAGE_HEIGHT_IN,
)


class TestGenerateTemplateImage:
    @pytest.mark.parametrize("question_count", [MIN_QUESTIONS, 10, 20, MAX_QUESTIONS])
    def test_image_dimensions_match_expected_page_size(self, question_count):
        image = generate_template_image(question_count)
        assert image.shape == (_px(PAGE_HEIGHT_IN), _px(PAGE_WIDTH_IN), 3)

    @pytest.mark.parametrize(
        "question_count,number_of_choices",
        [
            (MIN_QUESTIONS, MIN_CHOICES),
            (MIN_QUESTIONS, 4),
            (MIN_QUESTIONS, MAX_CHOICES),
            (10, 4),
            (20, 6),
            (MAX_QUESTIONS, 4),
            (MAX_QUESTIONS, MAX_CHOICES),
        ],
    )
    def test_generated_template_is_detector_compatible(self, question_count, number_of_choices):
        """A freshly generated (unfilled) template must round-trip through
        the real detector with the exact question/choice counts it was
        generated for - this is what guarantees a filled-in scan of a
        printed template will actually be gradable."""
        image = generate_template_image(question_count, number_of_choices)
        processor = ImageProcessor(debug=False)

        boxes, _, detected_questions, detected_choices = processor.detect_guided_boxes(
            f"template_{question_count}_{number_of_choices}.png", image
        )

        assert detected_questions == question_count
        assert detected_choices == number_of_choices
        assert len(boxes) == question_count * number_of_choices

    @pytest.mark.parametrize("invalid_question_count", [MIN_QUESTIONS - 1, MAX_QUESTIONS + 1])
    def test_out_of_range_question_count_rejected(self, invalid_question_count):
        with pytest.raises(ValueError):
            generate_template_image(invalid_question_count)

    @pytest.mark.parametrize("invalid_choice_count", [MIN_CHOICES - 1, MAX_CHOICES + 1])
    def test_out_of_range_choice_count_rejected(self, invalid_choice_count):
        with pytest.raises(ValueError):
            generate_template_image(10, invalid_choice_count)


class TestGenerateTemplatePdfAndConfig:
    def test_pdf_bytes_start_with_pdf_header(self):
        pdf_bytes = generate_template_pdf_bytes(10)
        assert pdf_bytes.startswith(b"%PDF-")

    def test_blank_config_has_placeholder_for_every_question(self):
        config = generate_blank_config(5)
        assert config == {"correct_answers": {"1": "A", "2": "A", "3": "A", "4": "A", "5": "A"}}

    def test_zip_contains_pdf_and_config(self):
        zip_bytes = build_template_zip_bytes(10, 4)
        zf = zipfile.ZipFile(BytesIO(zip_bytes))

        assert set(zf.namelist()) == {"template_10.pdf", "config.json"}
        assert zf.read("template_10.pdf").startswith(b"%PDF-")


class TestTemplateEndpoint:
    def setup_method(self):
        self.client = TestClient(app)

    @pytest.mark.parametrize("question_count", [MIN_QUESTIONS, MAX_QUESTIONS])
    def test_in_range_question_count_returns_valid_zip(self, question_count):
        response = self.client.get(f"/templates/{question_count}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        zf = zipfile.ZipFile(BytesIO(response.content))
        assert set(zf.namelist()) == {f"template_{question_count}.pdf", "config.json"}

    @pytest.mark.parametrize("invalid_question_count", [MIN_QUESTIONS - 1, MAX_QUESTIONS + 1])
    def test_out_of_range_question_count_returns_400(self, invalid_question_count):
        response = self.client.get(f"/templates/{invalid_question_count}")
        assert response.status_code == 400

    @pytest.mark.parametrize("invalid_choice_count", [MIN_CHOICES - 1, MAX_CHOICES + 1])
    def test_out_of_range_choice_count_returns_400(self, invalid_choice_count):
        response = self.client.get("/templates/10", params={"number_of_choices": invalid_choice_count})
        assert response.status_code == 400
