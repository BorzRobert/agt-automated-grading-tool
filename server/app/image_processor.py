import cv2
import numpy as np
from typing import List, Tuple

class ImageProcessor:
    """Detect and extract answer boxes from the sheet image."""

    def __init__(self, debug=False):
        self.debug = debug

    def load_image_from_bytes(self, data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
        return img

    def find_main_sheet_contour(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Find the largest rectangular contour (exam sheet)."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        edged = cv2.Canny(blur, 50, 150)
        cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            raise RuntimeError("No contours found")
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        page_cnt = None
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                page_cnt = approx
                break
        if page_cnt is None:
            x, y, w, h = cv2.boundingRect(cnts[0])
            page_cnt = np.array([[[x,y]], [[x+w,y]], [[x+w,y+h]], [[x,y+h]]], dtype=np.int32)

        warped = self.four_point_transform(img, page_cnt.reshape(4,2))
        return warped, page_cnt

    def four_point_transform(self, image, pts):
        rect = self.order_points(pts)
        (tl, tr, br, bl) = rect
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def detect_mark_boxes(self, warped_img: np.ndarray, expected_questions:int=20, expected_choices:int=6):
        """Detects answer boxes and returns list of bounding boxes (x, y, w, h)."""
        gray = cv2.cvtColor(warped_img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 25, 10)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        h, w = gray.shape
        min_area = (w*h) * 0.0004
        max_area = (w*h) * 0.02
        for c in cnts:
            x, y, ww, hh = cv2.boundingRect(c)
            area = ww*hh
            ar = ww/float(hh) if hh > 0 else 0
            if area < min_area or area > max_area:
                continue
            if 0.6 <= ar <= 1.6:
                boxes.append((x,y,ww,hh))
        boxes_sorted = sorted(boxes, key=lambda b: (b[1], b[0]))
        return boxes_sorted, thresh

    def compute_fill_confidence(self, roi_gray: np.ndarray) -> float:
        """Compute how filled a box is (0..1 scale)."""
        _, th = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        black = np.count_nonzero(th == 0)
        total = th.size
        return float(black / total)
