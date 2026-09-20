import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from app import service, template_generator
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

@app.get("/templates/{question_count}")
async def get_template_endpoint(question_count: int, number_of_choices: int = 4, exam_title: str = "Exam Title"):
    try:
        zip_bytes = template_generator.build_template_zip_bytes(question_count, number_of_choices, exam_title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=template_{question_count}.zip"},
    )

@app.post("/grade/")
async def grade_endpoint(
    list_of_images: List[UploadFile] = File(...),
    config_json: UploadFile = File(...),
    fill_threshold: float = Form(0.5),
):
    if not list_of_images:
        raise HTTPException(status_code=400, detail="Please upload at least one exam image.")
    if not 0.0 <= fill_threshold <= 1.0:
        raise HTTPException(status_code=400, detail="Fill threshold must be between 0.0 and 1.0.")

    job_id = await service.start_grading_job(
        list_of_images,
        config_json,
        fill_threshold=fill_threshold,
    )

    return {"job_id": job_id}


@app.get("/grade/{job_id}/progress")
async def grade_progress_endpoint(job_id: str):
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Grading job not found. It may have expired or the id is invalid.")

    return {
        "status": job.status,
        "processed": job.processed,
        "total": job.total,
        "error": job.error,
        "failed_images": job.failed_images,
    }


@app.get("/grade/{job_id}/result")
async def grade_result_endpoint(job_id: str):
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Grading job not found. It may have expired or the id is invalid.")

    if job.status in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Grading is still in progress. Please wait for it to finish.")

    if job.status == "error":
        detail = job.error or "The uploaded images couldn't be graded. Please try again."
        service.delete_job(job_id)
        raise HTTPException(status_code=500, detail=detail)

    assert job.zip_bytes is not None
    zip_bytes = job.zip_bytes
    service.delete_job(job_id)

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=grade_results.zip"},
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
