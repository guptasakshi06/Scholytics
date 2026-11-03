"""Development data contracts and integrity checks, never inference inputs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Literal, Self

from PIL import Image
import pypdfium2 as pdfium
from pydantic import model_validator

from .schemas import (
    Box, Contract, DatasetRecord, FIELD_CATALOG, Hash, PositiveInt, Text,
    ApplicantProfile, RelativePath, relative_path,
)

WATERMARK = "SYNTHETIC - FOR ACADEMIC DEMONSTRATION"
LABELS = (*FIELD_CATALOG, "other")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_inside(root: Path, relative: str) -> Path:
    relative_path(relative)
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes dataset root: {relative}")
    return path


class ReferenceLine(Contract):
    text: Text
    box: Box


class ReferenceField(Contract):
    state: Literal["present", "absent", "unreadable"]
    raw_text: Text | None
    normalized_value: str | int | None
    person_role: Literal["applicant", "guardian"] | None
    unit: Text | None
    box: Box | None

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if self.state == "present" and (self.raw_text is None or self.normalized_value is None or self.box is None):
            raise ValueError("present reference field requires text, value and box")
        if self.state != "present" and any(v is not None for v in (self.raw_text, self.normalized_value, self.box)):
            raise ValueError("absent/unreadable reference values must be null; inspect clean source separately")
        return self


class PageAnnotation(Contract):
    sample_id: Text
    width: PositiveInt
    height: PositiveInt
    coordinate_space: Text
    full_text: Text
    lines: list[ReferenceLine]
    fields: dict[str, ReferenceField]
    reference_status: Literal["provisional"] = "provisional"
    reference_origin: Literal["generator_specification"] = "generator_specification"
    clean_sample_id: Text
    source_to_sample: list[list[float]]

    @model_validator(mode="after")
    def geometry(self) -> Self:
        if self.full_text != "\n".join(line.text for line in self.lines):
            raise ValueError("full text must include every visible reference line, in reading order")
        boxes = [line.box for line in self.lines] + [f.box for f in self.fields.values() if f.box]
        for x, y, w, h in boxes:
            if x + w > self.width + 0.01 or y + h > self.height + 0.01:
                raise ValueError("reference box outside page")
        import numpy as np
        matrix = np.asarray(self.source_to_sample)
        if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-12:
            raise ValueError("source-to-sample transform must be finite and invertible")
        return self


class BundleInput(Contract):
    scenario_id: Text
    profile: ApplicantProfile
    files: list[RelativePath]
    declared_type_hints: dict[RelativePath, Text]

    @model_validator(mode="after")
    def hints(self) -> Self:
        if len(self.files) != len(set(self.files)):
            raise ValueError("duplicate bundle file")
        if set(self.declared_type_hints) - set(self.files):
            raise ValueError("hint refers to missing bundle file")
        if set(self.declared_type_hints.values()) - set(LABELS):
            raise ValueError("unknown declared document hint")
        return self


def read_page(path: Path, page_index: int) -> Image.Image:
    """Dataset inspection only. S03 will own bounded runtime ingestion."""
    if path.suffix.lower() == ".pdf":
        with pdfium.PdfDocument(str(path)) as document:
            if not 1 <= page_index <= len(document):
                raise ValueError("PDF page index outside input")
            page = document[page_index - 1]
            try:
                bitmap = page.render(scale=2)  # pilot's declared 144 DPI
                try:
                    return bitmap.to_pil().convert("RGB").copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("unsupported pilot input format")
    if page_index != 1:
        raise ValueError("single image must have page_index 1")
    with Image.open(path) as image:
        image.load()
        return image.convert("RGB").copy()


def validate_dataset(root: Path, manifest: Path) -> dict:
    """Fail closed on pilot integrity defects; no OCR or requirement engine."""
    root = root.resolve()
    manifest = manifest.resolve()
    metadata = json.loads(manifest.with_suffix(".metadata.json").read_text())
    if metadata["manifest_sha256"] != sha256(manifest):
        raise ValueError("manifest hash mismatch")
    if metadata["dataset_version"] != "pilot-1.0" or metadata["synthetic_only"] is not True:
        raise ValueError("unexpected pilot provenance")
    records = [DatasetRecord.model_validate_json(line) for line in manifest.read_text().splitlines()]
    if not records or len({r.sample_id for r in records}) != len(records):
        raise ValueError("empty dataset or duplicate sample IDs")
    if set(r.document_type for r in records) != set(LABELS):
        raise ValueError("all six pilot classes must have actual examples")
    by_id = {r.sample_id: r for r in records}
    clean = {(r.source_document_id, r.page_index): r for r in records if r.variant_id == "clean"}
    clean_records = [r for r in records if r.variant_id == "clean"]
    if len(clean) != len(clean_records):
        raise ValueError("duplicate clean source/page link")
    artifacts = metadata["artifact_hashes"]
    for relative, expected_hash in artifacts.items():
        path = resolve_inside(root, relative)
        if sha256(path) != expected_hash:
            raise ValueError(f"artifact hash mismatch: {relative}")
    source_identity = {}
    file_pages = {}
    for r in records:
        source = clean.get((r.source_document_id, r.source_page_index or r.page_index))
        if source is None:
            raise ValueError(f"missing clean source link: {r.sample_id}")
        if r.variant_id == "clean" and (r.source_page_index or r.page_index) != r.page_index:
            raise ValueError("clean input page must equal source page")
        if r.degradation.type != ("none" if r.variant_id == "clean" else r.variant_id):
            raise ValueError("variant/degradation type mismatch")
        identity = (r.applicant_id, r.document_type, r.layout_id, r.source_hash)
        if identity != (source.applicant_id, source.document_type, source.layout_id, source.source_hash):
            raise ValueError(f"inconsistent source identity: {r.sample_id}")
        if r.source_document_id in source_identity and source_identity[r.source_document_id] != identity:
            raise ValueError("source document reused with inconsistent identity")
        source_identity[r.source_document_id] = identity
        if (r.source_category != "synthetic" or r.development_role != "development_only"
                or r.applicant_id not in metadata["fictional_applicants"]):
            raise ValueError("pilot must use registered fictional applicants and development-only roles")
        source_path = resolve_inside(root, source.relative_path)
        if sha256(source_path) != r.source_hash:
            raise ValueError(f"source hash mismatch: {r.sample_id}")
        for relative in (r.relative_path, r.annotation_path):
            if relative not in artifacts:
                raise ValueError(f"artifact missing from inventory: {relative}")
        annotation = PageAnnotation.model_validate_json(resolve_inside(root, r.annotation_path).read_text())
        if annotation.sample_id != r.sample_id or annotation.clean_sample_id != source.sample_id:
            raise ValueError("annotation sample/source link mismatch")
        if annotation.coordinate_space != f"{r.sample_id}:original_pixels":
            raise ValueError("incorrect annotation coordinate space")
        expected_fields = FIELD_CATALOG.get(r.document_type, set())
        if set(annotation.fields) != expected_fields:
            raise ValueError(f"incomplete selected-field annotation: {r.sample_id}")
        if WATERMARK not in annotation.full_text:
            raise ValueError("synthetic watermark missing from full transcription")
        # Narrow fictional-schema privacy guard; not a general-purpose PII detector.
        allowed = metadata["fictional_applicants"][r.applicant_id]
        for name, field in annotation.fields.items():
            if name in {"applicant_name", "student_name", "guardian_name"} and field.state == "present":
                role = "guardian" if name == "guardian_name" else "applicant"
                if field.person_role != role or field.raw_text != allowed[role]:
                    raise ValueError("unregistered fictional name or incorrect person role")
            if field.state == "present" and field.raw_text not in annotation.full_text:
                raise ValueError("selected-field text absent from full-page reference")
        import re
        if re.search(r"(?:https?://|\S+@\S+|\b\d{10,12}\b)", annotation.full_text):
            raise ValueError("unexpected identifier/contact-like content in fictional pilot")
        image = read_page(resolve_inside(root, r.relative_path), r.page_index)
        if image.size != (annotation.width, annotation.height):
            raise ValueError("annotation dimensions do not match readable input")
        file_pages.setdefault(r.relative_path, set()).add(r.page_index)
    for relative, pages in file_pages.items():
        if relative.endswith(".pdf"):
            with pdfium.PdfDocument(str(resolve_inside(root, relative))) as document:
                if pages != set(range(1, len(document) + 1)):
                    raise ValueError("PDF contains unrecorded pages")
    bundle_counts = Counter()
    for bundle in metadata["bundles"]:
        for key in ("input_path", "reference_path"):
            if bundle[key] not in artifacts:
                raise ValueError("bundle missing from hash inventory")
        inputs = BundleInput.model_validate_json(resolve_inside(root, bundle["input_path"]).read_text())
        expected = json.loads(resolve_inside(root, bundle["reference_path"]).read_text())
        if inputs.scenario_id != expected["scenario_id"]:
            raise ValueError("bundle reference scenario mismatch")
        if expected["reference_status"] != "provisional" or not expected["rationale"]:
            raise ValueError("bundle reference review status/rationale missing")
        if set(expected["requirements"]) != {"marksheet", "income", "bonafide", "domicile", "category"}:
            raise ValueError("incomplete bundle requirement references")
        if set(expected["requirements"].values()) - {"satisfied", "missing", "unreadable", "needs_review", "not_applicable"}:
            raise ValueError("invalid reference requirement state")
        if expected["overall_state"] not in {"ready", "incomplete", "needs_clearer_upload", "needs_review"}:
            raise ValueError("invalid reference headline")
        if set(expected["sample_ids"]) - set(by_id):
            raise ValueError("bundle references nonexistent samples")
        if {by_id[s].relative_path for s in expected["sample_ids"]} != set(inputs.files):
            raise ValueError("bundle inventory/reference mismatch")
        for relative in inputs.files:
            if {r.sample_id for r in records if r.relative_path == relative} - set(expected["sample_ids"]):
                raise ValueError("bundle references must account for every page in each file")
        bundle_counts[inputs.scenario_id] += 1
    if set(bundle_counts) != {"complete", "missing_document", "conditional_not_applicable", "unreadable", "mismatch"}:
        raise ValueError("missing named pilot readiness scenario")
    if any(count != 1 for count in bundle_counts.values()):
        raise ValueError("duplicate scenario IDs")
    clean_hashes = [(r.source_hash, r.page_index) for r in clean_records]
    if len(set(clean_hashes)) != len(clean_hashes):
        raise ValueError("duplicate source page presented as independent")
    return {
        "status": "passed", "dataset_version": metadata["dataset_version"],
        "manifest_sha256": sha256(manifest), "samples": len(records),
        "source_documents": len(source_identity), "clean_pages": len(clean_records),
        "derived_pages": len(records) - len(clean_records),
        "applicants": len({r.applicant_id for r in records}),
        "clean_pages_by_class": dict(sorted(Counter(r.document_type for r in clean_records).items())),
        "source_documents_by_class": {label: len({r.source_document_id for r in clean_records if r.document_type == label}) for label in LABELS},
        "samples_by_variant": dict(sorted(Counter(r.variant_id for r in records).items())),
        "clean_pages_by_layout": dict(sorted(Counter(r.layout_id for r in clean_records).items())),
        "unique_input_files_by_format": dict(sorted(Counter(Path(p).suffix for p in file_pages).items())),
        "multipage_files": sorted(p for p, pages in file_pages.items() if len(pages) > 1),
        "scenarios": sorted(bundle_counts), "generated_reference_status": "all provisional; separate review ledger may attest to hash-bound spot checks",
        "final_test_consumed": False,
    }
