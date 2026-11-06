# Reproducing ScholarReady

Use the local S11 submission archive for the complete frozen experiment. A Git checkout contains source, small fictional fixtures, references and compact evidence; it omits large generated media, saved model binaries and original stage images. The archive includes the exact ignored assets needed by the unchanged freeze and both S10 runs. Nothing is deployed or submitted externally. See the [submission inventory](SUBMISSION_INVENTORY.md) and [S11 verification](verification/S11.md).

Only Ubuntu 24.04.4 LTS x86_64, CPython **3.12.3**, Tesseract **5.3.4**, and the exact [59-package lock](../requirements.lock.txt) were verified. English `eng` data and `/usr/bin/tesseract` are separate from Python. PDFium is supplied by `pypdfium2==5.14.0`; Poppler is not required by this application. Key versions are NumPy2.5.4, OpenCV headless5.0.0.93, Pillow13.0.0, pytesseract0.3.13, scikit-learn1.9.1, Pydantic2.14.2, Streamlit1.66.1, pytest9.2.0 and ReportLab5.1.0. The tested build backend is separately pinned to **setuptools84.2.1**; the original frozen lock remains unchanged. The lock is an environment snapshot, not a cross-platform or package-hash lock. The optional offline wheel archive has its own SHA256 inventory.

## Install from the submission archive

Extract `scholarready-s11.tar.gz` into a new directory. It creates `ScholarReady/` containing `SUBMISSION_MANIFEST.json`, source and frozen evidence. Work inside that extracted directory; replace the example `cd` with its actual location. Verify its included file inventory with `python3.12 scripts/package_submission.py --verify-root .` before installation. Do not copy an existing virtual environment. Tesseract and its English data must already be installed and discoverable. On Ubuntu the usual installation is `sudo apt-get install tesseract-ocr tesseract-ocr-eng`; this project did not run that system command. Repository setup cannot guarantee a particular OS package version.

When a package index is reachable:

```bash
cd /path/to/extracted/ScholarReady
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install setuptools==84.2.1
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
```

The direct index installation attempt in S11 failed because DNS/network access was unavailable. The successful fresh installation used original cached wheel archives, without copying any installed site-packages. For the tested offline route, extract the separate `scholarready-s11-wheels-linux-x86_64.tar.gz` beside `ScholarReady/`, creating `wheelhouse/`, then run:

```bash
cd /path/to/extracted/ScholarReady
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links ../wheelhouse -r requirements.lock.txt
.venv/bin/python -m pip install --no-index --find-links ../wheelhouse setuptools==84.2.1
.venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
```

The 60 wheels comprise all 59 locked packages plus the build backend, for the tested Linux/CPython environment. They do not supply Python, Tesseract, language data, or system shared libraries. The archive hash and per-wheel hashes are recorded in `docs/verification/s11/distribution.json`. To assemble the same wheel set on a connected compatible machine, use `python -m pip download --only-binary=:all: --dest wheelhouse -r requirements.lock.txt setuptools==84.2.1`; S11 exercised this command with `--no-index --find-links` against existing wheel archives. Runtime OCR, CLI, UI and saved-result verification need no network or paid APIs. Streamlit launches below disable usage statistics and bind to loopback.

Editable installation is intentional: the frozen `demo` command locates repository fixtures relative to its installed source module. Run from an intact extracted repository, not a standalone copied `site-packages` folder. CLI analysis accepts arbitrary local input paths, without reference annotations. The source has no executable dependency on the original `/home/ubuntu/Documents/ChatGPT/DIP_` location.

## Smoke reproduction

```bash
MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/reproduce.py --mode smoke
```

The command chooses a unique new directory under `artifacts/runs/reproduce-smoke-*`; `--output <new-directory>` is optional. It reports actual imports, locked package versions, English Tesseract invocation, 300-DPI PDF renderer/color/buffer lifetime, and `pip check`. It loads the trusted frozen S09 model and runs the actual CLI on the small versioned development fixtures, copying/renaming analysis inputs into an input-only directory. It neither regenerates the dataset nor trains a model nor reads final-test documents/references. Expectations are explicit smoke checks, not measured generalization results:

| CLI case | Overall state | Completeness | Additional check |
| --- | --- | ---: | --- |
| Keyword demo | ready | 100 | Five tiny fictional documents |
| Frozen learned classifier, renamed complete files | ready | 100 | Original model hash and reload |
| Missing income | incomplete | 80 | Income requirement is missing |
| Erased income content | needs_review | 80 | Income cannot be satisfied |
| Two-page PDF, unknown category applicability | needs_review | null | Both pages retained |

Inspect `reproduction.json`, `environment.json`, per-command logs/arguments and each shared-schema `result.json`. An erased labelled region may remain ambiguous and need review; this is different from a confidently absent upload. Smoke failures exit1 with the exact reason; existing output directories exit2 and remain intact. The successful fresh run took16.22 seconds; the relocated run took18.59 seconds on this machine. These durations include environment checking and CLI subprocesses and are not an OCR performance benchmark.

## Final artifact reproduction

```bash
.venv/bin/python scripts/reproduce.py --mode final
```

Final mode **loads** the frozen dataset, model, protocol, saved actual OCR and original predictions; it does not regenerate data, refit weights, tune parameters or run Tesseract. It checks all780 frozen artifacts and the exact Python/library/Tesseract executable/language-data environment, all4,396 original run hashes,1,053 compact copies, report asset hashes and durable consumption records. It recomputes classification, extraction, readiness and frozen scoring from saved OCR for every declared variant, verifies all13 routes against original page/bundle predictions and metrics, and writes a separate `recomputed_summary.json`. All predictions are checked before references are opened for scoring. Timing/provenance pointers are excluded only from semantic comparison; original values remain in the preserved evidence.

**Final test consumed remains YES.** This is verification of the existing consumed experiment, not a new performance experiment or confirmatory holdout. It writes only its new reproduction directory, records the operation in `reproduction.json`, and does not append a new S10 experiment-consumption start or rewrite any original. The first fresh-environment saved-OCR computation took13.79 seconds and the relocated check17.17 seconds; actual original S10 OCR+evaluation took327.128 seconds. These are different workloads. A new final OCR experiment would require the frozen driver and explicit consumption registration, preservation of every run and a documented reason; it is unnecessary for reproduction setup.

The original freeze deliberately checks exact executable/language hashes and absolute **system** paths. A different Tesseract build or OS cannot claim exact frozen reproduction by editing that record. Windows/macOS, other Python series and other Linux builds are unverified. Historical absolute workspace paths in `inputs.json`, commands, model training metadata, consumption records and old UI screenshots are immutable provenance. New code resolves executable inputs and original run assets relative to the extracted repository; it does not dereference historical workspace strings. The strict frozen checks pass from a relocated extracted copy.

## UI and checks

```bash
MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/check_ui_launch.py --output artifacts/runs/my-ui-launch
.venv/bin/python -m pytest -q tests/test_reproduce.py tests/test_environment.py tests/test_pipeline.py tests/test_ui.py tests/test_classification.py tests/test_freeze.py
.venv/bin/python scripts/check_documentation.py
```

The launch check starts a real local server on an available port, requires HTTP200 `ok`, runs the actual app with Streamlit AppTest, checks initial Unknown category applicability and stops the server even on failure. It verifies initial launch/render; S08 retains the actual browser upload/evidence/download checks. For interactive use:

```bash
.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501
```

Open the local URL and follow the [UI guide](UI_GUIDE.md). The frozen learned model is `artifacts/runs/s09-training-complete/model`; use branchA and its recorded settings. Keyword A/B/C need no learned model. Fresh and relocated smoke/final/UI/test evidence is linked in the acceptance record. Students have review prompts, not a recorded sign-off: explain why missing Tesseract differs from a missing Python import, why saved OCR verification is not a fresh speed measurement, and why synthetic fixture success cannot prove scholarship approval.

## Source-only checkout and troubleshooting

Smoke requires small `tests/fixtures/pilot` media and the frozen S09 model. Final mode additionally requires the assets explicitly listed by the freeze and original run inventories. Missing assets cause failure rather than fallback training or invented scores. Obtain the local archive from this workspace for exact reproduction. If deliberately rebuilding outside the archive, use the separate-root generation/training commands and hashes in [S09 verification](verification/S09.md), restore the exact frozen model metadata, and compare every artifact before replacing anything. Generated references do not automatically inherit review status. Pilot media for historical development commands can be regenerated with `scripts/generate_pilot.py --output data/synthetic/pilot --seed 42`; they are not needed by S11 smoke/final mode.

Never regenerate over original final outputs or run historical `verify_s09.py` as a current check: it asserts unconsumed test. Original `audit_s10.py` is a historical workspace audit that rewrites identical registry snapshots and matches historical absolute output paths; use S11 `--mode final` for a read-only relocated verification. All original results, negative ablations, errors, uncertainty and synthetic-only limits remain unchanged. See [troubleshooting](troubleshooting.md) for actionable missing-model, package-index, executable, renderer, version and existing-output diagnostics.


## S12 academic companion

Keep the original S11 core archive and wheel archive unchanged. Extract `artifacts/runs/s12-delivery/scholarready-s12-companion.zip` beside the core, merging its `ScholarReady/` tree. It supplies `output/`, current project records, full-pipeline viva notes and the new demo/authoring/audit scripts. `S12_MANIFEST.json` lists each companion file hash and size; archive-side `package.json` records the ZIP hash. It does not change the frozen model, methods, data, lock or final results. The source report/slide builders use separate Codex bundled authoring tools, not additional core application dependencies. Final DOCX/PDF/PPTX files need no authoring runtime to read.

```bash
MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/run_demo.py --output artifacts/runs/my-demo
```

The four actual fictional CLI/OCR cases give ready100, incomplete80, needs-clearer-upload80 and needs-review0. The [timed script](../output/demo/DEMO_SCRIPT.md) distinguishes the omitted-amount demo from S11's different erased-content fixture. No final-test access, model training or manual OCR correction occurs. See [S12 verification](verification/S12.md) for artifact rendering, source-number checks, current launch and preserved-result verification.
