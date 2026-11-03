# S07 fictional development token scenarios

`inputs.json` contains base OCR-token lines and input edits only. `references.json` contains manually specified expected requirement states, headline, completeness and rationale. The agent checked them against the written project rules in a separate review pass, without using production predictions to produce expected answers. No student approval or second human reviewer is claimed.

All 33 cases are related deterministic fixtures, not independent real OCR observations or final-test data. `scripts/evaluate_readiness.py` saves inference before opening references. Unit tests join them for regression assertions. Runtime upload inference never imports the development fixture builder or reads these files.

Initial empty amount anchors actually compete with nearby issue-date labels and are ambiguous; simple unreadable scenarios now omit the amount label. Expected answers were preserved, and a separate final test checks the ambiguous-anchor behavior. Failed initial artifacts/differences remain documented in [S07 verification](../../../docs/verification/S07.md).

Real fictional document images, including deliberately blank/corrupt probes, are generated separately by `scripts/verify_s07.py`; they exercise actual CLI/Tesseract. Their specifications/review do not blanket-validate earlier provisional synthetic dataset annotations.
