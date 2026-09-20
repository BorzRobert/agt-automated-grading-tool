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

## Deployment

The app is designed to be deployed with the frontend and backend hosted separately.

### Backend (Render)

The backend ships with a `server/Dockerfile` and a root `render.yaml` blueprint, so it can be deployed to [Render](https://render.com) as a Dockerized Web Service with no extra setup:

1. Create a new "Blueprint" service on Render pointing at this repository (it will pick up `render.yaml` automatically), or manually create a Web Service with environment "Docker" and Dockerfile path `server/Dockerfile`.
2. Set the `ALLOWED_ORIGINS` environment variable on the service to a comma-separated list of the frontend origin(s) allowed to call the API, e.g. `https://<user>.github.io`.
3. Render builds and deploys automatically on every push to `main`. A `GET /health` endpoint is used for the service's health check.

> **Note:** the free Render tier spins the service down after inactivity, so the first request after idling will be slow (cold start) while the container restarts.

### Frontend (GitHub Pages)

A GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) builds the Vite app and publishes `frontend/dist` to GitHub Pages on every push to `main`:

1. Enable GitHub Pages for this repository (Settings → Pages → Source: GitHub Actions).
2. Set a repository variable `VITE_API_BASE_URL` (Settings → Secrets and variables → Actions → Variables) to the deployed Render backend URL, e.g. `https://agt-server.onrender.com`.
3. Push to `main` — the workflow builds and deploys the site automatically.

### Wiring frontend and backend together

Once both are deployed, set `ALLOWED_ORIGINS` on Render to the live frontend URL(s), and `VITE_API_BASE_URL` in the frontend build to the live Render URL, so the two deployments can talk to each other.

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

## License

This project is licensed under the [MIT License](LICENSE).
