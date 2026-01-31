# Automated Grading Tool (AGT)

A full-stack application for automatically grading multiple-answer question sheets from scanned images. Combines a FastAPI + OpenCV backend with a React + TypeScript + Vite frontend.

## Features

### Backend
✅ Detects and warps the answer sheet  
✅ Detects filled answer boxes  
✅ Supports multiple correct answers per question  
✅ Returns detailed JSON results with confidences and correctness  
✅ Modular and easy to extend  

### Frontend
✅ Upload scanned answer sheet images  
✅ Submit images to the grading backend  
✅ Download detailed grading results with confidence scores  
✅ Clean and responsive user interface  

## Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 14 or higher
- npm or yarn

### Backend Setup

```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Development

### Running the Backend

```bash
cd server
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m app.main
```

The API will be available at `http://localhost:8000`

### Running the Frontend

```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`

---

## Usage

1. Start the backend server
2. Start the frontend development server
3. Open your browser to `http://localhost:5173`
4. Upload a scanned answer sheet image
5. Submit for grading
6. Download the detailed results with confidence scores

---

## Configuration

Answer sheet templates and configurations are located in the `templates/` directory. Each template includes an `example_config.json` file that defines the answer sheet structure and correct answers.
