import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

from app import service
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import List
app = FastAPI(title="Automated Grading Tool")

# Comma-separated list of allowed origins, e.g. "https://user.github.io,https://app.vercel.app"
_default_origins = "http://127.0.0.1:5173,http://localhost:5173"
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/grade/")
async def grade_endpoint(
    list_of_images: List[UploadFile] = File(...),
    config_json: UploadFile = File(...),
    fill_threshold: float = Form(0.5),
):
    if not 0.0 <= fill_threshold <= 1.0:
        raise HTTPException(status_code=400, detail="fill_threshold must be between 0.0 and 1.0")

    list_of_results = await service.grade_images(
        list_of_images,
        config_json,
        fill_threshold=fill_threshold,
    )

    if not list_of_results:
        print(f"[DEBUG]The uploaded images couldn't be graded! Please try again!")
        raise HTTPException(status_code=500, detail=f"The uploaded images couldn't be graded! Please try again!")

    zip_with_results = service.get_zip_containing_results(list_of_results, "./debug_results")
    service.clear_files_from_directory("./debug_results")

    return zip_with_results

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
