import React, { useState } from "react";
import { extractErrorMessage, getTemplate } from "../api";

const MIN_QUESTIONS = 5;
const MAX_QUESTIONS = 30;
const MIN_CHOICES = 2;
const MAX_CHOICES = 6;

const downloadFile = (fileBlob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(fileBlob);
  const downloadLink = document.createElement("a");
  downloadLink.href = url;
  downloadLink.download = filename;
  downloadLink.click();
  window.URL.revokeObjectURL(url);
};

export const TemplateGenerator: React.FC = () => {
  const [questionCount, setQuestionCount] = useState(20);
  const [numberOfChoices, setNumberOfChoices] = useState(4);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (questionCount < MIN_QUESTIONS || questionCount > MAX_QUESTIONS) {
      setError(`Number of questions must be between ${MIN_QUESTIONS} and ${MAX_QUESTIONS}.`);
      return;
    }
    if (numberOfChoices < MIN_CHOICES || numberOfChoices > MAX_CHOICES) {
      setError(`Number of choices must be between ${MIN_CHOICES} and ${MAX_CHOICES}.`);
      return;
    }

    setLoading(true);
    try {
      const blob = await getTemplate(questionCount, numberOfChoices);
      downloadFile(blob, `template_${questionCount}.zip`);
    } catch (err) {
      setError(await extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>
        Generate a Blank Template <em>(⚠️experimental)</em>
      </h2>
      <form onSubmit={handleDownload}>
        <div className="input-group">
          <label htmlFor="template-question-count">Number of questions ({MIN_QUESTIONS}-{MAX_QUESTIONS})</label>
          <input
            id="template-question-count"
            type="number"
            min={MIN_QUESTIONS}
            max={MAX_QUESTIONS}
            value={questionCount}
            onChange={(e) => setQuestionCount(Number(e.target.value))}
          />
        </div>

        <div className="input-group">
          <label htmlFor="template-choice-count">Number of choices ({MIN_CHOICES}-{MAX_CHOICES})</label>
          <input
            id="template-choice-count"
            type="number"
            min={MIN_CHOICES}
            max={MAX_CHOICES}
            value={numberOfChoices}
            onChange={(e) => setNumberOfChoices(Number(e.target.value))}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Generating..." : "Download Template"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  );
};
