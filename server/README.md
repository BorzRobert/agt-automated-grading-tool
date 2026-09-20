# Automated Grading Tool

A FastAPI + OpenCV-based application for automatically grading multiple-answer question sheets from scanned images.

---

## Features
✅ Detects and warps the answer sheet  
✅ Detects filled answer boxes  
✅ Supports multiple correct answers per question  
✅ Returns detailed JSON results with confidences and correctness  
✅ Modular and easy to extend  

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Testing

Unit tests use `pytest` and synthetically generated grid images (no external
assets required), covering the perfectly-aligned regression baseline, rotated
scans (deskew), and faint/broken guide lines (adaptive threshold fallback):

```bash
cd server
pytest -v
```

Real scanned sample images are intentionally **not** committed to this repo
(privacy/size). If you have a local dataset of scanned sheets, point
`AGT_MANUAL_DATASET_DIR` at it and run tests marked `manual_dataset` (once
added) to spot-check detection success rate against real photos:

```bash
AGT_MANUAL_DATASET_DIR="/path/to/your/scanned/sheets" pytest -m manual_dataset -v
```

