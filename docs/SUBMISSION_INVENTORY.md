# Local submission inventory — S11

The local package is built with `scripts/package_submission.py --output <new-directory>`. It contains source and complete frozen experiment evidence under `ScholarReady/`, plus `SUBMISSION_MANIFEST.json` listing every included file's SHA256 and size. The separately supplied wheel archive supports the tested offline installation. Exact archive paths, hashes and verification are in [distribution.json](verification/s11/distribution.json); [reproduction instructions](REPRODUCIBILITY.md) explain setup. These are local artifacts; no publication or course submission occurred.

| Deliverable | Included location / reproduction |
| --- | --- |
| Setup, project and course scope | [README](../README.md), [specification](PROJECT_SPEC.md), [course PDF](reference/DIP_Course_Project_Guidelines_2026.pdf), unchanged lock and pyproject |
| Executable implementation | `src/scholarready/`, `app/streamlit_app.py`, `scripts/`, semantic/integration tests and small fictional fixtures |
| Shared architecture and meanings | [contracts](CONTRACTS.md), [DIP methods](METHODS.md), [classification](CLASSIFICATION.md), [fields](EXTRACTION.md), [readiness](READINESS.md), [UI guide](UI_GUIDE.md) |
| Provenance and grouped data | [dataset card](DATASET_CARD.md), [data guide](../data/README.md), manifests/splits, annotations and input/reference bundle inventories; exact expanded media bound by freeze |
| Independent source review | `data/annotations/expanded_review.json`, `docs/verification/s09/source_review_final/` and review-scope records; same-agent review, no second annotator/student sign-off |
| Original trained model and choices | `artifacts/runs/s09-training-complete/model/{model.joblib,metadata.json}`, training/tuning plans/selections required by the freeze; no retraining |
| Immutable protocol and environment | [evaluation protocol](EVALUATION_PROTOCOL.md), `configs/evaluation.json`, `docs/verification/s09/freeze.json`, [S01 platform record](verification/S01.md) |
| Full original final and replay runs | `artifacts/runs/s10-final/`, `artifacts/runs/s10-replay/`; original OCR, stages, tokens, predictions, results, settings, metadata and all hash inventories |
| Durable consumed status/run IDs | [S10 registry](verification/s10/run_registry.json), consumption starts, [S10 acceptance](verification/S10.md); original fresh experiment327.128s |
| Generated comparison tables/figures | [tables](verification/s10/assets/tables.md), summary/per-class/per-field/page/bundle CSVs, all12 ablations, nine PNGs and their original stage-image sources |
| Traceable errors/limitations | [error analysis](ERROR_ANALYSIS.md), raw errors/breakdowns, compact exact JSONs and visual review under `docs/verification/s10/` |
| Reproduction/acceptance | `scripts/reproduce.py`, `scripts/check_ui_launch.py`, `scripts/package_submission.py`, [S11 record](verification/S11.md), [guide](REPRODUCIBILITY.md), S11 logs/reports/hashes |
| Honest contributions and continuation | [contribution ledger](CONTRIBUTIONS.md), [sprint history](SPRINT_HISTORY.md), [handoff](../HANDOFF.md) |
| Final report, presentation, timed demo and viva notes | **S12 NOT_STARTED**; no final report/slide artifact is claimed by this package |

The package allowlist includes repository documentation, code/tests/configs and nonprivate data descriptions/references, then adds exact frozen assets and both complete S10 runs. It excludes Git metadata, virtual environments, package caches, secrets, `data/private`, unselected large historical generated runs and ordinary future applicant uploads. All supplied documents are visibly fictional/synthetic. Existing detailed historical compact evidence is retained; old bulk experiment/model/media folders outside the selected freeze/S10 runs are regenerated only for those optional historical commands. The pilot generator is reproducible; its unreviewed development data are not final-test evidence.

The core archive does not contain system Python, Tesseract, English traineddata or dependency wheels. The optional separate60-wheel Linux archive has per-file hashes. SHA256 inventories provide integrity checks, not a digital signature or proof of trust in arbitrary pickle files. The shipped classifier is the original locally generated frozen model; use that artifact and its bound metadata.

S12 still needs the final academic report, slides, timed scenario demonstration and beginner viva notes. Roll numbers, institution/template, final deadline and actual student review are not supplied. Preserve labelled unknowns; do not invent contributions, citations, evaluation results or approval.
