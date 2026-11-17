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

## Documentation

- [Installation](docs/installation.md): prerequisites and backend/frontend setup
- [Development](docs/development.md): running the backend and frontend locally
- [Usage](docs/usage.md): grading an answer sheet end to end
- [Configuration](docs/configuration.md): answer sheet templates
- [Deployment](docs/deployment.md): Render (backend) and GitHub Pages (frontend)
- [Contributing](docs/contributing.md): branch and commit naming rules and local Git hooks

## License

This project is licensed under the [MIT License](LICENSE).
