"""Semantic UI boundary checks, including real OCR and CLI equivalence."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from scholarready.config import load_config
from scholarready.ingestion import IngestionLimits
from scholarready.preprocessing import load_preprocessing
from scholarready.schemas import ApplicantProfile, ApplicationResult
from scholarready.ui import (Upload, LocalRun, validate_uploads, request_key, invalidate_result,
                             discard_result, result_json, findings_csv, overlay)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / 'configs/scholarship_demo.json')
PREPROCESSING = load_preprocessing(ROOT / 'configs/preprocessing.json')
APPLICANT = ApplicantProfile(applicant_reference='ui-check', category_certificate_required=True,
                             expected_name='Fictional Aster')


def semantic(value):
    """Only run identity and measured timing vary between these fixed runs."""
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items()
                if k not in {'run_id', 'runtime_seconds', 'estimation_seconds'}}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def test_request_changes_and_cleanup():
    upload = Upload('page.png', b'one')
    def key(uploads=None, config=CONFIG, applicant=APPLICANT, branch='A', preprocessing=PREPROCESSING, model=None):
        return request_key(uploads or [upload], config, applicant, branch, preprocessing, model)
    original = key()
    config = CONFIG.model_copy(deep=True)
    config.requirements.pop()
    preprocessing = PREPROCESSING.model_copy(deep=True)
    preprocessing.adaptive_c = 17.
    alternatives = [key([Upload('page.png', b'two')]), key([Upload('renamed.png', b'one')]),
        key([Upload('page.png', b'one', 'marksheet')]), key(config=config),
        key(applicant=APPLICANT.model_copy(update={'category_certificate_required': None})),
        key(applicant=APPLICANT.model_copy(update={'expected_name': 'Another'})),
        key(branch='B'), key(preprocessing=preprocessing), key(model='different')]
    assert all(k != original for k in alternatives)
    run = LocalRun()
    root = run.root
    state = dict(local_run=run, result_key=original)
    assert not invalidate_result(state, original) and root.exists()
    assert invalidate_result(state, alternatives[0]) and not root.exists() and not state
    second = LocalRun()
    state.update(local_run=second, result_key=original)
    discard_result(state)
    assert not second.root.exists() and not state


@pytest.mark.parametrize('uploads', [[], [Upload('../a.png', b'')], [Upload('a\\b.png', b'')],
    [Upload('a.txt', b'')], [Upload('a.png', b'', 'invented')], [Upload('a.png', b'')] * 21])
def test_invalid_uploads(uploads):
    with pytest.raises(ValueError):
        validate_uploads(uploads)


def test_byte_bound():
    with pytest.raises(ValueError, match='limit'):
        validate_uploads([Upload('a.png', b'1234')], IngestionLimits(max_file_bytes=3))


def test_ui_initial_profile_and_reset():
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run()
    assert not app.exception
    assert app.selectbox(key='profile_category').value == 'Unknown'
    assert app.button[1].disabled
    app.selectbox(key='profile_category').select('Yes').run()
    app.text_input(key='profile_name').input('Fictional Aster').run()
    app.button[0].click().run()
    assert app.selectbox(key='profile_category').value == 'Unknown'
    assert app.text_input(key='profile_name').value == ''
    assert not app.exception


def test_real_upload_cli_equivalence_exports_failures_and_isolation(tmp_path):
    uploads = [Upload(f'src-{n:03d}.png', (ROOT / f'tests/fixtures/pilot/src-{n:03d}.png').read_bytes()) for n in range(1,6)]
    run = LocalRun()
    second = LocalRun()
    try:
        events = []
        result = run.execute(uploads, config=CONFIG, applicant=APPLICANT, preprocessing=PREPROCESSING,
                             progress=lambda *args: events.append(args))
        assert result.overall_state == 'ready' and result.completeness == 100
        assert events[0][0] == 0 and events[-1][0:2] == (5, 5)
        assert not (run.root / 'uploads').exists()
        profile = tmp_path / 'profile.json'
        profile.write_text(APPLICANT.model_dump_json())
        bundle = tmp_path / 'bundle.json'
        bundle.write_text(json.dumps(dict(scenario_id='ui-equivalence', declared_type_hints={},
            files=[f'tests/fixtures/pilot/{u.name}' for u in uploads], profile=APPLICANT.model_dump(mode='json'))))
        proc = subprocess.run([sys.executable, '-m', 'scholarready', 'analyze', '--bundle', str(bundle),
            '--input-root', str(ROOT), '--output', str(tmp_path / 'cli')], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        cli = ApplicationResult.model_validate_json((tmp_path / 'cli/result.json').read_text())
        assert semantic(cli.model_dump(mode='json')) == semantic(result.model_dump(mode='json'))
        assert ApplicationResult.model_validate_json(result_json(result)) == result
        rows = list(csv.DictReader(io.StringIO(findings_csv(result).decode('utf-8-sig'))))
        assert len(rows) == 5 and {r['state'] for r in rows} == {'satisfied'}
        for document in result.documents:
            for page in document.pages:
                processing = next(p for p in document.processing if p.page_id == page.page_id)
                with Image.open(run.output / page.original_image_path) as image:
                    assert overlay(image, document, page.page_id, processing.transform.target_space).size == image.size
                    with pytest.raises(ValueError, match='coordinate'):
                        overlay(image, document, page.page_id, 'wrong-space')
        corrupt = second.execute([Upload('corrupt.png', b'not a PNG', 'income_certificate')],
            config=CONFIG, applicant=APPLICANT)
        assert corrupt.overall_state == 'needs_review' and corrupt.documents[0].errors
        assert corrupt.documents[0].declared_type_hint == 'income_certificate'
        assert run.result.overall_state == 'ready' and run.root != second.root
        assert len(list(csv.DictReader(io.StringIO(findings_csv(corrupt).decode('utf-8-sig'))))) == 5 + len(corrupt.issues)
        result.requirements[0].actions = ['=1+1']
        assert "'=1+1" in findings_csv(result).decode('utf-8-sig')
    finally:
        run.close()
        second.close()
    assert not run.root.exists() and not second.root.exists()


def test_failed_run_cleans(monkeypatch):
    run = LocalRun()
    def fail(*args, **kwargs):
        raise ValueError('Explicit failure')
    monkeypatch.setattr('scholarready.ui.analyze', fail)
    with pytest.raises(ValueError, match='Explicit failure'):
        run.execute([Upload('a.png', b'bytes')], config=CONFIG, applicant=APPLICANT)
    assert not run.root.exists()


def test_invalid_run_also_cleans():
    run = LocalRun()
    with pytest.raises(ValueError):
        run.execute([], config=CONFIG, applicant=APPLICANT)
    assert not run.root.exists()


def test_model_mismatch_is_actionable(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr('scholarready.classification.LearnedClassifier.load',
        lambda path: SimpleNamespace(metadata={'model_sha256': 'test-only', 'inference_settings': {'branch': 'A'}}))
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run()
    app.selectbox(key='experiment_branch').select('B').run()
    app.selectbox(key='experiment_classifier').select('S05 learned classifier (trusted local model)').run()
    assert not app.exception and app.button[1].disabled
    assert any('requires branch A' in e.value for e in app.error)


def test_unknown_boolean_display_is_explicit():
    # Render a real shared result with unknown applicability; do not replace the
    # upload boundary or invoke any separate UI readiness logic.
    config = CONFIG
    applicant = ApplicantProfile(applicant_reference='unknown-display')
    run = LocalRun()
    try:
        app = AppTest.from_string("""
import runpy
import streamlit as st
module = runpy.run_path(APP_PATH, run_name='ui_import_only')
module['show_result'](st.session_state.test_run)
""".replace('APP_PATH', repr(str(ROOT / 'app/streamlit_app.py'))))
        run.execute([Upload('corrupt.png', b'bad')], config=config, applicant=applicant)
        app.session_state['test_run'] = run
        app.run()
        assert not app.exception
        table = app.dataframe[0].value
        category = table.loc[table['requirement'] == 'category'].iloc[0]
        assert category['applicable'] == category['in_denominator'] == 'Unknown'
    finally:
        run.close()


def test_reset_replaces_persistent_widget_values():
    from scholarready.ui import reset_application
    run = LocalRun()
    state = dict(local_run=run, result_key='old', upload_epoch=4, profile_category='Yes',
                 profile_name='Prior applicant', profile_reference='prior', experiment_branch='C',
                 experiment_classifier='S05 learned classifier (trusted local model)',
                 hint_prior='income_certificate', page_prior=2)
    reset_application(state)
    assert not run.root.exists() and 'local_run' not in state and 'result_key' not in state
    assert state['upload_epoch'] == 5 and 'hint_prior' not in state and 'page_prior' not in state
    assert state['profile_category'] == 'Unknown' and state['profile_name'] == ''
    assert state['profile_reference'] == 'local-application'
    assert state['experiment_branch'] == 'A' and state['experiment_classifier'] == 'Keyword baseline'
