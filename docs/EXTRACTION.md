# Spatial field extraction — S06

The shared `scholarready.extraction.extract` function serves the CLI and development evaluation. It reads only OCR tokens and page provenance. No annotation, expected applicant name, scholarship answer, filename or source ID supplies a value. Five supported types use the catalog in [schemas](../src/scholarready/schemas.py); unresolved/other types have no default field catalog. Explicit `requested_fields` outside a resolved catalog yield `unsupported` null fields.

## Method and evidence

`spatial-s06-1.0` groups words by coordinate space, block and line, then sorts words by x and physical rows by y/x. Missing line IDs use row-center geometry within the same space/block. Labels must have a colon for same-line values or occupy a standalone label segment for below-label extraction. A title such as “CATEGORY CERTIFICATE” is not a category-value pair. Separate labels on one physical line delimit their values. Large horizontal gaps (over 12% page width) remain ambiguous.

A below-label value must start within 4% page width of the label's left edge, with a vertical gap between zero and the smaller of 6% page height or three label heights. Exactly one nearby row must qualify. Known labels, unknown colon headings, competing rows and distant columns prevent borrowing a value. This deliberately supports the pilot's inline and stacked layouts, not arbitrary forms or multiline paragraphs. These bounds are development heuristics, not calibrated layout models.

Supported synonyms include:

| Field | Printed anchors (case-insensitive) |
| --- | --- |
| student_name | Student name, Student's name, Name of student, Learner name |
| applicant_name | Applicant name, Applicant's name, Name of applicant |
| guardian_name | Guardian name, Parent name, Father's name, Mother's name |
| institution | Institution, Institution name, College name, Name of college/institution |
| academic_year | Academic year, Academic session, Session |
| course | Course, Course name, Programme, Program |
| annual_income | Annual/Monthly/Yearly income, corresponding family-income labels, Family income with explicit units |
| issue_date | Issue date, Date of issue, Issued on |
| domicile_region | Domicile region, State of domicile, Domicile state |
| stated_category | Stated category, Category, Social category |
| stated_total | Stated total, Total marks, Marks obtained, Grand total |
| stated_percentage | Stated percentage, Percentage, Percentage obtained, Overall percentage |

Student and applicant names remain different field names. Both denote the applicant role in this project's references; guardian/parent fields carry `guardian` and never substitute for an applicant. Generic “Name,” “State,” an address and birth/expiry dates do not provide those fields. No subject table is summed and no percentage is inferred from a denominator.

Every candidate saves raw value, normalized value or null, state/reason, unit, role, filename, page ID, token IDs, individual token boxes, coordinate space and minimum token score. `extraction_version`, `normalization_rule`, `score_source` and `candidates` are additive schema-v1 extensions; old results remain loadable. Tesseract's minimum score of 50 is an uncalibrated development filter, not a probability. Missing scores stay unreadable. Repeated agreeing candidates retain all evidence; disagreeing candidates return an ambiguous null. Incomplete/error OCR pages prevent a confident value that could conflict with unseen evidence.

## Normalization and unresolved states

`field-normalization-s06-1.0` preserves raw text and uses NFC plus collapsed whitespace. It does not repair spelling, add decimal points, casefold names for accuracy scoring or fuzzy-match wrong OCR to annotations.

| Field family | Rule |
| --- | --- |
| Names | Preserve letters, case, spaces, periods, apostrophes and hyphens; unsupported characters are invalid. |
| Other text | NFC/whitespace only; printed category/region/institution/course preserved without inference. |
| Issue date | Calendar-valid ISO YYYY-MM-DD or day + English month name/abbreviation + four-digit year. English month lookup is explicit, independent of machine locale. Numeric local date order stays ambiguous. |
| Academic year | Explicit consecutive four-digit start/end years, separated by hyphen/en dash/slash; normalize to YYYY-YYYY. No year expansion or academic eligibility rule. |
| Numbers | Explicit nonnegative decimal, plain/Western/Indian comma grouping; no denominator or OCR repair. Canonical decimal string for totals/percentages; whole income as integer, fractional income as decimal string. |
| Percentage | Optional printed `%`; require 0..100. A lost dot yielding `725` is invalid, but a wrong in-range `5` can still pass. |
| Income | Currency prefix INR/Rs/₹ can be stripped from the numeric value; both INR and exactly one annual/monthly period must be explicit in label/value. Conflicts or missing units remain ambiguous. Monthly `8000 INR/month` stays monthly in the legacy `annual_income` field; never multiply by 12. |

`valid` means a supported anchored value passed these heuristics; it does not guarantee OCR truth. `absent` requires a readable explicit marker: `not stated`, `not provided`, `not applicable` or `n/a`. It is a field-level printed marker, not scholarship applicability. No label, cropped text, a blank value or low/missing score is `unreadable`; readable invalid syntax is `invalid`; competing interpretations/candidates are `ambiguous`; out-of-catalog requests are `unsupported`. All unresolved states have null normalized values. The pipeline still reports document uncertainty separately when it cannot route extraction.

## Evidence figures and coordinates

[Overlay renderer](../src/scholarready/evidence.py) requires matching page/coordinate space and in-image boxes. A overlays ingested originals; B/C overlays belong on the processed image, with no implicit original mapping. Green means the aggregate field/candidate passed validation, red means unresolved. Green does **not** certify the value is correct.

Actual inspected examples:

- [Applicant/guardian, three dates and monthly unit](verification/s06/roles_dates_monthly_evidence.png): only the issue-date label supplies issue_date.
- [Two conflicting issue dates](verification/s06/conflicting_dates_evidence.png): both candidates remain, with red boxes and ambiguous null.
- [Below-label values](verification/s06/below_label_evidence.png): aligned regions give traceable evidence.
- [Faint decimal](verification/s06/faint_decimal_evidence.png): printed `72.5` became OCR `72 5`; extraction rejected it as invalid.
- [Branch C processed-space overlay](verification/s06/processed_C_evidence.png): actual transformed OCR boxes are drawn on the final C image. Supplying original space is rejected.
- [Confident wrong percentage](verification/s06/wrong_percentage_evidence.png): printed `75.5` became OCR `5`, score 68, passed range validation and remains a recorded error. No reference-based correction was made.

## Development evaluation and actual failures

[Field metrics](../src/scholarready/evaluation/field_metrics.py) compare canonical normalized value **and unit and role** exactly. Present targets always enter the denominator, even when no field was emitted after routing abstention. Value-only counts are also retained. Absent targets have separate support, false extra-nonnull counts and explicit-absence-resolution counts; an unreadable null is not credited as confirmed physical absence. Reference-unreadable fields are reported separately and excluded from present-target accuracy. Extra schema fields, wrong nonnull values, missing values and every emitted state are counted. Empty present support gives a null rate, not zero accuracy.

The [recorded run](verification/s06/run.json) `s06-fields-complete` uses hash-bound real S05 branch-A OCR on 61 train-diagnostic and 65 validation pages, reuses unchanged connected splits and learned model, and saves all inference **before** opening field annotations. No new fit or threshold search occurs. The 30-page layout probe is not evaluated in S06. All outer roles remain development-only. Runtime includes cached OCR validation/model loading/extraction/scoring, **not** the original OCR acquisition; it is not an OCR speed benchmark.

| Same validation pages | Present exact matches | Missing predictions | Wrong nonnull | Extra nonnull on absent targets |
| --- | --- | --- | --- | --- |
| True-type routing | 169/180 (93.89%) | 6 | 5 | 0/35 |
| Keyword-type routing | 169/180 (93.89%) | 6 | 5 | 0/35 |
| Learned-type routing | 169/180 (93.89%) | 6 | 5 | 0/35 |

Clean validation: 36/36 present targets, 7 absent; 13 pages including continuation/other. Each other variant has the same 36 present and 7 absent targets: low contrast 36/36, rotation 36/36, compression 35/36, blur/noise 26/36. These views are related, not independent observations. The learned classifier's continuation abstentions add 25 missing *field outputs* across variants, but those targets are reference-absent, so present-target accuracy happens to equal true-type routing. This is **not** evidence that classification errors never affect extraction. A regression fixture shows an abstention with a present field remains in the denominator. Page-level scores do not establish document/readiness accuracy.

| True-type field | Exact / present support | Missing | Wrong nonnull | Reference-absent support |
| --- | --- | --- | --- | --- |
| marksheet.student_name | 9/10 | 0 | 1 | 5 |
| marksheet.institution | 10/10 | 0 | 0 | 5 |
| marksheet.academic_year | 10/10 | 0 | 0 | 5 |
| marksheet.stated_percentage | 8/10 | 1 | 1 | 5 |
| marksheet.stated_total | not estimable (0 present) | 0 | 0 | 15 |
| income.applicant_name | 9/10 | 1 | 0 | 0 |
| income.guardian_name | 10/10 | 0 | 0 | 0 |
| income.annual_income | 10/10 | 0 | 0 | 0 |
| income.issue_date | 10/10 | 0 | 0 | 0 |
| bonafide.student_name | 9/10 | 0 | 1 | 0 |
| bonafide.institution | 9/10 | 1 | 0 | 0 |
| bonafide.course | 9/10 | 1 | 0 | 0 |
| bonafide.academic_year | 10/10 | 0 | 0 | 0 |
| domicile.applicant_name | 8/10 | 1 | 1 | 0 |
| domicile.domicile_region | 10/10 | 0 | 0 | 0 |
| domicile.issue_date | 10/10 | 0 | 0 | 0 |
| category.applicant_name | 8/10 | 1 | 1 | 0 |
| category.stated_category | 10/10 | 0 | 0 | 0 |
| category.issue_date | 10/10 | 0 | 0 | 0 |

Complete [metrics](verification/s06/metrics.json), [actual predictions/evidence](verification/s06/predictions.json) and [11 failure records](verification/s06/failures.json) preserve support and identities. Four wrong names (`Elm` -> `Eim`/`Elim`, minimum scores 68–91) plus the wrong in-range percentage pass the heuristics. Six other present fields are unresolved after blur/noise. No fuzzy scoring hides these errors. Train diagnostic: 180/180 present targets, 10 absent and 4 reference-unreadable; this is development debugging, not independent validation.

The pilot contains no printed summary-total positives. A separate fresh OCR `Marks obtained: 400` fixture extracts `400` and leaves percentage unresolved, with no guessed denominator. Nine fresh A pages plus one C page exercise synonyms, role/date separation, monthly unit, cropped label, unfamiliar layout, explicit absence, ambiguous numeric date, stacked labels, printed total and faint dot. All 19 content-specific checks passed; these fixtures are not added to pilot splits or used for accuracy claims. Their specifications were written before inference; no student sign-off is claimed.

## Repeat, limitations and student review

From the workspace root, using **new** output directories:

```bash
.venv/bin/python scripts/evaluate_fields.py --output artifacts/runs/my-s06-fields
.venv/bin/python scripts/check_s06_uploads.py --output artifacts/runs/my-s06-uploads
.venv/bin/python -m scholarready demo --classifier artifacts/runs/s05-classification-final/model --output artifacts/runs/my-s06-demo
.venv/bin/python scripts/verify_s06.py --run artifacts/runs/my-s06-fields --uploads artifacts/runs/my-s06-uploads --demo artifacts/runs/my-s06-demo
.venv/bin/python -m pytest -q
```

Evaluation/audit needs the ignored S05 original OCR batches/cache and trusted classifier. Regenerate these with [S05 commands](verification/S05.md) after checkout; never synthesize predictions from annotations when artifacts are absent. Current runnable CLI extraction needs only inputs/config and an optional model, with no annotation files.

The configured required fields are unchanged in [fictional checklist](../configs/scholarship_demo.json). Optional total/percentage/guardian fields do not become required. Full duplicate/constraint/readiness aggregation remains S07. Remaining limits: two layouts, tiny connected groups, provisional synthetic annotations, no real applicant data, no final test/freeze/calibration, no arbitrary multiline/table/handwriting support, imperfect unknown-layout detection and confident wrong OCR. None of these measurements are scholarship approval or authenticity evidence.

Both students should inspect a valid candidate and a conflicting pair, explain why a missing OCR label does not prove absence, distinguish monthly income from annual income, and recompute a field denominator containing an abstention. Sakshi can trace C's coordinate space to its image; Jigisha can explain why `75.5` -> `5` is still wrong despite passing range validation. These are learning prompts, not claims of student work or approval.
