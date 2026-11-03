"""Evaluation cannot accidentally consume protected roles or silently misjoin references."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_s03_evaluator_rejects_test_before_inference(tmp_path):
    record = json.loads((ROOT / 'data/manifests/pilot.jsonl').read_text().splitlines()[0])
    record['development_role'] = 'test'
    manifest = tmp_path / 'protected.jsonl'
    manifest.write_text(json.dumps(record) + '\n')
    output = tmp_path / 'run'
    process = subprocess.run([sys.executable, 'scripts/evaluate_ocr_baseline.py', '--manifest', str(manifest),
        '--samples', record['sample_id'], '--output', str(output)], cwd=ROOT, text=True, capture_output=True)
    assert process.returncode == 2 and 'final test is forbidden' in process.stderr
    assert not output.exists()


def test_s04_comparison_rejects_test_before_inference(tmp_path):
    record = json.loads((ROOT / 'data/manifests/pilot.jsonl').read_text().splitlines()[0])
    record['development_role'] = 'test'
    manifest = tmp_path / 'protected.jsonl'
    manifest.write_text(json.dumps(record) + '\n')
    output = tmp_path / 'run'
    process = subprocess.run([sys.executable, 'scripts/compare_preprocessing.py', '--manifest', str(manifest),
        '--samples', record['sample_id'], '--output', str(output)], cwd=ROOT, text=True, capture_output=True)
    assert process.returncode == 2 and 'final test is forbidden' in process.stderr
    assert not output.exists()
