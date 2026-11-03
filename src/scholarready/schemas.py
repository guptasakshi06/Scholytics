"""Version 1.0 wire contracts; no OCR, classification, or readiness inference here."""
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator, BaseModel, ConfigDict, Field, JsonValue, StringConstraints, StrictBool,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveInt = Annotated[int, Field(gt=0)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
DocumentType = Literal[
    "marksheet", "income_certificate", "bonafide_certificate",
    "domicile_certificate", "category_certificate", "other",
]
SupportedType = Literal[
    "marksheet", "income_certificate", "bonafide_certificate",
    "domicile_certificate", "category_certificate",
]
Branch = Literal["A", "B", "C"]
RequirementState = Literal["satisfied", "missing", "unreadable", "needs_review", "not_applicable"]
OverallState = Literal["ready", "incomplete", "needs_clearer_upload", "needs_review"]

FIELD_CATALOG: dict[str, set[str]] = {
    "marksheet": {"student_name", "institution", "academic_year", "stated_total", "stated_percentage"},
    "income_certificate": {"applicant_name", "guardian_name", "annual_income", "issue_date"},
    "bonafide_certificate": {"student_name", "institution", "course", "academic_year"},
    "domicile_certificate": {"applicant_name", "domicile_region", "issue_date"},
    "category_certificate": {"applicant_name", "stated_category", "issue_date"},
}


def relative_path(value: str) -> str:
    """Portable repository-relative artifact paths, never host absolute paths."""
    if (PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or "\\" in value or ".." in PurePosixPath(value).parts or value == "."):
        raise ValueError("use a repository-relative POSIX path without '..'")
    return value


RelativePath = Annotated[Text, AfterValidator(relative_path)]


def valid_box(value: list[float]) -> list[float]:
    if value[2] <= 0 or value[3] <= 0:
        raise ValueError("box width and height must be positive")
    return value


Box = Annotated[list[NonNegative], Field(min_length=4, max_length=4), AfterValidator(valid_box)]
Matrix3 = Annotated[list[Annotated[list[float], Field(min_length=3, max_length=3)]], Field(min_length=3, max_length=3)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, validate_assignment=True)
    schema_version: Literal["1.0"] = "1.0"


class Degradation(Contract):
    type: Text
    parameters: dict[str, JsonValue]
    seed: int | None


class DatasetRecord(Contract):
    sample_id: Text
    source_document_id: Text
    applicant_id: Text
    layout_id: Text
    relative_path: RelativePath
    document_type: DocumentType
    page_index: PositiveInt
    variant_id: Text
    degradation: Degradation
    source_category: Literal["synthetic", "public", "consented_private"]
    consent_note: Text
    source_hash: Hash
    annotation_path: RelativePath
    development_role: Literal["development_only", "train", "validation", "test"]


class SplitRecord(Contract):
    sample_id: Text
    group_id: Text
    split: Literal["train", "validation", "test", "development_only"]
    seed: int
    manifest_version: Text
    manifest_hash: Hash


class PageImage(Contract):
    document_id: Text
    page_id: Text
    page_index: PositiveInt
    original_filename: Text
    width: PositiveInt
    height: PositiveInt
    color_space: Literal["RGB", "L"]
    rasterization_dpi: PositiveInt | None
    original_image_path: RelativePath
    coordinate_space: Text


class QualityAssessment(Contract):
    page_id: Text
    brightness: NonNegative
    contrast: NonNegative
    blur_measure: NonNegative
    width: PositiveInt
    height: PositiveInt
    heuristic_flags: list[Text]
    thresholds: dict[str, float]
    config_version: Text


class ProcessingStage(Contract):
    name: Text
    parameters: dict[str, JsonValue]
    image_path: RelativePath
    runtime_seconds: NonNegative


class GeometricTransform(Contract):
    source_space: Text
    target_space: Text
    direction: Literal["original_to_processed"] = "original_to_processed"
    matrix: Matrix3

    @model_validator(mode="after")
    def invertible(self) -> Self:
        a, b, c = self.matrix
        det = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
        if abs(det) < 1e-12:
            raise ValueError("coordinate transform must be invertible")
        return self


class ProcessingResult(Contract):
    page_id: Text
    branch_id: Branch
    stages: list[ProcessingStage]
    width: PositiveInt
    height: PositiveInt
    transform: GeometricTransform
    errors: list[Text]


class OCRToken(Contract):
    token_id: Text
    text: Text
    box: Box
    page_id: Text
    coordinate_space: Text
    line_id: int | None
    block_id: int | None
    engine_score: Annotated[float, Field(ge=0, le=100)] | None


class OCRResult(Contract):
    page_id: Text
    branch_id: Branch
    text: str
    tokens: list[OCRToken]
    engine: Text
    engine_version: Text
    language: Text
    settings: dict[str, JsonValue]
    runtime_seconds: NonNegative
    status: Literal["ok", "empty", "error"]
    reason: Text | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if any(t.page_id != self.page_id for t in self.tokens):
            raise ValueError("token page must match OCR page")
        if len({t.token_id for t in self.tokens}) != len(self.tokens):
            raise ValueError("duplicate token IDs")
        if self.status == "ok" and not self.text.strip():
            raise ValueError("ok OCR needs nonblank text")
        if self.status == "empty" and (self.text.strip() or self.tokens):
            raise ValueError("empty OCR cannot contain text or tokens")
        if self.status != "ok" and self.reason is None:
            raise ValueError("empty/error OCR requires a reason")
        return self


class DocumentPrediction(Contract):
    document_type: DocumentType | None
    decision: Literal["classified", "uncertain", "unreadable", "error"]
    method: Text
    model_version: Text
    scores: dict[DocumentType, NonNegative]
    score_kind: Literal["keyword_score", "model_probability", "calibrated_probability", "none"]
    reason: Text

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.decision == "classified" and self.document_type is None:
            raise ValueError("classified prediction requires a type")
        if self.decision != "classified" and self.document_type is not None:
            raise ValueError("unresolved prediction must not assert a type")
        if self.score_kind == "none" and self.scores:
            raise ValueError("score_kind none requires empty scores")
        if "probability" in self.score_kind and any(v > 1 for v in self.scores.values()):
            raise ValueError("probabilities must be in [0, 1]")
        return self


class ExtractedField(Contract):
    field_name: Text
    person_role: Literal["applicant", "student", "guardian"] | None
    raw_text: str | None
    normalized_value: JsonValue
    unit: Text | None
    page_id: Text | None
    filename: Text | None
    token_references: list[Text]
    boxes: list[Box]
    coordinate_space: Text | None
    engine_score: Annotated[float, Field(ge=0, le=100)] | None
    validation_state: Literal["valid", "absent", "unreadable", "ambiguous", "invalid", "unsupported"]
    reason: Text

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if self.validation_state != "valid" and self.normalized_value is not None:
            raise ValueError("unresolved field must have null normalized value")
        if self.validation_state == "valid":
            if (self.normalized_value is None or self.raw_text is None or not self.raw_text.strip()
                    or not self.token_references or not self.boxes or self.page_id is None
                    or self.filename is None or self.coordinate_space is None):
                raise ValueError("valid field requires value, raw text, page and token/box evidence")
        return self


class ApplicantProfile(Contract):
    applicant_reference: Text
    category_certificate_required: bool | None = None
    expected_name: Text | None = None
    expected_name_source: Literal["user_input"] = "user_input"


def require_true(value: bool) -> bool:
    if value is not True:
        raise ValueError("must be explicitly true")
    return value


ExplicitTrue = Annotated[StrictBool, AfterValidator(require_true)]


class ConditionalPredicate(Contract):
    attribute: Literal["category_certificate_required"]
    equals: ExplicitTrue = True


class FieldConstraint(Contract):
    field_name: Text
    kind: Literal["unit_equals", "format_regex"]
    value: Text


class RequirementDefinition(Contract):
    requirement_id: Text
    document_type: SupportedType
    required_fields: list[Text]
    condition: ConditionalPredicate | None = None
    constraints: list[FieldConstraint]
    action: Text

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if len(set(self.required_fields)) != len(self.required_fields):
            raise ValueError("duplicate required field")
        if set(self.required_fields) - FIELD_CATALOG[self.document_type]:
            raise ValueError("unsupported required field for document type")
        seen = set()
        for constraint in self.constraints:
            if constraint.field_name not in self.required_fields:
                raise ValueError("constraint must target a configured required field")
            key = (constraint.field_name, constraint.kind)
            if key in seen:
                raise ValueError("duplicate or contradictory constraint")
            seen.add(key)
            if constraint.kind == "format_regex":
                import re
                try:
                    re.compile(constraint.value)
                except re.error as exc:
                    raise ValueError("invalid constraint regex") from exc
        return self


class RequirementResult(Contract):
    requirement_id: Text
    state: RequirementState
    reasons: Annotated[list[Text], Field(min_length=1)]
    actions: list[Text]
    document_references: list[Text]
    field_references: list[Text]
    page_references: list[Text]
    applicable: bool | None
    included_in_denominator: bool | None

    @model_validator(mode="after")
    def applicability(self) -> Self:
        expected = (None if self.applicable is None else self.applicable)
        if self.included_in_denominator != expected:
            raise ValueError("denominator treatment must match resolved applicability")
        if self.applicable is False and self.state != "not_applicable":
            raise ValueError("false applicability requires not_applicable")
        if self.state == "not_applicable" and self.applicable is not False:
            raise ValueError("not_applicable requires resolved false applicability")
        if self.applicable is None and self.state != "needs_review":
            raise ValueError("unknown applicability requires needs_review")
        return self


class DocumentResult(Contract):
    document_id: Text
    pages: list[PageImage]
    processing: list[ProcessingResult]
    ocr: list[OCRResult]
    prediction: DocumentPrediction
    fields: list[ExtractedField]
    errors: list[Text]


class ApplicationResult(Contract):
    config_version: Text
    run_id: Text
    documents: list[DocumentResult]
    requirements: list[RequirementResult]
    issues: list[Text]
    overall_state: OverallState
    completeness: Annotated[float, Field(ge=0, le=100)] | None
    completeness_reason: Text
    quality_findings: list[QualityAssessment]
    runtime_seconds: NonNegative

    @model_validator(mode="after")
    def summary(self) -> Self:
        if len({r.requirement_id for r in self.requirements}) != len(self.requirements):
            raise ValueError("duplicate requirement result")
        applicable = [r for r in self.requirements if r.applicable]
        unresolved = any(r.applicable is None for r in self.requirements)
        if unresolved or not applicable:
            if self.completeness is not None:
                raise ValueError("unresolved or empty denominator requires null completeness")
        else:
            expected = 100 * sum(r.state == "satisfied" for r in applicable) / len(applicable)
            if self.completeness is None or abs(self.completeness - expected) > 1e-6:
                raise ValueError("completeness disagrees with requirement items")
        if self.overall_state == "ready" and (
            not applicable or unresolved or self.issues or any(d.errors for d in self.documents)
            or any(d.prediction.decision != "classified" or any(p.errors for p in d.processing)
                   or any(o.status == "error" for o in d.ocr) for d in self.documents)
            or any(r.state not in {"satisfied", "not_applicable"} for r in self.requirements)
        ):
            raise ValueError("ready cannot contain unresolved/empty requirements or errors")
        return self


class RunMetadata(Contract):
    run_id: Text
    dataset_hash: Hash | None
    split_hash: Hash | None
    config_hash: Hash
    model_hash: Hash | None
    code_version: Text
    python_version: Text
    library_versions: dict[str, Text]
    tesseract_version: Text
    seeds: dict[str, int]
    exact_command: Text
    timing_scope: Text
    runtime_seconds: NonNegative
    output_paths: list[RelativePath]
    exceptions: list[Text]
