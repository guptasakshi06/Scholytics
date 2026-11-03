# S07 — conservative document readiness

ScholarReady evaluates a **fictional academic checklist**, using local OCR evidence. It does not authenticate certificates, prove identity, assess scholarship eligibility or decide awards. CLI, evaluation and the later Streamlit interface call the same engine in `src/scholarready/requirements.py`.

## Configuration and states

The default [JSON checklist](../configs/scholarship_demo.json), now `demo-1.1`, still has four mandatory types and category only when `category_certificate_required` is explicitly true. Each named requirement is one denominator item. The required-field subset is unchanged from S06; percentage/total and guardian name remain optional. `false` excludes category; omitted/null means review with an unresolved denominator. No category is inferred from a name or document.

| State | Meaning and action |
| --- | --- |
| satisfied | Resolved type, all configured fields and explicit constraints satisfied; no open conflict on the item |
| missing | Applicable type absent from a resolved inventory; supply that document |
| unreadable | Known type has absent/unreadable required fields, or an unverified hint suggests an unresolved candidate; supply readable complete evidence |
| needs_review | Unknown applicability/type, invalid/ambiguous fields, conflicting evidence or processing failure; inspect the reasons and correct the input/profile |
| not_applicable | Explicit false conditional profile attribute; excluded from the denominator |

Any unresolved upload can conceal a needed type. A hint suggests a possible document but never verifies it, and does not prove other types absent. A resolved `other` upload is different from an unclassified upload. Extra unclassified uploads and failures prevent an overall ready result even if all checklist items are satisfied. Processing, document and OCR error channels are checked directly.

Change required fields, remove an item, or edit constraints in JSON, then rerun into a new output directory. Changing `stated_percentage` from optional to required changes an otherwise identical fixture from ready to needs_clearer_upload without editing engine code. Config validation rejects unknown fields/predicates, duplicate IDs/types/constraints, constraints on optional fields, invalid regex, impossible date bounds and reversed date intervals. V1 deliberately retains one named item per type; an empty list is allowed but cannot establish readiness.

`demo-1.1` adds explicit full-match ISO date formatting to the existing annual `INR/year` unit requirement. Calendar validity is already checked by extraction. Optional `date_on_or_after` and `date_on_or_before` constraints accept inclusive, valid `YYYY-MM-DD` bounds on `issue_date`. No date bounds are enabled by default. There is no implicit current-date/expiry, income limit, percentage threshold, financial-year rule or unit conversion. All such format/unit/date conditions are fictional checklist conventions. Constraints evaluate normalized field values and preserved units, so an unambiguous English-month source date can normalize to ISO and pass. Local JSON regex is Python full-match syntax.

## Evidence, duplicates and people

All pages in a file belong to one document. S06 extraction aggregates page evidence and retains every repeated label candidate; agreeing values can span pages, while conflicting dates/names yield ambiguous/null values. Requirement references retain every selected document/page plus the relevant field IDs. Page count alone does not imply a missing page.

Complete duplicate uploads with matching normalized values/units/roles satisfy a single item; they do not boost the score. Conflicting readable fields, including optional values in duplicates, trigger review. Optional missing/unreadable fields do not become requirements. An incomplete duplicate cannot be ignored in favor of a clean copy. Separate incomplete files are not spliced into a supposedly complete certificate. Each upload has a distinct occurrence ID; accidentally repeating an internal document ID is a contract error. Byte-identical real uploads receive distinct IDs from ingestion and retain both references.

`name-comparison-s07-1.0` uses Unicode NFC, casefolding, punctuation-to-spaces and whitespace collapse. It preserves accents, spelling, initials and token order. It never repairs OCR or changes stored extraction values. Student/applicant fields identify the same applicant role; guardian evidence is compared only with guardian evidence. Guardian names cannot substitute for an applicant field or be compared against the user-provided expected applicant name. A wrong/missing required role triggers review.

Readable same-role name disagreement, including with the explicitly labelled user expected name, marks all implicated checklist items for review. The largest pairwise string similarity is only a review clue; neither a high fuzzy score nor exact matching proves identity. Names in supplied supported documents remain reviewable even when a conditional item is excluded. Do not silently discard a contradictory supplied certificate.

## Headline, score and image quality

Headline precedence is **needs_review → needs_clearer_upload → incomplete → ready**. All reasons/actions remain in `issues` even when another issue determines the headline. Unknown inventory, applicability, conflicting/invalid evidence and failures have review precedence.

Completeness is `100 * satisfied applicable named items / applicable named items`. Only resolved not_applicable items are excluded. Unknown applicability or no applicable items gives null with a reason. Duplicates never add denominator items. A missing income item in the default true-category profile gives 4/5 = 80%; false category and four complete items gives 4/4 = 100%. An unresolved extra upload can coexist with 100% completeness and still require review. Name conflicts now change the affected item states too; historical S03 mismatch/100% snapshots describe the old baseline.

Original-image brightness/contrast/blur/dimensions and heuristic flags stay in `quality_findings`, separately from completeness. Their numeric values are not a document-readiness probability. Neither a quality score nor 100% completeness can clear an unresolved issue.

New `ApplicationResult.requirement_engine_version` identifies `requirements-s07-1.0`; it defaults to null when loading older v1.0 JSON. The shared result guard continues to reject a ready result with open requirements/errors/issues or an invalid denominator.

## Scenario expectations and metrics

[Input-only token specifications](../tests/fixtures/readiness/inputs.json) and [manually reviewed expectations](../tests/fixtures/readiness/references.json) are separate. The agent checked the visible base lines and edits against the written project contract without calling production or reading predictions to obtain expected outcomes. This is a distinct specification/review pass by the same agent, not a second human reviewer or student sign-off. These are explicit development fixtures, not independent population samples or a final benchmark. Real OCR scenarios separately use an inspected pilot contact sheet and freshly printed fictional documents, with expectations saved before inference.

The first token run exposed three empty-anchor fixtures that actually create competing nearby labels. Those are spatially ambiguous, so review is correct. The unreadable fixtures were corrected to omit the amount label; retained initial artifacts document the distinction. No expected answer was changed to match predictions. See [S07 evidence](verification/S07.md) for final actual counts and commands.

`evaluation/readiness_metrics.py` reports full five-state requirement and four-state application confusion tables/supports. Confirmed `missing` is the binary positive. All named items, including review, unreadable and not_applicable references, remain in the declared binary accounting as non-missing states; full state tables expose these cases. Prediction/reference item-ID mismatch is an error, preventing dropped failures. Scenario duplicates and invalid states are rejected.

False-ready rate is `reference non-ready predicted ready / all reference non-ready`. The count and denominator are always saved. The separately named false-ready share among predicted-ready uses predicted-ready as its denominator. Missing precision, recall and F1 use the usual TP/FP/FN formulas. Zero denominators give null (not estimable), including an empty scenario set or no reference non-ready cases. Tests include deliberately wrong outcomes, not only perfect fixtures.

## Run and inspect

From `/home/ubuntu/Documents/ChatGPT/DIP_`, choose new output paths:

```bash
.venv/bin/python -m scholarready validate-config configs/scholarship_demo.json
.venv/bin/python scripts/evaluate_readiness.py --output artifacts/runs/my-readiness-tokens
.venv/bin/python scripts/verify_s07.py --output artifacts/runs/my-readiness-cli
.venv/bin/python -m scholarready demo --output artifacts/runs/my-readiness-demo
```

The token evaluator saves all predictions before opening references. It performs classification/spatial extraction/checklist on deterministic OCR tokens; it does not measure Tesseract. The CLI verifier creates input-only bundles, runs actual CLI/Tesseract and saves references, exact commands, exit codes, inputs/config/engine/code/version hashes and all results. It needs only the versioned tiny pilot fixtures, not bulk data, annotations or a trained model. Each real CLI example can be repeated using its saved bundle and `--input-root` with a new destination. It covers every headline, conditional uncertainty, other, duplicate/name conflicts and failure.

The saved model remains optional. A remains the default branch. S07 does not retrain, tune classifier/field thresholds, modify dataset grouping, use the layout probe or consume a final test.

## Learning and troubleshooting

Read one requirement's reasons and action, follow its document/page/field references, then inspect OCR candidates on their recorded coordinate space. A disagreement is a request to review imperfect evidence, not proof that the applicant is inconsistent. Five confidently wrong S06 field values remain a known limitation; two agreeing wrong OCR values may still pass.

Both students should explain: why unreadable is not confirmed missing; why a hint cannot resolve type; how true/false/null category changes the denominator; why a guardian differs from an applicant; why near names require review; why complete duplicates count once; and why an unresolved extra upload blocks ready despite 100% completeness. No student review or mastery is claimed.

If a run directory exists, choose a new one. If a date or unit constraint fails, inspect the printed value and JSON rather than invent a conversion or expiry policy. If several duplicate files are present, preserve every reference and replace/remove a wrong upload deliberately before rerunning. Configure required versus optional fields explicitly instead of relying on an extracted value to create a requirement.
