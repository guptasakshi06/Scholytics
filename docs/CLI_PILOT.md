# S03 — real OCR and the shared CLI pilot

This is a local development baseline for printed English documents. It provides document readiness findings under `demo-1.0`; it cannot establish authenticity, identity, scholarship eligibility or an award decision. S04 adds DIP/quality as described below; S05 adds optional [learned classification](CLASSIFICATION.md); S06 adds [spatial extraction](EXTRACTION.md); S07 will strengthen requirement logic.

## Run and inspect

From the repository root, after the [verified setup](../README.md#verified-setup):

```bash
.venv/bin/python -m scholarready demo --output artifacts/runs/my-demo
.venv/bin/python -m scholarready analyze --bundle data/bundles/pilot/missing_document/inputs.json --branch A --output artifacts/runs/my-missing
.venv/bin/python -m scholarready analyze --input tests/fixtures/pilot/src-025.pdf --output artifacts/runs/my-pdf
```

Every output directory must be new. Demo uses five versioned fictional PNGs and a built-in explicitly labelled user profile; it reads no references and needs no bulk generator. Bundle examples require ignored media; generate it using the README command if absent. `--input <file-or-directory>` accepts arbitrary local paths and scans immediate supported media files only. Direct unsupported paths produce explicit failures; nonmedia directory entries are ignored. Directory metadata JSON is never parsed. All applications use `scholarready.pipeline.analyze`; CLI contains input/argument adaptation only.

For a single file/directory, supply `--applicant-profile <json>` if the category condition is known. Example contents:

```json
{"schema_version":"1.0","applicant_reference":"fictional-local","category_certificate_required":false,"expected_name":"Fictional Aster","expected_name_source":"user_input"}
```

The expected name is user input, not verified identity. Omitting the category attribute means unknown. `--profile` selects a validated fictional checklist JSON. `--bundle` accepts only the input inventory shape; annotations and expected-answer JSON fail that schema. Bundle file paths resolve relative to `--input-root` (default current working directory), and may not escape it. Hints are recorded separately and never supply a predicted class or field value.

The CLI prints a compact summary and saves complete JSON:

```json
{"run_id":"<actual UUID in metadata>","overall_state":"ready","completeness":100.0,"result_path":"<selected run directory>/result.json"}
```

This shows the shape, not an invented run. Actual IDs are in [the run index](verification/s03/run_index.json). Inspect `result.json` for each document's prediction, pages, OCR words, boxes and raw engine scores, extracted-field evidence, requirement states/reasons/actions and all issues. `metadata.json` records the exact command, source snapshot hash, configuration hash, dependency/Tesseract versions, timing scope, exceptions and output paths. Config, applicant, settings, code hashes, input provenance and ingestion details are saved alongside it. Relative image paths resolve against that run directory. Original selected absolute paths live only in the input provenance snapshot; keep private runs local.

Exit 0 means processing completed and can include `incomplete`/review findings. Exit 1 means a processing failure was saved. Exit 2 means a configuration/argument/setup error, including an existing output directory. Readiness is determined by JSON state, not the shell exit status alone.

## Ingestion and branch A

PNG/JPEG decoding applies EXIF orientation and composites transparency onto white, then saves RGB pixels. The ingested original defines the OCR coordinate space; boxes do not refer to the pre-EXIF file grid. PDFium renders every allowed page at 300 DPI without extracting embedded PDF text. Pixel dimensions round upwards; the pilot PDF pages render to 2500 × 3334. The bitmap is copied before closing native resources, and runtime PDFium calls use one process-wide lock. Protected/encrypted PDFs are rejected, including empty-password encryption.

Default limits: 20 files/application, 40 page slots/application, 25 MiB/file, 20 million pixels/page, 100 million pixels/application, and 300 DPI (configurable up to 600). Oversized pages are rejected before rendering. Partial PDFs retain successful pages plus explicit failure/omission messages. No failure can quietly become an empty successful document. These bounds limit work; they are not an OS memory sandbox or a whole-application wall-clock timeout.

Branch A adds no enhancement. Its processing record uses an identity transform and an `ingested_original` stage with zero preprocessing duration. End-to-end timing includes common ingestion, while per-page OCR timing includes wrapper/image serialization/subprocess work. Tesseract uses English, OEM 3 and PSM 3 by default. Each page call has a 20-second timeout (`--ocr-timeout`, positive and at most 120 seconds). The executable version probe has a separate five-second timeout. TSV word order defines text; unique block/paragraph/line groups become newline-separated lines. Engine sentinel/invalid scores become null, not probabilities. Empty OCR and failed OCR have distinct statuses/reasons.

## Limited baseline decisions

- Classification uses only OCR text. Exactly one literal title family must match; multiple/no families abstain. `other` recognizes the pilot notice title families only, so unknown arbitrary text remains uncertain. Filenames, sample/applicant IDs, hints, scenario IDs and references are not features. Scores are 0/1 keyword indicators, not probabilities.
- Extraction recognizes the documented pilot labels, either a colon value on the same line or an immediately following nearby line (gap at most 6% of page height, aligned within ten pixels to the left). Another label cannot be used as a value. Names retain applicant/guardian roles. Evidence includes the label and value tokens/box. Repeated agreeing values retain first-page evidence; disagreements return ambiguous/null. A missing anchor returns unreadable/null because OCR cannot prove printed absence.
- Whitespace is collapsed. ISO dates are validated as calendar dates; other date formats require review. Academic years require `YYYY-YYYY`. Labelled numeric values accept plain digits or conventional comma groups, with optional decimals; there is no guessed percentage denominator. INR/year and INR/month remain different units, and income is never annualized. A minimum evidence engine score of 50 is a **fixed, uncalibrated development heuristic**, not a correctness guarantee; low/missing scores return unreadable/null. These are historical S03 rules; current S06 normalization and region rules supersede this paragraph in [EXTRACTION](EXTRACTION.md).
- A checklist item requires a classified document of that type and all JSON-required fields plus its explicit constraints. Optional fields do not affect completeness. Duplicate documents of a type require review in this baseline. No expiry/grade/income eligibility limits are invented.
- Missing means no matching type in a resolved inventory. Any unclassified/unreadable/failed upload can be the missing type, so that item requires review. A matching user hint can label a possible upload unreadable but never verifies its class. All unresolved inventory prevents an overall ready result, including extra uploads. Unknown applicability gives review/null completeness; explicit false resolves not applicable.
- Applicant/student name comparisons use casefolded word tokens; guardian names are excluded. Exact normalized disagreement with the explicit expected name or between documents triggers review. Fuzzy matching and comprehensive conflict handling remain S07. A review issue can coexist with 100% completeness.

Headline precedence is review (including unresolved inventory, applicability, names or invalid/ambiguous evidence), then unreadable required fields (`needs_clearer_upload`), then confirmed missing (`incomplete`), then `ready`. All issues remain listed. Completeness is satisfied applicable document items divided by applicable document items, times 100. Unknown applicability or no applicable items gives null. S03 snapshots have empty quality findings; current S04 runs compute original-image measures separately.

## Observed development evidence and OCR measures

Actual clean/conditional bundles returned ready/100%. Missing income returned incomplete/80%. The erased-income page still contains a visible watermark but no class title: its prediction is uncertain; its user hint gives income unreadable and the overall result needs review/80%. Mismatched names returned needs review/100%. A true blank has empty OCR/unreadable class; a corrupt input and a forced real OCR timeout retain explicit failures and require review. [Acceptance evidence](verification/S03.md) maps these outcomes to saved runs.

Offline evaluation is deliberately separate. The S03 evaluator permits only explicitly selected `development_only` records; test-role data is rejected before inference. It sends input paths to the same pipeline, waits for predictions, then opens references for scoring. It never supplies reference text/fields/class labels to OCR or extraction. Every score contains run/sample/document/page IDs and input/reference hashes. Failures use an empty prediction and remain in the denominator. References remain provisional.

Normalization `nfc_casefold_collapse_whitespace_v1` applies Unicode NFC, casefolding and whitespace collapse to both texts; punctuation is retained. Raw prediction/reference text is also saved. CER is character edit distance/reference characters, WER token edit distance/reference words. An empty prediction with a nonempty reference has rate 1; an empty reference has null per-sample rate, with edits/insertions and empty counts retained. Corpus metrics sum **all** edits (including empty-reference insertions) and divide by total reference characters/words; zero total denominator gives null. Rates may exceed 1. This is a development convention for later freeze review, not a frozen S09 protocol.

The expanded run contains 14 selected pages: nine clean, four variants of one marksheet, and one erased-income page, from eight source documents/four applicant groups. They are related pages, not 14 independent observations. It measured 2 character edits / 3744 reference characters (CER 0.0534%) and 2 word edits / 518 reference words (WER 0.3861%), with no OCR failures. Both errors were on the blurred/noisy marksheet footer (`Page 1 of 1` became `Page lof 1`). The first 10-page smoke subset had zero normalized edits; the expanded sample is the main S03 OCR record. Neither result estimates real-world/generalization accuracy. The erased page's low OCR error against its visible watermark says nothing about document completeness.

No learned model, grouped split, final-test data, UI, classification/extraction accuracy or readiness false-ready rate has been evaluated in S03. The existing five bundle expectations remain provisional; these CLI checks are development scenarios specified independently in the verifier, not a final benchmark.

## Learning and joint review

Both students can trace a field from the JSON back through a token ID and box to saved pixels. The classifier answers which document title the OCR suggests; extraction answers which labelled values are readable; the checklist answers whether that evidence meets the fictional configuration. Each step can be wrong independently.

Suggested joint review: explain why a watermark can OCR perfectly while every useful field is unreadable; why an unknown extra upload prevents confirmed absence; why a guardian name cannot supply applicant identity; why 100% completeness can still need review; why a PDF page's 144-DPI reference box cannot be drawn unchanged on the 300-DPI rendering. Run `demo`, inspect a token and compare the missing/erased scenarios. These are learning prompts, not claims that the students completed review.

## S04 branch extension

The CLI now accepts `--branch A|B|C` and `--preprocessing configs/preprocessing.json`. Default A still uses the ingested original. B/C and quality metrics use the common analysis pipeline. See [methods](METHODS.md) and [S04 verification](verification/S04.md) for geometry restrictions, saved stages, paired results and runnable commands; earlier S03 commands/results above remain historical evidence.

## S05 optional learned classifier

Add `--classifier artifacts/runs/s05-classification-final/model` to `analyze` or `demo` to load the verified local model; regenerate it with the [classification commands](CLASSIFICATION.md) when ignored artifacts are absent. Default CLI behavior retains the keyword baseline. Real learned-demo processing returned ready/100%; watermark-only, unknown and conflicting-title uploads all returned needs_review. This is development fixture behavior, not readiness accuracy. Saved classifier metadata and the model hash identify the method even though the existing orchestrator's run IDs retain an `s04-` prefix.


## S06 extraction update

Current CLI runs use `spatial-s06-1.0` through the same pipeline. Inspect each field's candidates, extraction version, normalization rule, score source and token boxes; repeated conflicts retain every candidate and return null. Explicit printed absence differs from an unreadable label/value. English month dates, documented synonyms, bounded below-label values and strict numeric/unit validation are supported. No annotation or expected-name input supplies field values. Original A overlays and processed C overlays were checked. The learned demo still returns ready/100%; per-field development errors remain visible in [S06 verification](verification/S06.md). Full readiness rules remain S07.
