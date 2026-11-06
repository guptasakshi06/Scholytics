# Setup and troubleshooting

Verified locally: CPython 3.12.3, Ubuntu 24.04.4 LTS x86_64, Tesseract 5.3.4 with `eng` and `osd`. Exact Python packages are in [requirements.lock.txt](../requirements.lock.txt); actual report in [environment.json](verification/s01/environment.json). No system packages were changed in S01.

Run from the repository root with `.venv/bin/python`; activation is unnecessary. See [README](../README.md) for setup.

| Symptom | Action |
| --- | --- |
| Tesseract not on PATH | Install the OS executable and English data. On Ubuntu/Debian the usual command is `sudo apt-get install tesseract-ocr tesseract-ocr-eng`. This command was not run here because both already existed. Re-run the checker. |
| `eng` absent | Inspect `tesseract --list-langs` and `TESSDATA_PREFIX`. Install matching English language data; the Python wrapper does not supply it. |
| `No module named scholarready` | Use the project venv and run `.venv/bin/python -m pip install --no-deps -e .` after installing the lock. |
| NumPy/OpenCV import or binary errors | Recreate an isolated Python 3.12 venv and use the lock; avoid mixing global packages or multiple OpenCV wheel variants. Then run `pip check` and the checker. |
| Renderer unavailable | Install the locked pypdfium2/Pillow and development dependencies. The smoke also uses ReportLab to create a fictional PDF. Inspect the exact report error before changing packages. |
| Render is one pixel wider | PDFium rounds `points * (dpi / 72)` upward, including floating point residuals. The verified 432×144 point smoke is 1801×600 at 300 DPI. Do not silently stretch it to nominal dimensions. |
| Wrong PDF colors or closed-buffer failure | Convert to RGB and copy PIL data before closing the bitmap/page/document. See the checker and renderer regression test. |
| Category is omitted | Keep null/unknown and request review in the future engine; omission is not false. Strings `"false"` and numeric booleans are rejected. |
| UI unavailable | Use the local Streamlit launch command in the UI guide, or `python -m scholarready --help` for CLI analysis. |
| Existing output directory | Choose a new `--output`; runs are never silently overwritten. Exit 2 is expected for an existing directory. |
| Empty/ambiguous OCR or unresolved fields | Inspect saved originals, OCR tokens and reasons. Unsupported/low-score labels remain null; an unresolved upload requires review instead of confirmed absence. |
| OCR timeout or missing executable/data | Errors remain in `result.json` and the CLI exits 1. Inspect `metadata.json`/OCR reasons; run the environment checker. `--ocr-timeout` defaults to 20 seconds/page. |
| PDF/page/file limit exceeded | Read the explicit input/page error; reduce the inventory or use documented limit flags. Omitted pages prevent readiness. No silent downscaling occurs. |
| Encrypted/corrupt/unsupported file | Supply a locally readable unencrypted PNG/JPEG/PDF. The pipeline records failure and preserves unresolved inventory. It does not unlock PDFs. |
| Category unknown on a single-file analysis | Supply `--applicant-profile` JSON with an explicit true/false attribute if known. Unknown stays review and completeness is null. |
| Pilot media paths missing | Bulk media is Git-ignored. Run the exact generator command in the dataset card with seed 42 before validating. |
| Pilot hash/reference/source error | Preserve the validator's message. Restore/regenerate the pilot or explicitly correct and re-review a reference; do not bypass checks. Regeneration overwrites generated references, so retain manual review separately. |
| Derived PNG from PDF page 2 seems to link to page 1 | `page_index` is the actual uploaded file page; `source_page_index` identifies the source PDF page. Use both as documented in the data contract. |
| Synthetic PDF appearance differs between renderers | S02 initially observed substitution with non-embedded standard fonts. Final fixtures embed ReportLab's packaged Vera fonts; retain font hashes and the tested dependency lock. |

On macOS, Homebrew's Tesseract package is an installation option. On Windows, use a Tesseract distribution linked from the [official installation guidance](https://tesseract-ocr.github.io/tessdoc/Installation.html), ensure `tesseract.exe` and English data are discoverable, and use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. These are untested alternatives, not verified project instructions. Python series other than 3.12 are not yet supported by the package metadata. Runtime OCR/rendering stays local; package installation requires a package index or cached wheels.

Official sources consulted in S01: [OpenCV wheel selection](https://pypi.org/project/opencv-python-headless/) (headless avoids GUI dependencies), [scikit-learn dependency metadata](https://pypi.org/project/scikit-learn/), [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) and [PDFium render/PIL lifetime and threading API](https://pypdfium2.readthedocs.io/en/stable/python_api.html). Their current documentation is context; compatibility evidence is the installed metadata, actual imports, `pip check` and smoke checks. Import verification does not establish future algorithm compatibility: later sprints must test the methods they use.

S01 actual fixes: the initial renderer check expected exactly 1800×600 and failed; the corrected check uses the renderer's ceil rule and verifies color/copy behavior. The optional OCR invocation initially failed downstream because that failed check had not saved a PNG; it is now explicitly blocked when rendering fails. Numeric `1` unexpectedly passed a `Literal[True]` validation; explicit-true fields now use strict boolean validation plus a true-only validator, with regression tests.

S03 actual fix: the installed `PdfPage` has no context-manager protocol. Initial ingestion tests caught the error on both PDF pages; runtime now closes pages explicitly in `finally` and copies bitmap pixels before closure. Final multipage tests and real OCR passed. Upstream APIs consulted: [pytesseract TSV/timeout](https://github.com/madmaze/pytesseract), [PDFium rendering/resources/thread safety](https://pypdfium2.readthedocs.io/en/stable/python_api.html), [Pillow EXIF transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose). These API choices were also checked against the installed libraries and executed locally.

## S04 DIP diagnostics

- Worse OCR after C: inspect all saved stages and raw OCR, then compare the grayscale-only/no-step controls using development data. Thresholding and morphology can damage decimal points or thin strokes; do not assume the darkest result wins. Keep A available.
- Deskew is skipped: check the recorded reason/gain; blank, sparse, noisy or boundary-angle evidence causes abstention. This is not proof of alignment. Disable deskew for edge content or unsupported orientation; same-size rotation can crop.
- Misplaced evidence boxes: B/C boxes use processed pixels. Draw on the final saved stage; do not reuse coordinates on the original. The matrix direction is original -> processed. Even morphology kernels may shift ink independently of this geometric matrix.
- Tiny adaptive input: inspect `fallback=otsu_for_tiny_page` and actual block size. Tiny/blank/noisy inputs can return empty/error OCR and review findings, not a readability probability.
- Invalid config: filters/block sizes must be odd; kernels are [height,width], integers 1..5. Disable morphology when disabling binary thresholding. Existing run directories are preserved; use a fresh output name.
- Missing comparison artifacts after checkout: regenerate pilot media, then run the exact command in [S04 verification](verification/S04.md); compact JSON snapshots and stage hashes are retained, while bulk stage images are ignored.

See [methods and learning questions](METHODS.md) for purpose, parameter meanings and observed failures.

## S05 classifier and split diagnostics

- Missing model after checkout: models are ignored generated artifacts. Train from the preserved development split into a new output using [classification commands](CLASSIFICATION.md).
- Model hash/dependency mismatch: restore the locally trusted generated artifact and exact lock environment, or retrain explicitly. Adjacent metadata hashes do not make an untrusted pickle safe to load.
- OCR/preprocessing mismatch: use the branch, PSM, timeout, 300-DPI PDF and preprocessing policy in model metadata; the shared pipeline rejects differences before creating output.
- Stale split/bundle/cache: restore the bound dataset or create a new split/run. Do not change a source's partition to bypass an overlap error; the mismatch bundle links applicants 4 and 5.
- Low learned score or sparse vocabulary: inspect raw OCR, saved probabilities and reasons. `other` is a limited learned notice class; arbitrary unknown text can require review. Scores are uncalibrated.
- Zero-sample metric: S05's initial sklearn helper call failed on empty inputs; the metric now explicitly emits null aggregate rates and zero supports. Empty data is not perfect performance.


## S06 spatial extraction

- Null field despite visible text: inspect the exact OCR words, supported label and candidate reason. Cropped/unfamiliar labels remain unreadable; do not substitute a reference value. A below-label region must be nearby, aligned and unique.
- Ambiguous date or income: use a clear ISO or English-month printed date and explicitly printed currency/period. Numeric local date order is not guessed. Monthly income stays INR/month and fails the demo's INR/year constraint; no automatic annualization.
- Green evidence can be wrong: a compressed printed 75.5 was OCR 5 with score 68; four names were also wrong above the score threshold. Inspect the image; engine scores and format checks are not correctness guarantees.
- Overlay space error: A uses ingested-original pixels; C uses the final saved stage's processed pixels. Supply the exact OCR coordinate-space string and image. Do not relabel a processed box as original.
- Missing evaluation inputs/model: regenerate S05 original OCR/training using its recorded commands. Evaluation refuses an existing output directory and rejects protected data roles. The ordinary CLI can run with only input documents/config, without annotations. See [extraction guide](EXTRACTION.md).


## S07 requirement rules

Current rules are in [READINESS](READINESS.md). A high image-quality measure is separate from completeness; 100% completeness with an unresolved extra upload still needs review. Name mismatches now also affect implicated item states, unlike the historical S03 baseline. Guardian/applicant roles never substitute for each other. Near spellings remain review cases.

For duplicate documents, inspect all references and remove/replace a mistaken upload deliberately before rerunning; the engine accepts complete agreeing copies but cannot choose a correct conflicting value. An unknown category attribute gives null score, not false applicability. Explicit JSON date/unit/regex constraints may need configuration or a clearer document; no implicit expiry or monthly-to-annual conversion exists. Choose new output directories so evidence is preserved.


## Local UI

Launch the loopback Streamlit server using the command in [UI_GUIDE](UI_GUIDE.md). Keep the terminal running and open its local URL. Changing files, profile or experiment settings intentionally clears previous results; analyze again. The S05 learned model requires its recorded branch A and existing locally generated artifacts. Missing or incompatible models give an error and processing remains disabled until settings are resolved. Choose the keyword baseline for B/C comparisons.

A failed page stays an explicit review result with its error. For invalid selection limits or an exception before a complete result, correct the input/settings and retry. Clear the application between applicants. Downloads preserve JSON/CSV findings only; temporary image paths stop resolving after cleanup. No report-PDF export or manual field correction is provided. See the [S08 acceptance record](verification/S08.md) for the distinction between AppTest checks and actual browser evidence.


After editing package source while Streamlit is already running, restart the server and reload the browser if an old import or file-change banner persists. Final verification used a fresh server process after package edits. Normal documented launches load the current source.


## Frozen experiment checks (S09)

A frozen artifact/hash/environment failure means the recorded method/data no longer matches the local files. Restore or regenerate exactly the recorded bytes in a separate directory and compare hashes; do not edit the freeze to suppress a failure. The trusted model is local/ignored; use the S11 local submission archive for exact original bytes. A source-only clone lacks that model; separate-root regeneration is an optional reconstruction, not an automatic setup step. `generate_expanded.py` refuses an existing generated destination; use `--root <new-directory>` for a comparison copy and preserve review attestations. A reference hash mismatch requires reinspection, not automatic approval.

Long OCR runs may be interrupted by the execution environment. S09 training/tuning accept `--reuse-inference <prior-inference-directory>` (for tuning, the prior variant root) to reuse only completed batches after checking inputs, shared implementation and settings. Use a new output directory; incomplete batches are rerun. Preserve interrupted outputs and their logs. Cached durations remain the original page timings and are not a fresh runtime benchmark. The frozen driver supports a separately hash-checked `--replay-from <completed-fresh-run>`; replay does not re-run OCR. Test requires `--consume-test` and records consumption before inference; do not use it during ordinary smoke/validation checks.


## Final results and reporting (S10)

The final test is permanently consumed; use `scripts/audit_s10.py` to verify existing fresh/replay artifacts and `scripts/build_report_assets.py` to regenerate reporting into a new directory. Historical `verify_s09.py` asserts zero test-consumption records and therefore intentionally no longer passes as a current checker. Preserve that historical acceptance evidence. Do not delete consumption records, change frozen files, or use a new output directory to hide a test rerun. Replay still records another consumption start and must be reported; it reuses saved OCR rather than measuring new OCR latency.

A Matplotlib cache warning can occur in this restricted workspace. Set `MPLCONFIGDIR=/tmp/scholarready-report-cache` for report generation, as in README; the original warning still produced valid images. If artifact verification fails because ignored media/model are missing, preserve the compact JSON snapshots and follow S11 reproduction work rather than inventing timing or silently refreezing. Correctly transcribed text may still fail the frozen token-score heuristic; compare fields/reasons and readiness as well as CER. A zero false-ready count is not complete outcome agreement.


## S11 reproduction and submission

See [REPRODUCIBILITY](REPRODUCIBILITY.md) and [SUBMISSION_INVENTORY](SUBMISSION_INVENTORY.md). Missing ignored media/model/run artifacts require the local submission archive for exact frozen checks. Never change hashes or retrain merely to silence an error. `scripts/reproduce.py --mode final` works from a relocated extracted root and writes only a new output directory; it avoids historical absolute output-path assumptions in `audit_s10.py`.

The S11 direct package-index installation failed with DNS resolution errors. The tested alternative installs the unchanged lock from the separate60-wheel Linux archive with `--no-index --find-links`, then installs setuptools84.2.1 and the project with `--no-build-isolation --no-deps -e .`. No copied global/site-packages or `--system-site-packages` fallback was used. Wheels are platform-specific and do not install Tesseract. On an offline machine without those wheels, the Python installation step is an explicit prerequisite, not a passed check.

Set `MPLCONFIGDIR=/tmp/scholarready-matplotlib` when the default cache is unwritable. Setuptools is a separately recorded build tool, not an amendment to the frozen dependency snapshot. Existing output directories exit2; preserve failed logs and use a new name. An initial S11 smoke attempt omitted the required empty `declared_type_hints` input mapping; the reproduction wrapper was fixed and repeated, with no production/frozen-source change. Erased labelled content remains `needs_review`/80, while missing income is `incomplete`/80. Equal scores do not imply equal findings.

The UI launch checker verifies real HTTP health plus initial AppTest render and always stops its child server. Full browser uploads/downloads remain S08 evidence; no new S11 browser exercise is implied by a health response. Exact final reproduction on a different Tesseract build or OS fails the original environment checks; label that environment unverified rather than rewriting the freeze.
