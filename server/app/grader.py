from typing import List, Dict, Set
from image_processor import ImageProcessor
from models import BoxResult, GradeResult
import cv2

LETTER_MAP = ["A", "B", "C", "D", "E", "F"]

class Grader:
    def __init__(self, debug=False):
        self.ip = ImageProcessor(debug=debug)
        self.debug = debug

    def grade(self, image_bytes: bytes, config: dict) -> GradeResult:
        img = self.ip.load_image_from_bytes(image_bytes)
        warped, _ = self.ip.find_main_sheet_contour(img)
        boxes, _ = self.ip.detect_mark_boxes(warped, expected_questions=len(config), expected_choices=len(LETTER_MAP))

        # Group boxes into rows
        rows = []
        tol = 12
        boxes_sorted = sorted(boxes, key=lambda b: (b[1], b[0]))
        for b in boxes_sorted:
            x, y, w, h = b
            placed = False
            for r in rows:
                if abs(r[0][1] - y) <= tol:
                    r.append(b)
                    placed = True
                    break
            if not placed:
                rows.append([b])
        rows = [sorted(r, key=lambda b: b[0]) for r in sorted(rows, key=lambda r: r[0][1])]

        expected_questions = len(config)
        num_cols = max(len(r) for r in rows) if rows else 6
        q_boxes = [r[:num_cols] for r in rows[:expected_questions]]

        per_question_results = []
        correct_count = 0
        MIN_CONFIDENCE = 0.15

        for qi, row in enumerate(q_boxes, start=1):
            letter_conf: Dict[str, float] = {}
            selected_letters: List[str] = []

            for ci, b in enumerate(row):
                if ci >= len(LETTER_MAP):
                    break
                letter = LETTER_MAP[ci]
                x, y, w, h = b
                pad = int(min(w, h) * 0.15)
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1, y1 = x + w + pad, y + h + pad
                roi_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)[y0:y1, x0:x1]
                conf = self.ip.compute_fill_confidence(roi_gray)
                letter_conf[letter] = conf
                if conf > MIN_CONFIDENCE:
                    selected_letters.append(letter)

            correct_answer = config.get(qi)
            if correct_answer is None:
                is_correct = None
            else:
                if isinstance(correct_answer, str):
                    correct_set: Set[str] = {correct_answer}
                else:
                    correct_set: Set[str] = set(correct_answer)
                selected_set = set(selected_letters)
                is_correct = selected_set == correct_set
                if is_correct:
                    correct_count += 1

            per_question_results.append(BoxResult(
                question=qi,
                selected=selected_letters,
                is_correct=is_correct,
                confidences=letter_conf
            ))

        score_percent = (correct_count / expected_questions) * 100.0 if expected_questions else 0.0

        return GradeResult(
            total_questions=expected_questions,
            correct_count=correct_count,
            score_percent=round(score_percent, 2),
            per_question=per_question_results,
            debug={"boxes_detected": len(boxes), "rows": len(rows)} if self.debug else None
        )
