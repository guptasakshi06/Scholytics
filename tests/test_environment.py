"""Small renderer regression and actionable missing-executable behavior."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("environment_check", Path(__file__).resolve().parents[1] / "scripts/check_environment.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_render_color_dimensions_and_closed_buffer(tmp_path):
    report = checker.renderer_smoke(tmp_path)
    assert report["status"] == "passed"
    assert report["dpi"] == 300
    # PDFium rounds fractional pixel extents upwards, including floating point residuals.
    assert report["width"] in (1800, 1801)
    assert report["height"] in (600, 601)
    assert report["color_and_closed_buffer_copy"] == "passed"


def test_missing_tesseract_actionable(monkeypatch, tmp_path):
    monkeypatch.setattr(checker.shutil, "which", lambda _: None)
    report = checker.check_environment(tmp_path)
    assert report["status"] == "failed"
    assert any("Install Tesseract plus English data" in error for error in report["errors"])
