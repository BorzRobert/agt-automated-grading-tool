import React, { useState } from "react";
import { gradeExam } from "../api";



const downloadFile = (fileBlob: Blob) =>{
      const url = window.URL.createObjectURL(fileBlob);
      const downloadLink = document.createElement("a");
      downloadLink.href = url;
      downloadLink.download = "Grades.xlsx";
      downloadLink.click();
      window.URL.revokeObjectURL(url);
}
export const UploadForm: React.FC = () => {
  const [listOfImages, setListOfImages] = useState<File[]>([]);
  const [config, setConfig] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (listOfImages.length === 0 || !config) {
      setError("Please upload both the exam images and configuration JSON.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await gradeExam(listOfImages, config);
      downloadFile(res);
    } catch (err) {
      console.error(err);
      setError("Error while grading. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2 style={{color: "lightgray"}}>Automated Grading Tool</h2>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label>Exam Images (.jpg, .png)</label>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setListOfImages(Array.from(e.target.files || []))}
          />
        </div>

        <div className="input-group">
          <label>Configuration (.json)</label>
          <input
            type="file"
            accept="application/json"
            onChange={(e) => setConfig(e.target.files?.[0] || null)}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Grading..." : "Grade Exam"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  );
};
