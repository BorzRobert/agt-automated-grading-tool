from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from config_loader import load_config_from_json_bytes
from grader import Grader
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Automated Grading Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

grader = Grader(debug=True)

@app.post("/grade/")
async def grade_endpoint(
    image: UploadFile = File(...),
    config_json: UploadFile = File(...)
):
    image_bytes = await image.read()
    config_bytes = await config_json.read()
    try:
        cfg = load_config_from_json_bytes(config_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")
    try:
        result = grader.grade(image_bytes, cfg.correct_answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")
    return JSONResponse(content=result.dict())

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
