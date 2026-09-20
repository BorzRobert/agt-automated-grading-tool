import React, { useState } from "react";
import { gradeExam } from "../api";



const downloadFile = (fileBlob: Blob) =>{
      const url = window.URL.createObjectURL(fileBlob);
      const downloadLink = document.createElement("a");
      downloadLink.href = url;
      downloadLink.download = "grade_results.zip";
      downloadLink.click();
      window.URL.revokeObjectURL(url);
}
export const UploadForm: React.FC = () => {
  const [listOfImages, setListOfImages] = useState<File[]>([]);
  const [config, setConfig] = useState<File | null>(null);
  const [fillThreshold, setFillThreshold] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (listOfImages.length === 0 || !config) {
      setError("Please upload both the exam images and configuration JSON.");
      return;
    }
    if (fillThreshold < 0 || fillThreshold > 1) {
      setError("Fill threshold must be between 0 and 1.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await gradeExam(listOfImages, config, fillThreshold);
      downloadFile(res);
    } catch {
      setError(`Error encountered while grading! Check backend logs!`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>Automated Grading Tool</h2>
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

        <div className="input-group">
          <label htmlFor="fill-threshold">Fill threshold</label>
          <input
            id="fill-threshold"
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={fillThreshold}
            onChange={(e) => setFillThreshold(Number(e.target.value))}
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
