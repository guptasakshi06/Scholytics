# Shared contracts v1.0

S01 implements the vocabulary and validation in `src/scholarready/schemas.py` and `config.py`. S03 adds the first shared ingestion/OCR/classification/extraction/checklist pipeline and CLI. Later evaluation and Streamlit use these same contracts as the modules are strengthened.

## Serialization and validation

Models use Pydantic 2 with strict types, finite numbers, forbidden extra keys, and `schema_version: "1.0"` (default when omitted). Pydantic was selected over hand-written dataclass serializers to provide one nested validation/JSON implementation. This is a deliberate additional dependency. Strings labelled as identifiers/reasons are stripped and must be nonblank. Integers/strings cannot stand in for boolean profile attributes. Explicit-true configuration values also reject `1` and `"true"`.

```python
from scholarready.config import load_config, ScholarshipConfig
from scholarready.schemas import ApplicantProfile

config = load_config("configs/scholarship_demo.json")
serialized = config.model_dump_json(indent=2)
assert ScholarshipConfig.model_validate_json(serialized) == config
profile = ApplicantProfile(applicant_reference="fictional-01")
assert profile.category_certificate_required is None
```

Use `model_validate` for decoded dictionaries and `model_validate_json` for JSON strings. `model_dump(mode="json")` produces JSON-compatible values. Malformed JSON raises `JSONDecodeError`; inaccessible files raise `OSError`; invalid content raises `ValidationError` with field paths. The configuration CLI exits 2 on these failures. Do not use `model_construct` or unvalidated `model_copy(update=...)` for external data; rebuild/revalidate objects after edits. Nested lists/dictionaries remain mutable, so validation at module boundaries is necessary. Unknown schema versions are rejected; a future version needs an explicit migration.

Saved dataset/annotation/stage/output paths use repository-relative POSIX paths, without absolute paths, Windows drives, backslashes or parent traversal. User-selected input paths can be absolute at the eventual ingestion boundary; that boundary must preserve safe local provenance separately. File existence, source hashes, connected grouping and reference joins are checked by later dataset/pipeline validators, not inferred from these shape contracts. The S01 schema tests use labelled fictional values/hashes; these are not measured dataset artifacts.

## Entity map

| Contract | Meaning |
| --- | --- |
| DatasetRecord, Degradation | Sample/source/applicant/layout identity, 1-based page, variant, seed/parameters, source category/consent note, SHA256, annotation path and development role |
| SplitRecord | Sample membership in a connected applicant/source group, train/validation/test/development-only role, seed and manifest version/hash; split generation is S05 |
| PageImage | Document/page identity, original filename, width/height, RGB or grayscale, PDF DPI or null, original image path and coordinate space |
| QualityAssessment | Raw brightness, contrast and blur measures, resolution, heuristic flags, thresholds and version; measurement algorithms are S04 |
| ProcessingStage, ProcessingResult, GeometricTransform | Branch A/B/C, ordered stage records with parameters/path/runtime, dimensions, invertible 3×3 mapping, explicit error list |
| OCRToken, OCRResult | Stable token IDs, text, boxes/page/space, line/block IDs, engine score; ordered page text, engine/version/language/settings/runtime and ok/empty/error state |
| DocumentPrediction | Type or null, classified/uncertain/unreadable/error, method/model version, scores with score kind and reason |
| ExtractedField | Field name/role, raw and normalized values, unit, page/filename, token/box evidence, engine score, state and explanation |
| ApplicantProfile | Applicant reference, explicit boolean/null category condition, optional expected name labelled user input |
| RequirementDefinition, ConditionalPredicate, FieldConstraint | Unique checklist item, supported type, required fields, optional explicit condition, configured unit/regex constraints and action |
| RequirementResult | State, reasons/actions, document/field/page references, tri-state applicability and denominator inclusion |
| DocumentResult, ApplicationResult | Nested document evidence, requirements/issues, overall state, separate quality findings, completeness/explanation and runtime |
| RunMetadata | Run ID, dataset/split/config/model hashes, code state, Python/library/Tesseract versions, seeds, exact command, timing scope, output paths and exceptions |

Source IDs and applicant IDs are grouping/provenance, never classifier input. Reference annotations are labels for training/evaluation, never inference evidence. File/group joins, box bounds against image dimensions, calibrated score verification and overall state precedence beyond the ready guard require later module-level checks.

S02 implements development data checks in `dataset.py`: full-page reference text, catalog-complete selected fields with explicit present/absent/unreadable states, boxes against page bounds, hashes, clean source links and input-only bundle contracts. It adds optional `DatasetRecord.source_page_index` within v1.0; existing records without it inherit `page_index`. `page_index` always means the page in the actual file; `source_page_index` retains the clean PDF page for a single-image derivative (e.g. input page 1 from source page 2). This additive extension preserves old v1.0 records. Generated reference contracts are evaluation/development-only and must not be loaded by inference. Details and provisional-review rules are in the [dataset card](DATASET_CARD.md).

## Coordinates and images

- Page indices start at 1. Document IDs group every page of a multipage input.
- A pixel box is `[x, y, width, height]`, origin at top left, x rightward and y downward. Coordinates are finite and nonnegative; width and height are positive. Floating point coordinates allow geometric mapping. An image-bound check must be done when the owning image is available.
- Coordinate spaces identify a page and representation, for example `p1:original` or `p1:C:final`. Tokens/fields keep their own spaces. No overlays across spaces without a transform.
- A homogeneous 3×3 matrix maps column vectors **original → processed**: `[x', y', w'] = M @ [x, y, 1]`; divide x'/y' by w'. Use the inverse for processed → original. Map every box corner, then bound if displaying a transformed rectangle. Identity must be recorded for unchanged geometry. Singular transforms are rejected.
- Public page images are RGB or L; future OpenCV code must explicitly convert BGR before saving/displaying RGB. PDF rasterization starts at 300 DPI (`scale = dpi / 72`); pixel extents round upwards. The smoke PDF is 432×144 points and actually renders to 1801×600 on the verified PDFium version because of floating point rounding.
- Copy the PIL image while its PDFium bitmap is alive, then close bitmap/page/document. S01 checks red/white pixels after closure and saves/reopens the copy. Future concurrent PDFium calls need serialization or separate processes; PDFium is not thread-safe ([official API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)).

## Required and optional fields

[The fictional config](../configs/scholarship_demo.json) is version `demo-1.0`. Each document is one denominator item; fields are conditions on that item, not additional score items.

| Document | Required by demo | Supported optional extraction |
| --- | --- | --- |
| marksheet | student_name, institution, academic_year | stated_total, stated_percentage |
| income_certificate | applicant_name, annual_income, issue_date | guardian_name |
| bonafide_certificate | student_name, institution, course, academic_year | none in v1 |
| domicile_certificate | applicant_name, domicile_region, issue_date | none in v1 |
| category_certificate | applicant_name, stated_category, issue_date, only when explicitly required | none in v1 |

The demo explicitly constrains `annual_income` to `INR/year`; this is a fictional format/unit requirement, not an income eligibility limit. Guardian name cannot substitute for applicant name in this profile. Store labelled person roles; compare matching roles only. Do not guess annual income from monthly/ambiguous units, date expiry, academic eligibility, a percentage denominator, a domicile region from an unrelated address, or a category from a name. Regex constraints are full-match format rules for later evaluation; no date/age/income thresholds are configured. Config rejects unknown fields/predicates, duplicate IDs/types, repeated required fields, constraints on optional fields, repeated constraint kinds on one field, invalid regex and unknown keys. V1 allows one requirement item per document type; empty configurations are valid but cannot produce a numeric completeness or ready result.

## Uncertainty and scores

`other` is the sixth class for supported training examples of unsupported documents. It is distinct from a null type plus `uncertain`, `unreadable`, or `error`. Only `classified` may assert a type. Scores are labelled `keyword_score`, `model_probability`, `calibrated_probability`, or `none`. Keyword scores can exceed 1. Probability-valued scores must be in [0, 1]; calibration must have independent evaluation before that label is used. Scores need not sum to 1 (e.g. partial score views), so the inference module must state which scores it reports. S03 uses literal OCR title keywords with 0/1 scores and abstains unless one family matches. Learned classification remains S05.

Tesseract engine scores are raw 0–100 scores, not calibrated correctness probabilities. Missing scores and engine sentinel -1 become null at the OCR boundary. Empty/error OCR requires an explicit reason; empty cannot carry text/tokens. A valid extracted field requires a non-null normalized value, raw text, page/filename and token/box/space evidence. `absent`, `unreadable`, `ambiguous`, `invalid` and `unsupported` require null normalized values plus a reason; there are no invented defaults.

`category_certificate_required` true → applicable; false → not applicable; omitted/null → unknown. `condition_applicability` implements this small configuration rule now. It never infers the attribute from a name or OCR. Unknown attributes require `needs_review` with null denominator inclusion, not `not_applicable`.

## Readiness contract for S03/S07

Requirement states are exactly `satisfied`, `missing`, `unreadable`, `needs_review`, `not_applicable`. `missing` requires sufficiently resolved upload inventory. A possible unreadable/unclassified candidate prevents confident absence. `not_applicable` requires resolved false applicability and exclusion from the denominator. Every state has reasons/actions and supporting references where available. Processing failures must remain explicit.

Completeness is `100 * satisfied applicable items / applicable items`. Unknown applicability or an empty applicable denominator gives null with an explanation. Quality measurements stay separate. The schema rejects mismatched completeness and ready results with unresolved requirements/issues or explicit document/processing/OCR errors. This is a serialization guard, not a readiness algorithm. S07 implements and tests headline precedence: `needs_review` > `needs_clearer_upload` > `incomplete` > `ready`; all issues remain visible. Evidence consistency across documents/pages also belongs to that engine. There are no readiness performance claims in S01.

## Learning and joint review

Sakshi and Jigisha can follow the same path: image/PDF → page pixels → DIP → OCR tokens → class → fields with evidence → configured checklist → local CLI/UI. DIP changes pixel appearance; OCR turns pixels into imperfect text; classification names the document; extraction locates selected fields; the checklist compares evidence with explicit requirements. Tesseract is a separate OS executable: `pytesseract` only calls it. Installing the Python wrapper alone cannot supply OCR or English language data.

Review prompts for both students: Why is unknown category applicability different from false? Why can a clear image still have wrong OCR? How would a rotation change a token box? Why is a guardian name different from an applicant name? Why does 100% completeness still need unresolved-check guards? These explanations are provided for review; no student response or sign-off is claimed.

## S03 additive contracts and runtime paths

`BundleInput` now lives in shared `schemas.py` and remains importable from `dataset.py` for S02 compatibility. Runtime does not import dataset annotations. Its accepted shape remains the input-only inventory: scenario ID, explicit applicant profile, paths and unverified hints. Scenario ID is not an inference feature.

`DocumentResult` gains optional `source_filename`, `source_sha256` and `declared_type_hint` fields; old v1.0 documents remain valid. A hint never turns an uncertain prediction into a classified type. IDs are content-SHA256 based (20 hex characters plus duplicate occurrence), independent of filename; pages append their one-based index. Duplicate byte-identical uploads get separate occurrence IDs within an inventory. Missing/oversized files use a deterministic input-path digest and null source hash; this digest is an identity fallback, not a content hash.

Dataset/annotation paths remain repository-relative. For runtime `PageImage.original_image_path`, processing image paths and `RunMetadata.output_paths`, the base is the **run directory**. This deliberate context-specific interpretation allows arbitrary local inputs and external output directories without weakening path validation. `inputs.json` separately records selected absolute local paths, content hashes and hints for provenance; these are never classifier features and can be private. `ingestion.json` records raw dimensions/EXIF and PDF points/DPI; its PDF scale maps top-left-origin point coordinates to ingested original pixels. Branch A uses the same ingested coordinate space for OCR and an identity transform. The pilot's 144-DPI reference grid is separate; a PDF reference coordinate scales by 300/144 at default runtime DPI. No reference boxes are used by runtime.

`ingested_original` is a common-ingestion stage, with no branch-A preprocessing time (0). Overall timing includes decode/render/save and OCR; `OCRResult` times include image serialization and wrapper/subprocess overhead. S03 snapshots have empty quality findings; S04 now computes original-image measures separately from completeness. See the [CLI guide](CLI_PILOT.md) for implemented baseline rules, headline precedence and metric conventions.

## S04 preprocessing and evidence spaces

A/B/C now share the pipeline. Original `PageImage` entries stay unchanged, quality is measured on those originals, and `ProcessingResult.transform` maps original pixels to processed pixels. For B/C, OCR tokens and extracted-field boxes carry the transform's target space and refer to the last saved stage; current overlays are restricted to that processed image. Same-size deskew may crop edges. Morphology changes ink and does not define an additional invertible geometric transform. Every enabled image stage, operation parameters and time is saved; the full `dip-1.0` snapshot includes disabled controls. Tiny adaptive pages use a recorded Otsu fallback. Preprocessing failures yield explicit processing/OCR/document errors and prevent ready. No schema fork was needed; see [methods](METHODS.md).
