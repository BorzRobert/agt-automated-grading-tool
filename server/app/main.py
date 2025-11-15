from fastapi import FastAPI, UploadFile, File, HTTPException

from app import service
from grader import Grader
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import List
app = FastAPI(title="Automated Grading Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

grader = Grader(debug=False)

@app.post("/grade/")
async def grade_endpoint(
    list_of_images: List[UploadFile] = File(...),
    config_json: UploadFile = File(...)
):
    list_of_results = await service.grade_images(list_of_images, config_json)

    if not list_of_results:
        print(f"[DEBUG]The uploaded images couldn't be graded! Please try again!")
        raise HTTPException(status_code=500, detail=f"The uploaded images couldn't be graded! Please try again!")

    zip_with_results = service.get_zip_containing_results(list_of_results, "./debug_results")

    return zip_with_results

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
