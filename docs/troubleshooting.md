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
| UI unavailable | S03 supplies CLI analysis; Streamlit arrives in S08. Use `python -m scholarready --help`. |
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
