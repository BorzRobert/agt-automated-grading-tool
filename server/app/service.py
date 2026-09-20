import asyncio
import json
import os
import uuid
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fastapi import UploadFile, HTTPException

from app.config_loader import load_config_from_json_bytes
from app.grader import Grader

grader = Grader(debug=True)


@dataclass
class JobState:
    status: str = "pending"  # pending -> running -> done | error
    processed: int = 0
    total: int = 0
    error: Optional[str] = None
    failed_images: List[str] = field(default_factory=list)
    zip_bytes: Optional[bytes] = None


_jobs: Dict[str, JobState] = {}
# Keeps references to background tasks so they are not garbage-collected mid-run.
_background_tasks: Dict[str, asyncio.Task] = {}


def get_job(job_id: str) -> Optional[JobState]:
    return _jobs.get(job_id)


def delete_job(job_id: str) -> None:
    _jobs.pop(job_id, None)
    _background_tasks.pop(job_id, None)


async def start_grading_job(
    list_of_images: List[UploadFile],
    config_json: UploadFile,
    fill_threshold: float = 0.5,
) -> str:
    """Reads all uploads into memory, validates the config, and schedules a
    background job that reports progress via `get_job`."""
    config_bytes = await config_json.read()
    try:
        configuration_file = load_config_from_json_bytes(config_bytes)
    except Exception as e:
        print(f"[DEBUG]The provided configuration file is invalid: {e}")
        raise HTTPException(status_code=400, detail=f"The configuration file could not be read ({e}). Please upload a valid JSON configuration.")

    images_data: List[Tuple[str, bytes]] = []
    for image in list_of_images:
        images_data.append((image.filename or "unnamed_image", await image.read()))

    job_id = uuid.uuid4().hex
    _jobs[job_id] = JobState(status="pending", total=len(images_data))
    task = asyncio.create_task(
        _run_grading_job(job_id, images_data, configuration_file.correct_answers, fill_threshold)
    )
    _background_tasks[job_id] = task
    return job_id


async def _run_grading_job(
    job_id: str,
    images_data: List[Tuple[str, bytes]],
    correct_answers,
    fill_threshold: float,
) -> None:
    job = _jobs[job_id]
    job.status = "running"

    list_of_results = []
    failed_images: List[str] = []
    for filename, image_bytes in images_data:
        try:
            result = await asyncio.to_thread(
                grader.grade,
                filename,
                image_bytes,
                correct_answers,
                fill_threshold=fill_threshold,
            )
            list_of_results.append(
                {"Candidate": filename, "Grade": result.score_percent, "Extended result": json.dumps(result.model_dump())})
        except Exception as e:
            print(f"[DEBUG]Error encountered for image={filename}: {e}")
            failed_images.append(f"{filename} ({e})")
        finally:
            job.processed += 1

    if not list_of_results:
        job.status = "error"
        job.error = (
            "None of the uploaded images could be graded. "
            + (
                f"Details: {'; '.join(failed_images)}"
                if failed_images
                else "Please check that the images clearly show the answer grid and match the uploaded configuration."
            )
        )
        return

    try:
        zip_bytes = build_zip_bytes(list_of_results, "./debug_results")
        clear_files_from_directory("./debug_results")
    except Exception as e:
        print(f"[DEBUG]Failed to build the results archive: {e}")
        job.status = "error"
        job.error = f"Grading finished but the results file could not be built ({e}). Please try again."
        return

    job.zip_bytes = zip_bytes
    job.failed_images = failed_images
    job.status = "done"

def clear_files_from_directory(folder_path: str):
    if not os.path.exists(folder_path):
        print(f"[DEBUG]Error: Directory not found at {folder_path}")
        return

    for item_name in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item_name)
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
        except Exception as e:
            print(f"[DEBUG]Failed to delete {item_path}. Reason: {e}")

def build_zip_bytes(list_of_results: list[dict], debug_results_directory: str) -> bytes:
    df = pd.DataFrame(list_of_results)
    df_sorted_by_grade = df.sort_values(by=["Grade"], ascending=False)

    excel_bytes = BytesIO()
    with pd.ExcelWriter(excel_bytes, engine="openpyxl") as writer:
        df_sorted_by_grade.to_excel(writer, index=False, sheet_name="Grades")
    excel_bytes.seek(0)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:

        # Add Excel file
        zipf.writestr("Grades.xlsx", excel_bytes.getvalue())

        # Add all images
        if os.path.isdir(debug_results_directory):
            for filename in os.listdir(debug_results_directory):
                file_path = os.path.join(debug_results_directory, filename)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=f"debug_results/{filename}")

    return zip_buffer.getvalue()
