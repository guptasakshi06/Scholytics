# ScholarReady demonstration

This four minute demonstration uses only the seven clearly fictional development images in [fixtures](fixtures), four input-only bundle files, branch A, the keyword baseline, and the unchanged fictional checklist. It shows automatic findings without manual OCR correction. It is separate from the frozen final-test experiment.

Run from `/home/ubuntu/Documents/ChatGPT/DIP_` after the setup in [REPRODUCIBILITY](../../docs/REPRODUCIBILITY.md). Use a new output folder each time:

```bash
MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/run_demo.py --output artifacts/runs/my-demo
```

The command executes actual CLI subprocesses and Tesseract for all four scenarios, checks each headline, completeness and every requirement state, and retains arguments, logs, timings and results in the chosen folder. Inputs contain filenames, explicit applicant profile and empty type hints. They contain no reference answers. Model training and final-test access are absent.

| Time allocation | Show and explain | Expected automatic result |
| --- | --- | --- |
| 0:00-0:25 | State printed-English, local-processing scope and visibly fictional input label. Explain that readiness does not establish authenticity or scholarship approval. Start the command. | Four real OCR runs |
| 0:25-1:05 | Open `complete/result.json`. Follow income field text, token evidence and required-item states. Category is explicitly true and expected applicant name is Fictional Aster. | `ready`, 100%, all five items satisfied |
| 1:05-1:45 | Open `missing/result.json`. Show that no income document is in the resolved inventory. Other evidence is unchanged. | `incomplete`, 80%, income `missing` |
| 1:45-2:30 | Show `fixtures/unreadable.png` and `unreadable/result.json`. The income certificate title is present but its amount is omitted. Show null field evidence and the requested action. | `needs_clearer_upload`, 80%, income `unreadable` |
| 2:30-3:15 | Show `fixtures/name_mismatch.png` and `name_mismatch/result.json`. The income applicant is Fictional Birch while the other documents and user expectation refer to Fictional Aster. Guardian roles do not decide applicant matching. | `needs_review`, 0%, all five implicated items require review |
| 3:15-4:00 | Explain the five item states, Unknown category producing review/null completeness, and why zero observed false ready is limited synthetic evidence. Show `rehearsal.json` and one original/processed stage path. | All issues remain visible beneath the headline |

These are planned narration allocations, not measured student speaking times. The agent's actual four-case computation took 9.327 seconds on this host, with all outcomes verified. The report, slides and notes do not assert that either student has rehearsed or mastered the demonstration.

For individual live commands, replace `complete` with `missing`, `unreadable` or `name_mismatch` and select a fresh output name:

```bash
.venv/bin/python -m scholarready analyze --bundle output/demo/complete.inputs.json --input-root output/demo --branch A --profile configs/scholarship_demo.json --output artifacts/runs/my-single-complete
```

For an optional Streamlit walkthrough:

```bash
.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501
```

Use the file sets from each bundle JSON, choose category **Yes**, expected name **Fictional Aster**, branch **A**, and the keyword method. Clear the previous application between cases. Inspect the checklist, original/processed page, field evidence and JSON/CSV export according to the [UI guide](../../docs/UI_GUIDE.md). S12 checked real server health and initial rendering. Its four-case rehearsal above used the CLI; S08 retains the prior full browser-flow evidence.

If live OCR cannot run, explicitly announce **saved-result fallback from the agent's S12 rehearsal, not live inference** before opening `artifacts/runs/s12-demo-rehearsal`. No prerecorded video is supplied. The companion bundle includes [rehearsal results](rehearsal_results) for that labelled fallback. These files are outputs, never inference inputs. Check installation rather than replacing a failed live run with an unlabeled success claim.

Troubleshooting: use a new output directory; confirm `.venv/bin/python` and Tesseract/eng; use the complete project with fixtures; inspect the case `.log` for failures. An omitted amount is not the same fixture as S11's erased-content smoke example, whose headline is `needs_review`. Preserve that distinction. Use [viva notes](../../docs/VIVA_NOTES.md) for full-pipeline explanations and the [provenance inventory](provenance.json) for copied source hashes.
