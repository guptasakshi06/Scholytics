#!/usr/bin/env python3
"""Render pilot review materials; this does not approve references or run inference."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
from scholarready.dataset import read_page, resolve_inside


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/pilot.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.root / args.manifest).read_text().splitlines()]
    clean = [r for r in rows if r["variant_id"] == "clean"]
    args.output.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1500, ((len(clean)+4)//5)*425), "#dddddd")
    for i, r in enumerate(clean):
        image = read_page(resolve_inside(args.root, r["relative_path"]), r["page_index"])
        image.thumbnail((290, 390))
        x, y = (i % 5)*300, (i // 5)*425
        sheet.paste(image, (x+5, y+25))
        ImageDraw.Draw(sheet).text((x+5, y+5), r["sample_id"], fill="black")
    sheet.save(args.output / "clean_contact_sheet.png")
    selected = [*(f"src-{i:03d}-p01-clean" for i in range(1, 8)), "src-025-p02-clean", "src-026-p01-clean",
                "src-002-p01-erased_content", *(f"src-001-p01-{v}" for v in ("rotation", "blur_noise", "low_contrast", "compression"))]
    for sid in selected:
        record = next(r for r in rows if r["sample_id"] == sid)
        image = read_page(resolve_inside(args.root, record["relative_path"]), record["page_index"])
        image.thumbnail((780, 1040))
        image.save(args.output / (sid + ".png"))
    for sid in ("src-002-p01-clean", "src-001-p01-rotation"):
        record = next(r for r in rows if r["sample_id"] == sid)
        image = read_page(resolve_inside(args.root, record["relative_path"]), record["page_index"])
        annotation = json.loads(resolve_inside(args.root, record["annotation_path"]).read_text())
        draw = ImageDraw.Draw(image)
        for field in annotation["fields"].values():
            if field["box"]:
                x, y, w, h = field["box"]
                draw.rectangle((x, y, x+w, y+h), outline="red", width=2)
        image.thumbnail((780, 1040))
        image.save(args.output / (sid + "-field-boxes.png"))
    print(f"Wrote {len(clean)}-page contact sheet, {len(selected)} detail images and 2 field-box overlays. No review status changed.")


if __name__ == "__main__":
    main()
