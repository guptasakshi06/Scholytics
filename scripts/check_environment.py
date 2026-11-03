#!/usr/bin/env python3
"""Check the actual local stack, renderer, and optionally OCR; no dataset needed."""
import argparse
import importlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

IMPORTS = {
    "scholarready": "scholarready", "numpy": "numpy", "opencv-python-headless": "cv2",
    "pandas": "pandas", "Pillow": "PIL", "pytesseract": "pytesseract",
    "pypdfium2": "pypdfium2", "scikit-learn": "sklearn", "matplotlib": "matplotlib",
    "seaborn": "seaborn", "streamlit": "streamlit", "pydantic": "pydantic",
    "pytest": "pytest", "reportlab": "reportlab",
}


def renderer_smoke(directory: Path) -> dict:
    import pypdfium2 as pdfium
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas

    directory.mkdir(parents=True, exist_ok=True)
    pdf_path = directory / "environment_synthetic.pdf"
    png_path = directory / "environment_render.png"
    canvas = Canvas(str(pdf_path), pagesize=(432, 144), invariant=1)
    canvas.setFillColorRGB(1, 0, 0)
    canvas.rect(0, 72, 72, 72, stroke=0, fill=1)
    canvas.setFillColorRGB(0, 0, 0)
    canvas.setFont("Helvetica", 16)
    canvas.drawString(82, 90, "ENVIRONMENT CHECK")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(10, 25, "SYNTHETIC - FOR ACADEMIC DEMONSTRATION")
    canvas.save()
    dpi = 300
    with pdfium.PdfDocument(str(pdf_path)) as document:
        page = document[0]
        try:
            expected_size = (math.ceil(page.get_width() * (dpi / 72)), math.ceil(page.get_height() * (dpi / 72)))
            bitmap = page.render(scale=dpi / 72)
            try:
                # to_pil may share the bitmap buffer. Copy BEFORE closing any owner.
                image = bitmap.to_pil().convert("RGB").copy()
            finally:
                bitmap.close()
        finally:
            page.close()
    # These checks deliberately happen after PDF/page/bitmap have closed.
    if image.size != expected_size or image.mode != "RGB":
        raise RuntimeError(f"unexpected rendered size/mode: {image.size}/{image.mode}")
    if image.getpixel((50, 50)) != (255, 0, 0):
        raise RuntimeError("red patch color/orientation is incorrect")
    if image.getpixel((1750, 550)) != (255, 255, 255):
        raise RuntimeError("white background is incorrect")
    image.save(png_path)
    with Image.open(png_path) as reopened:
        reopened.load()
        if reopened.getpixel((50, 50)) != (255, 0, 0):
            raise RuntimeError("saved copy did not retain its pixel data")
    return {"status": "passed", "dpi": dpi, "width": image.width, "height": image.height,
            "mode": image.mode, "page_points": [432, 144], "rounding": "ceil(points * (dpi / 72))", "color_and_closed_buffer_copy": "passed",
            "pdf": str(pdf_path), "png": str(png_path)}


def check_environment(smoke_dir: Path, ocr_smoke: bool = False) -> dict:
    report = {"python": platform.python_version(), "executable": sys.executable,
              "platform": platform.platform(), "os_release": platform.freedesktop_os_release()
              if sys.platform.startswith("linux") else {}, "packages": {}, "errors": []}
    if sys.version_info[:2] != (3, 12):
        report["errors"].append("Use Python 3.12; only that Python series is verified for this project.")
    for distribution, module in IMPORTS.items():
        try:
            importlib.import_module(module)
            report["packages"][distribution] = version(distribution)
        except Exception as exc:
            report["errors"].append(f"{distribution}: {exc}. Install with this interpreter: python -m pip install -e '.[dev]'")
    executable = shutil.which("tesseract")
    report["tesseract_executable"] = executable
    if executable is None:
        report["errors"].append("Tesseract executable missing from PATH. Install Tesseract plus English data; see docs/troubleshooting.md.")
    else:
        try:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=True, timeout=15)
            report["tesseract_version"] = result.stdout.splitlines()[0]
            result = subprocess.run([executable, "--list-langs"], capture_output=True, text=True, check=True, timeout=15)
            report["tesseract_languages"] = result.stdout.splitlines()[1:]
            if "eng" not in report["tesseract_languages"]:
                report["errors"].append("English 'eng' data missing. Install tesseract-ocr-eng or fix TESSDATA_PREFIX.")
        except (OSError, subprocess.SubprocessError) as exc:
            report["errors"].append(f"Tesseract invocation failed: {exc}. Check PATH/TESSDATA_PREFIX.")
    try:
        report["renderer"] = renderer_smoke(smoke_dir)
    except Exception as exc:
        report["renderer"] = {"status": "failed", "reason": str(exc)}
        report["errors"].append(f"PDF render failed: {exc}. Reinstall the locked pypdfium2/Pillow and dev dependencies.")
    report["ocr_smoke"] = {"status": "not_requested"}
    if ocr_smoke and report["renderer"]["status"] != "passed":
        report["ocr_smoke"] = {"status": "blocked", "reason": "renderer smoke failed"}
    elif ocr_smoke:
        try:
            import pytesseract
            from PIL import Image
            with Image.open(smoke_dir / "environment_render.png") as image:
                text = pytesseract.image_to_string(image, lang="eng", config="--psm 6", timeout=30)
            if not text.strip():
                raise RuntimeError("no text returned from synthetic environment fixture")
            report["ocr_smoke"] = {"status": "passed", "text": text, "language": "eng", "settings": "--psm 6",
                                   "scope": "environment invocation only; not performance evidence"}
        except Exception as exc:
            report["ocr_smoke"] = {"status": "failed", "reason": str(exc)}
            report["errors"].append(f"OCR smoke failed: {exc}. Check executable, eng data and renderer result.")
    report["status"] = "passed" if not report["errors"] else "failed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="save JSON evidence")
    parser.add_argument("--smoke-dir", type=Path, help="retain tiny fictional PDF/PNG; otherwise use temporary files")
    parser.add_argument("--ocr-smoke", action="store_true", help="also invoke actual local English Tesseract")
    args = parser.parse_args()
    if args.smoke_dir:
        report = check_environment(args.smoke_dir, args.ocr_smoke)
    else:
        with tempfile.TemporaryDirectory(prefix="scholarready-env-") as directory:
            report = check_environment(Path(directory), args.ocr_smoke)
        if report.get("renderer", {}).get("status") == "passed":
            report["renderer"]["pdf"] = None
            report["renderer"]["png"] = None
            report["renderer"]["artifact_note"] = "temporary smoke files removed"
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
