# ScholarReady

**Project 042:** Scholarship Document Readiness and Missing-Requirement Detection using Digital Image Processing and Data Science. **Team:** Sakshi Gupta and Jigisha Baiswar.

S01 foundation and S02 fictional development data are implemented: verified environment/contracts/config, deterministic pilot generation, full-page references, scenario bundles and integrity validation. Document analysis, model training and Streamlit arrive in later sprints. No accuracy or readiness results have been measured. The scope is document readiness, with all processing local.

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

The [demo checklist](configs/scholarship_demo.json) requires four document types and a conditional category certificate. Unknown category applicability remains null. Required versus optional fields, score meanings, evidence and coordinates are explained in [contracts](docs/CONTRACTS.md). The full readiness engine is scheduled for S07.

## Fictional pilot data

```bash
.venv/bin/python scripts/generate_pilot.py --output data/synthetic/pilot --seed 42
.venv/bin/python scripts/validate_dataset.py --manifest data/manifests/pilot.jsonl
.venv/bin/python scripts/inspect_pilot.py --output docs/verification/s02
```

The pilot has 30 distinct source documents / 31 clean pages across all six labels and five applicant groups, plus 125 derived pages. It includes PNG/JPEG, single/two-page PDFs, two layout families and five readiness scenarios. The generator rewrites its generated pilot files; bulk media is ignored and must be regenerated in a new checkout. References remain provisional with separate, hash-bound partial visual review. These development fixtures provide no final-test or performance evidence. See the [dataset card](docs/DATASET_CARD.md), [data guide](data/README.md) and [S02 verification](docs/verification/S02.md). `analyze`, `demo` and Streamlit are not implemented yet; S03 is next.

## Project records and continuation

- [Current handoff and sprint ledger](HANDOFF.md)
- [Append-only sprint history](docs/SPRINT_HISTORY.md)
- [Project specification and registration draft](docs/PROJECT_SPEC.md)
- [Actual contributions and student review status](docs/CONTRIBUTIONS.md)
- [S01 verification evidence](docs/verification/S01.md)
- [S02 verification evidence](docs/verification/S02.md)
- [Original course guidelines](docs/reference/DIP_Course_Project_Guidelines_2026.pdf)
- [Workspace agent instructions](AGENTS.md)

For the next chat: “Read `/home/ubuntu/Documents/ChatGPT/DIP_/HANDOFF.md` and execute the next unfinished sprint. Verify its acceptance criteria and update the handoff and sprint history before finishing.”
