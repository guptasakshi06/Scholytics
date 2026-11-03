"""Real Tesseract integration and checklist regression checks, no references as inputs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image
import pytest

from scholarready.cli import discover
from scholarready.config import load_config
from scholarready.ocr import recognize, OCRSettings
from scholarready.pipeline import analyze
from scholarready.requirements import evaluate
from scholarready.schemas import ApplicantProfile, ApplicationResult

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/pilot'
CONFIG = ROOT / 'configs/scholarship_demo.json'


@pytest.fixture(scope='module')
def clean_run(tmp_path_factory):
    root = tmp_path_factory.mktemp('real_ocr')
    paths = []
    for n in range(1, 6):
        destination = root / f'upload-{n}.png'
        shutil.copyfile(FIXTURES / f'src-{n:03d}.png', destination)
        paths.append(destination)
    # Real inference must survive renamed files in a directory with no annotations/manifests.
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        assert not {'annotations', 'manifests'} & set(path.parts)
        assert path.name != 'expected.json'
        return original_open(path, *args, **kwargs)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, 'open', guarded_open)
        result = analyze(paths, config=load_config(CONFIG), applicant=ApplicantProfile(
            applicant_reference='fictional-test', category_certificate_required=True,
            expected_name='Fictional Aster'), output=root / 'run')
    return root, paths, result


def test_real_bundle_has_evidence_and_portable_roundtrip(clean_run):
    root, _, result = clean_run
    assert result.overall_state == 'ready' and result.completeness == 100.
    assert len(result.documents) == 5
    assert all(d.ocr[0].engine == 'Tesseract' and d.ocr[0].engine_version.startswith('tesseract 5.') for d in result.documents)
    assert all(d.ocr[0].tokens for d in result.documents)
    assert ApplicationResult.model_validate_json((root / 'run/result.json').read_text()) == result
    for d in result.documents:
        ids = {t.token_id for o in d.ocr for t in o.tokens}
        for f in d.fields:
            if f.validation_state == 'valid':
                assert set(f.token_references) <= ids
                assert f.page_id in {p.page_id for p in d.pages}
    metadata = json.loads((root / 'run/metadata.json').read_text())
    assert metadata['dataset_hash'] is None and metadata['model_hash'] is None
    assert all((root / 'run' / p).exists() for p in metadata['output_paths'])
    moved = root / 'moved-run'
    shutil.copytree(root / 'run', moved)
    assert all((moved / p.original_image_path).exists() for d in result.documents for p in d.pages)


def test_missing_unknown_conditional_names_and_empty_config(clean_run):
    _, _, result = clean_run
    config = load_config(CONFIG)
    profile = ApplicantProfile(applicant_reference='fictional', category_certificate_required=True)
    docs = [d for d in result.documents if d.prediction.document_type != 'income_certificate']
    requirements, _, overall, completeness, _ = evaluate(config, profile, docs)
    assert overall == 'incomplete' and completeness == 80.
    assert next(r for r in requirements if r.requirement_id == 'income').state == 'missing'
    profile.category_certificate_required = None
    _, _, overall, completeness, _ = evaluate(config, profile, result.documents)
    assert overall == 'needs_review' and completeness is None
    profile.category_certificate_required = False
    requirements, _, overall, completeness, _ = evaluate(config, profile, result.documents)
    assert overall == 'ready' and completeness == 100.
    assert requirements[-1].state == 'not_applicable'
    profile.expected_name = 'Fictional Different'
    assert evaluate(config, profile, result.documents)[2] == 'needs_review'
    empty = load_config(CONFIG)
    empty.requirements = []
    assert evaluate(empty, profile, result.documents)[2:4] == ('needs_review', None)


def test_monthly_constraint_duplicate_and_invalid_fields(clean_run):
    _, _, result = clean_run
    docs = [d.model_copy(deep=True) for d in result.documents]
    profile = ApplicantProfile(applicant_reference='fictional', category_certificate_required=True)
    income = next(d for d in docs if d.prediction.document_type == 'income_certificate')
    amount = next(f for f in income.fields if f.field_name == 'annual_income')
    amount.unit = 'INR/month'
    req = evaluate(load_config(CONFIG), profile, docs)[0]
    assert next(r for r in req if r.requirement_id == 'income').state == 'needs_review'
    assert evaluate(load_config(CONFIG), profile, docs + [income])[2] == 'needs_review'


def test_unreadable_corrupt_and_ambiguous_inventory(clean_run, tmp_path):
    _, paths, _ = clean_run
    blank = tmp_path / 'unknown.png'
    Image.new('RGB', (400, 300), 'white').save(blank)
    # No declared type hint: do not confidently label the absent income item missing.
    selected = [paths[0], blank, *paths[2:]]
    result = analyze(selected, config=load_config(CONFIG), applicant=ApplicantProfile(
        applicant_reference='fictional', category_certificate_required=True), output=tmp_path / 'blank-run')
    assert result.overall_state == 'needs_review'
    assert next(r for r in result.requirements if r.requirement_id == 'income').state == 'needs_review'
    assert result.documents[1].prediction.decision == 'unreadable'
    assert result.documents[1].ocr[0].status == 'empty'
    bad = tmp_path / 'bad.png'; bad.write_bytes(b'bad')
    failed = analyze([bad], config=load_config(CONFIG), applicant=ApplicantProfile(applicant_reference='fictional'), output=tmp_path / 'bad-run')
    assert failed.documents[0].errors and failed.overall_state == 'needs_review'
    assert all(r.state == 'needs_review' for r in failed.requirements)


def test_hint_is_unverified_and_references_are_never_opened(monkeypatch, tmp_path):
    blank = tmp_path / 'blank.png'; Image.new('RGB', (400, 300), 'white').save(blank)
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        assert not {'annotations', 'manifests'} & set(path.parts)
        assert path.name != 'expected.json'
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded_open)
    result = analyze([blank], config=load_config(CONFIG), applicant=ApplicantProfile(
        applicant_reference='fictional', category_certificate_required=True), output=tmp_path / 'run',
        hints={str(blank.resolve()): 'income_certificate'})
    assert result.documents[0].prediction.document_type is None
    assert result.documents[0].declared_type_hint == 'income_certificate'
    states = {r.requirement_id: r.state for r in result.requirements}
    assert states['income'] == 'unreadable' and states['marksheet'] == 'needs_review'


def test_ocr_timeout_is_explicit(monkeypatch, clean_run):
    root, _, result = clean_run
    def timeout(*args, **kwargs):
        assert kwargs['timeout'] == .1
        raise RuntimeError('Tesseract process timeout')
    monkeypatch.setattr('scholarready.ocr.pytesseract.image_to_data', timeout)
    ocr = recognize(result.documents[0].pages[0], root / 'run', OCRSettings(timeout_seconds=.1), 'fixture')
    assert ocr.status == 'error' and 'timeout' in ocr.reason


def test_directory_discovery_ignores_json_and_is_bounded(tmp_path):
    (tmp_path / 'expected.json').write_text('{invalid labels should never be parsed')
    shutil.copyfile(FIXTURES / 'src-001.png', tmp_path / 'arbitrary.png')
    assert [p.name for p in discover(tmp_path, 2)] == ['arbitrary.png']
    shutil.copyfile(FIXTURES / 'src-002.png', tmp_path / 'second.png')
    with pytest.raises(ValueError, match='max_files'):
        discover(tmp_path, 1)


def test_cli_failures_and_existing_run_are_actionable(tmp_path, clean_run):
    root, _, _ = clean_run
    cmd = [sys.executable, '-m', 'scholarready', 'analyze', '--input', str(tmp_path / 'missing.png'),
           '--profile', str(CONFIG), '--output', str(tmp_path / 'failed')]
    process = subprocess.run(cmd, text=True, capture_output=True)
    assert process.returncode == 1 and 'preserved' in process.stderr
    assert json.loads((tmp_path / 'failed/result.json').read_text())['overall_state'] == 'needs_review'
    existing = subprocess.run([sys.executable, '-m', 'scholarready', 'demo', '--profile', str(CONFIG),
        '--output', str(root / 'run')], text=True, capture_output=True)
    assert existing.returncode == 2 and 'exists' in existing.stderr


@pytest.mark.parametrize('timeout', [0., -1., float('nan'), 121.])
def test_invalid_ocr_timeouts(timeout):
    with pytest.raises(ValueError):
        OCRSettings(timeout_seconds=timeout)
