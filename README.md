# ScholarReady

**Project 042:** Scholarship Document Readiness and Missing-Requirement Detection using Digital Image Processing and Data Science. **Team:** Sakshi Gupta and Jigisha Baiswar.

S01–S10 are implemented and verified. S01–S08 provide: verified environment/contracts, fictional pilot data, bounded image/PDF ingestion, real local A/B/C OCR with saved DIP stages and original quality indicators, and a shared CLI with keyword classification, spatial labelled fields and the full conservative JSON checklist. Paired development OCR measurements and negative preprocessing results are recorded. S05 adds grouped development splits, EDA and a reloadable TF-IDF/Logistic Regression classifier; the Streamlit interface calls that same pipeline. The scope is document readiness, with all processing local.

## Verified setup

Tested on Ubuntu 24.04.4 LTS x86_64 with CPython 3.12.3 and an existing `/usr/bin/tesseract` 5.3.4 (`eng` data). The Python package supports the verified 3.12 series. Tesseract is a separate system executable; installing `pytesseract` alone is insufficient. Other operating systems are unverified; see [troubleshooting](docs/troubleshooting.md).

From the repository root:

```bash
cd /home/ubuntu/Documents/ChatGPT/DIP_
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
.venv/bin/python scripts/check_environment.py
.venv/bin/python -m pytest -q
```

The lock is an exact snapshot of the tested Python environment (including dev dependencies and pip), not a cross-platform or hash-verified lock. Editable project installation is separate to avoid embedding the original workspace path. The initial environment was resolved with `.venv/bin/python -m pip install -e '.[dev]'`; use the lock to retain those verified versions. `reportlab` is a development-only dependency for tiny synthetic PDFs. `opencv-python-headless` supplies `cv2` without a desktop GUI dependency. A different checkout should replace only the `cd` path.

## Available commands

```bash
.venv/bin/python -m scholarready --help
.venv/bin/python -m scholarready --version
.venv/bin/python -m scholarready validate-config configs/scholarship_demo.json
.venv/bin/python scripts/check_environment.py --ocr-smoke --smoke-dir docs/verification/s01 --output docs/verification/s01/environment.json
```

The checker imports the stack, reports actual versions and Tesseract languages, and renders a small visibly synthetic PDF at 300 DPI. It validates RGB colors, image data after closing PDF buffers and saved PNG readability. The optional OCR smoke invokes English Tesseract; its text is environment evidence only. Missing dependencies/executable/data cause actionable errors and exit 1. Config validation prints canonical JSON or exits 2 with field details. No applicant uploads or external calls occur in these commands.

The [demo checklist](configs/scholarship_demo.json) requires four document types and a conditional category certificate. Unknown category applicability remains null. Required versus optional fields, score meanings, evidence and coordinates are explained in [contracts](docs/CONTRACTS.md). The [S07 readiness engine](docs/READINESS.md) handles conditional uncertainty, names/roles, duplicates/conflicts and explicitly configured format/unit/date checks.

## Fictional pilot data

```bash
.venv/bin/python scripts/generate_pilot.py --output data/synthetic/pilot --seed 42
.venv/bin/python scripts/validate_dataset.py --manifest data/manifests/pilot.jsonl
.venv/bin/python scripts/inspect_pilot.py --output docs/verification/s02
```

The pilot has 30 distinct source documents / 31 clean pages across all six labels and five applicant groups, plus 125 derived pages. It includes PNG/JPEG, single/two-page PDFs, two layout families and five readiness scenarios. The generator rewrites its generated pilot files; bulk media is ignored and must be regenerated in a new checkout. References remain provisional with separate, hash-bound partial visual review. These development fixtures provide no final-test or performance evidence. See the [dataset card](docs/DATASET_CARD.md), [data guide](data/README.md) and [S02 verification](docs/verification/S02.md). The CLI pilot is available below. The local Streamlit interface and verification status are described below. S04 DIP alternatives and quality indicators are available.

## Real OCR and CLI pilot

Run from the repository root. Each output directory must be **new**; previous runs are preserved.

```bash
# Five tiny versioned fictional documents; no bulk generation or references needed.
.venv/bin/python -m scholarready demo --output artifacts/runs/my-demo

# S02 scenario inventory (regenerate ignored media first if absent).
.venv/bin/python -m scholarready analyze --bundle data/bundles/pilot/complete/inputs.json --branch A --output artifacts/runs/my-complete

# Arbitrary image/PDF or nonrecursive media directory.
.venv/bin/python -m scholarready analyze --input tests/fixtures/pilot/src-025.pdf --profile configs/scholarship_demo.json --branch A --output artifacts/runs/my-pdf
```

`--applicant-profile <json>` supplies explicit user attributes for `analyze`. Without a bundle/profile attribute, category applicability remains unknown, so the result requires review. Directory input reads PNG/JPG/JPEG/PDF media only and never reads label/annotation JSON. Bundle paths resolve relative to the working directory, or `--input-root`. User type hints are retained as unverified hints. All processing is local.

Each run saves `result.json`, metadata, code/config/settings/input/preprocessing snapshots and ingested page images. B/C also save every enabled intermediate stage. Original-image brightness, contrast, blur and pixel dimensions remain separate from completeness. JSON includes OCR words/boxes/scores, spatial fields and evidence, per-requirement states, issues and completeness. The clean demo returned `ready`/100%; missing income returned `incomplete`/80%; erased income and mismatched names returned `needs_review`. In S07, name conflicts also mark implicated items for review; a global unresolved extra upload can still coexist with 100% completeness. Exit 0 means processing completed, including non-ready findings; processing failures save explicit JSON and exit 1; invalid arguments/configuration or an existing output directory exit 2.

The default bounds are 20 files, 40 pages total, 25 MiB/file, 20 million pixels/page and 100 million pixels total, with 300-DPI PDFs and a 20-second per-page OCR timeout. These are development safeguards, not calibrated readability criteria. No enhancement is applied in branch A. See the [CLI pilot, rules and metric definitions](docs/CLI_PILOT.md) and [S03 acceptance evidence](docs/verification/S03.md). The 14-page development OCR result is **2/3744 character edits** and **2/518 word edits** against provisional synthetic references; this is not held-out evidence or a readiness accuracy estimate.

## Image preprocessing experiments

```bash
.venv/bin/python -m scholarready demo --branch C --preprocessing configs/preprocessing.json --output artifacts/runs/my-C-demo
.venv/bin/python scripts/verify_s04.py
```

`--branch A|B|C` is shared by CLI, analysis and development comparison. B is grayscale/Otsu; C has configurable deskew, CLAHE, filtering, adaptive threshold and morphology. A remains the default. Quality flags are uncalibrated hints; evidence boxes for B/C belong on processed images. See [methods, settings and harm cases](docs/METHODS.md), [S04 acceptance/results and repeat commands](docs/verification/S04.md), and [comparison figures](docs/verification/s04/metrics.png). The verifier needs the generated `artifacts/runs/s04-comparison` images; regenerate using the documented comparison command when absent.

All 12 development variants used the same 14 pages/settings. A/B/C CER was 0.0534%/0.2404%/0.4274%; C did not improve OCR. The 2×2 variant changed a printed `72.5` to OCR `725`. Grayscale-only had zero edits on this selected set. These provisional synthetic results are not held-out evidence; the separate frozen final test was evaluated in S10. S05 grouped splitting and learned classification are described below.

## Learned document classification

S05 keeps the inspected pilot development-only and joins applicant/source/hash/file/bundle reuse into four connected groups. TF-IDF and Logistic Regression fit only 12 clean training pages; validation uses a separate connected group. On the same 65 validation pages, keyword/learned macro-F1 is 0.8333/0.9111, with ten unresolved each and identical 55/65 accuracy. The six-page untuned layout diagnostic is 0.8333 for both. These small provisional synthetic results support no final-test/generalization claim.

```bash
# Existing pilot split; create a new output directory.
.venv/bin/python scripts/train_classifier.py --manifest data/manifests/pilot.jsonl --splits data/manifests/pilot.splits.jsonl --branch A --output artifacts/runs/my-classification
.venv/bin/python -m scholarready demo --classifier artifacts/runs/my-classification/model --output artifacts/runs/my-learned-demo
```

The recorded model is `artifacts/runs/s05-classification-final/model`; regenerate ignored artifacts after checkout. `--classifier` loads a locally trusted generated model with metadata/settings/version/hash checks; omission keeps the keyword baseline. Scores are uncalibrated, with empty, unknown and ambiguous text left unresolved. See [classification methods, EDA, figures and learning prompts](docs/CLASSIFICATION.md) and [S05 verification](docs/verification/S05.md) for split/repeat commands, actual metrics, model provenance and limitations. S06 extraction and evidence are described below.

## Spatial fields and evidence

S06 shares conservative label/region extraction across CLI and evaluation, with raw values, strict normalization, units/roles, all repeated candidates and token/page/image evidence. Ambiguous, unreadable, invalid, absent and unsupported states preserve nulls. The original and processed coordinate spaces remain explicit.

On 65 provisional synthetic validation pages, true-type, keyword-type and learned-type routes each match **169/180 present fields (93.89%)**; clean pages match 36/36. Six missing and five wrong nonnull values remain visible. The equality across routes occurs because classification abstentions here affect other/absent-continuation targets. This is development evidence, not final-test/generalization accuracy. S06 did not consume a final test.

```bash
# Requires original S05 OCR batches/cache and saved model; choose new destinations.
.venv/bin/python scripts/evaluate_fields.py --output artifacts/runs/my-s06-fields
.venv/bin/python scripts/check_s06_uploads.py --output artifacts/runs/my-s06-uploads
```

See [extraction rules, per-field results, failure examples and learning prompts](docs/EXTRACTION.md) and [S06 acceptance/repeat commands](docs/verification/S06.md). Nine fresh A fixtures plus one C fixture and inspected overlays cover spatial/role/unit/date uncertainty. The [S07 readiness engine](docs/READINESS.md) is complete; the UI reuses its rules.

## Requirement rules and readiness checks

The default `demo-1.1` checklist retains the S06 required fields and adds explicit ISO date formatting. `requirements-s07-1.0` aggregates page evidence, accepts complete agreeing duplicates as one item, preserves conflicts and compares applicant/student and guardian names within their roles. Unknown applicability gives null completeness. All issues/actions survive the headline precedence: review, clearer upload, missing, ready. Image quality stays separate.

```bash
.venv/bin/python scripts/evaluate_readiness.py --output artifacts/runs/my-readiness-tokens
.venv/bin/python scripts/verify_s07.py --output artifacts/runs/my-readiness-cli
```

The 33 manually specified token scenarios and 12 actual CLI/Tesseract scenarios matched their expected states and scores. Fixture false-ready counts were 0/24 and 0/9 reference non-ready cases, respectively; these small related development fixtures do not estimate a real-world rate. See [rules, metrics and student explanations](docs/READINESS.md) and [S07 acceptance evidence and runnable examples](docs/verification/S07.md). S07 used development fixtures; final-test consumption began in S10.

## Local Streamlit interface

```bash
.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501
```

Open [the local app](http://127.0.0.1:8501), upload the five tiny fictional PNGs from `tests/fixtures/pilot`, select category **Yes**, and analyze. Inspect checklist actions, raw/normalized fields, original/processed pages, OCR boxes, stages and multipage navigation; download shared-schema JSON and findings CSV. Profile, file, hint and experiment changes clear stale results. **Clear application** removes temporary evidence. See [the UI walkthrough and learning prompts](docs/UI_GUIDE.md) and [S08 verification and browser evidence](docs/verification/S08.md). Actual browser uploads, conditional changes, evidence/error views, PDF navigation and native downloads are verified.

## Project records and continuation

- [Current handoff and sprint ledger](HANDOFF.md)
- [Append-only sprint history](docs/SPRINT_HISTORY.md)
- [Project specification and registration draft](docs/PROJECT_SPEC.md)
- [Actual contributions and student review status](docs/CONTRIBUTIONS.md)
- [S01 verification evidence](docs/verification/S01.md)
- [S02 verification evidence](docs/verification/S02.md)
- [S03 verification evidence](docs/verification/S03.md)
- [S04 verification evidence](docs/verification/S04.md)
- [S05 verification evidence](docs/verification/S05.md)
- [S06 verification evidence](docs/verification/S06.md)
- [S07 verification evidence](docs/verification/S07.md)
- [S08 verification status](docs/verification/S08.md)
- [Original course guidelines](docs/reference/DIP_Course_Project_Guidelines_2026.pdf)
- [Workspace agent instructions](AGENTS.md)

For the next chat: “Read `/home/ubuntu/Documents/ChatGPT/DIP_/HANDOFF.md` and execute the next unfinished sprint. Verify its acceptance criteria and update the handoff and sprint history before finishing.”


## Frozen experiment preparation (S09)

The [frozen protocol](docs/EVALUATION_PROTOCOL.md) and [acceptance record](docs/verification/S09.md) add 108 new fictional sources /234 pages and18 connected applicant groups, separate from the development-only pilot. All52 test references and24 test-bundle expectations received a documented same-agent source review. S09 froze the test before inference; S10 has now evaluated it, as recorded below. The dataset is synthetic and modest; 138 total sources do not establish real-world accuracy.

```bash
# Inspect the immutable methods/data/model before further experiments.
.venv/bin/python scripts/run_experiments.py --config configs/evaluation.json --partition validation --verify-only
# Repeat validation into a NEW output directory (no final-test use).
.venv/bin/python scripts/run_experiments.py --config configs/evaluation.json --partition validation --suite core --output artifacts/runs/my-frozen-validation
```

The freeze includes the new trusted local model at `artifacts/runs/s09-training-complete/model`; the UI may select that directory for branch A using its recorded settings. The existing S05 model and all earlier evidence remain unchanged. New data generation refuses an existing media/annotation destination; for a clean clone or an isolated copy use `.venv/bin/python scripts/generate_expanded.py --root <repository-or-new-data-root>`. It regenerates bulk media and provisional references; preserved hash-bound review is separate. See the protocol and verification record before regeneration or training. Do not run final-test commands as a smoke check.


## Frozen final evaluation (S10)

**Final test consumed: YES, 4 November 2026.** All 12 declared preprocessing variants ran on the same 52 synthetic pages /24 sources /four applicant groups, with 24 correlated application scenarios. A/B/C produced 3/22/50 character edits out of14,900; full C increased errors here. Learned A classification macro-F1 was1.000 versus keyword0.944444, using the same OCR. A/B/C field exact counts were161/153/158 of164 present targets. Every route had false-ready0/16 reference non-ready; B and some ablations still worsened readiness agreement. These small synthetic results do not establish real-world accuracy.

Read the [generated result tables](docs/verification/s10/assets/tables.md), [measured error analysis](docs/ERROR_ANALYSIS.md), [acceptance evidence](docs/verification/S10.md) and [consumption/run registry](docs/verification/s10/run_registry.json). All declared neutral/negative ablations, predictions, confidence rejections and wrong nonnull fields remain visible. The frozen method/config/model were unchanged. The separate saved-OCR replay reproduced all semantic predictions and metrics.

Verify existing artifacts without running final OCR again:

```bash
.venv/bin/python scripts/audit_s10.py
# Regenerate tables/figures from the preserved final run into a NEW directory.
MPLCONFIGDIR=/tmp/scholarready-report-cache .venv/bin/python scripts/build_report_assets.py --run artifacts/runs/s10-final --output artifacts/runs/my-report-assets
```

Large media/model/run folders are ignored local assets; compact final JSONs and figures are preserved under `docs/verification/s10/assets/`. S11 will provide fresh-environment reproduction. Do not run historical `verify_s09.py` as a current check: it intentionally asserts that test consumption has not begun. Use `audit_s10.py` after S10.
