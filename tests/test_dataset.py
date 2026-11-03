"""Data integrity regressions; these never call an analysis/requirement engine."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from scholarready.dataset import sha256, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot_generator", ROOT / "scripts/generate_pilot.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


@pytest.fixture(scope="module")
def pilot(tmp_path_factory):
    root = tmp_path_factory.mktemp("pilot")
    generator.generate(root, "data/synthetic/pilot", 42)
    return root


@pytest.fixture
def edited(pilot):
    """Restore mutations; don't copy bulk media for each negative check."""
    backups = {}

    def write(relative, content):
        path = pilot / relative
        if path not in backups:
            backups[path] = path.read_bytes()
        path.write_text(content)

    def refresh():
        metadata_path = "data/manifests/pilot.metadata.json"
        metadata = json.loads((pilot / metadata_path).read_text())
        metadata["manifest_sha256"] = sha256(pilot / "data/manifests/pilot.jsonl")
        for relative in metadata["artifact_hashes"]:
            metadata["artifact_hashes"][relative] = sha256(pilot / relative)
        write(metadata_path, json.dumps(metadata))

    yield write, refresh
    for path, content in backups.items():
        path.write_bytes(content)


def test_actual_counts_formats_and_scenarios(pilot):
    result = validate_dataset(pilot, pilot / "data/manifests/pilot.jsonl")
    assert (result["source_documents"], result["clean_pages"], result["derived_pages"], result["samples"]) == (30, 31, 125, 156)
    assert set(result["source_documents_by_class"].values()) == {5}
    assert len(result["clean_pages_by_layout"]) == 2
    assert set(result["unique_input_files_by_format"]) == {".png", ".jpg", ".pdf"}
    assert len(result["multipage_files"]) == 1
    assert len(result["scenarios"]) == 5
    assert result["final_test_consumed"] is False


def test_generation_byte_reproducible(pilot, tmp_path):
    generator.generate(tmp_path, "data/synthetic/pilot", 42)
    original = json.loads((pilot / "data/manifests/pilot.metadata.json").read_text())
    repeated = json.loads((tmp_path / "data/manifests/pilot.metadata.json").read_text())
    assert original == repeated
    assert (pilot / "data/manifests/pilot.jsonl").read_bytes() == (tmp_path / "data/manifests/pilot.jsonl").read_bytes()


@pytest.mark.parametrize("defect,match", [
    ("duplicate", "duplicate sample"), ("source_link", "missing clean source"),
    ("applicant", "registered fictional"), ("class", "document_type"),
    ("source_hash", "source hash"), ("variant_identity", "inconsistent source"),
])
def test_broken_manifest_rejected(pilot, edited, defect, match):
    write, refresh = edited
    path = "data/manifests/pilot.jsonl"
    rows = [json.loads(line) for line in (pilot / path).read_text().splitlines()]
    if defect == "duplicate": rows.append(rows[0])
    if defect == "source_link": rows[1]["source_document_id"] = "missing-source"
    if defect == "applicant":
        for row in rows:
            if row["source_document_id"] == "src-001": row["applicant_id"] = "unregistered-person"
    if defect == "class": rows[0]["document_type"] = "passport"
    if defect == "source_hash":
        for row in rows:
            if row["source_document_id"] == "src-001": row["source_hash"] = "0" * 64
    if defect == "variant_identity": rows[1]["applicant_id"] = "fictional-02"
    write(path, "".join(json.dumps(row) + "\n" for row in rows))
    refresh()  # Test semantics, beyond checksum protection.
    with pytest.raises(ValueError, match=match):
        validate_dataset(pilot, pilot / path)


@pytest.mark.parametrize("defect,match", [
    ("missing_field", "incomplete selected-field"), ("box", "outside page"),
    ("name", "unregistered fictional name"), ("transcription", "full text must include"),
    ("source_link", "annotation sample/source link"), ("identifier", "identifier/contact"),
])
def test_broken_annotations_rejected(pilot, edited, defect, match):
    write, refresh = edited
    path = "data/annotations/pilot/src-001-p01-clean.json"
    annotation = json.loads((pilot / path).read_text())
    if defect == "missing_field": del annotation["fields"]["academic_year"]
    if defect == "box": annotation["fields"]["student_name"]["box"] = [1190., 100., 100., 20.]
    if defect == "name": annotation["fields"]["student_name"]["raw_text"] = "Unregistered Name"
    if defect == "transcription": annotation["full_text"] = "Only desired fields"
    if defect == "source_link": annotation["clean_sample_id"] = "missing-sample"
    if defect == "identifier":
        annotation["lines"][-1]["text"] = "Contact demo@example.test"
        annotation["full_text"] = "\n".join(line["text"] for line in annotation["lines"])
    write(path, json.dumps(annotation))
    refresh()
    with pytest.raises(ValueError, match=match):
        validate_dataset(pilot, pilot / "data/manifests/pilot.jsonl")


def test_hash_corruption_rejected(pilot, edited):
    write, _ = edited
    write("data/annotations/pilot/src-001-p01-clean.json", "{}")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        validate_dataset(pilot, pilot / "data/manifests/pilot.jsonl")


def test_bundle_cannot_omit_an_input_page(pilot, edited):
    write, refresh = edited
    path = "data/bundles/pilot/complete/expected.json"
    reference = json.loads((pilot / path).read_text())
    reference["sample_ids"].pop()
    write(path, json.dumps(reference))
    refresh()
    with pytest.raises(ValueError, match="bundle inventory/reference mismatch"):
        validate_dataset(pilot, pilot / "data/manifests/pilot.jsonl")


def test_corrupt_image_rejected_even_with_updated_hash(pilot, edited):
    write, refresh = edited
    write("data/synthetic/pilot/src-001.png", "invalid image")
    refresh()
    # Restore source hashes as well to reach the actual image decoder.
    path = "data/manifests/pilot.jsonl"
    rows = [json.loads(line) for line in (pilot / path).read_text().splitlines()]
    for row in rows:
        if row["source_document_id"] == "src-001":
            row["source_hash"] = sha256(pilot / "data/synthetic/pilot/src-001.png")
    write(path, "".join(json.dumps(row) + "\n" for row in rows))
    refresh()
    with pytest.raises(OSError):
        validate_dataset(pilot, pilot / path)


def test_bundle_inputs_contain_no_reference_answers(pilot):
    for path in (pilot / "data/bundles/pilot").glob("*/inputs.json"):
        inputs = json.loads(path.read_text())
        assert set(inputs) == {"schema_version", "scenario_id", "profile", "files", "declared_type_hints"}
        assert all(Path(p).suffix in {".png", ".jpg", ".pdf"} for p in inputs["files"])
        assert not any("annotations" in p for p in inputs["files"])


def test_multipage_variant_links_correct_source_page(pilot):
    rows = [json.loads(line) for line in (pilot / "data/manifests/pilot.jsonl").read_text().splitlines()]
    continuation = [r for r in rows if r["source_document_id"] == "src-025" and r["source_page_index"] == 2]
    assert len(continuation) == 5
    assert next(r for r in continuation if r["variant_id"] == "clean")["page_index"] == 2
    assert all(r["page_index"] == 1 for r in continuation if r["variant_id"] != "clean")
    assert all(json.loads((pilot / r["annotation_path"]).read_text())["clean_sample_id"] == "src-025-p02-clean" for r in continuation)


def test_rotation_transform_matches_visible_landmark():
    image = Image.new("RGB", generator.SIZE, "white")
    image.paste("black", (400, 500, 420, 520))
    reference = dict(lines=[dict(text="landmark", box=[400., 500., 20., 20.])], fields={}, source_to_sample=generator.IDENTITY)
    rotated, annotation, _, _ = generator.degrade(image, reference, "rotation", 43)
    predicted = generator.transform_box([400., 500., 20., 20.], annotation["source_to_sample"])
    ys, xs = np.where(np.asarray(rotated).mean(axis=2) < 80)
    assert abs(xs.mean() - (predicted[0] + predicted[2] / 2 - 0.5)) < 1.5
    assert abs(ys.mean() - (predicted[1] + predicted[3] / 2 - 0.5)) < 1.5


def test_validation_cli_missing_manifest_is_actionable(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_dataset.py"), "--root", str(tmp_path),
                             "--manifest", "missing.jsonl"], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "failed"


def test_generator_rejects_escaping_output(tmp_path):
    with pytest.raises(ValueError, match="repository-relative"):
        generator.generate(tmp_path, "../escaped", 42)
