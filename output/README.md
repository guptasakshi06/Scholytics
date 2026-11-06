# ScholarReady final academic deliverables

S12 provides an 18-page editable report and PDF, a 12-slide editable presentation and PDF, a four minute demonstration script with seven fictional images and four input-only bundles, and full-pipeline viva notes. The proposed format is A4 academic report and 16:9 slides because no institutional template was supplied. Student review, contributions, roll numbers, institution, supervisor, approved-title refinements and deadline remain unreported.

| Artifact | Location |
| --- | --- |
| Editable report | [ScholarReady report DOCX](report/ScholarReady_Report.docx) |
| Report export | [Report PDF](report/ScholarReady_Report.pdf) |
| Editable slides | [Presentation PPTX](presentation/ScholarReady_Slides.pptx) |
| Slide export | [Slides PDF](presentation/ScholarReady_Slides.pdf) |
| Speaker notes and source evidence | [Notes JSON](presentation/speaker_notes.json), source citations in the PPTX notes |
| Timed demo and troubleshooting | [Demo script](demo/DEMO_SCRIPT.md), [input provenance](demo/provenance.json) |
| Full-pipeline explanations | [Viva notes](../docs/VIVA_NOTES.md) |
| Local code and frozen result reproduction | [Reproduction guide](../docs/REPRODUCIBILITY.md), [submission inventory](../docs/SUBMISSION_INVENTORY.md) |
| Sprint acceptance evidence | [S12 verification](../docs/verification/S12.md) |

Run the demonstration from the project root with a new output folder:

```bash
MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/run_demo.py --output artifacts/runs/my-demo
```

All four actual CLI/OCR rehearsal cases passed. Saved results under `demo/rehearsal_results` are a **labelled saved-result fallback**, not live inference or a video. They are never inference inputs. The source image and prediction evidence remains separately available in the complete workspace.

The local S12 companion ZIP and its per-file inventory sit beside this directory under `artifacts/runs/s12-delivery`. Preserve it alongside the unchanged S11 core archive and offline wheels referenced in the submission inventory. S11's original package predates S12. The companion ZIP adds `output/`, the new authoring/demo scripts, viva notes and final project records into the same `ScholarReady/` tree. It does not embed another virtual environment, model copy or private document collection. No publication, upload or course submission occurred.
