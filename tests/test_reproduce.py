"""Submission/reproduction integrity boundaries; no frozen method changes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_rejects_changed_missing_and_escaping_artifacts(tmp_path):
    reproduce = script('reproduce')
    path = tmp_path / 'evidence.json'
    path.write_text('original')
    hashes = {'evidence.json': reproduce.digest(path)}
    assert reproduce.check_hashes(tmp_path, hashes) == 1
    path.write_text('changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        reproduce.check_hashes(tmp_path, hashes)
    path.unlink()
    with pytest.raises(ValueError, match='Missing packaged artifact'):
        reproduce.check_hashes(tmp_path, hashes)
    with pytest.raises(ValueError, match='escapes inventory root'):
        reproduce.check_hashes(tmp_path, {'../elsewhere': 'x'})


def test_existing_reproduction_output_is_preserved(tmp_path):
    sentinel = tmp_path / 'keep.txt'
    sentinel.write_text('preserve')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/reproduce.py'), '--mode', 'final',
                             '--output', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 2 and 'already exists' in result.stderr
    assert sentinel.read_text() == 'preserve'
    assert not (tmp_path / 'reproduction.json').exists()


def test_package_excludes_private_files_environments_and_symlinks(tmp_path):
    package = script('package_submission')
    for name in package.TOP_FILES:
        (tmp_path / name).write_text('public')
    freeze_path = tmp_path / 'docs/verification/s09/freeze.json'
    freeze_path.parent.mkdir(parents=True)
    freeze_path.write_text('{"artifact_hashes": {}}')
    for relative in ['data/private/applicant.pdf', 'data/synthetic/unselected.png', '.venv/secret',
                     '.env', 'src/cache.egg-info/metadata', 'src/__pycache__/bytecode.pyc']:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('exclude')
    paths = {p.relative_to(tmp_path).as_posix() for p in package.collect(tmp_path)}
    assert paths == set(package.TOP_FILES) | {'docs/verification/s09/freeze.json'}
    link = tmp_path / 'src/linked.py'
    link.symlink_to(tmp_path / 'README.md')
    with pytest.raises(ValueError, match='Symlink'):
        package.collect(tmp_path)


def test_extracted_package_detects_changed_deliverable(tmp_path):
    package = script('package_submission')
    path = tmp_path / 'README.md'
    path.write_text('included')
    manifest = {'files': {'README.md': {'bytes': path.stat().st_size, 'sha256': package.digest(path)}}}
    (tmp_path / 'SUBMISSION_MANIFEST.json').write_text(json.dumps(manifest))
    assert package.verify(tmp_path)['files'] == 1
    path.write_text('tampered')
    with pytest.raises(ValueError, match='missing or changed'):
        package.verify(tmp_path)
