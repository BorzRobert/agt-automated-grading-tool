import json
import os
import zipfile
from io import BytesIO
from typing import List

import pandas as pd
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from app.config_loader import load_config_from_json_bytes
from app.grader import Grader

grader = Grader(debug=True)


async def grade_images(list_of_images: List[UploadFile], config_json: UploadFile):
    config_bytes = await config_json.read()
    try:
        configuration_file = load_config_from_json_bytes(config_bytes)
    except Exception as e:
        print(f"[DEBUG]The provided configuration file is invalid: {e}")
        raise HTTPException(status_code=400, detail=f"The provided configuration file is invalid: {e}")

    list_of_results = []
    for image in list_of_images:
        image_bytes = await image.read()
        try:
            result = grader.grade(image.filename, image_bytes, configuration_file.correct_answers)
            list_of_results.append(
                {"Candidate": image.filename, "Grade": result.score_percent, "Extended result": json.dumps(result.model_dump())})
        except Exception as e:
            print(f"[DEBUG]Error encountered for image={image.filename}: {e}")

    return list_of_results

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

def get_zip_containing_results(list_of_results: list[dict], debug_results_directory: str):
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

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=grade_results.zip"}
    )
