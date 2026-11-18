# AGT – Backlog Requirements (input for implementation planning)

> **Purpose.** This document turns the owner's draft list ("Aspects to address gradually") into requirements written against the *current* state of the repository, so an agent can later derive an implementation plan from it.
> It is **not** an implementation plan: it states what must be true, what exists today, and what is still undecided.
>
> **Status of every item:** not started. Items are independent unless a *Depends on* line says otherwise.
> **Wording:** MUST = required, SHOULD = desired, MAY = optional / "maybe" in the original draft (needs a go/no-go decision before planning).

---

## 0. Project context (verified against the repo)

### 0.1 Architecture

| Area | Facts |
| --- | --- |
| Backend | `server/` – FastAPI + OpenCV (`opencv-python`), pandas/openpyxl, Python 3.11 (Dockerfile). `requirements.txt` is **unpinned** and also contains `pytest`. |
| Frontend | `frontend/` – React 19, TypeScript, Vite 7, `react-router-dom` 7, `axios`, Vitest + Testing Library. Routes in `src/App.tsx`: `/` (`UploadForm`), `/template` (`TemplateGenerator`), `/guide` (`TutorialPage`). Header nav lives in `src/components/AppLayout.tsx`. All HTTP calls live in `src/api.ts`. |
| Hosting | Backend on Render (Docker, `render.yaml`, health check `GET /health`, `ALLOWED_ORIGINS` env var). Frontend on GitHub Pages (`.github/workflows/deploy-pages.yml`, copies `index.html` → `404.html` for SPA routing, `VITE_API_BASE_URL` repo variable). |
| CI | Only two workflows: `deploy-pages.yml` (push to `main`, `frontend/**` only) and `naming.yml` (PR branch/commit naming). **No workflow runs tests.** |
| Conventions | Branch `AGT-<id>-<message>`, commit/PR title `AGT-<id> <message>` (enforced by `.githooks/` and `naming.yml`; see `docs/contributing.md`). |
| Docs | `README.md`, `server/README.md`, `frontend/README.md`, `docs/{installation,development,usage,configuration,deployment,contributing}.md`. |

### 0.2 Backend modules (`server/app/`)

- `main.py` – endpoints:
  - `GET /health`
  - `GET /templates/{question_count}?number_of_choices=4&exam_title=Exam Title` → ZIP (`template_<N>.pdf` + `config.json`)
  - `POST /grade/` (multipart: `list_of_images[]`, `config_json`, `fill_threshold` form float, default 0.5) → `{job_id}`
  - `GET /grade/{job_id}/progress` → `{status, processed, total, error, failed_images}`
  - `GET /grade/{job_id}/result` → ZIP; **the job is deleted from memory right after the result is served** (single download).
- `service.py` – in-memory job store (`_jobs`, one `asyncio` task per job). Grades images sequentially via `asyncio.to_thread`. Builds the result ZIP:
  - `Grades.xlsx` (sheet `Grades`, columns `Candidate`, `Grade`, `Extended result`; sorted by grade desc; `Extended result` is a **JSON string** of `GradeResult`)
  - `debug_results/<original image filename>` – debug visualisation images.
  - Debug images are written to a shared relative folder `./debug_results` (named by the uploaded filename) and wiped after each job. Two concurrent jobs or two images with the same filename would collide.
- `grader.py` – `Grader.grade(image_name, image_bytes, configuration, fill_threshold)`:
  - Detects the grid via `ImageProcessor.detect_guided_boxes`, groups boxes into rows (10 px tolerance), takes the first `number_of_questions` rows.
  - Per box: pads ROI by 15 %, `compute_fill_confidence` (Otsu binarisation → ratio of black pixels, 0..1). A choice is "selected" if `confidence > fill_threshold`.
  - A question is correct **only if the selected set exactly equals the correct set** (all-or-nothing). `score_percent = correct_count / number_of_questions * 100`. Questions missing from the config get `is_correct = None`.
  - Letters are `A–F` (max 6 choices).
- `models.py` – `GradeRequestConfig{correct_answers: Dict[int, Letter | List[Letter]]}`, `BoxResult{question, selected, is_correct, confidences}`, `GradeResult{total_questions, correct_count, score_percent, per_question, debug}`.
- `image_processor.py` – deskew, find the title **separator line**, crop below it, detect horizontal/vertical guide lines via projections with adaptive thresholds, build boxes. Raises `GridDetectionError` with diagnostics. **Assumes a single answer grid per image.**
- `template_generator.py` – renders a blank sheet at 300 DPI, Letter size. `MIN_QUESTIONS=5`, `MAX_QUESTIONS=30`, `MIN/MAX_CHOICES=2/6`. The functions already accept `exam_title` (default `"Exam Title"`), printed as the 2nd header line next to `Name:`. Returns a ZIP with the PDF and a blank config (`"A"` for every question). The page geometry is tuned so a **single page** fits at most 30 questions.
- `config_loader.py` – `json.loads` → `GradeRequestConfig`.

### 0.3 Frontend behaviour today

- `UploadForm.tsx`: two plain `<input type="file">` controls (images: `accept="image/*" multiple`; config: single JSON), a numeric fill-threshold input (default 0.5, validated 0..1), submit → `startGradeJob` → poll `/progress` every 1 s → `getGradeJobResult` → automatic browser download of `grade_results.zip`. Failed images are reported in an error message. **The ZIP is only downloaded; nothing is kept in app state and nothing is displayed.**
- `TemplateGenerator.tsx`: inputs for question count (5–30) and choices (2–6); labelled "experimental". `getTemplate()` in `api.ts` **does not send `exam_title`** even though the backend supports it, and the UI has no field for it.
- Styling is in `src/App.css` / `src/index.css`; the layout is meant to be responsive (see commit "Fixed app layout scrolling on small screens").

### 0.4 Tests today

- Backend (`server/tests/`, `pytest`, `pytest.ini` with a `manual_dataset` marker): `test_grader_threshold.py`, `test_image_processor.py`, `test_template_generator.py` (synthetic images), `test_manual_dataset.py` (opt-in, needs `AGT_MANUAL_DATASET_DIR`; real scans are **not** committed for privacy/size). `conftest.py` puts both `server/` and `server/app/` on `sys.path` because app modules mix `from app.x import` and bare `from x import`.
- Frontend: `src/App.test.tsx` (Vitest + Testing Library).
- No committed real-scan fixtures; no end-to-end/regression suite; nothing runs in CI.

### 0.5 Cross-cutting rules for every item below

- Follow the branch/commit naming convention (§0.1).
- Do not break existing API behaviour unless the item says so; new request fields MUST be optional with the current behaviour as default (backwards compatible with the deployed frontend/backend pair, which are released independently).
- Update the affected docs (`README.md`, `docs/*.md`, `server/README.md`, `frontend/README.md`, in-app `TutorialPage.tsx`) in the same change.
- Add/adjust automated tests for new behaviour (backend `pytest`, frontend Vitest).
- Do not commit scans containing personal data (see REQ-15 for how fixtures are to be handled).

---

## 1. Maintenance & quality

### REQ-01 – Resolve `npm install` warnings
**Goal:** `npm install` (and `npm ci`) in `frontend/` completes without warnings.
**Current state:** Warnings exist (reported by the owner) but have not been catalogued. Dependencies are in `frontend/package.json` (React 19, Vite 7, Vitest 3, ESLint 9, `eslint-plugin-react-hooks` ^5, etc.).
**Requirements**
- MUST first capture the exact warnings (deprecated packages, peer-dependency conflicts, engine mismatches, audit notices) and record them in the PR description.
- MUST resolve each by upgrading/replacing the offending direct dependency, or by an explicit, justified override when the warning comes from a transitive dependency that cannot be upgraded yet.
- MUST keep `package-lock.json` in sync, and keep `npm run lint`, `npm run build` and `npm test` passing.
- SHOULD align the Node version used in `deploy-pages.yml` (currently 20) with what the upgraded toolchain requires.
**Acceptance:** clean `npm ci` output; lint/build/test green; GitHub Pages workflow still builds.

### REQ-02 – Server dependency vulnerabilities
**Goal:** No known-vulnerable Python dependencies on the server side, and ongoing detection.
**Current state:** `server/requirements.txt` is unpinned (`fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `opencv-python`, `numpy`, `Pillow`, `pandas`, `openpyxl`, `pytest`); the Docker image installs whatever is latest at build time. No Dependabot/CodeQL configuration exists in `.github/`.
**Requirements**
- MUST audit the current resolved versions (e.g. `pip-audit` and/or GitHub's Dependabot alerts) and fix findings by bumping versions.
- SHOULD pin versions (or add a lock/constraints file) so builds are reproducible and audits are meaningful.
- SHOULD move `pytest` out of the production runtime requirements (e.g. `requirements-dev.txt`) – requires updating `docs/installation.md`, `server/README.md` and the CI job from REQ-12.
- SHOULD enable Dependabot (pip, npm, github-actions) via `.github/dependabot.yml`; MAY add a scheduled `pip-audit`/`npm audit` workflow.
- The same Docker image build (`server/Dockerfile`) MUST still succeed and the test-suite MUST pass after bumps (OpenCV/NumPy/pandas bumps can change behaviour – rely on REQ-15).
**Acceptance:** audit reports no known vulnerabilities (or documented, justified exceptions); automated dependency updates are configured.

---

## 2. Frontend UX

### REQ-03 – Better-looking, drag-and-drop upload areas
**Goal:** Replace the plain file inputs in `UploadForm.tsx` with polished drop zones.
**Requirements**
- Exam-images zone: MUST accept drag-and-drop **and** click-to-browse of **multiple** images (`image/*`), MUST allow adding more files incrementally, SHOULD list the selected files (name, size, optional thumbnail) with per-file remove and a "clear all" action, SHOULD de-duplicate identical files.
- Config zone: MUST accept exactly **one** JSON file at a time (dropping another replaces the current one; dropping several MUST take only one or show a clear message); MUST show the selected file name with a remove/replace action; SHOULD reject non-JSON files early with a clear message.
- MUST show visual states: idle, drag-over, populated, error; MUST be keyboard-accessible (focusable, Enter/Space opens the picker, labelled for screen readers, `aria-live` feedback).
- MUST remain usable on small screens (touch devices: tap-to-browse is the primary path).
- MUST keep the current validation/submit flow (`handleSubmit`) and error messages working; existing tests in `App.test.tsx` MUST be updated, not deleted.
- SHOULD be a reusable component (e.g. `components/DropZone.tsx` configured by `multiple`, `accept`) rather than duplicated markup; SHOULD avoid adding a heavy dependency unless justified (native HTML5 drag-and-drop is sufficient).
**Acceptance:** Vitest tests cover multi-drop, single-drop replacement, removal, and rejection of invalid types.

### REQ-04 – Optional test/subject name in the blank template generator
**Goal:** The user can optionally provide the name of the test/subject, printed on the generated template.
**Current state:** The backend **already supports it** (`exam_title` query parameter on `GET /templates/{question_count}` → `template_generator.*`, default `"Exam Title"`). The gap is the frontend: `TemplateGenerator.tsx` has no field and `api.ts#getTemplate` does not send the parameter.
**Requirements**
- MUST add an optional text field to the Blank Template page and pass it as `exam_title` only when non-empty (otherwise keep the backend default).
- MUST validate/limit length (the title is rendered with `cv2.putText` in the header area, which has limited width and **only supports basic ASCII glyphs** – non-ASCII characters such as Romanian diacritics render as `?`). The plan MUST decide between: restricting/normalising input, or switching the title rendering to a Unicode-capable approach (e.g. Pillow `ImageDraw` + TTF font). Either way the title MUST NOT break grid detection.
- SHOULD sanitise/trim the value server-side and reject over-long input with HTTP 400 (consistent with existing `ValueError` → 400 handling).
- MAY include the title in the downloaded file names.
**Acceptance:** a template generated with a title still passes the existing template→grader round-trip tests; new tests cover empty, normal, long and non-ASCII titles.

### REQ-05 – Results viewer tab
**Goal:** After a batch is successfully graded, the user can browse the results in the app instead of only opening the downloaded ZIP.
**Depends on:** none strictly, but see REQ-08 (multi-page) and REQ-06 (partial points) so the data contract is designed once.
**Current state:** `UploadForm` downloads `grade_results.zip` and discards it; the server deletes the job after the first `GET /result`. The ZIP contains `Grades.xlsx` (with a JSON string per candidate) and `debug_results/*`. The answer key is only in the user's uploaded config. There is no persistence or state shared between routes.
**Requirements**
- Navigation: a new header item in `AppLayout.tsx` (e.g. "Results") MUST be rendered **only after** a batch was successfully graded in the current session (job `done`, result downloaded/received); route e.g. `/results`. Direct navigation to it without data MUST redirect to `/` (extend the existing catch-all behaviour). It SHOULD be possible to open it in a **new browser tab** (the draft says "open a new tab") – therefore the results data MUST survive being opened in another tab (e.g. `sessionStorage`/`IndexedDB`/blob handoff, or re-parsing a stored ZIP) – the plan MUST pick and justify the mechanism, remembering that sessions are not shared via in-memory React state across tabs.
- Data source (decision needed, recorded in the plan): (a) parse the returned ZIP client-side (needs an XLSX/ZIP parser, or – preferred – add a machine-readable `results.json` to the ZIP next to `Grades.xlsx` so the client does not parse Excel), or (b) change the API so results are fetchable as JSON without deleting the job on first fetch. Whatever is chosen, the existing ZIP download MUST keep working and the result MUST stay backwards compatible (keep `Grades.xlsx` and `debug_results/`).
- Content, **per candidate/test**: candidate name (file name), final grade, and for **each question**: the selected answer(s), whether it was correct, the **correct answer(s)** (requires the answer key to be included in the results payload or merged client-side from the uploaded config), and the **fill percentage (confidence) for every variant** (A–F as detected). Also: the corresponding **debug image**, and any failed images with reasons (`failed_images`).
- Presentation: MUST be clear and concise: batch summary (count, average, min/max), sortable/filterable list of candidates, expandable candidate detail with a compact per-question table/grid (visually distinguish correct/incorrect/unanswered, highlight the correct answer, show fill % per option), debug image viewable (modal/zoom).
- Responsive: MUST work on tablets and phones (cards instead of wide tables on narrow viewports, no horizontal page overflow, touch-friendly targets). The layout shell already scrolls inside `.page-scroll`; do not regress it.
- MUST NOT send the results to any third party; everything stays between the browser and the app's own backend.
- Memory: batches can be large (many images + debug images); the plan SHOULD address lazy loading of debug images and releasing object URLs.
**Acceptance:** Vitest tests for conditional nav visibility, redirect without data, rendering of a fixture result (correct/incorrect/unanswered, multi-answer), plus a manual check on narrow viewports.

---

## 3. Grading engine

### REQ-06 – Partial points (configurable)
**Goal (MAY – decide go/no-go):** allow awarding part of a question's point when a candidate selects some, but not all, of the correct answers (e.g. 2 of 3 correct chosen → partial credit).
**Current state:** All-or-nothing: `is_correct = selected_set == correct_set`; `correct_count` is an integer; `score_percent = correct_count / total * 100`; `BoxResult` has no score field; the config schema (`GradeRequestConfig`) only has `correct_answers`.
**Requirements**
- The scoring policy MUST be supplied **before grading starts**, in the configuration file and/or as an optional form parameter. When absent, behaviour MUST remain exactly as today (all-or-nothing) so existing configs and tests keep passing.
- The plan MUST define the scoring formula and rules explicitly, including: points per question (default 1), proportional credit for correct selections, **penalty/zero for incorrect extra selections** (e.g. `max(0, (correct_hits − wrong_hits) / |correct|)` or a configurable alternative), behaviour for single-answer questions (stays binary), and rounding.
- `BoxResult` SHOULD expose the per-question awarded points (and max points) in addition to `is_correct`; `GradeResult` SHOULD expose total awarded points; `score_percent` MUST be derived from points. The new fields MUST be reflected in `Grades.xlsx`/results payload and in the results viewer (REQ-05).
- `is_correct` semantics MUST be clarified (e.g. `true` only for full credit) and documented.
- Config validation MUST give friendly 400 errors for invalid policies (the current `/grade/` already converts config errors to HTTP 400).
- Unit tests MUST cover: full, partial, zero, extra wrong selection, single-answer, missing config entry, and policy omitted.
**Docs:** `docs/configuration.md` and `TutorialPage.tsx` MUST document the new config option with an example.

### REQ-09 – Verify/repair detection of the app's own generated templates
**Goal:** Templates produced by `template_generator.py` (still flagged "experimental") must be reliably recognised by the grader after being printed, filled and scanned.
**Current state:** `template_generator.py` is carefully tuned to the `ImageProcessor` thresholds (`MINIMUM_LINE_GAP`, `LINE_MAX_THICKNESS`, corner registration marks to stabilise `_deskew`, tick marks, separator line). `test_template_generator.py` exercises it on synthetic images; detection on real printed+scanned/photographed generated sheets is not verified. The checked-in reference templates are `templates/20` and `templates/30` (`.docx`).
**Requirements**
- MUST define a test matrix of scenarios: every supported combination of question count (5–30, at least the boundaries and typical values) × choices (2–6); blank vs. partially/fully filled; light and heavy marks; stray marks/noise; slight rotation and perspective/photo-style distortion; different scan resolutions/contrast; both digital rendering and real print-scan samples (see REQ-15 for fixtures).
- MUST fix any detection failure in either the generator or the `ImageProcessor` without regressing the existing reference-template behaviour (the `templates/20|30` baselines and existing tests are the regression guard).
- MUST verify the template→config→grade round trip (generated `config.json` + generated sheet marked programmatically → expected grade).
- SHOULD remove the "experimental" label (`TemplateGenerator.tsx`, docs) only when the matrix passes.
- MUST stay consistent with REQ-08 (multi-page templates change the generator).
**Acceptance:** the scenario matrix is automated (parametrised tests) and green; each fixed bug has a regression test.

### REQ-10 – Suggested fill threshold (MAY – decide go/no-go)
**Goal:** Help the user choose a fill threshold for a given set of tests when many candidates marked boxes lightly.
**Current state:** A single global threshold (`fill_threshold`, default 0.5, UI field in `UploadForm`) compared against `compute_fill_confidence` (Otsu black-pixel ratio on the box ROI padded by 15 %). Non-selected boxes frequently have confidence > 0 due to the box border or noise/accidental marks, so "empty" is **not** 0.
**Requirements**
- The suggestion mechanism MUST be advisory: it MUST NOT silently change the threshold used for grading; the user confirms/overrides it.
- It MUST operate on the confidence distribution of the whole batch (e.g. analyse the per-box confidences, which are already produced as `BoxResult.confidences`) and propose a value in the valid range (0..1) with a short explanation (e.g. distribution of "empty" vs "marked" clusters, expected number of selections per question).
- It MUST be robust to the baseline noise described above: the algorithm MUST model the empty-box baseline (border/noise) instead of assuming 0, and MUST NOT interfere with how a non-selected answer is currently identified (same `confidence > threshold` rule; the suggestion only proposes a different threshold value). Where the distribution is not clearly bimodal, it SHOULD report low confidence/no suggestion rather than a misleading number.
- Candidate approaches the plan should compare: Otsu/valley detection on the pooled confidence histogram; k-means (k=2) on confidences; per-batch sensitivity table ("at 0.3 → N selections, at 0.5 → M selections").
- UX option for the plan to evaluate: a dry-run/analysis endpoint (e.g. `POST /grade/suggest-threshold`) or a field in the results; and showing the suggestion in the results viewer (REQ-05) with a "re-grade with this value" action.
- MUST have unit tests on synthetic confidence distributions (clean, light-marking, noisy, ambiguous).

### REQ-08 – Multi-page answer sheets (up to 100 questions)
**Goal:** Support a test whose questions are spread across several scanned images (e.g. 100 questions on 4 pages) for **both** grading and template generation.
**Current state:** One image = one candidate = one grid. `ImageProcessor` finds one separator + one grid; the generator caps questions at `MAX_QUESTIONS = 30` and one Letter page. `service.py` grades each uploaded file independently and emits one row per file (`Candidate` = file name). Question numbering is implicit (row index starting at 1 on each image). There is no notion of candidate identity across files.
**Requirements**
- Limits: total questions **≤ 100**; choices per question **≤ 6** (A–F, unchanged). Question counts above 100 MUST be rejected (HTTP 400 + UI validation); update the constants/validators on both sides (`template_generator.MAX_QUESTIONS`, `TemplateGenerator.tsx`).
- **Template generation:** MUST produce a multi-page document (a single PDF with N pages) where every page holds a contiguous block of questions and **continues the numbering** (e.g. page 2 starts at 26 if 25 per page); each page MUST carry what the grader needs to recognise it (separator line, grid geometry, **page index / identifier** that is machine-detectable, e.g. a small marker pattern, and a candidate-identifier mechanism – see below). The zip's blank `config.json` MUST cover all questions. The plan MUST decide questions-per-page (the current geometry fits ≤ 30 per Letter page; 100 questions ⇒ ≥ 4 pages) and keep single-page output unchanged for ≤ 30 questions.
- **Grading:** MUST map images to (candidate, page) and aggregate all pages of a candidate into **one** result/grade. The plan MUST choose and document the grouping mechanism, e.g. (a) a machine-readable page+candidate marker on the sheet (preferred if reliable), or (b) a file-naming convention / upload grouping (`<candidate>_p1.jpg`…), or (c) an explicit UI step to group files. It MUST define behaviour for missing pages, duplicate pages, pages out of order, extra pages, and pages whose detected question count differs from the expected block (report as a failed/incomplete candidate; do not silently grade a partial sheet as complete).
- `Grader`/`GradeResult` MUST support a global question offset per page so `per_question[].question` uses the global numbering matching the config. Backwards compatible: a single image without markers keeps the current 1..N behaviour.
- Job progress (`processed`/`total`) and `failed_images` semantics MUST stay meaningful (document whether they count images or candidates).
- Results file and viewer (REQ-05) MUST present one entry per candidate with all pages merged; debug images for every page MUST be kept and be linked to their page.
- Update `UploadForm`/guide so users know how to upload multi-page sets.
- **Depends on / interacts with:** REQ-09 (generated-template detection), REQ-11 (the same multi-image grouping idea for open answers), REQ-15 (multi-page fixtures).
**Acceptance:** a 100-question, 4-page generated template, marked programmatically in a test, is graded into a single candidate result with correct global numbering; negative tests for missing/duplicate/out-of-order pages.

### REQ-11 – AI scoring of free-text / open-question answers (MAY – decide go/no-go; largest item)
**Goal:** Optionally score handwritten/printed open answers from scanned images using an AI agent, and combine them with the multiple-choice result of the same candidate.
**Current state:** Nothing exists. The app is stateless w.r.t. candidates, has no external-service integration, no secrets management beyond `ALLOWED_ORIGINS`, and no per-candidate multi-file model (see REQ-08).
**Requirements**
- Scope: for an open question, the answer may span **multiple scanned images**; the system MUST be able to associate all images belonging to one (candidate, question) and submit them together to the AI. The grouping mechanism SHOULD be shared with REQ-08.
- Input model: MUST define how the user supplies, before grading, per open question: the question text, the reference/ideal answer or rubric, and max score (config schema extension, e.g. an `open_questions` section in the config JSON, validated by Pydantic). Existing configs without it MUST behave as today.
- Output: for each open answer the system MUST return a **score in [0, 100]** (validated/clamped, numeric) and a **textual reasoning** explaining how the score was derived (and SHOULD return the transcribed text so the grader can audit it).
- A candidate may have **both** a multiple-choice sheet and open-answer images. The result MUST **aggregate** both parts into one clear, concise candidate result: MC grade, per-open-question score + reasoning, and a **combined final grade** whose weighting (e.g. configurable weights MC vs open) is defined in the config. The Excel output and the results viewer (REQ-05) MUST present the combined result clearly.
- The plan MUST evaluate and decide: provider/model (vision-capable LLM), where the API key is stored (server-side env var only – NEVER in the repo or the frontend), cost/latency and the effect on the Render free tier (long-running; reuse the async job + progress model in `service.py`), failure handling and retries (an AI failure for one answer MUST NOT fail the whole batch – mark as "needs manual review"), determinism/consistency (low temperature, fixed rubric prompt), and testing without calling the real service (provider interface + mock in tests).
- **Privacy/compliance:** student handwriting is personal data. The plan MUST state what data is sent to the third-party provider, require explicit user consent/notice in the UI, avoid persisting data server-side beyond the job lifetime, and make the feature opt-in (disabled unless the server is configured with credentials). The AI score MUST be presented as a suggestion with the reasoning visible; human override SHOULD be possible in the viewer.
- **Depends on:** REQ-08 (multi-image grouping), REQ-05 (presentation), REQ-06 (scoring policy/aggregation conventions).

---

## 4. Engineering process, docs and automation

### REQ-12 – CI pipeline running server and frontend tests
**Goal:** Tests run automatically for every PR and for every change merged to `main`.
**Current state:** No test workflow exists (only `deploy-pages.yml` and `naming.yml`). Backend tests: `cd server && pytest -v`. Frontend: `cd frontend && npm ci && npm run lint && npm run build && npm test`.
**Requirements**
- MUST add a workflow (e.g. `.github/workflows/ci.yml`) triggered on `pull_request` and on `push` to `main` with two jobs: **server** (Python 3.11 to match the Dockerfile; install requirements incl. OpenCV system libs if needed; run `pytest`) and **frontend** (Node version consistent with `deploy-pages.yml`; `npm ci`, lint, type-check/build, `vitest run`).
- MUST NOT run the opt-in `manual_dataset` tests by default; SHOULD run the committed regression suite from REQ-15.
- SHOULD cache pip/npm, use path filters or a single required status check pattern that does not leave PRs "pending" when a path filter skips a job, and set the workflow(s) as required checks in branch protection (manual repo-settings step – document it).
- SHOULD make `deploy-pages.yml` depend on green tests (or at least not deploy a broken build); SHOULD upload test artifacts on failure.
- Workflow names/branches MUST stay compatible with the naming rules (`naming.yml` is separate and must keep working).
- `docs/contributing.md` and `docs/development.md` MUST be updated to describe running the same checks locally.
**Acceptance:** a PR shows both jobs; a deliberately failing test turns the check red.

### REQ-13 – Tidy and align README files
**Goal:** Clear, concise, well-organised READMEs for all audiences (developer, user, repo visitor) without losing information.
**Current state:** `README.md` (root, feature list + doc index), `server/README.md`, `frontend/README.md`, and `docs/*.md` (installation, development, usage, configuration, deployment, contributing). Some content is stale or thin (e.g. `docs/usage.md` still describes upload + immediate download and doesn't mention the blank-template generator, fill threshold or progress flow; `docs/configuration.md` is a single paragraph; `server/README.md` claims `pytest` "no external assets" etc.).
**Requirements**
- MUST preserve existing information, reorganise it by audience (what it is / quick start / user guide / developer guide / deployment / contributing), and remove duplication between root/server/frontend READMEs and `docs/`.
- MUST be aligned with the **latest** state of the repo at the time of the change: blank-template generator, async job flow with progress, configurable fill threshold, results format, CI (REQ-12), and every capability added by the other REQs (partial points, results viewer, multi-page, AI scoring, preview deployments…). Because of that, this item SHOULD be done **last** (or re-done/closed with a checklist at the end of each feature PR – "update docs" is already a cross-cutting rule, §0.5).
- MUST verify all relative links and shell commands in the docs still work.
- SHOULD decide whether `docs/requirements.md` (this file) is linked from the README or kept as an internal planning document.

### REQ-14 – Research: PR "Preview" deployments
**Goal (research deliverable, not an implementation):** determine how to deploy a per-PR preview so the owner and reviewers can test a PR without checking it out.
**Current state:** Frontend is on GitHub Pages (a single site per repo, deployed only from `main` and only when `frontend/**` changes; `VITE_API_BASE_URL` points at one Render backend). Backend is a single Render free-tier Docker service (`render.yaml`, `ALLOWED_ORIGINS` env var; cold starts). The frontend uses `BrowserRouter`-style routing with a `404.html` fallback, which affects sub-path hosting.
**Requirements**
- MUST produce a written comparison (in the PR/issue or a short doc) of viable options for **both** tiers, covering: Render PR Previews (preview environments from `render.yaml`, cost on free plan), Cloudflare Pages / Netlify / Vercel / Azure Static Web Apps previews for the frontend, GitHub Pages sub-path-per-PR workaround, and container-based alternatives (Fly.io, Railway, etc.) for the backend.
- MUST address the specifics of this project: the frontend needs the preview backend URL at **build time** (`VITE_API_BASE_URL`), the backend needs the preview frontend origin in `ALLOWED_ORIGINS` (CORS), SPA routing/base path, secrets exposure for **fork PRs**, cleanup when the PR closes, cost/limits, cold-start behaviour, and the dependency on the AI provider key if REQ-11 lands (preview must not leak or burn production credentials).
- MUST end with a recommendation and an outline (not full implementation) of the workflow/config changes required, plus effort estimate. Implementation is a separate follow-up item.

### REQ-15 – Automated regression tests with ≥ 25 real scanned images
**Goal:** A repeatable regression suite exercising the full grading pipeline on **at least 25 scanned images**, run automatically (REQ-12).
**Current state:** Tests use synthetic images; real scans are deliberately **not** committed ("privacy/size", see `server/README.md`); `test_manual_dataset.py` is opt-in via `AGT_MANUAL_DATASET_DIR` and only checks detection completeness against a dummy config (it also uses a bare `from grader import Grader`, relying on `conftest.py` path hacks).
**Prerequisite (input from the developer):** before implementation of this item starts, the developer (repo owner) MUST provide **both** the scanned images (at least 25) **and** their expected results (ground truth: the expected selected answers per question and/or expected grade per image, plus the answer-key config used for each set). The agent MUST NOT invent, guess or auto-derive the expected results from the grader's own output, and MUST stop and ask for these inputs if they are missing, incomplete or ambiguous (e.g. an image without an expected result). Format of the delivery (folder layout, manifest file) is to be agreed at the start of the work.

**Requirements**
- MUST provide ≥ 25 images with **ground truth** (expected selected answers per question and/or expected grade per image, stored alongside, e.g. a JSON/CSV manifest) and assert the grader's output against it (selections, correctness, final score, detected rows/columns), not just detection.
- The dataset MUST cover the variability that matters: different question/choice counts (including generated templates, REQ-09), rotations/skew, lighting, blank/partial/fully-filled sheets, multi-answer questions, noisy marks, and (once REQ-08 lands) multi-page sets. The suite SHOULD record a baseline so future detection/threshold changes show diffs.
- **Privacy/size:** fixtures MUST contain no personal data (anonymised/synthetic names, no real student handwriting identifiable data). the plan MUST choose a storage strategy for the developer-provided images and decide the repo policy: commit compressed, anonymised images (check total size; consider Git LFS) **or** keep them outside the repo and point the tests at them (as `AGT_MANUAL_DATASET_DIR` does today). Generated and programmatically degraded images (rotation, blur, noise, perspective) MAY supplement, but never replace, the developer-provided set. Whichever is chosen, `server/README.md`'s "no real scans committed" statement MUST be updated accordingly.
- MUST run via plain `pytest` in CI in reasonable time (set a budget; mark slow ones if needed) and report per-image failures clearly (parametrised test ids = image names).
- SHOULD be extended to cover the HTTP flow end to end (`/grade/` → `/progress` → `/result`, ZIP content assertions) using FastAPI's `TestClient`.
- Fix the import inconsistency (`app.x` vs bare `x`) only if needed by the new tests; otherwise leave as is.

---

## 5. Known technical debt that affects several items (not separate requirements)

1. **Shared `./debug_results` directory and filename-keyed debug images** (`image_processor.py`, `service.py`): concurrent jobs, or equal filenames within a batch, overwrite/delete each other's debug images. Becomes more visible with REQ-05, REQ-08, REQ-11; the plan SHOULD make debug output job-scoped (e.g. per-job temp dir or in-memory bytes) when touching this code.
2. **In-memory jobs, one-shot results**: jobs vanish on restart/after the first download; Render free tier restarts/cold starts. Relevant to REQ-05 (viewer needs data after download), REQ-11 (long jobs).
3. **Import style mix** (`from app.x` vs `from x`) requires `conftest.py` `sys.path` hacks.
4. **Exact-match correctness** and global threshold (see REQ-06, REQ-10).
5. **Hard-coded limits duplicated** between backend and frontend (`MIN/MAX_QUESTIONS`, `MIN/MAX_CHOICES`) – changes in REQ-08 must update both.

## 6. Suggested sequencing (informational – the planner may reorder)

1. Foundations: **REQ-12** (CI) → **REQ-15** (regression suite, using whatever exists today) → **REQ-01**, **REQ-02** (dependency work, protected by the suite).
2. Quick wins: **REQ-04** (frontend-only wiring + font decision), **REQ-03** (drop zones).
3. Engine: **REQ-09** → **REQ-08** → **REQ-06** → **REQ-10** (each with new regression fixtures).
4. Presentation: **REQ-05** (design the results payload once, with REQ-06/REQ-08 fields already in mind).
5. Optional/large: **REQ-11** (after REQ-08 and REQ-05), **REQ-14** (research can run any time; informs CI/CD).
6. Wrap-up: **REQ-13** (README/doc alignment, after the features it must describe).

## 7. Open decisions to resolve before/while planning

| # | Question | Relevant REQs |
| --- | --- | --- |
| 1 | Go / no-go for the "maybe" items (partial points, threshold suggestion, AI scoring). | 06, 10, 11 |
| 2 | Results viewer data source: add `results.json` to the ZIP vs. JSON API vs. client-side ZIP/XLSX parsing; cross-tab storage mechanism. | 05 |
| 3 | Candidate/page grouping mechanism for multi-page and open-answer images (on-sheet markers vs. file naming vs. UI grouping). | 08, 11 |
| 4 | Template title rendering: ASCII-only restriction vs. Unicode-capable font rendering. | 04 |
| 5 | Real-scan fixtures: commit anonymised images / Git LFS vs. generated + degraded images. | 15 |
| 6 | AI provider, key handling, consent/privacy stance, MC-vs-open weighting. | 11 |
| 7 | Partial-credit formula and penalty policy. | 06 |
