"""Semantic contract checks, independent of OCR or readiness implementation."""
import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from scholarready.config import ScholarshipConfig, condition_applicability, load_config
from scholarready.schemas import (
    ApplicantProfile, ApplicationResult, DatasetRecord, DocumentPrediction, ExtractedField,
    OCRResult, OCRToken, RequirementResult,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    return load_config(ROOT / "configs/scholarship_demo.json")


def test_demo_roundtrip_and_required_optional_fields(config):
    assert ScholarshipConfig.model_validate_json(config.model_dump_json()) == config
    assert len(config.requirements) == 5
    assert sum(r.condition is None for r in config.requirements) == 4
    marksheet = config.requirements[0]
    assert "stated_percentage" not in marksheet.required_fields
    assert "stated_total" not in marksheet.required_fields


@pytest.mark.parametrize("attribute, expected", [(True, True), (False, False), (None, None)])
def test_explicit_category_applicability(config, attribute, expected):
    profile = ApplicantProfile(applicant_reference="fictional-01", category_certificate_required=attribute)
    assert condition_applicability(config.requirements[-1], profile) is expected
    assert condition_applicability(config.requirements[0], profile) is True


def test_omitted_category_is_unknown(config):
    profile = ApplicantProfile(applicant_reference="fictional-01")
    assert condition_applicability(config.requirements[-1], profile) is None
    assert ApplicantProfile.model_validate_json(profile.model_dump_json()) == profile


@pytest.mark.parametrize("attribute", ["false", "true", 0, 1, []])
def test_profile_does_not_coerce_conditional_attribute(attribute):
    with pytest.raises(ValidationError):
        ApplicantProfile(applicant_reference="fictional-01", category_certificate_required=attribute)


@pytest.mark.parametrize("change", ["duplicate_id", "duplicate_type", "unknown_field", "duplicate_constraint", "bad_regex", "unknown_predicate", "real_profile", "extra_key"])
def test_contradictory_or_unsupported_config_rejected(config, change):
    data = copy.deepcopy(config.model_dump())
    if change == "duplicate_id":
        data["requirements"][1]["requirement_id"] = "marksheet"
    elif change == "duplicate_type":
        data["requirements"].append(dict(data["requirements"][0], requirement_id="duplicate"))
    elif change == "unknown_field":
        data["requirements"][0]["required_fields"].append("annual_income")
    elif change == "duplicate_constraint":
        data["requirements"][1]["constraints"].append({"field_name": "annual_income", "kind": "unit_equals", "value": "INR/month"})
    elif change == "bad_regex":
        data["requirements"][1]["constraints"] = [{"field_name": "annual_income", "kind": "format_regex", "value": "["}]
    elif change == "unknown_predicate":
        data["requirements"][-1]["condition"]["attribute"] = "guessed_category"
    elif change == "real_profile":
        data["fictional"] = False
    else:
        data["unknown"] = True
    with pytest.raises(ValidationError):
        ScholarshipConfig.model_validate(data)


def token(**changes):
    return dict(token_id="t1", text="Fictional", box=[0, 1, 40, 12], page_id="p1",
                coordinate_space="p1:original", line_id=1, block_id=1, engine_score=87, **changes)


def test_token_and_ocr_roundtrip():
    t = OCRToken(**token())
    result = OCRResult(page_id="p1", branch_id="A", text="Fictional", tokens=[t], engine="Tesseract",
                       engine_version="fixture", language="eng", settings={"psm": 6},
                       runtime_seconds=0.1, status="ok", reason=None)
    assert OCRResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("box", [[1, 2, 3], [0, 0, 0, 3], [-1, 0, 1, 1], [0, 0, float("nan"), 1], [0, 0, 1, 1, 1], [True, 0, 1, 1]])
def test_malformed_boxes(box):
    values = token()
    values["box"] = box
    with pytest.raises(ValidationError):
        OCRToken(**values)


def requirement(state="needs_review", applicable=None):
    return dict(requirement_id="category", state=state, reasons=["fixture reason"], actions=[],
                document_references=[], field_references=[], page_references=[], applicable=applicable,
                included_in_denominator=applicable)


@pytest.mark.parametrize("state", ["approved", "", "ready", "MISSING"])
def test_invalid_requirement_states(state):
    with pytest.raises(ValidationError):
        RequirementResult(**requirement(state))


def test_not_applicable_requires_resolved_false():
    with pytest.raises(ValidationError):
        RequirementResult(**requirement("not_applicable"))
    result = RequirementResult(**requirement("not_applicable", False))
    assert RequirementResult.model_validate_json(result.model_dump_json()) == result


def test_empty_or_unknown_denominator_cannot_be_100_percent():
    base = dict(config_version="demo-1.0", run_id="fixture", documents=[], requirements=[], issues=[],
                overall_state="needs_review", completeness=None, completeness_reason="empty checklist",
                quality_findings=[], runtime_seconds=0)
    assert ApplicationResult.model_validate_json(ApplicationResult(**base).model_dump_json()) == ApplicationResult(**base)
    with pytest.raises(ValidationError):
        ApplicationResult(**dict(base, completeness=100))
    with pytest.raises(ValidationError):
        ApplicationResult(**dict(base, overall_state="ready"))
    unknown = RequirementResult(**requirement())
    with pytest.raises(ValidationError):
        ApplicationResult(**dict(base, requirements=[unknown], completeness=100))
    with pytest.raises(ValidationError):
        ApplicationResult(**dict(base, requirements=[unknown], overall_state="ready"))
    satisfied = RequirementResult(**requirement("satisfied", True))
    assert ApplicationResult(**dict(base, requirements=[satisfied], completeness=100, overall_state="ready"))
    with pytest.raises(ValidationError):
        ApplicationResult(**dict(base, requirements=[satisfied], completeness=25))


def test_prediction_score_semantics():
    base = dict(document_type="other", decision="classified", method="keyword", model_version="fixture",
                scores={"other": 12}, score_kind="keyword_score", reason="fixture")
    assert DocumentPrediction(**base).scores["other"] == 12
    with pytest.raises(ValidationError):
        DocumentPrediction(**dict(base, score_kind="model_probability"))
    with pytest.raises(ValidationError):
        DocumentPrediction(**dict(base, decision="uncertain"))


def test_valid_field_requires_evidence_and_null_is_explicit():
    base = dict(field_name="applicant_name", person_role="applicant", raw_text=None, normalized_value=None,
                unit=None, page_id=None, filename=None, token_references=[], boxes=[], coordinate_space=None,
                engine_score=None, validation_state="unreadable", reason="fixture: no readable evidence")
    field = ExtractedField(**base)
    assert ExtractedField.model_validate_json(field.model_dump_json()) == field
    with pytest.raises(ValidationError):
        ExtractedField(**dict(base, validation_state="valid", normalized_value="Fictional Name"))
    with pytest.raises(ValidationError):
        ExtractedField(**dict(base, normalized_value="invented default"))


@pytest.mark.parametrize("path", ["/tmp/page.png", "../page.png", "C:/page.png", "data\\page.png", "."])
def test_dataset_paths_portable(path):
    base = dict(sample_id="s1", source_document_id="d1", applicant_id="a1", layout_id="layout1",
                relative_path=path, document_type="other", page_index=1, variant_id="clean",
                degradation={"type": "none", "parameters": {}, "seed": 42}, source_category="synthetic",
                consent_note="fictional fixture", source_hash="a" * 64, annotation_path="data/annotations/s1.json",
                development_role="development_only")
    with pytest.raises(ValidationError):
        DatasetRecord(**base)
    base["relative_path"] = "data/synthetic/s1.png"
    value = DatasetRecord(**base)
    assert DatasetRecord.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize("value", [1, "true", False])
def test_explicit_true_configuration_is_strict(config, value):
    data = config.model_dump()
    data["fictional"] = value
    with pytest.raises(ValidationError):
        ScholarshipConfig.model_validate(data)
    data = config.model_dump()
    data["requirements"][-1]["condition"]["equals"] = value
    with pytest.raises(ValidationError):
        ScholarshipConfig.model_validate(data)


def test_remaining_contract_roundtrips_and_transform_safety():
    from scholarready.schemas import (
        GeometricTransform, PageImage, ProcessingResult, ProcessingStage,
        QualityAssessment, RunMetadata, SplitRecord,
    )
    transform = GeometricTransform(source_space="p1:original", target_space="p1:C",
                                   matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    examples = [
        transform,
        PageImage(document_id="d1", page_id="p1", page_index=1, original_filename="fictional.pdf",
                  width=1801, height=600, color_space="RGB", rasterization_dpi=300,
                  original_image_path="tests/fixtures/fictional.png", coordinate_space="p1:original"),
        SplitRecord(sample_id="s1", group_id="connected-component-1", split="development_only",
                    seed=42, manifest_version="fixture", manifest_hash="a" * 64),
        QualityAssessment(page_id="p1", brightness=220, contrast=35, blur_measure=100,
                          width=1801, height=600, heuristic_flags=[], thresholds={"blur": 50}, config_version="fixture"),
        ProcessingResult(page_id="p1", branch_id="C", stages=[ProcessingStage(name="fixture",
                         parameters={"identity": True}, image_path="tests/fixtures/fictional.png", runtime_seconds=0)],
                         width=1801, height=600, transform=transform, errors=[]),
        RunMetadata(run_id="fixture", dataset_hash=None, split_hash=None, config_hash="b" * 64,
                    model_hash=None, code_version="fixture only", python_version="3.12.3",
                    library_versions={"example": "fixture"}, tesseract_version="fixture",
                    seeds={"fixture": 42}, exact_command="fixture only", timing_scope="no measured run",
                    runtime_seconds=0, output_paths=[], exceptions=[]),
    ]
    for item in examples:
        assert type(item).model_validate_json(item.model_dump_json()) == item
    with pytest.raises(ValidationError):
        GeometricTransform(source_space="original", target_space="processed", matrix=[[0, 0, 0]] * 3)
    with pytest.raises(ValidationError):
        PageImage(**dict(examples[1].model_dump(), page_index=0))
