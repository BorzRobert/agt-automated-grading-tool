import React, { useState } from "react";
import {
  extractErrorMessage,
  getGradeJobProgress,
  getGradeJobResult,
  startGradeJob,
} from "../api";

const POLL_INTERVAL_MS = 1000;

const downloadFile = (fileBlob: Blob) =>{
      const url = window.URL.createObjectURL(fileBlob);
      const downloadLink = document.createElement("a");
      downloadLink.href = url;
      downloadLink.download = "grade_results.zip";
      downloadLink.click();
      window.URL.revokeObjectURL(url);
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const UploadForm: React.FC = () => {
  const [listOfImages, setListOfImages] = useState<File[]>([]);
  const [config, setConfig] = useState<File | null>(null);
  const [fillThreshold, setFillThreshold] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (listOfImages.length === 0 || !config) {
      setError("Please upload both the exam images and the configuration JSON.");
      return;
    }
    if (fillThreshold < 0 || fillThreshold > 1) {
      setError("Fill threshold must be between 0 and 1.");
      return;
    }

    setLoading(true);
    setProgress({ processed: 0, total: listOfImages.length });

    try {
      const jobId = await startGradeJob(listOfImages, config, fillThreshold);

      let job = await getGradeJobProgress(jobId);
      setProgress({ processed: job.processed, total: job.total });
      while (job.status === "pending" || job.status === "running") {
        await sleep(POLL_INTERVAL_MS);
        job = await getGradeJobProgress(jobId);
        setProgress({ processed: job.processed, total: job.total });
      }

      if (job.status === "error") {
        setError(job.error ?? "Grading failed. Please check your images and configuration and try again.");
        return;
      }

      const resultBlob = await getGradeJobResult(jobId);
      downloadFile(resultBlob);

      if (job.failed_images.length > 0) {
        setError(
          `${job.failed_images.length} of ${job.total} image(s) could not be graded and were skipped: ${job.failed_images.join(", ")}`,
        );
      }
    } catch (err) {
      setError(await extractErrorMessage(err));
    } finally {
      setLoading(false);
      setProgress(null);
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

      {loading && (
        <div className="progress-indicator" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <span>
            {progress && progress.total > 0
              ? `Processing images... (${progress.processed} of ${progress.total})`
              : "Starting up..."}
          </span>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
};
