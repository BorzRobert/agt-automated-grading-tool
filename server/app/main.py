from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from config_loader import load_config_from_json_bytes
from grader import Grader
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
from io import BytesIO
from utils import extended_result_info
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
    list_of_images: List[UploadFile] = File(...),
    config_json: UploadFile = File(...)
):

    config_bytes = await config_json.read()
    try:
        configuration_file = load_config_from_json_bytes(config_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration file: {e}")

    list_of_results = []
    for image in list_of_images:
        image_bytes = await image.read()
        try:
            result = grader.grade(image_bytes, configuration_file.correct_answers)
            list_of_results.append({"Candidate": image.filename, "Grade": result.score_percent, "Extended result": extended_result_info(result)})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing error: {e}")

    df = pd.DataFrame(list_of_results)
    df_sorted_by_grade = df.sort_values(by=["Grade"], ascending=False)
    final_results = BytesIO()

    with pd.ExcelWriter(final_results, engine="openpyxl") as writer:
        df_sorted_by_grade.to_excel(writer, index=False, sheet_name="Grades")
    final_results.seek(0)

    return StreamingResponse(final_results)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
