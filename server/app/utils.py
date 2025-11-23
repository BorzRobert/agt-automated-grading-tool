import cv2
import numpy as np


def load_image_from_bytes(data: bytes) -> np.ndarray:
    image_array = np.frombuffer(data, np.uint8)
    image_array_decoded = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image_array_decoded is None:
        raise ValueError("Could not decode image")
    return image_array_decoded

def compute_fill_confidence(region_of_interest_gray: np.ndarray) -> float:
    """Compute how filled a box is (0..1 scale)."""
    _, threshold = cv2.threshold(region_of_interest_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    black = np.count_nonzero(threshold == 0)
    total = threshold.size
    return float(black / total) if total > 0 else 0.0
