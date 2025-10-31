import React, { useState } from "react";
import { gradeExam } from "../api";

interface GradeResult {
  total_questions: number;
  correct_count: number;
  score_percent: number;
  per_question: {
    question: number;
    selected: string[];
    is_correct: boolean;
  }[];
}

export const UploadForm: React.FC = () => {
  const [image, setImage] = useState<File | null>(null);
  const [config, setConfig] = useState<File | null>(null);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!image || !config) {
      setError("Please upload both the exam image and configuration JSON.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await gradeExam(image, config);
      setResult(res);
    } catch (err) {
      console.error(err);
      setError("Error while grading. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>Automated Grading Tool</h2>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label>Exam Image (.jpg, .png)</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setImage(e.target.files?.[0] || null)}
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

      {result && (
        <div className="results">
          <h3>Result</h3>
          <p>
            Score: {result.correct_count}/{result.total_questions} (
            {result.score_percent}%)
          </p>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Selected</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {result.per_question.map((q) => (
                <tr key={q.question}>
                  <td>{q.question}</td>
                  <td>{q.selected.join(", ") || "-"}</td>
                  <td>{q.is_correct ? "✅" : "❌"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
