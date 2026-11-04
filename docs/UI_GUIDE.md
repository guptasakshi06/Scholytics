# Local Streamlit interface

S08 implements a local interface to the same `scholarready.pipeline.analyze` used by the CLI and evaluation. Readiness rules, limits, classification and field normalization remain in shared modules. All examples below use visibly fictional academic documents. Browser acceptance is tracked separately in [S08 verification](verification/S08.md).

## Launch and try a fictional application

From the repository root, with the verified environment installed:

```bash
cd /home/ubuntu/Documents/ChatGPT/DIP_
.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501
```

Open [the local app](http://127.0.0.1:8501) in a browser on this computer. Keep the terminal running; Ctrl+C stops it. Binding to loopback keeps the app local. No hosted deployment or paid service is used. The launch command disables Streamlit usage telemetry.

1. The checklist selector shows the fictional `demo-1.1` profile. Its configuration lives in [scholarship_demo.json](../configs/scholarship_demo.json). Required fields/explicit constraints appear in **Academic experiment settings**; other extracted fields remain optional.
2. Select **Yes** for category certificate required, and optionally enter **Fictional Aster** as the expected name. This name is recorded as user input. Unknown category applicability stays unresolved; it never silently becomes No.
3. Upload `src-001.png` through `src-005.png` from [the tiny pilot fixture folder](../tests/fixtures/pilot). Select all five files together. These versioned files need no bulk generation. The clean baseline example is ready/100% in real OCR checks.
4. Optional document-type hints retain your declaration separately from the predicted type. A hint does not make a failed or unknown upload valid. No manual OCR correction interface is implemented.
5. Choose **Analyze documents**. Decode and page progress precede the findings. Read every issue and each requirement's reasons/actions, including review at 100% completeness.
6. Choose a document and page. Inspect fields/raw values/units/roles/reasons, the original, and the OCR-input image with evidence boxes. Field boxes are green for valid evidence and red for unresolved evidence; blue boxes mark OCR tokens. B/C boxes stay on processed coordinates. Open the OCR/stages view for stage images, text and geometric transforms. Image quality measures are separate heuristics, not readability probabilities or completeness.
7. Download application JSON and findings CSV. JSON validates as the shared `ApplicationResult`; CSV includes every requirement plus global issues. JSON image paths refer to the temporary run; these two exports do not package images or supply a PDF report. Store exports locally if you want to retain findings.
8. Change the category attribute, expected name, reference, files, type hints, branch or classifier: previous results and their temporary workspace are discarded. Analyze again. **Clear application** also resets profile widgets and the file-upload widget. Closing a browser tab lets Streamlit expire its session and release its temporary workspace; cleanup on explicit clear/change is immediate, while disconnect cleanup follows session expiration/garbage collection. Process exit also cleans live temporary directories under normal shutdown. Abrupt OS/process termination is not a guaranteed secure wipe.

## Academic comparisons and limits

A remains the default original-image baseline. B is grayscale/Otsu; C uses the saved DIP configuration. The **S05 learned classifier** option loads only the existing locally trusted `artifacts/runs/s05-classification-final/model`; no arbitrary model upload/unpickling is offered. Missing model files produce an actionable error. The saved model requires its recorded branch A/settings. A B/C/model mismatch disables processing until resolved. See [classification](CLASSIFICATION.md) for its exact regeneration command and small synthetic support.

The shared defaults remain 20 files, 25 MiB/file, 40 pages, 20 million pixels/page, 100 million pixels total, 300-DPI PDF rasterization, and Tesseract English OEM3/PSM3/20-second per-page timeout. Unsupported, encrypted, corrupt or over-budget pages stay explicit failures. The app never silently converts a processing failure into readiness. Large applications can take several minutes. There is no cancel/parallel OCR feature.

Temporary copies use isolated indexed folders, preserving repeated original filenames and content-derived document identities. Raw uploaded copies are deleted after inference; ingested originals/stages survive only for that result's evidence views. No `st.cache_data`/global applicant cache is used. The request identity includes ordered bytes/names/hints, applicant/config/preprocessing, model metadata, shared limits/OCR settings and package source hashes. Browser downloads already saved by the user remain the user's responsibility.

## Repeat checks and troubleshooting

```bash
.venv/bin/python -m pytest -q tests/test_ui.py
.venv/bin/python scripts/verify_s08.py --output artifacts/runs/my-ui-headless
```

The verifier substitutes only AppTest's unsupported upload widget with local fictional bytes. It runs real Tesseract, the production Streamlit script/controls/views and actual CLI subprocesses. It verifies conditional/hint invalidation, page navigation, exported bytes and semantic equality. **It does not verify native browser uploads, layout or browser downloads.** Required browser checks, screenshots and outstanding evidence are recorded in [S08 verification](verification/S08.md).

A new verifier output directory is required; existing run evidence is preserved. If the model is absent, regenerate it using the recorded S05 command before running the learned case. Read [troubleshooting](troubleshooting.md) for missing Tesseract/English data or setup issues. An analysis exception clears the incomplete result and gives a retry action. A decoded corrupt document instead has an explicit saved failure result with review findings and downloads. If port 8501 is already occupied, stop the prior local app or select another port and use its displayed URL. Do not remove unrelated processes.

## Learning and joint review

Both students should trace one field from pixels through tokens to normalization and its checklist item, explain why unknown applicability yields null completeness, and compare an original/processed overlay on branch C. Change an attribute after analysis and explain why reprocessing is required. Compare the JSON export with a CLI result, preserving null values, unresolved issues and user-input provenance. These are proposed exercises; no student review or mastery is claimed.

Implementation used the installed Streamlit 1.66.1 signatures and official [upload widget](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), [session-state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) and [download widget](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button) documentation. Dependency compatibility is evidenced by the unchanged lock, actual imports, `pip check` and recorded tests.
