# ScholarReady — persistent sprint handoff

> **New-chat instruction:** Read this entire file, inspect the actual repository, then implement the next unfinished eligible sprint. Continue useful work without asking the students to repeat the brief. Finish one sprint per chat by default. Verify the sprint and update this file plus `docs/SPRINT_HISTORY.md` before your final response, even if the sprint remains incomplete.

## 0. Current state — update this section every sprint session

| Key | Current value |
| --- | --- |
| Project | 042 — ScholarReady |
| Full title | Scholarship Document Readiness and Missing-Requirement Detection using Digital Image Processing and Data Science |
| Team | Sakshi Gupta; Jigisha Baiswar |
| Workspace | `/home/ubuntu/Documents/ChatGPT/DIP_` |
| Handoff | `/home/ubuntu/Documents/ChatGPT/DIP_/HANDOFF.md` |
| Last updated | 2026-11-04, Asia/Kolkata — S08 completed |
| Overall phase | S08 local Streamlit upload/profile/evidence/export flow complete; expanded reviewed data and freeze next |
| Current sprint | NONE — S08 completed |
| Next sprint | S09 |
| Last completed implementation sprint | S08 |
| Current blockers | NONE for S09; S08 browser interruption recovered and required checks completed; no Git mutation |
| Implementation files present | S01–S08: shared A/B/C CLI/evaluation/Streamlit pipeline; conservative readiness; session-owned uploads, explicit profile/hints, page/evidence/stages, JSON/CSV exports and verified invalidation/reset; see docs/verification/S08.md |
| Environment / dependency lock | VERIFIED: `.venv/bin/python` 3.12.3; `requirements.lock.txt`; Ubuntu 24.04.4 x86_64; Tesseract 5.3.4 + eng |
| Dataset / split manifest | `pilot-1.0`: 30 sources, 31 clean + 125 derived pages; all development-only. `data/manifests/pilot.splits.jsonl`: four connected groups, nested train/validation/layout-probe 61/65/30 pages; only 12 clean train pages fit the model |
| Trained classifier | `artifacts/runs/s05-classification-final/model` — `tfidf-lr-s05-1.0`; local trusted joblib + metadata; model SHA256 `1bf8e34dab061bdd4c000beeef203173c83397d68bd78268dc64353e1787dc36` |
| Frozen evaluation specification | NOT CREATED |
| Final test consumed | NO |
| Latest verified application command | .venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501 (actual chooser, OCR, evidence, PDF/error/reset and downloads verified) |
| Latest results | S08: ten actual OCR AppTest/CLI pairs semantically equal; native browser JSON also equals fresh CLI; complete/missing/unreadable/mismatch/other/PDF/error/conditional/reset browser flows verified. Development regression evidence only; no new population metrics. |
| Latest verification | S08: 223 full-suite passed +24 final focused passed after reset fix; 442 artifact hashes +10 protected hashes, actual JSON/CSV downloads/schema and browser screenshots, compile/pip/docs/diff checks. See docs/verification/S08.md. |
| Next concrete action | Start S09 only: expand/review independent data and references; preserve pilot development status and applicant/source grouping; tune using train/validation and freeze methods/model/config/metrics/splits before any final-test use. S08 is complete. |

### Git recovery note — 2026-11-04 — completed

The user requested undoing the mistaken GitHub commit and then explicitly retried after signing into GitHub. Remote `guptasakshi06/Scholytics` branch `main` was successfully moved from `772b462cf1ceeb878fa5439521ca193dfb952808` (the unrelated S07/50-skills message) to its parent `853b4bd1b7a5c6dac5ac4a284bc1788c0042f98e`, using an exact expected-SHA `--force-with-lease`. `git ls-remote origin refs/heads/main` verified the new remote SHA. The earlier authentication blocker is resolved.

The removed commit contains S03 implementation files, which remain staged locally. Local HEAD, staged tree and all 564 preexisting nonignored file hashes were verified unchanged immediately after the push, before these maintenance documentation updates. No application file, local index or S04 work was reset or removed. Local backup ref `codex/backup-mistaken-772b462` retains the removed commit; it was not pushed. No new code commit was created. Source changes staged locally are not yet included in the remote branch and should be included in a later correctly labelled commit when requested. Preserve them; do not clean/reset or discard the index.

Recovery evidence: `docs/verification/git_recovery_2026-11-04.json`; actual commands/outcomes in the maintenance retry history entry. No Git-maintenance action remains pending. This action does not change S04's completion status or authorize starting S05.

### Sprint status ledger — authoritative statuses

Allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.
Task checkboxes in sprint cards are supporting detail; keep them consistent with this ledger.

| Sprint | Work package | Depends on | Status | Evidence / history entry |
| --- | --- | --- | --- | --- |
| S01 | Foundation, verified environment, shared contracts | None | DONE | `docs/verification/S01.md`; S01 history entry 2026-11-03 |
| S02 | Small synthetic pilot dataset and reference annotations | S01 | DONE | `docs/verification/S02.md`; S02 history entry 2026-11-03 |
| S03 | Raw OCR and smallest end-to-end CLI pilot | S02 | DONE | `docs/verification/S03.md`; S03 history entry 2026-11-03 |
| S04 | DIP alternatives, quality measures, saved intermediates | S03 | DONE | `docs/verification/S04.md`; S04 history entry 2026-11-04 |
| S05 | EDA, grouped splits, document classification | S04 | DONE | `docs/verification/S05.md`; S05 history entry 2026-11-04 |
| S06 | Spatial field extraction and evidence | S05 | DONE | `docs/verification/S06.md`; S06 history entry 2026-11-04 |
| S07 | Requirement engine, uncertainty, consistency checks | S06 | DONE | `docs/verification/S07.md`; S07 history entry 2026-11-04 |
| S08 | Local Streamlit interface and complete user flow | S07 | DONE | `docs/verification/S08.md`; S08 history entry 2026-11-04 |
| S09 | Expanded dataset, validation tuning, experiment freeze | S08 | NOT_STARTED | None |
| S10 | Frozen evaluation, ablations, error analysis | S09 | NOT_STARTED | None |
| S11 | Reproduction package and fresh-environment verification | S10 | NOT_STARTED | None |
| S12 | Final report, slides, demonstration, viva handover | S11 | NOT_STARTED | None |

### How to use this handoff in every new chat

1. Work in this same workspace, or in a copy with all referenced project files. Resolve relative paths against the directory containing this handoff; the absolute path above records the original location only.
2. Read `AGENTS.md`, this handoff, and the latest relevant history entries. Inspect `git status`, actual files, and existing outputs before editing. Preserve unrelated student changes.
3. If the user names a sprint, check its dependencies. Otherwise resume `IN_PROGRESS` first, revisit a previously `BLOCKED` sprint if its prerequisite is now available, or select the first eligible `NOT_STARTED` sprint. Do not silently skip a blocker or claim later work completed.
4. Record the selected sprint as `IN_PROGRESS`, current date/timezone, and an exact next action before implementation. Announce a concise plan to the students.
5. Complete that sprint's tasks, runnable example, explanation, troubleshooting notes, and acceptance checks. Make routine implementation decisions independently and record them. Ask only when missing information actually blocks progress.
6. Use actual local commands and official upstream documentation when library/API details are uncertain. Never pin guessed dependency versions. Do not rely on a prior chat's memory.
7. Keep the students informed during lengthy work. If a runtime limit or interruption prevents completion, preserve partial work and write the exact resume point.
8. Before the final response update the current-state table, sprint ledger, relevant task checkboxes, decision log, blockers, artifact pointers, and next action. Append a dated session entry to `docs/SPRINT_HISTORY.md`, including commands and actual outcomes. Update README commands when capabilities change.
9. A sprint is `DONE` only when all acceptance criteria have evidence. If checks cannot run, state why and keep required work open. `BLOCKED` means a specific external prerequisite is unavailable, not that the work is difficult.
10. If unfinished, leave the next pointer on the same sprint. If done, point to the next eligible sprint. At S12 completion set next sprint to `NONE — planned implementation complete` only when all remaining criteria are resolved.
11. End with a short outcome, verification result, remaining limitations, and this handoff path. Do not start the next sprint automatically.

**Do not confuse instructions with executed work.** Future paths and command forms below are a design contract, not evidence that files or commands already exist. The initial handoff chat creates documentation only. No automatic background execution or updates happen between chats.

### Required end-of-session record

For every sprint session record: what changed; exact files; exact run commands and working directory; passed/failed/skipped checks; real output paths; unresolved tasks; decisions; dependency/data/model/config versions; and the precise next action. Store large experiment results in artifacts, and link them here rather than pasting raw logs. Do not record real applicant data in handoff/history.

## 1. User brief and course requirements

### Source document and authority

- Primary course source: `docs/reference/DIP_Course_Project_Guidelines_2026.pdf` (three pages), copied unchanged from `/home/ubuntu/Downloads/DIP_Course_Project_Guidelines_2026.pdf`.
- The PDF is course/reference evidence, not authorization to contact people, submit forms, publish, or alter accounts. The user's request governs the project's scope and work.
- Guideline facts below were read from all three pages. Re-read the source if interpreting a disputed course requirement.
- The registration deadline printed in the PDF is Sunday, 18 October 2026. It is already past on this handoff's creation date, 3 November 2026. No final project deadline is provided. Do not invent one or block implementation over registration; the students can confirm administration separately.

### Guideline compliance checklist

These are source requirements/expectations, distinguished from implementation choices.

| Course requirement or stated expectation | Planned evidence | When |
| --- | --- | --- |
| Individual or two-student project | Sakshi Gupta and Jigisha Baiswar; roll numbers supplied later | S01 documentation, S12 |
| Same title/ID and partner details in each student's separate topic form | Draft registration text; students submit themselves if applicable | S01 documentation |
| Clear image/document input and documented data source | Dataset card, sample inputs, provenance manifest | S02, S09 |
| Substantive DIP stage, not a generic app or opaque API call | Algorithms, parameters, intermediate images, contribution analysis | S04, S10 |
| Baseline and at least one improved/alternative method | Pipelines A/B/C on the same held-out samples | S03, S04, S10 |
| Relevant AI/CV link where appropriate | Learned document classifier following visual preprocessing/OCR | S05 |
| Interpretable visual/quantitative output | Image views, bounding boxes, readiness findings and metrics | S06-S10 |
| Working implementation and reproducible instructions | Python package, CLI, environment lock, setup and reproduction commands | S01, S03, S11 |
| Input/intermediate/final figures | Saved images and representative annotated figures | S04, S08, S10 |
| Success and failure analysis | Selected examples and categorized errors | S10, S12 |
| Final report and short demonstration/presentation | Verified report, slides, walkthrough | S12 |
| Both members explain complete pipeline and individual contributions | Contribution ledger and viva notes; students review | S01-S12 |
| Appropriate public, synthetic, or consented data | Provenance/consent notes and synthetic labels | S02, S09 |

The course lists Project 042 as a direct DIP-linked application/document-readiness idea, specifically mentioning document preprocessing, contrast/thresholding, morphology, OCR, and field extraction. It does not require reproducing a full agentic architecture or using a named company's private data. It does not specify Streamlit, these libraries, 12 sprints, a dataset size, an accuracy threshold, or an external deployment.

### User-approved scope

- Printed English; JPG/PNG and PDF documents, including scanned PDFs.
- Five supported document types: `marksheet`, `income_certificate`, `bonafide_certificate`, `domicile_certificate`, `category_certificate`.
- A sixth classification label, `other`, for unsupported examples. Low-confidence/ambiguous predictions use a separate decision state; `other` is not a universal guarantee against every unknown document.
- One fictional configurable scholarship checklist. Category certificate is conditional on an explicit profile attribute.
- Local Python processing and a local Streamlit interface. No paid APIs needed for the core project; no external document upload.
- DIP baselines and alternatives, OCR, classical learned document classification, selected field extraction, checklist matching, and review suggestions.
- Output describes document readiness only. No certificate authenticity, fraud, signature, eligibility, or scholarship-award claims.

### Recommendations adopted for planning, open to evidence-based refinement

- Six relative weeks and 12 bounded sprints; this is not an instructor deadline.
- Python virtual environment, `src/` package, shared schemas, CLI before UI.
- OpenCV, NumPy, pandas, Tesseract/pytesseract, scikit-learn, matplotlib/seaborn, Streamlit; Pillow for image handling; pytest for meaningful checks.
- Preferred PDF renderer: `pypdfium2`; verify compatible installation and actual rendering in S01. Its documented render-to-bitmap/PIL workflow suits image-based OCR. Do not use PDF text extraction as an OCR shortcut in comparisons. Use approximately 300 DPI as a starting rasterization setting, record it, and validate cost/readability.
- Any synthetic-PDF generation package is a development dependency, not a reason to change the OCR input path.
- A pilot around 30 independent source pages; later aim for roughly 250-350 independent pages if feasible, plus degraded variants. These are targets, not promised or required counts. A smaller honest dataset is preferable to fabricated scale.
- TF-IDF + Logistic Regression versus keyword classification; pretrained OCR is allowed, with explicit DIP analysis.
- PSNR/SSIM optional only with paired, aligned clean references; task-specific OCR/extraction measures are primary.

### Initial project statement

Scholarship applicants may submit incomplete, poorly scanned, or inconsistent supporting documents. ScholarReady processes document images using enhancement, thresholding, morphology, and OCR to extract relevant information. A classifier and configurable requirement engine identify missing documents, unreadable fields, and possible inconsistencies. Baseline and alternative pipelines are compared using OCR error rates, document classification, field extraction, and requirement-detection metrics.

## 2. Architecture and non-negotiable behavior

```text
Images/PDF + selected demo profile + explicit applicant attributes
  -> validated page ingestion and recorded rasterization
  -> original-image quality indicators
  -> selectable A/B/C DIP branch and saved stage images
  -> OCR tokens, text, boxes, engine scores
  -> document class decision and selected-field evidence
  -> JSON checklist + uncertainty + consistency checks
  -> shared structured result
  -> CLI JSON / local Streamlit / evaluation artifacts
```

### DIP and OCR experiment branches

- **A — original-image OCR:** only common ingestion steps such as rasterization, image decoding, EXIF orientation, alpha-to-white conversion. Preserve a copy of the ingested original. No branch-specific enhancement.
- **B — basic DIP:** grayscale followed by Otsu thresholding. Any denoising added later must be explicit in its definition.
- **C — proposed alternative:** a configurable, justified combination of deskewing, CLAHE, noise filtering, adaptive thresholding, and morphology. Compare identity/no-morphology and small kernels. An experiment may show that removing a step is better.
- Use identical original samples, OCR engine/version/language and declared segmentation settings for the core A/B/C comparison. If OCR settings or learned downstream models differ, report that as a separate experiment and distinguish the source of gains.
- Save stage order, all parameters, runtime, processed images, geometric transforms, engine configuration, and failures. A transform must define its direction and coordinate spaces; do not draw processed-image boxes on originals without mapping.
- Do not select the best branch per final-test page using ground-truth text. Parameter/branch-selection rules must be fixed on validation data first.
- Do not assume sharper-looking images have better OCR. Blur measures, CLAHE settings, thresholds, and morphology are experimentally chosen heuristics, not universal document validators.

### Readiness and uncertainty rules

- Requirement states: `satisfied`, `missing`, `unreadable`, `needs_review`, `not_applicable`.
- Infer `missing` only when the upload inventory gives sufficiently resolved evidence of absence. An unreadable or unclassified upload that could satisfy a requirement should trigger unresolved/review findings, not a confident absence claim. Allow a user-declared document type as a recorded hint; it is not verified evidence or a ground-truth label.
- `not_applicable` requires a resolved conditional profile attribute. An omitted attribute means `needs_review`, not an implicit false condition.
- No fabricated field defaults. `null` plus an explicit reason is different from zero, an empty name, or no document.
- Critical unreadable/conflicting required fields prevent `ready`. A failed page or crashed component is an explicit unresolved result, never a silent empty successful output.
- Cross-document checks compare the same person role. Never compare guardian name with applicant name as if both described the applicant. Fuzzy name matches only suggest review; they do not prove identity.
- Invalid or ambiguous dates/amounts stay flagged. Do not invent expiry periods, income limits, financial-year rules, or grade eligibility rules. Only implement constraints explicitly stated in the fictional JSON and label them fictional.
- All five supported types remain available; four are mandatory in the default demo, category certificate applies only when `category_certificate_required` is explicitly true.
- Completeness = `100 * satisfied applicable requirements / total applicable requirements`. Define requirement items in configuration. Exclude only resolved `not_applicable` items. If applicability or denominator is unresolved, output `null` with a reason rather than a misleading score. Handle empty configuration explicitly.
- Keep image quality separate from completeness. A numeric score cannot override unresolved checks.
- Return a list of issues plus an overall state: `ready`, `incomplete`, `needs_clearer_upload`, or `needs_review`. Define and test precedence. Recommended conservative order: unresolved review > unreadable required evidence > confirmed missing > ready. All individual issues remain visible regardless of the headline.
- For multipage documents preserve all pages and group evidence; do not assume page 1 contains all fields or call a document incomplete based on guessed page counts.

### Academic and data integrity

- All synthetic pages visibly state `SYNTHETIC - FOR ACADEMIC DEMONSTRATION`; no official seals, real IDs, or authenticity claims.
- Keep synthetic watermarks consistent across classes so they do not reveal the class. Class-specific generation metadata, filenames, reference labels, and applicant IDs are not model features.
- Preserve source provenance and consent for any real examples; use anonymized local copies and keep private data out of version control, logs, screenshots, and handoff files.
- Reference transcriptions/field annotations are for evaluation/training labels only, never inference shortcuts. Runtime must work with arbitrary user-selected paths and without access to ground-truth files.
- Synthetic generator output is provisional ground truth until reviewed. Application-level expected outcomes must be independently reviewed, not produced by calling the same requirement engine being evaluated.
- Independent review means checking visible source content and scenario definitions against annotations without treating the production pipeline's outputs as truth. A future agent may perform and document this reference review using a separate inspection/checking method. Student spot-checks are recommended, but student sign-off is not an added prerequisite for implementation or evaluation unless the user or course explicitly requires it.
- Do not claim students performed work merely because it was assigned to them. Record AI-assisted implementation and actual student review/contributions honestly.

## 3. Repository design and shared contracts

Only planning files and the preserved reference PDF exist initially. Create the following incrementally as the relevant sprint runs; do not generate empty placeholders for the entire application in S01.

```text
DIP_/
  AGENTS.md
  HANDOFF.md                         # current status + detailed backlog
  README.md                         # verified setup and commands as implemented
  pyproject.toml                    # package and dependency declarations
  requirements.lock.txt             # exact tested environment; generated after verification
  .gitignore
  configs/
    scholarship_demo.json
    preprocessing.json
    evaluation.json
  src/scholarready/
    __init__.py
    __main__.py                     # python -m scholarready
    cli.py
    schemas.py
    config.py
    ingestion.py
    quality.py
    preprocessing.py
    geometry.py
    ocr.py
    classification.py
    extraction.py
    requirements.py
    pipeline.py                    # common orchestrator, not duplicated in UI
    evaluation/
      ocr_metrics.py
      classification_metrics.py
      field_metrics.py
      readiness_metrics.py
      runner.py
  app/
    streamlit_app.py
  scripts/
    check_environment.py
    generate_pilot.py
    validate_dataset.py
    make_splits.py
    train_classifier.py
    run_experiments.py
    build_report_assets.py
    reproduce.py
  tests/                           # semantic unit, integration and regression checks
    fixtures/                      # tiny documented fictional examples
  data/
    README.md
    manifests/
    annotations/
    bundles/
    synthetic/
    private/                       # ignored; never committed
  artifacts/
    runs/                          # run-ID specific; large generated outputs ignored
    models/
    figures/
  docs/
    PROJECT_SPEC.md
    CONTRACTS.md
    DATASET_CARD.md
    METHODS.md
    EVALUATION_PROTOCOL.md
    ERROR_ANALYSIS.md
    REPRODUCIBILITY.md
    CONTRIBUTIONS.md
    SPRINT_HISTORY.md
    troubleshooting.md
    reference/DIP_Course_Project_Guidelines_2026.pdf
  output/
    report/
    presentation/
```

Use repository-relative paths inside saved manifests so the project can move. Record absolute commands for the students in each session's handoff. Library imports should have no side effects such as launching Streamlit or running OCR.

### Shared schema specification v1

S01 implements validated Python representations and documents serialization. Standard-library dataclasses plus explicit validation are sufficient; use another schema library only with justification. Required fields below can be extended deliberately with version migration. Do not introduce incompatible independent dictionaries in each module.

| Entity | Required information |
| --- | --- |
| DatasetRecord | `schema_version`, `sample_id`, `source_document_id`, `applicant_id`, `layout_id`, `relative_path`, `document_type`, `page_index`, `variant_id`, `degradation` (type, parameters, seed), source/consent category, source hash, annotation path, intended development role |
| SplitRecord | `sample_id`, `group_id`, `split` (`train`/`validation`/`test`/`development_only`), split seed, manifest version/hash; grouping must include every connected applicant/source reuse |
| PageImage | `document_id`, `page_id`, `page_index` (1-based), original filename, dimensions, color space, rasterization DPI if applicable, original image path, coordinate space |
| QualityAssessment | Raw brightness/contrast/blur measurements, resolution, heuristic flags, threshold/config version; do not call them calibrated probabilities |
| ProcessingResult | Page ID, branch ID, stage names/parameters/image paths/timings, processed dimensions, geometric transform and direction, errors |
| OCRToken | Text, box `[x, y, width, height]` in pixels, `page_id`, coordinate space, line/block IDs when available, engine confidence score or null |
| OCRResult | Ordered text, token list, engine/version/language/settings, page/branch IDs, runtime, explicit failure/empty status |
| DocumentPrediction | Supported class or `other`, decision state (`classified`/`uncertain`/`unreadable`/`error`), method/model version, scores and score kind, reason; keyword score is not a probability |
| ExtractedField | Field name, person role where relevant, raw text, normalized value or null, unit if applicable, page/filename, token references, box(es), coordinate space, engine score or null, validation state and reason |
| ApplicantProfile | Applicant reference and explicit `category_certificate_required` boolean or null; expected name optional and labelled as user input |
| RequirementDefinition | Unique ID, supported document type, required fields, conditional predicate if any, explicitly configured constraints, human action text |
| RequirementResult | Requirement ID, one allowed state, reasons/actions, supporting document/field/page references; conditional applicability and denominator treatment |
| ApplicationResult | Schema/config/run versions, document results, requirement results, issues, overall state, completeness or null and explanation, separate quality findings, timing |
| RunMetadata | Run ID, dataset/split/config/model hashes, code version or working-tree snapshot, Python/library/Tesseract versions, seeds, exact command, timing scope, output paths, exceptions |

### Extraction scope v1

| Type | Fields | Important distinctions |
| --- | --- | --- |
| marksheet | student_name, institution, academic_year, stated_total or stated_percentage when labelled | Do not infer percentage from a guessed denominator or reconstruct all subject tables |
| income_certificate | applicant_name and/or guardian_name as labelled, annual_income, issue_date | Preserve person role, currency, and annual/monthly unit; do not silently annualize ambiguous amounts |
| bonafide_certificate | student_name, institution, course, academic_year | Institution and student can both contain names; anchor/spatial evidence matters |
| domicile_certificate | applicant_name, domicile_region, issue_date | Do not infer state from an unrelated address line without a declared extraction rule |
| category_certificate | applicant_name, stated_category, issue_date | Extract the printed label; do not infer a category from a person's name |

The demo checklist should require only a documented subset of these fields. Extracted optional fields are not automatically required. Publish that distinction in JSON, the UI, and evaluation.

### Planned command interface

S01–S08 forms are implemented, including `analyze --bundle <input-only-json>`, `--branch A|B|C` and `--preprocessing configs/preprocessing.json`; output directories must be new. S05 additionally implements splitting, training and `--classifier <trusted-model-directory>`. Local Streamlit launch is implemented; S09–S11 evaluation/reproduction forms remain planned. Exact successful invocations and current limits are in README and sprint verification records.

```bash
# S01
python scripts/check_environment.py

# S02
python scripts/generate_pilot.py --output data/synthetic/pilot --seed 42
python scripts/validate_dataset.py --manifest data/manifests/pilot.jsonl

# S03 and later
python -m scholarready analyze --input <image-pdf-or-directory> --profile configs/scholarship_demo.json --applicant-profile <profile-json> --branch A --output <run-directory>
python -m scholarready demo --output <run-directory>

# S05
python scripts/make_splits.py --manifest <manifest> --output <split-manifest> --seed 42
python scripts/train_classifier.py --manifest <manifest> --splits <split-manifest> --branch <fixed-branch> --output <model-directory>

# S08
.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501

# S09/S10
python scripts/run_experiments.py --config configs/evaluation.json --partition validation
python scripts/run_experiments.py --config configs/evaluation.json --partition test

# S11
python scripts/reproduce.py --mode smoke
python scripts/reproduce.py --mode final
```

Do not write handoff instructions that assume shell aliases or an activated virtual environment from a previous chat. Use the environment's exact interpreter path where helpful.

## 4. Six-week schedule and team learning plan

This is a relative schedule, adjustable to actual course dates, access, and measured workload.

| Suggested week | Sprints | Milestone |
| --- | --- | --- |
| 1 | S01-S03 | Verified setup, small labelled pilot, smallest real end-to-end CLI |
| 2 | S04 | Visible DIP methods and saved comparison images |
| 3 | S05-S06 | Learned classification and evidence-linked extraction |
| 4 | S07-S08 | Conservative readiness behavior and complete local UI |
| 5 | S09-S10 | Expanded reviewed data, frozen experiments, actual findings |
| 6 | S11-S12 | Reproducible submission, report, presentation and viva |

### Planned leads, not claims of completed student work

- Sakshi Gupta: image acquisition/degradation, quality assessment, DIP methods/geometry, visual comparisons, DIP methodology explanations.
- Jigisha Baiswar: annotation coordination, OCR organization, classification, field extraction, requirement configuration and evaluation explanations.
- Joint: contracts, integration, dataset review, final experiments, report, demonstration, and all-pipeline viva preparation.
- Every sprint includes a short learning note and joint review questions. Update `docs/CONTRIBUTIONS.md` with actual work and review status, separating AI-assisted implementation from student verification. Neither student should be restricted to knowing only her assigned module.
- Missing roll numbers, approved submission format, actual final deadline, and instructor feedback are administrative unknowns. Leave labelled placeholders where required; they do not block coding.

## 5. Detailed sprint cards

### S01 — Foundation, verified environment, and shared contracts

**Dependency:** none. **Suggested leads:** joint; Sakshi reviews image contracts, Jigisha reviews field/checklist contracts.

**Purpose:** establish one compatible environment and one shared vocabulary before modules diverge. This sprint does not claim a full document-analysis application exists.

**Tasks**
- [x] Inspect the workspace, Python versions, installed Tesseract executable, and English language data. Use an isolated `.venv`; avoid changing global Python packages.
- [x] Check official compatibility information and resolve the selected stack together. Test imports and run `pip check` before generating an exact lock. Record platform/Python assumptions. Tesseract is a separately installed executable; `pip install pytesseract` alone is insufficient. Document system setup and OS alternatives; install only as authorized/available.
- [x] Verify PDF rendering through pypdfium2 using a tiny fictional PDF; record dimensions/DPI and validate image color/lifetime handling.
- [x] Create package metadata, minimal package entry point, `.gitignore`, environment checker, validated schemas/config loader, and the fictional scholarship JSON. Do not build all later modules as empty stubs.
- [x] Define required versus optional fields, conditional category behavior, status vocabulary, score semantics, and shared coordinate conventions in `docs/CONTRACTS.md`.
- [x] Create `docs/PROJECT_SPEC.md` with guideline-to-project mapping, objectives, limitations, architecture, registration draft, and assumptions. Initialize `docs/CONTRIBUTIONS.md` and troubleshooting notes.
- [x] Replace README setup placeholders with verified commands only; record installed versions and the exact interpreter path in the handoff.

**Expected files:** `pyproject.toml`, `requirements.lock.txt`, `.gitignore`, `src/scholarready/{__init__,__main__,schemas,config}.py`, `scripts/check_environment.py`, `configs/scholarship_demo.json`, `docs/{PROJECT_SPEC,CONTRACTS,CONTRIBUTIONS}.md`, `docs/troubleshooting.md`, relevant schema/config tests.

**Acceptance and verification**
- Environment checker reports actual Python, OpenCV, Tesseract executable/version, English language data, and renderer availability; missing components produce actionable errors.
- Imports and `pip check` pass in the selected environment. Any unverified OS claims are labelled, not described as tested.
- Demo config and schema examples round-trip; invalid statuses, malformed boxes, contradictory config, and ambiguous conditional attributes have explicit handling.
- A real renderer smoke check passes. Any OCR smoke invocation is reported as an environment check, not performance evidence.
- Both students have a plain-language explanation of pipeline boundaries and the separate OCR executable.

**Typical problems:** missing `eng` data; executable absent from PATH; incompatible NumPy wheels; editable package not installed; PDF/image buffers closed before copying. Record actual fixes, not speculative success.

**Next handoff:** point to S02 only after the environment and contracts are usable; list exact setup commands and known platform limitations.

### S02 — Pilot dataset, annotations, and provenance

**Dependency:** S01. **Suggested leads:** Sakshi generates/captures images; Jigisha coordinates annotation and bundle review.

**Purpose:** create a small understandable development dataset before investing in training or a UI.

**Tasks**
- [x] Generate approximately 30 independent, clearly labelled fictional source pages across five supported types plus `other`, with varied applicants and at least two practical layouts where feasible. State the actual counts; do not duplicate one page and call it a new independent source.
- [x] Include JPG/PNG and single/multipage PDF fixtures. Keep clean pages and deterministic degraded variants linked by source IDs; initially test low contrast, rotation, blur/noise, and compression.
- [x] Store reference text, selected-field values, person roles, and available field boxes. Preserve full-page reference text for OCR metrics, not only the desired fields.
- [x] Create complete, missing-document, conditional-not-applicable, unreadable, and mismatch application scenarios. Mark expected labels provisional until separately reviewed; never call the production engine to generate its own ground truth.
- [x] Implement manifest validation: unique samples, real paths, readable pages, valid boxes, known classes, source links, consistent applicant IDs, hashes, annotation completeness and no accidental real identifiers.
- [x] Document provenance, generation parameters, seeds, layout coverage, known bias, intended uses, and development-only status in the dataset card. Keep generated bulk artifacts separate from tiny versioned fixtures.
- [x] Explain how independent reference review is performed; record reviewer/method and reviewed/unreviewed counts honestly. The agent can inspect generated pages and annotations independently; do not invent student approval or stop solely to request it. Keep unreviewed references provisional until checked before final test freeze.

**Expected files:** `scripts/{generate_pilot,validate_dataset}.py`, `data/manifests/pilot.jsonl`, annotations and bundle manifests, small fictional fixtures, `docs/DATASET_CARD.md`, `data/README.md`.

**Acceptance and verification**
- Generator is reproducible for a fixed seed; validator passes on the generated pilot and detects deliberately broken source links/annotations.
- All six labels have actual examples; class/source/variant counts are reported separately.
- At least one multipage input and all named readiness scenarios have inspectable examples.
- Reference-review status and method are explicit. Development fixtures are not described as final held-out evidence.
- No data/model inference path has been written to read annotation labels as answers.

**Typical problems:** watermark/template reveals class, source IDs change for augmentations, repeated applicant data crosses groups, transcription omits visible synthetic labels. Fix the data contract rather than hiding these issues.

**Next handoff:** S03, with exact generator/validator commands and sample bundle paths.

### S03 — Raw OCR and the smallest end-to-end CLI pilot

**Dependency:** S02. **Suggested leads:** Jigisha leads OCR and minimal extraction; Sakshi validates ingestion and image coordinates.

**Purpose:** prove the full upload-to-finding path with real OCR before adding complexity. This is the first end-to-end milestone, not a final-performance claim.

**Tasks**
- [x] Implement image/PDF ingestion, stable document/page IDs, EXIF orientation, alpha compositing, filename/page provenance, explicit corrupt/encrypted/unsupported input errors, and bounded page/image processing.
- [x] Implement branch A using real local Tesseract tokens/text/confidence. Record segmentation/language settings, executable version, per-page runtime, blank/error status, and a useful timeout.
- [x] Implement keyword classification, a limited label-anchor extraction baseline on pilot layouts, and a simple real checklist evaluator using shared schemas. These are functioning baselines to strengthen in later sprints, not mocks returning canned results.
- [x] Add the shared pipeline orchestrator, CLI `analyze` and reproducible `demo` command. Input directories/bundles must not load label manifests as inference evidence.
- [x] Return minimal evidence-linked JSON with required uncertainty states. A missing value should be null with a reason, not an invented successful extraction.
- [x] Implement reference-based CER/WER with documented normalization and empty-reference behavior; save development-only baseline results and run metadata.
- [x] Document a small run example, expected output shape, actual observed findings, and limitations. Include CLI-only instructions before a UI exists.

**Expected files:** `ingestion.py`, `ocr.py`, baseline `classification.py`, `extraction.py`, `requirements.py`, `pipeline.py`, `cli.py`, `evaluation/ocr_metrics.py`, CLI fixtures/integration checks, baseline artifact directory, README example.

**Acceptance and verification**
- A real clean fictional bundle traverses input -> OCR -> class -> limited fields -> checklist -> JSON without consulting reference annotations.
- Missing-document and unreadable-upload examples do not become a false `ready` result; an ambiguous unreadable upload is not automatically called a missing type.
- PDF pages retain correct provenance, and corrupt input produces an explicit failure result.
- At least one actual Tesseract integration run is recorded. Token-fixture unit checks cannot substitute for this.
- CER/WER examples with known edits and empty outputs behave as documented; results contain run/sample IDs.

**Typical problems:** Tesseract returns no text, OCR line order is unstable, regex grabs a date from another field, a partial page failure is silently dropped. Preserve uncertainty and inspect the original/token boxes.

**Next handoff:** S04, linking the smallest working command and first genuine development run.

### S04 — DIP methods, image quality, and intermediates

**Dependency:** S03. **Suggested lead:** Sakshi; Jigisha checks downstream OCR effects.

**Purpose:** make the course's DIP contribution inspectable and measurable.

**Tasks**
- [x] Implement original-image brightness/contrast/resolution and blur indicators with configurable heuristic flags. Keep raw measurements and explain their limits.
- [x] Implement B (grayscale + Otsu) and configurable C with deskew, CLAHE, denoising choices, adaptive thresholding, and morphology. Keep no-op controls and avoid applying unsupported correction assumptions blindly.
- [x] Compare practical small kernels such as 1x2, 2x1, and 2x2, plus identity; state text foreground convention and opening/closing order. Demonstrate that a method can damage decimal points or join strokes.
- [x] Estimate skew conservatively; test with known rotations and blank/low-text pages. Record coordinate transforms and preserve the original. Perspective correction is optional and should not hold up the required core.
- [x] Save every enabled stage image, histogram/comparison figures, configuration snapshot, OCR result, and timing under a unique development run ID.
- [x] Use the same OCR settings for the paired A/B/C comparison. Define an ablation matrix for deskew/CLAHE/filtering/threshold/morphology, with pipeline order held explicit.
- [x] Update methods and troubleshooting documentation with algorithm purpose, parameters, and harm cases.

**Expected files:** `quality.py`, `preprocessing.py`, `geometry.py`, `configs/preprocessing.json`, `docs/METHODS.md`, real comparison figures and stage-image artifacts, meaningful geometry/preprocessing checks.

**Acceptance and verification**
- A/B/C run on the same development pages with matching engine settings and recorded parameters.
- Saved intermediate images demonstrate contrast/thresholding/morphology contributions and at least one detrimental or no-improvement case if observed; do not fabricate one.
- Known-coordinate tests verify transformations or explicitly restrict overlays to processed coordinates.
- Blank/noisy/small pages do not crash the pipeline or yield confident readability from an unvalidated constant.
- No assertion or report assumes C outperforms A; measured development CER/WER and runtime are shown as observed.

**Next handoff:** S05, linking configs, branch definitions, figures and ablation plan.

### S05 — EDA, grouped splitting, and document classification

**Dependency:** S04. **Suggested lead:** Jigisha; Sakshi reviews degradation/layout breakdowns.

**Purpose:** add the explicit Data Science component without leaking related documents into validation/test.

**Tasks**
- [x] Produce EDA covering classes, independent applicants/sources, layouts, degradation groups, OCR text length, missing labels, and quality distributions. Count augmented pages separately.
- [x] Implement reproducible grouping by connected applicant/source reuse, including source hashes and bundle reuse. Split source groups before augmentation or propagate their split to every variant. Aim for sensible train/validation/test proportions only when group/class counts permit; do not force an invalid stratification.
- [x] Mark tiny pilot partitions development-only if they cannot support reliable claims. Protect final-test roles for later reviewed data; do not tune to an early convenience test set and relabel it final.
- [x] Train a scikit-learn `Pipeline` containing TF-IDF and Logistic Regression on OCR text. Fit vectorizer/model only on training data; tune using grouped training folds/validation as appropriate.
- [x] Compare the trained model to the existing keyword baseline on the same partition. Include `other`; separately handle empty text and uncertain scores with validation-selected thresholds.
- [x] Save model plus class mapping, feature policy, training sample IDs/hash, OCR/preprocessing settings, seed, dependency versions, and validation results. Never infer class from filename/path/applicant ID.
- [x] Add a deliberately unseen-layout check if feasible, clearly separated from development tuning and future final-test selection.

**Expected files:** `scripts/{make_splits,train_classifier}.py`, strengthened `classification.py`, split manifests, EDA/classification figures, `evaluation/classification_metrics.py`, model metadata, leakage validation checks.

**Acceptance and verification**
- Automated overlap checks confirm no connected applicant/source group or variant crosses partitions. Deliberately broken examples are rejected.
- Keyword and learned macro-F1/per-class results and a confusion matrix are generated from actual development predictions, with counts and support.
- Text from empty/unsupported/ambiguous uploads produces conservative outcomes. Confidence is labelled by score kind; model scores are not claimed calibrated unless evaluated.
- A saved model reloads and produces reproducible predictions; reference labels are used only as labels/evaluation, never features.

**Typical problems:** all examples from a class land in one group, augmentation inflates apparent sample size, filenames encode document class, vectorizer fitted before splitting. Resolve and document these before reporting gains.

**Next handoff:** S06 with split policy, exact training command, model path and honest limitations.

### S06 — Spatial field extraction and evidence

**Dependency:** S05. **Suggested lead:** Jigisha; Sakshi verifies boxes and transformed coordinates.

**Purpose:** extract the documented fields with inspectable evidence rather than untraceable regex guesses.

**Tasks**
- [x] Use OCR line/token grouping, label anchors, nearby-region rules, and regular expressions for the v1 field table. Support documented synonyms and multiple development layouts.
- [x] Distinguish student/applicant/guardian names, annual/monthly units, stated totals/percentages, and issue/academic dates. Preserve raw text alongside normalized values.
- [x] Return null plus explicit states for absent, unreadable, ambiguous, invalid, or unsupported fields. Field-level uncertainty and a genuinely absent printed field are different cases.
- [x] Preserve filename/page/token references, boxes, coordinate space, confidence source, and normalization decisions. Highlight evidence on the correct image.
- [x] Define and validate normalization rules per field. Do not treat two equally wrong OCR values as accurate merely because a loose fuzzy matcher accepts them.
- [x] Implement per-field normalized exact-match evaluation, missing/extra output accounting, and support counts. Report extraction with true document types separately from end-to-end predicted-type routing to expose classification errors.
- [x] Add representative and adversarial fixtures: multiple dates, guardian/student names, monthly income, cropped labels, faint decimal, missing summary total, unfamiliar layout.

**Expected files:** strengthened `extraction.py`, extraction documentation, `evaluation/field_metrics.py`, annotated evidence figures, focused semantic regression checks.

**Acceptance and verification**
- Every non-null extracted value can be traced to OCR evidence and a documented normalization rule.
- All five supported types have field coverage and per-field counts; unsupported fields return explicit states.
- Multiple dates/names do not silently pick the first occurrence without a reason.
- Original and processed coordinate overlays are correct or restricted/labeled honestly.
- Real field metrics and failure examples are recorded without substituting reference annotations for predictions.

**Next handoff:** S07, documenting field limitations and critical-field configuration.

### S07 — Full requirement engine and conservative readiness

**Dependency:** S06. **Suggested lead:** Jigisha; joint scenario review.

**Purpose:** convert document evidence into actionable findings while preserving uncertainty.

**Tasks**
- [x] Implement complete JSON-configured requirement logic and validation, including four default mandatory documents and explicit conditional category requirement. Keep supported optional fields distinct from configured required ones.
- [x] Implement all five requirement states, conditional unknown handling, multi-document/page evidence aggregation, duplicate/conflicting evidence handling, and unresolved upload inventory behavior.
- [x] Implement semantic name normalization and review-only fuzzy comparison for matching person roles. Add explicitly configured date/unit/format checks without inventing real scholarship rules.
- [x] Define headline-state precedence, complete issue list, actions, completeness denominator/unknown behavior, and independent image-quality display data.
- [x] Create independently specified scenario expectations for complete, absent, unreadable, unknown class, conditional true/false/unknown, name mismatch, role distinction, conflicting duplicate, and processing failure cases.
- [x] Implement missing-requirement and application-outcome metrics, including false-ready behavior and zero-denominator handling.
- [x] Update pipeline JSON and CLI documentation; explain the rules in plain language for students and users.

**Expected files:** strengthened `requirements.py`, demo JSON, `evaluation/readiness_metrics.py`, scenario tests/annotations, contract/method updates.

**Acceptance and verification**
- No intentionally unresolved or incomplete scenario is incorrectly marked ready in the specified regression fixtures. This is a fixture check, not a claim of zero real-world false-ready rate.
- An unclassified/unreadable upload is not silently converted into confirmed absence; an unknown conditional attribute is not treated as not-applicable.
- Changing JSON requirements changes results without editing application logic.
- Completeness agrees with named requirement items, handles unknown applicability, and cannot override open required checks.
- Expected scenario outcomes are reviewed independently of the implementation; unresolved review status is recorded and addressed before final freeze.

**Next handoff:** S08 with a reliable CLI example for every major outcome.

### S08 — Streamlit interface and complete local user flow

**Dependency:** S07. **Suggested leads:** Sakshi leads image inspection, Jigisha leads requirement/result views; joint integration.

**Purpose:** let a student inspect how a document produced its findings using the already verified shared pipeline.

**Tasks**
- [x] Build local multi-file JPG/PNG/PDF upload, explicit profile/applicant attributes, page navigation, branch selection for academic comparison, processing progress, and actionable errors.
- [x] Show original and processed pages, stage images and quality indicators, OCR/evidence overlays, extracted values with reasons, document-type uncertainty, and checklist findings/actions.
- [x] Show the fictional-profile label and document-readiness scope in concise user language. Keep implementation details in an optional experiment view where they help interpretation.
- [x] Support explicit document-type hints and editable profile information without presenting user input as verified OCR. If manual corrections are allowed, preserve their provenance and keep uncorrected automated results separate in evaluation.
- [x] Export application JSON and a simple findings CSV using the same result schema. Avoid claiming a report-PDF export exists unless implemented and verified.
- [x] Manage temporary uploads, session state, cache keys, reruns, and errors so one application's data or profile does not contaminate another's result. Bound page/file processing and clean temporary files.
- [x] Exercise the actual browser flow if available, including PDF upload, conditional changes, error handling, evidence views, and downloads. Record precisely which checks were possible.

**Expected files:** `app/streamlit_app.py` and small UI helpers if needed, updated README, verified UI screenshots, integration checks around shared pipeline/export behavior.

**Acceptance and verification**
- A student can launch locally, upload a fictional bundle, select attributes, inspect evidence, and download results using documented steps.
- The UI and CLI yield equivalent semantic results for the same inputs/config/model; timestamps/run paths may differ.
- Conditional-profile changes invalidate results correctly; processing failures remain visible.
- Complete, missing, unreadable, mismatch, other-document, and multipage examples are exercised through the real flow when tools permit.
- If browser tooling is unavailable, record the exact unverified acceptance items and keep the sprint open until an authorized browser/student check supplies evidence.

**Next handoff:** S09 with launch command, screenshots, and any unresolved UI limitations.

### S09 — Expanded data, validation tuning, and frozen protocol

**Dependency:** S08. **Suggested leads:** joint; Sakshi on visual diversity, Jigisha on annotation/split/label review.

**Purpose:** prepare credible final evidence without changing methods after seeing final-test performance.

**Tasks**
- [ ] Expand independent sources toward the practical target (roughly 250-350 total if feasible) and several layouts per type. Include diverse unsupported examples, clear/degraded pages, and varied bundle scenarios. Record actual totals and any smaller-sample justification.
- [ ] Review text, fields, class labels, grouping and expected bundle outcomes independently of production predictions, using source-page inspection and scenario definitions. Record method and actual reviewer/agent involvement; agent review is acceptable and must not be represented as student sign-off. Only checked samples enter the final-test role. Unreviewed data remains development-only.
- [ ] For real images, document consent/anonymization and report synthetic versus real results separately. If no real images exist, explicitly limit claims to synthetic conditions.
- [ ] Construct final immutable grouped splits before tuning. Keep source/applicant/bundle connected components together. Reserve unseen layouts if sample size supports it; record whether claims concern known or unseen layouts.
- [ ] Tune preprocessing, kernels, OCR modes if part of a separate experiment, classifier hyperparameters, and uncertainty thresholds only on training/validation. If earlier pilot data has been inspected heavily, keep it in development/train roles.
- [ ] Freeze A/B/C definitions, ablations, downstream model policy, field normalization, requirements, metric definitions, timing scope, seeds, trained model, and run commands. Write `docs/EVALUATION_PROTOCOL.md` and `configs/evaluation.json` with hashes/versions and chosen dataset IDs.
- [ ] Declare two comparison questions: (1) preprocessing effects with downstream components/settings fixed, and (2) optional end-to-end variants with any retraining changes explicitly identified. Avoid attributing combined changes solely to DIP.
- [ ] Check that validation outputs are reproducible, test predictions/metrics have not been inspected, and acceptance/support counts are sufficient or limits are clearly documented.

**Expected files:** final dataset/annotation/bundle manifests, frozen splits, updated dataset card, validation runs, final model metadata, `configs/evaluation.json`, `docs/EVALUATION_PROTOCOL.md`, a freeze record with artifact hashes.

**Acceptance and verification**
- No applicant/source/variant/bundle leakage; exact/near-duplicate checks and grouping evidence are recorded.
- Every final-test item has a reviewed reference and immutable split role; source counts and class/layout/degradation support are explicit.
- Chosen parameters/model and all metric definitions are frozen with reproducible commands. Final-test consumption remains `NO`.
- If reference content cannot be inspected or checked reliably, continue useful development/validation and record the concrete missing evidence; do not label unchecked references validated. Do not add a student-approval gate merely because student spot-checks would be helpful.
- No result file contains invented performance values or placeholders masquerading as measurements.

**Next handoff:** S10 with exact frozen command, freeze hash, paths and statement that test is still untouched.

### S10 — Final evaluation, ablations, and failure analysis

**Dependency:** S09. **Suggested leads:** Sakshi leads DIP ablations/visual failures; Jigisha leads classifier/extraction/readiness analysis.

**Purpose:** answer the research questions with measured, traceable evidence.

**Tasks**
- [ ] Validate the freeze/hashes and execute the declared final-test runs on identical sample IDs. Mark `Final test consumed` as `YES` with run IDs/date once actually evaluated; this must survive future chats.
- [ ] Report A/B/C CER/WER, classification macro-F1 and per-class confusion, per-field extraction accuracy, missing-requirement precision/recall/F1, application-outcome agreement, false-ready rate, and runtime. Record supports, exclusions, crashes and unresolved outputs.
- [ ] Execute the frozen no-step and morphology-kernel ablations. Do not pick per-test-page winners from ground truth. Report neutral or negative improvements honestly.
- [ ] Separate true-type versus predicted-type field extraction, known/unknown layout, synthetic/real, and degradation breakdowns where support permits. Use applicant/source-group resampling for uncertainty intervals if implementing them; do not treat variants as independent observations.
- [ ] Generate tables/plots directly from run artifacts and provenance IDs. Save per-sample and per-bundle predictions/errors, not just aggregate screenshots.
- [ ] Choose representative success/failure cases and explain causes: blur, cropping, threshold damage, merged strokes, wrong class, unfamiliar label, ambiguous date/name/units, unresolved applicability, or unsupported input.
- [ ] Write a concise evidence-backed error analysis and limitations. If a software bug requires a post-test change, document the defect and every rerun; do not tune to test or quietly replace the original run. A new confirmatory holdout may be needed for changed methods.

**Expected files:** `scripts/{run_experiments,build_report_assets}.py`, completed evaluation runner/metrics, immutable final run directories, tables/figures, `docs/ERROR_ANALYSIS.md`, protocol/run registry updates.

**Acceptance and verification**
- Every reported number traces to predictions, reviewed references, a metric definition, sample IDs and run metadata.
- Core comparisons use the same held-out items; failures are not silently removed from denominators.
- Ablations and visual intermediates substantiate DIP claims. Negative results remain visible.
- Final-test consumption and any reruns are recorded. This sprint does not remain open simply because results are unimpressive.
- Results contain the predeclared false-ready denominator and count; an empty denominator is `not estimable`, not a fabricated zero.

**Next handoff:** S11 with frozen report asset paths and measured findings, including their limits.

### S11 — Reproduction package and fresh-environment checks

**Dependency:** S10. **Suggested leads:** joint; each follows the other's setup/module instructions.

**Purpose:** make the project executable by an instructor without relying on this chat or an existing machine session.

**Tasks**
- [ ] Finalize verified installation instructions, exact tested Python/package/Tesseract versions, English language data, renderer setup, and OS-specific unverified notes. Preserve the lock and OS metadata.
- [ ] Implement a smoke reproduction command that checks environment, generates/loads small fictional inputs, runs CLI and checks expected semantic outcomes without retraining or touching final test unnecessarily.
- [ ] Implement a final reproduction mode using the frozen protocol/artifacts; state whether it regenerates data, trains or loads a model, evaluates test, and how long it actually takes on the measured machine.
- [ ] Verify package install/imports and a clean isolated environment; run meaningful behavior/integration checks, `pip check`, CLI demo, model reload, and a UI launch check. Do not claim Windows/macOS were tested if only Linux was used.
- [ ] Remove hard-coded original workspace assumptions from executable code/manifests. Document offline/runtime network requirements, generated artifact locations, dataset/model provenance and private-data exclusions.
- [ ] Review README and troubleshooting against actual commands, and publish a submission inventory linking source, data description, architecture, comparisons, stage images, analyses and run IDs.
- [ ] Resolve broken links/status pointers and re-run only tests relevant to fixes; record changes that could invalidate frozen results rather than silently updating model behavior.

**Expected files:** `scripts/reproduce.py`, `docs/REPRODUCIBILITY.md`, finished README, final lock/setup notes, submission inventory, environment verification logs.

**Acceptance and verification**
- Smoke reproduction succeeds from a newly created isolated environment using documented commands; actual constraints are recorded.
- Saved model/config and sample input yield the expected documented result; no runtime dependence on reference answers.
- All deliverable paths exist and are appropriately included or reproducibly generated; private data and local environments are excluded.
- Final run artifacts remain traceable and preserved; no unnecessary retraining/testing changes the story.

**Next handoff:** S12 with the complete verified submission inventory and remaining report metadata placeholders.

### S12 — Final report, slides, demo, and viva handover

**Dependency:** S11. **Suggested leads:** joint; Sakshi presents DIP rationale, Jigisha presents classification/extraction/readiness, both explain the full flow.

**Purpose:** communicate the implemented system and actual findings in a form suitable for course assessment.

**Tasks**
- [ ] Use verified source code/results to author the report: abstract, problem/scope, guideline connection, related work with verified citations, dataset/provenance, architecture, DIP methods, OCR/classifier/extraction/rules, experiments, actual results, failures, limitations, conclusion, reproduction steps and contributions.
- [ ] Include baseline/alternative tables, intermediate image panels, bounding-box evidence, actual dataset/support counts, confusion matrix, ablations and false-ready analysis. Do not write anticipated results as measured findings.
- [ ] Prepare a short presentation and a timed demonstration with complete, missing, unreadable and mismatch examples. Label any prerecorded fallback and use only fictional/anonymized documents.
- [ ] Create beginner-friendly viva notes explaining Otsu versus adaptive thresholds, CLAHE, filtering, opening/closing and kernels, skew/coordinates, CER/WER, TF-IDF/Logistic Regression, grouped leakage prevention, field evidence, conditional rules, and false-ready risk.
- [ ] Finalize actual contribution statements and unresolved administrative placeholders. Leave roll numbers/institution/format as clearly flagged unknowns if unavailable rather than inventing them. Obtain student review where required for claims of sign-off.
- [ ] Use appropriate document/presentation/PDF skills when generating those formats; render and visually inspect final artifacts. Follow a provided institutional template if one becomes available. Until one is provided, document a simple academic format as a recommendation.
- [ ] Run the final submission inventory/link checks, confirm the launch/demo commands, update every sprint state honestly, and write a final handoff entry with known limitations and future extensions.

**Expected files:** final report in agreed editable/export formats, slides, demo script, viva notes, contribution statements, final deliverable inventory under `output/` and `docs/`.

**Acceptance and verification**
- Every numerical claim matches frozen artifacts; citations support related-work claims; no company sponsorship/authenticity/award claims appear.
- Report/slides render legibly with verified figures, labels, equations, and paths; outputs are opened/inspected using available tooling.
- A real demonstration follows the script and distinguishes automatic findings, uncertainty and any manual correction.
- Both students receive full-pipeline explanations and review prompts. Do not assert they mastered the material or approved a document without their actual response.
- All remaining work/unknowns are explicit. Mark implementation complete only when deliverables and required checks are complete; do not auto-publish or submit them.

**Final handoff:** set next sprint to `NONE` only if all criteria are met; list final files, launch/reproduction commands, measured limitations, and any student-only administrative actions.

## 6. Evaluation definitions to implement and freeze

These definitions prevent different chats from reporting incompatible metrics. S09 records exact normalization choices and scripts before S10.

- **CER:** character-level edit distance divided by reference character count; **WER:** token-level edit distance divided by reference word count. Report corpus totals plus per-document distributions as appropriate. Empty reference/prediction cases need explicit conventions and separate counts; do not divide by zero or discard blank pages silently. Error rates can exceed 1 when insertions are high.
- **Normalization:** preserve raw OCR and reference text. Fix case/whitespace/Unicode policies for OCR; use field-specific policies for dates/names/amounts. Never tune normalization on final-test errors to hide them.
- **Classification:** macro-F1 over a fixed declared label set; per-class precision/recall/F1/support and confusion matrix. Report abstentions/uncertain/unreadable cases separately and in a documented end-to-end accounting. Do not increase apparent accuracy by dropping them.
- **Fields:** normalized exact-match accuracy by field, with denominator including required target fields that were not extracted. Also count missing/invalid/extra predictions and distinguish true-type extraction from predicted-type end-to-end performance. Reference `absent` is different from a blank annotation.
- **Missing requirements:** treat confirmed `missing` as the positive label for the declared per-requirement binary metric; separately tabulate unreadable/review and conditional states. Class labels and expected outcomes come from reviewed reference bundle annotations.
- **Application outcomes:** agreement/confusion over the documented overall-state vocabulary. **False-ready rate** = reference non-ready applications predicted ready / all reference non-ready applications. Also show raw count; optionally report false-ready share among predicted-ready applications with its own clearly named denominator.
- **Runtime:** report hardware, page resolution/count, cold/warm conditions and whether load, OCR, classification, model training and UI overhead are included. Separate preprocessing/OCR/end-to-end time; do not compare differently scoped durations as equivalent.
- **Ablations:** fixed definitions, paired samples and fixed downstream settings where isolating DIP. Include no-morphology and multiple small kernels, plus step removal. Report all predeclared branches, not only the winner.
- **Uncertainty/support:** break results down only where sample counts allow interpretation. Preserve source/applicant grouping in any resampling. Clearly state limited synthetic/template generalization and avoid invented statistical significance.
- **Provenance:** every table/figure links to run ID, dataset/split/config/model/code state and actual prediction files. Placeholder values should be `NOT MEASURED`, never a fake 0 or 95%.

## 7. Verification policy

- Documentation-only sprint preparation needs path/link/status consistency checks, not an artificial application test suite.
- During implementation, test meaningful contracts and failure modes: no label leakage, source grouping, conditional applicability, unreadable versus missing, false-ready prevention, unit/person-role extraction, coordinates, multipage evidence, and actual CLI/OCR flow.
- Distinguish deterministic token-fixture unit checks from real OCR integration. A skipped integration check is not a passed environment capability.
- Run appropriate checks for each change and required sprint criteria; repeat/broaden only for new changes, failures or unresolved concerns.
- Record command, exit status and relevant outcome, not merely "tested". Never mark `DONE` on unverified claims or a running server process alone.
- On browser/document-rendering limitations, record exact missing evidence and resume action. Keep required acceptance items open instead of asking users to trust an unseen output.

## 8. Decisions, assumptions, blockers, and artifact pointers

### Decision log — append or supersede explicitly

| Date | Decision | Reason / revisit condition |
| --- | --- | --- |
| 2026-11-04 | S08 uses one session-owned disposable run, full input/settings/model/source identity and no global applicant cache; no manual OCR correction | Shared pipeline/schema for CLI/UI/evaluation, raw uploads removed after inference, evidence cleaned on change/clear; disconnect cleanup follows session expiry/GC. JSON/CSV export findings, not images/PDF reports. |
| 2026-11-04 | S08 renders tri-state applicability explicitly and resets widgets by assigning defaults rather than deleting keys | Actual browser exposed unknown bools as unchecked and old browser values resurrecting after key deletion. Fixed; final native null table and prior-name/Yes reset verified. Headless checks alone did not reveal these defects. |
| 2026-11-04 | S08 stable corrupt-image diagnostic omits PIL BytesIO addresses; pipeline optionally emits page progress | Ten actual OCR CLI/UI pairs and native downloaded result match semantically. Readiness rules/config/model/data unchanged. 223 full-suite +24 final focused, actual browser flows/downloads and 442 artifact hashes verified. |
| 2026-11-04 | S07 `requirements-s07-1.0` accepts complete agreeing duplicates once, retains conflicts and refuses to splice incomplete separate files | Required subset unchanged; matching roles and comparison-only NFC/case/punctuation normalization; fuzzy scores only explain review. Implicated name-conflict items now need review. |
| 2026-11-04 | S07 `demo-1.1` adds explicit ISO-date regex; inclusive issue-date bounds are opt-in JSON constraints | No default expiry/age/income/academic limits; all conventions fictional. Engine version is an additive optional schema-v1 field. |
| 2026-11-04 | S07 expectations are hand-specified in a distinct same-agent review pass, with inputs separated from post-inference references | 33 token +12 real CLI scenarios match; fixture false-ready counts 0/24 and0/9 are not population evidence. Blank-anchor ambiguity and zero denominators stay tested. No final-test promotion/student sign-off. |
| 2026-11-04 | S06 uses delimiter/standalone labels, bounded aligned regions, strict per-field normalization and complete repeated-candidate evidence | A broad colonless synonym initially treated CATEGORY CERTIFICATE as a field. Regression now rejects it. Unknown/cropped labels remain unresolved; no first-date/name/global regex fallback. |
| 2026-11-04 | S06 absence requires a printed marker; monthly income stays monthly; all unresolved normalized values are null | Avoids inferring omitted physical fields, silently annualizing, guessing numeric dates/decimal points or hiding conflicting pages. Required-field subset/config unchanged; full rules remain S07. |
| 2026-11-04 | S06 reuses fixed S05 A OCR/model/splits and scores exact value+unit+role after saved inference; evaluates train diagnostic/validation only | All five types have per-field counts; 169/180 present validation targets, 36/36 clean. Five wrong nonnull values remain errors. Layout probe excluded; final test NO. |
| 2026-11-04 | S05 keeps all pilot outer roles development_only; connected applicant/source/hash/file/input-bundle grouping yields four groups | Mismatch connects applicants 4+5. Fit only 12 clean pages in two train groups; validation has one linked group. No final-test data created or consumed. |
| 2026-11-04 | S05 fixed TF-IDF/LR C=4, seed 42; validation selected probability 0.4/margin 0.2 with fixed vocabulary/dual-title guards | Only two train groups preclude a reliable search/calibration claim. Untuned layout-A-to-B diagnostic uses 0.4/0.1 before tuning; six pages remain a small synthetic diagnostic. A stays default; model is optional in shared CLI/pipeline. |
| 2026-11-04 | S04 keeps A as default; C uses ordered configurable stages with identity 1×1 opening/closing and explicit no-step controls | Fixed 12-variant development comparison found A/B/C 2/9/16 character edits; no superiority claim, parameter retuning or per-page winner selection. S09 still owns final freeze. |
| 2026-11-04 | Quality is measured on ingested originals; B/C OCR/field evidence stays in processed pixels; same-size deskew and its limits are explicit | Preserves common pixel budgets/originals and avoids incorrect original overlays. Known geometry/skew/blank/noise tests passed; no perspective correction. |
| 2026-11-04 | S04 development runner rejects non-development roles and opens references only after all inference variants finish | Fixed shared OCR settings, same 14 pages, full saved intermediates/predictions/hash inventories; references remain provisional. |
| 2026-11-03 | S03 implements a conservative `keyword-1.0` + label-anchor + configured checklist baseline; user hints are never predicted labels | Demonstrates real end-to-end OCR; unresolved inventories/fields/names prevent ready. Learned/spatial/full-rule improvements stay in S05–S07. |
| 2026-11-03 | Runtime image/output paths are relative to each new run root; input absolute paths live separately in provenance | Preserves strict portable schema paths while allowing arbitrary local inputs and external output directories. Optional source filename/hash/hint fields and shared BundleInput are additive v1.0 extensions. |
| 2026-11-03 | Preserve 20-file/40-page/25-MiB/20M-per-page/100M-total limits, 300-DPI rendering and 20-second OCR timeout; branch A adds no enhancement | Real decode/limit/encryption/timeout checks passed. Bounds are development safeguards, not calibrated quality rules or a system sandbox. |
| 2026-11-03 | Development CER/WER use NFC + casefold + collapsed whitespace; empty-reference rates null, edits retained in corpus totals | Known-edit/empty tests and saved 14-page predictions verified; S09 must still freeze the final protocol. Final test remains unconsumed. |
| 2026-11-03 | S02 pilot-1.0: 30 distinct generated sources / 31 clean pages, 125 variants; five applicant groups, two layouts; all development-only | Hash reproducibility and integrity verified; template/format correlation and small support preclude generalization claims. S03 uses input-only bundle inventory. |
| 2026-11-03 | Add optional v1.0 `DatasetRecord.source_page_index`; omitted values inherit input page index | PNG derivatives from PDF page 2 need source page 2 while their actual input page is 1; regressions verify this. |
| 2026-11-03 | Embed ReportLab-packaged Vera fonts; pilot references rasterized at 144 DPI (1200 x 1600) | A second renderer exposed standard-font substitution. Font hashes/license retained; S03 300-DPI ingestion must record scale/mapping. |
| 2026-11-03 | Keep all generated references provisional; separate hash-bound record for 10 page-content spot checks, 146 unreviewed and five provisional bundle expectations | Visual inspection independent of generator specification is partial, not blanket approval or student sign-off; full final-test reference review stays in S09. |
| 2026-11-03 | Plan only in initial chat; no app implementation | User requested sprint handoff for separate future chats |
| 2026-11-03 | One unfinished sprint per new chat by default | User wants each sprint handled in a new conversation |
| 2026-11-03 | Local English printed documents and fictional scholarship profile | User scope; avoids pretending universal scholarship policy |
| 2026-11-03 | CLI/shared pipeline before Streamlit | Makes behavior reproducible and avoids UI-only logic |
| 2026-11-03 | pypdfium2 preferred; verified in S01 | 5.14.0 rendered a fictional 300-DPI RGB page; copied image survives bitmap/page/document closure |
| 2026-11-03 | No accuracy target promised; compare measured alternatives | No data/results exist and no threshold is required by the PDF |
| 2026-11-03 | Independent reference-review status/method must be explicit before final test freeze; documented agent review is acceptable | Prevents self-generated evaluation answers without imposing an unrequested student-approval gate |
| 2026-11-03 | CPython 3.12.3 isolated venv; headless OpenCV; exact resolved snapshot including dev dependencies | Verified imports/pip check on Ubuntu 24.04.4 x86_64; no global Python/system package changes. Other Python series/OSes unverified. |
| 2026-11-03 | Pydantic 2 shared contracts instead of manual dataclass serialization | Nested validation, strict profile booleans, JSON round-trips, forbidden extra keys. Explicit-true fields additionally reject numeric 1. |
| 2026-11-03 | Demo checklist v1 has one denominator item per document; income unit INR/year explicitly fictional | Four unconditional types, category true/false/null; optional extracted fields do not automatically become required. |
| 2026-11-03 | Renderer dimensions use PDFium ceil rule, not an exact nominal integer assumption | Initial 1800×600 assertion failed on actual 1801×600 render; correction and initial failure preserved. |

### Open administrative details — not coding blockers

- Sakshi Gupta roll number: NOT PROVIDED.
- Jigisha Baiswar roll number: NOT PROVIDED.
- Final approved topic/title and any instructor refinements: NOT PROVIDED.
- Final submission deadline and institutional report/slide format: NOT PROVIDED.
- Availability of consented real examples: UNKNOWN; synthetic-only work may proceed with limitations.
- Actual student review/sign-off: NOT YET PERFORMED; record only when obtained.

### Active blockers

None for S09. S08 is complete with actual browser evidence; no final freeze exists. Fields can still be confidently wrong: S06's four degraded names and one compressed in-range percentage passed heuristics. Duplicate agreement/name similarity cannot prove correctness or identity. The requirement engine is conservative for specified cases, not universally calibrated. The pilot still has two layouts/four connected groups, provisional bulk references, no positive summary-total benchmark and no real-world generalization evidence. S07 scenario expectations have a documented separate same-agent review, not independent human/student sign-off or final-test qualification. Bulk data/OCR/model/run images are ignored and need regeneration using recorded commands; compact evidence/source hashes remain preserved. Final test consumed: NO; layout probe not used in S07. Git recovery is resolved; actual initial S07 worktree was clean at `647cf3c` (completed S06), superseding older worktree observations. No Git mutation occurred.

### Verified artifact pointers

| Artifact | Current pointer |
| --- | --- |
| Course source PDF | `docs/reference/DIP_Course_Project_Guidelines_2026.pdf` |
| Current instructions | `AGENTS.md`; this file |
| Session history | `docs/SPRINT_HISTORY.md` |
| Verified environment | `.venv/bin/python`; `requirements.lock.txt`; `docs/verification/s01/environment.json`; `docs/verification/S01.md` |
| Pilot dataset | `data/manifests/pilot.jsonl`; `data/manifests/pilot.metadata.json`; `docs/DATASET_CARD.md`; `data/annotations/pilot_review.json`; five scenarios in `data/bundles/pilot/`; regenerate ignored media with seed 42 |
| Working CLI / demo | `.venv/bin/python -m scholarready demo --branch C --preprocessing configs/preprocessing.json --output <new-run-directory>`; `analyze --input` / `--bundle`; guides `docs/CLI_PILOT.md`, `docs/METHODS.md`; acceptance `docs/verification/S04.md` |
| DIP figures | Five inspected PNGs in `docs/verification/s04/`; methods `docs/METHODS.md`; comparison `artifacts/runs/s04-comparison`; compact JSON/hash inventory `docs/verification/s04/runs/` |
| Classifier / splits | `data/manifests/pilot.splits.jsonl` + metadata; model `artifacts/runs/s05-classification-final/model`; EDA/predictions/confusion/metadata snapshots `docs/verification/s05/`; guide `docs/CLASSIFICATION.md`; acceptance `docs/verification/S05.md` |
| Spatial extraction / field evaluation | `docs/EXTRACTION.md`; acceptance `docs/verification/S06.md`; canonical run `artifacts/runs/s06-fields-complete`; fresh `artifacts/runs/s06-uploads-complete`; compact metrics/predictions/failures/audit and six evidence PNGs in `docs/verification/s06/` |
| Requirement engine / readiness | `docs/READINESS.md`; acceptance `docs/verification/S07.md`; input/reference token fixtures `tests/fixtures/readiness/`; canonical runs `artifacts/runs/s07-scenarios-final`, `artifacts/runs/s07-cli`, `artifacts/runs/s07-learned-demo`; metrics/results/hashes/run index in `docs/verification/s07/` |
| Streamlit launch | `.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501`; `docs/UI_GUIDE.md`; acceptance/screenshots/downloads `docs/verification/S08.md`, `docs/verification/s08/` |
| Frozen protocol / model | Final protocol/model NOT CREATED; S05 development model exists as above |
| Final results / analysis | Final NOT CREATED; S07 fixture readiness metrics `docs/verification/s07/{tokens,cli}_metrics.json`; S06 field metrics `docs/verification/s06/metrics.json`; S05 classification `docs/verification/s05/{evaluation,predictions,eda}.json`; development A/B/C/ablations `artifacts/runs/s04-comparison/comparison.json`, compact JSON/hash snapshots `docs/verification/s04/runs/`; prior raw baseline retained in `docs/verification/s03/` |
| Reproduction package | NOT CREATED |
| Report / slides / demo / viva | NOT CREATED |

### Primary technical reference starting points

These are official documentation links, not a claim that any version is installed. Consult version-appropriate docs during implementation and record what was actually used.

- [OpenCV thresholding](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html)
- [OpenCV morphology](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html)
- [Tesseract image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Tesseract command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
- [Scikit-learn leakage and pipeline guidance](https://scikit-learn.org/stable/common_pitfalls.html)
- [Scikit-learn grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [pypdfium2 render-to-image API](https://pypdfium2.readthedocs.io/en/stable/readme.html)
- [Streamlit documentation](https://docs.streamlit.io/)

### Initial handoff verification note

Initial preparation checks passed on 2026-11-03: 12 unique sprint cards match the status ledger; dependencies form S01 -> S12; all initial implementation statuses are `NOT_STARTED`; planning files and README links resolve; Markdown fences balance; the preserved PDF is byte-identical to the user-provided source. Its SHA256 is `805afb1b48ff58a145e8eb0b506fd0b944b2addbfae987871a5c400a78546017`. No application tests or performance measurements were run. Actual application verification begins in S01. See the preparation entry in `docs/SPRINT_HISTORY.md`.

## 9. Exact prompt the students can reuse

```text
Read /home/ubuntu/Documents/ChatGPT/DIP_/HANDOFF.md and follow its
new-chat continuation instructions. Inspect the actual workspace.
Resume the unfinished sprint or execute the next eligible sprint,
one sprint only. Implement and verify the work, then update the
handoff's current state, sprint statuses, artifact pointers and next
action, and append the factual sprint history before finishing.
Do not ask me to repeat the project brief.
```

If the workspace moves, give the new path to `HANDOFF.md`; all project-relative links should continue to resolve. A chat without access to this folder cannot execute or update local files from a path alone. Use a new chat connected to this workspace for the intended workflow.
