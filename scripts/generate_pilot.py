#!/usr/bin/env python3
"""Generate the local, development-only fictional pilot (no inference or OCR)."""
import argparse
from copy import deepcopy
from io import BytesIO
import json
import math
from pathlib import Path
from importlib.metadata import version

import numpy as np
from PIL import Image, ImageFilter
import pypdfium2 as pdfium
import reportlab
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from scholarready.dataset import LABELS, WATERMARK, PageAnnotation, BundleInput, resolve_inside, sha256
from scholarready.schemas import DatasetRecord, FIELD_CATALOG

VERSION = "pilot-1.0"
SIZE = (1200, 1600)
IDENTITY = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
TITLES = dict(zip(LABELS, (
    "ACADEMIC MARKSHEET", "INCOME CERTIFICATE", "BONAFIDE CERTIFICATE",
    "DOMICILE CERTIFICATE", "CATEGORY CERTIFICATE", "LIBRARY NOTICE",
)))
NAMES = ["Fictional Aster", "Fictional Birch", "Fictional Clover", "Fictional Dahlia", "Fictional Elm"]
ABSENT = dict(state="absent", raw_text=None, normalized_value=None, person_role=None, unit=None, box=None)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def specifications(label, applicant, page):
    """Human-readable scenario content; no real person, ID, institution or policy."""
    name = NAMES[applicant]
    institution = f"Fictional Learning College {chr(65 + applicant)}"
    date = f"2026-0{applicant + 1}-15"
    if page == 2:
        return [], ["Supplementary subject record", "Laboratory: 78 / 100", "Project: 82 / 100"]
    definitions = {
        "marksheet": [("student_name", "Student name", name, name, "applicant", None),
                      ("institution", "Institution", institution, institution, None, None),
                      ("academic_year", "Academic year", "2025-2026", "2025-2026", None, None),
                      ("stated_percentage", "Stated percentage", f"{72 + applicant}.5", f"{72 + applicant}.5", None, "%")],
        "income_certificate": [("applicant_name", "Applicant name", name, name, "applicant", None),
                               ("guardian_name", "Guardian name", f"Fictional Guardian {chr(65 + applicant)}", f"Fictional Guardian {chr(65 + applicant)}", "guardian", None),
                               ("annual_income", "Annual income (INR/year)", str(96000 + applicant * 12000), 96000 + applicant * 12000, None, "INR/year"),
                               ("issue_date", "Issue date", date, date, None, None)],
        "bonafide_certificate": [("student_name", "Student name", name, name, "applicant", None),
                                 ("institution", "Institution", institution, institution, None, None),
                                 ("course", "Course", "BSc Demonstration Studies", "BSc Demonstration Studies", None, None),
                                 ("academic_year", "Academic year", "2025-2026", "2025-2026", None, None)],
        "domicile_certificate": [("applicant_name", "Applicant name", name, name, "applicant", None),
                                 ("domicile_region", "Domicile region", f"Fictional Region {chr(65 + applicant)}", f"Fictional Region {chr(65 + applicant)}", None, None),
                                 ("issue_date", "Issue date", date, date, None, None)],
        "category_certificate": [("applicant_name", "Applicant name", name, name, "applicant", None),
                                 ("stated_category", "Stated category", "DEMO GROUP A", "DEMO GROUP A", None, None),
                                 ("issue_date", "Issue date", date, date, None, None)],
        "other": [],
    }
    other_notes = [
        ["Reading room hours: 09:00 to 17:00", "Return demonstration books by Friday"],
        ["Campus shuttle departure: 08:30", "Demonstration route: North gate to library"],
        ["Laboratory practice begins at 10:00", "Bring a blank observation notebook"],
        ["Demonstration club meeting: Wednesday", "Agenda: exhibition planning and poster review"],
        ["Reading room hours: 10:00 to 16:00", "Fictional literature exhibition on Monday"],
    ]
    notes = other_notes[applicant] if label == "other" else []
    return definitions[label], notes


def draw_page(canvas, label, applicant, page, total_pages, layout):
    lines, fields = [], {name: deepcopy(ABSENT) for name in sorted(FIELD_CATALOG.get(label, set()))}

    def draw(text, x, y, font="PilotSans", size=12):
        # PDF bottom-left points -> raster top-left pixels at exactly 144 DPI.
        canvas.setFont(font, size)
        canvas.drawString(x, y, text)
        box = [2. * x, 2. * (800 - y - size), 2. * stringWidth(text, font, size), 2. * size * 1.25]
        lines.append(dict(text=text, box=box))
        return box

    draw(WATERMARK, 44, 765, size=10)
    title = ["LIBRARY NOTICE", "BUS TIMETABLE", "LABORATORY NOTICE", "CLUB MEETING AGENDA", "READING ROOM NOTICE"][applicant] if label == "other" else TITLES[label]
    draw(title, 44, 718, "PilotSansBold", 20)
    draw("Fictional teaching sample - document readiness only", 44, 686, size=11)
    definitions, notes = specifications(label, applicant, page)
    y = 625
    for name, caption, raw, value, role, unit in definitions:
        if layout == "layout_a":
            text = caption + ": " + raw
            box = draw(text, 44, y, size=12)
            value_x = 88 + 2 * stringWidth(caption + ": ", "PilotSans", 12)
            value_box = [value_x, box[1], 2 * stringWidth(raw, "PilotSans", 12), box[3]]
            y -= 65
        else:
            draw(caption, 60, y, "PilotSansBold", 11)
            value_box = draw(raw, 74, y - 23, size=13)
            y -= 85
        fields[name] = dict(state="present", raw_text=raw, normalized_value=value, person_role=role, unit=unit, box=value_box)
    for note in notes:
        draw(note, 44, y, size=12)
        y -= 38
    draw("No official seal, identifier or authenticity claim", 44, 82, size=10)
    draw(f"Page {page} of {total_pages}", 44, 56, size=10)
    canvas.showPage()
    return dict(width=SIZE[0], height=SIZE[1], full_text="\n".join(l["text"] for l in lines),
                lines=lines, fields=fields, source_to_sample=deepcopy(IDENTITY))


def render_bytes(content, page_index):
    with pdfium.PdfDocument(content) as document:
        page = document[page_index - 1]
        try:
            bitmap = page.render(scale=2)
            try:
                return bitmap.to_pil().convert("RGB").copy()
            finally:
                bitmap.close()
        finally:
            page.close()


def transform_box(box, matrix):
    x, y, w, h = box
    corners = np.array([[x, y, 1], [x+w, y, 1], [x, y+h, 1], [x+w, y+h, 1]]).T
    points = (np.asarray(matrix) @ corners)[:2]
    lower, upper = points.min(axis=1), points.max(axis=1)
    return [float(lower[0]), float(lower[1]), float(upper[0]-lower[0]), float(upper[1]-lower[1])]


def degrade(image, reference, variant, seed):
    annotation = deepcopy(reference)
    parameters = {}
    extension = ".png"
    if variant == "low_contrast":
        parameters = dict(scale=0.18, offset=205)
        image = Image.fromarray(np.clip(np.asarray(image) * 0.18 + 205, 0, 255).astype("uint8"))
    elif variant == "rotation":
        angle = 4.0 if seed % 2 else -4.0
        parameters = dict(angle_degrees_counterclockwise=angle, expand=False, resample="bicubic", fill=255)
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor="white")
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        cx, cy = SIZE[0] / 2, SIZE[1] / 2
        matrix = [[c, s, cx-c*cx-s*cy], [-s, c, cy+s*cx-c*cy], [0., 0., 1.]]
        annotation["source_to_sample"] = matrix
        for line in annotation["lines"]:
            line["box"] = transform_box(line["box"], matrix)
        for field in annotation["fields"].values():
            if field["box"]:
                field["box"] = transform_box(field["box"], matrix)
    elif variant == "blur_noise":
        parameters = dict(gaussian_blur_radius=1.8, gaussian_noise_sigma=8.0)
        blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(1.8))).astype(float)
        image = Image.fromarray(np.clip(blurred + np.random.default_rng(seed).normal(0, 8, blurred.shape), 0, 255).astype("uint8"))
    elif variant == "compression":
        parameters = dict(jpeg_quality=18, subsampling=2)
        extension = ".jpg"
    elif variant == "erased_content":
        # Explicit unreadable inventory fixture; keep a visible synthetic label.
        image = image.copy()
        image.paste("white", (0, 110, image.width, image.height))
        annotation["lines"] = annotation["lines"][:1]
        annotation["full_text"] = WATERMARK
        for field in annotation["fields"].values():
            if field["state"] == "present":
                field.update(state="unreadable", raw_text=None, normalized_value=None, box=None)
        parameters = dict(erase_rectangle=[0, 110, image.width, image.height], purpose="unreadable_upload_scenario")
    return image, annotation, parameters, extension


def generate(root, output, seed):
    if seed < 0:
        raise ValueError("seed must be nonnegative")
    root = root.resolve()
    output_path = resolve_inside(root, output)
    output_path.mkdir(parents=True, exist_ok=True)
    font_dir = Path(reportlab.__file__).parent / "fonts"
    font_files = {"PilotSans": font_dir / "Vera.ttf", "PilotSansBold": font_dir / "VeraBd.ttf"}
    for name, path in font_files.items():
        registerFont(TTFont(name, str(path)))
    records, artifacts, pages_by_key = [], set(), {}
    fictional = {f"fictional-{i+1:02d}": dict(applicant=name, guardian=f"Fictional Guardian {chr(65+i)}") for i, name in enumerate(NAMES)}

    def relative(path):
        return path.relative_to(root).as_posix()

    def add_record(source_id, applicant_id, label, layout, page, variant, input_path, source_hash, annotation, parameters, variant_seed):
        sample = f"{source_id}-p{page:02d}-{variant}"
        annotation.update(sample_id=sample, clean_sample_id=f"{source_id}-p{page:02d}-clean", coordinate_space=f"{sample}:original_pixels")
        reference_path = root / "data/annotations/pilot" / f"{sample}.json"
        reference = PageAnnotation.model_validate(annotation)
        write_json(reference_path, reference.model_dump())
        record = DatasetRecord(sample_id=sample, source_document_id=source_id, applicant_id=applicant_id,
            layout_id=layout, relative_path=relative(input_path), document_type=label, page_index=page if input_path.suffix == ".pdf" else 1,
            source_page_index=page,
            variant_id=variant, degradation=dict(type="none" if variant == "clean" else variant, parameters=parameters, seed=variant_seed),
            source_category="synthetic", consent_note="Generated fictional content only; no real applicant or institutional identifiers.",
            source_hash=source_hash, annotation_path=relative(reference_path), development_role="development_only")
        records.append(record)
        artifacts.update((relative(input_path), relative(reference_path)))
        pages_by_key[(applicant_id, label, page, variant)] = record

    for applicant in range(5):
        applicant_id = f"fictional-{applicant+1:02d}"
        layout = "layout_a" if applicant % 2 == 0 else "layout_b"
        extension = [".png", ".jpg", ".pdf", ".png", ".pdf"][applicant]
        for class_index, label in enumerate(LABELS):
            source_id = f"src-{applicant*6+class_index+1:03d}"
            count = 2 if applicant == 4 and label == "marksheet" else 1
            buffer = BytesIO()
            canvas = Canvas(buffer, pagesize=(600, 800), invariant=1, pageCompression=1)
            canvas.setTitle("Fictional academic document fixture")
            references = [draw_page(canvas, label, applicant, p, count, layout) for p in range(1, count+1)]
            canvas.save()
            content = buffer.getvalue()
            input_path = output_path / f"{source_id}{extension}"
            if extension == ".pdf":
                input_path.write_bytes(content)
            else:
                image = render_bytes(content, 1)
                image.save(input_path, **(dict(quality=95, subsampling=0) if extension == ".jpg" else {}))
            source_hash = sha256(input_path)
            for page, reference in enumerate(references, 1):
                add_record(source_id, applicant_id, label, layout, page, "clean", input_path, source_hash, deepcopy(reference),
                           dict(renderer="pypdfium2", dpi=144, pdf_points=[600, 800], jpeg_quality=95 if extension == ".jpg" else None), seed)
                # Single-image variants retain their source PDF page via source_page_index.
                image = render_bytes(content, page)
                if extension == ".jpg":
                    with Image.open(input_path) as stored:
                        image = stored.convert("RGB").copy()
                variants = ["low_contrast", "rotation", "blur_noise", "compression"]
                if applicant == 0 and label == "income_certificate":
                    variants.append("erased_content")
                for variant_index, variant in enumerate(variants, 1):
                    variant_seed = seed + (applicant*6+class_index)*100 + page*10 + variant_index
                    changed, annotation, parameters, ext = degrade(image, reference, variant, variant_seed)
                    path = output_path / f"{source_id}-p{page:02d}-{variant}{ext}"
                    changed.save(path, **(dict(quality=18, subsampling=2) if ext == ".jpg" else {}))
                    add_record(source_id, applicant_id, label, layout, page, variant, path, source_hash, annotation, parameters, variant_seed)
    bundles = []
    for scenario, applicant in [("complete", 0), ("missing_document", 1), ("conditional_not_applicable", 2), ("unreadable", 0), ("mismatch", 3)]:
        applicant_id = f"fictional-{applicant+1:02d}"
        selected = []
        for label in LABELS[:-1]:
            if (scenario == "missing_document" and label == "income_certificate") or (scenario == "conditional_not_applicable" and label == "category_certificate"):
                continue
            person = "fictional-05" if scenario == "mismatch" and label == "income_certificate" else applicant_id
            variant = "erased_content" if scenario == "unreadable" and label == "income_certificate" else "clean"
            selected += [r for (a, t, _, v), r in pages_by_key.items() if a == person and t == label and v == variant]
        files = sorted({r.relative_path for r in selected})
        hints = {r.relative_path: "income_certificate" for r in selected if r.variant_id == "erased_content"}
        inputs = BundleInput(scenario_id=scenario, profile=dict(applicant_reference=applicant_id,
                            category_certificate_required=scenario != "conditional_not_applicable", expected_name=NAMES[applicant]),
                            files=files, declared_type_hints=hints)
        states = dict.fromkeys(["marksheet", "income", "bonafide", "domicile", "category"], "satisfied")
        overall, rationale = {
            "complete": ("ready", "All five configured document types and required fields are visibly present for Fictional Aster."),
            "missing_document": ("incomplete", "The resolved inventory has no income certificate; four other required types are readable for Fictional Birch."),
            "conditional_not_applicable": ("ready", "Explicit category false excludes that item; all four mandatory documents are present for Fictional Clover."),
            "unreadable": ("needs_clearer_upload", "The income upload is visibly erased; its explicit user type hint is unverified. Preserve unreadable/review uncertainty, never ready or confident missing."),
            "mismatch": ("needs_review", "Income names Fictional Elm; the profile and other documents name Fictional Dahlia. Same applicant role conflicts; guardian is a separate role."),
        }[scenario]
        if scenario == "missing_document": states["income"] = "missing"
        if scenario == "conditional_not_applicable": states["category"] = "not_applicable"
        if scenario == "unreadable": states["income"] = "unreadable"
        if scenario == "mismatch": states["income"] = "needs_review"
        directory = root / "data/bundles/pilot" / scenario
        input_path, reference_path = directory / "inputs.json", directory / "expected.json"
        write_json(input_path, inputs.model_dump())
        write_json(reference_path, dict(schema_version="1.0", scenario_id=scenario, config_version="demo-1.0",
                   reference_status="provisional", reference_origin="manual_scenario_specification_no_engine",
                   sample_ids=[r.sample_id for r in selected], requirements=states, overall_state=overall,
                   rationale=rationale, acceptable_conservative_alternative="needs_review" if scenario == "unreadable" else None))
        bundles.append(dict(input_path=relative(input_path), reference_path=relative(reference_path)))
        artifacts.update((relative(input_path), relative(reference_path)))
    manifest = root / "data/manifests/pilot.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("".join(r.model_dump_json() + "\n" for r in records))
    metadata = dict(dataset_version=VERSION, generator_version=VERSION, seed=seed, output=output,
                    synthetic_only=True, fictional_applicants=fictional, bundles=bundles,
                    font_hashes={p.name: sha256(p) for p in font_files.values()},
                    generator_dependencies={name: version(name) for name in ("reportlab", "pypdfium2", "Pillow", "numpy")},
                    manifest_sha256=sha256(manifest), artifact_hashes={p: sha256(root / p) for p in sorted(artifacts)})
    write_json(manifest.with_suffix(".metadata.json"), metadata)
    return dict(manifest=relative(manifest), dataset_version=VERSION, samples=len(records), seed=seed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", default="data/synthetic/pilot", help="repository-relative generated media directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.root, args.output, args.seed), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Pilot generation failed: {exc}\n")


if __name__ == "__main__":
    main()
