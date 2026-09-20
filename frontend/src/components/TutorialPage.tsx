import React from "react";

export const TutorialPage: React.FC = () => {
  return (
    <div className="tutorial-page card">
      <h2>How to use the grading tool</h2>
      <p className="lead">
        Follow these steps to upload an exam, configure grading, and download the results.
      </p>

      <div className="tutorial-steps">
        <section className="tutorial-step">
          <h3>1. Prepare the exam images</h3>
          <p>
            Scan or photograph each answer sheet clearly. Keep the page flat, centered, and well-lit
            so the detector can find the answer grid reliably.
          </p>
        </section>

        <section className="tutorial-step">
          <h3>2. Create the configuration JSON</h3>
          <p>
            The config file is a small JSON document that tells the grader which questions exist and
            which answers are correct for each one. Each question can have either a single answer like
            "B" or multiple correct answers such as ["A", "C"].
          </p>
          <pre className="code-block">{`{
  "correct_answers": {
    "1": ["A", "C"],
    "2": "B",
    "3": ["D", "E"],
    "4": "B",
    "5": "B",
    "6": "C",
    "7": "F",
    "8": ["A", "C"],
    "9": "E",
    "10": "C",
    "11": ["A", "B"],
    "12": "D",
    "13": ["B", "D"],
    "14": ["A", "F"],
    "15": "B",
    "16": ["D", "E", "F"],
    "17": "A",
    "18": "E",
    "19": ["B", "C"],
    "20": "F"
  }
}`}</pre>
          <p>
            Copy the content above into a .json file, adjust the values to match your exam, and then
            upload that file in the grading form. The structure is intentionally simple: each question
            number maps to one correct option or a list of correct options.
          </p>
        </section>

        <section className="tutorial-step">
          <h3>3. Upload the sheet and config</h3>
          <p>
            On the main form, upload one or more exam images and the matching JSON configuration file
            that tells the grader which questions and answer choices are expected.
          </p>
        </section>

        <section className="tutorial-step">
          <h3>4. Check the fill threshold</h3>
          <p>
            The default fill threshold is 0.5, which preserves the current grading behavior. Increase
            or decrease it if you want a stricter or looser answer selection threshold.
          </p>
        </section>

        <section className="tutorial-step">
          <h3>5. Generate or review a template</h3>
          <p>
            Use the template generator to download a blank answer sheet matching the grading tool’s
            expected layout. This helps ensure the scanned document matches the detector assumptions.
          </p>
        </section>

        <section className="tutorial-step">
          <h3>6. Grade and download the results</h3>
          <p>
            Submit the form and the app will process the images, compile the selected answers, and
            return a ZIP archive containing the grading result files.
          </p>
          <p>
            The generated archive contains the grading report and a debugging folder with the annotated
            detection images. The main file is <strong>Grades.xlsx</strong>, which includes the grades and
            detailed results for each selected variant. The ZIP also contains a <strong>debug_results </strong> 
            folder with images showing the detection markup applied to the sheets so you can check that
            the grid detection was correct.
          </p>
          <pre className="code-block">{`grade_results.zip
├── debug_results/
│   ├── sheet_001_detected.png
│   └── sheet_002_detected.png
├── Grades.xlsx`}</pre>
        </section>
      </div>

      <div className="tutorial-notes">
        <h3>Helpful tips</h3>
        <ul>
          <li>Use a consistent scan orientation for every sheet in the same batch.</li>
          <li>Prefer high-contrast scans with visible guide lines for best detection accuracy.</li>
          <li>Keep the uploaded JSON aligned with the answer key for the specific exam version.</li>
          <li>Open the ZIP after grading to review the detected answers and confirm the sheet layout was interpreted correctly.</li>
        </ul>
      </div>
    </div>
  );
};
