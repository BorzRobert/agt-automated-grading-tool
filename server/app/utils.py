import numpy as np
import cv2
from typing import Tuple, List

def sort_contours_top_to_bottom(cnts, method="top-to-bottom"):
    bounding_boxes = [cv2.boundingRect(c) for c in cnts]
    cnts_bbs = sorted(zip(cnts, bounding_boxes), key=lambda b: (b[1][1], b[1][0]))
    cnts_sorted, bbs_sorted = zip(*cnts_bbs)
    return list(cnts_sorted), list(bbs_sorted)

def order_grid_cells(cells_centers: List[Tuple[int,int]], num_cols: int):
    centers = np.array(cells_centers)
    idxs = np.argsort(centers[:,1])
    centers_sorted = centers[idxs]
    rows = []
    for i in range(0, len(centers_sorted), num_cols):
        row = centers_sorted[i:i+num_cols]
        row = row[np.argsort(row[:,0])]
        rows.append([tuple(pt) for pt in row])
    return rows
