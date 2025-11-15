from typing import List, Dict

from app.utils import load_image_from_bytes, compute_fill_confidence
from image_processor import ImageProcessor
from models import BoxResult, GradeResult

LETTER_MAP = ["A", "B", "C", "D", "E", "F"]

class Grader:
    def __init__(self, debug):
        self.image_processor = ImageProcessor(debug=debug)
        self.debug = debug

    def grade(self, image_name: str, image_bytes: bytes, configuration: dict) -> GradeResult:
        image = load_image_from_bytes(image_bytes)
        boxes, grayscale_image, number_of__questions, number_of_choices = self.image_processor.detect_guided_boxes(image_name, image)

        # Group boxes by rows
        tolerance = 10 # vertical tolerance for two boxes to be considered in the same row
        boxes_sorted = sorted(boxes, key=lambda b: (b[1], b[0])) # sort all boxes by top left corner
        rows = []
        for box in boxes_sorted:
            x, y, w, h = box
            placed = False
            for r in rows:
                if abs(r[0][1] - y) <= tolerance:
                    r.append(box)
                    placed = True
                    break
            if not placed:
                rows.append([box])
        rows = [sorted(r, key=lambda b: b[0]) for r in sorted(rows, key=lambda r: r[0][1])]

        question_boxes = rows[:number_of__questions]

        per_question_results = []
        correct_count = 0
        minimum_confidence = 0.5

        for question_index, row in enumerate(question_boxes, start=1):
            letter_confidence: Dict[str, float] = {}
            selected_letters: List[str] = []

            for current_index, box in enumerate(row):
                if current_index >= number_of_choices:
                    break
                letter = LETTER_MAP[current_index] if current_index < len(LETTER_MAP) else f"Col{current_index+1}"
                x, y, w, h = box
                pad = int(min(w, h) * 0.15)
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1, y1 = x + w + pad, y + h + pad
                region_of_interest_gray = grayscale_image[y0:y1, x0:x1]
                confidence = compute_fill_confidence(region_of_interest_gray)
                letter_confidence[letter] = confidence
                if confidence > minimum_confidence:
                    selected_letters.append(letter)

            correct_answer = configuration.get(question_index)
            if correct_answer is None:
                is_correct = None
            else:
                correct_set = {correct_answer} if isinstance(correct_answer, str) else set(correct_answer)
                selected_set = set(selected_letters)
                is_correct = selected_set == correct_set
                if is_correct:
                    correct_count += 1

            per_question_results.append(BoxResult(
                question=question_index,
                selected=selected_letters,
                is_correct=is_correct,
                confidences=letter_confidence
            ))

        score_percent = (correct_count / number_of__questions) * 100.0 if number_of__questions else 0.0

        return GradeResult(
            total_questions=number_of__questions,
            correct_count=correct_count,
            score_percent=round(score_percent, 4),
            per_question=per_question_results,
            debug={
                "boxes_detected": len(boxes),
                "rows": len(rows),
                "questions_detected": number_of__questions,
                "choices_detected": number_of_choices
            } if self.debug else None
        )
