#!/usr/bin/env python3
"""Real OCR through the Streamlit script using AppTest; NOT a browser upload test.

Only file_uploader is substituted (unsupported by AppTest). All controls,
processing, views, invalidation and exports use the production app and pipeline.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
import reportlab
from streamlit.testing.v1 import AppTest

from scholarready.pipeline import write_json, code_snapshot
from scholarready.schemas import ApplicationResult
from scholarready.ui import result_json, findings_csv

ROOT = Path(__file__).resolve().parents[1]


def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items()
                if k not in {'run_id', 'runtime_seconds', 'estimation_seconds'}}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    fixtures = output / 'fixtures'
    fixtures.mkdir()
    for n in range(1, 6):
        shutil.copyfile(ROOT / f'tests/fixtures/pilot/src-{n:03d}.png', fixtures / f'upload-{n}.png')
    shutil.copyfile(ROOT / 'tests/fixtures/pilot/src-025.pdf', fixtures / 'multipage.pdf')
    shutil.copyfile(ROOT / 'tests/fixtures/pilot/src-007.jpg', fixtures / 'income-b.jpg')
    printed = dict(
        unreadable=['INCOME CERTIFICATE', 'Applicant name: Fictional Aster',
                    'Guardian name: Fictional Guardian A', 'Issue date: 2026-01-15'],
        mismatch=['INCOME CERTIFICATE', 'Applicant name: Fictional Birch',
                  'Guardian name: Fictional Guardian A', 'Annual income (INR/year): 96000', 'Issue date: 2026-01-15'],
        other=['LIBRARY NOTICE', 'Fictional reading hours: 09:00 to 17:00'])
    font = ImageFont.truetype(str(Path(reportlab.__file__).parent / 'fonts/Vera.ttf'), 28)
    for name, lines in printed.items():
        image = Image.new('RGB', (1400, 1300), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((60, 30), 'SYNTHETIC - FOR ACADEMIC DEMONSTRATION', font=font, fill='black')
        for index, line in enumerate(lines):
            draw.text((60, 130 + index * 130), line, font=font, fill='black')
        image.save(fixtures / f'{name}.png')
    (fixtures / 'corrupt.png').write_bytes(b'Explicit fictional corrupt input')
    # Written before inference, manually derived from printed fixture lines and
    # the already reviewed S07 scenario definitions. No final-test data.
    specifications = {
        'complete': ('ready', 100.), 'missing': ('incomplete', 80.),
        'unreadable': ('needs_clearer_upload', 80.), 'mismatch': ('needs_review', 0.),
        'other': ('incomplete', 80.), 'corrupt': ('needs_review', 80.),
        'multipage': ('needs_review', None),
        'branch_B': ('ready', 100.), 'branch_C': ('ready', 100.),
        'learned': ('ready', 100.),
    }
    write_json(output / 'specifications_before_inference.json', dict(
        review='Codex separate manual specification, S07 visible fixture/rule review reused; no student sign-off',
        printed=printed, expected=specifications, final_test_consumed=False))
    wrapper = """
import runpy
import streamlit as st
# AppTest does not support file uploads: substitute only the upload boundary.
st.file_uploader = lambda *args, **kwargs: st.session_state.get('test_uploads', [])
runpy.run_path(APP_PATH, run_name='__main__')
""".replace('APP_PATH', repr(str(ROOT / 'app/streamlit_app.py')))
    checks, index = [], []
    for case, expected in specifications.items():
        paths = [fixtures / f'upload-{n}.png' for n in range(1, 6)]
        category = 'Yes'
        if case == 'missing':
            paths.pop(1)
        if case in {'unreadable', 'mismatch', 'other', 'corrupt'}:
            paths[1] = fixtures / f'{case}.png'
        if case == 'multipage':
            paths = [fixtures / 'multipage.pdf']
            category = 'Unknown'
        uploads = []
        for path in paths:
            file = io.BytesIO(path.read_bytes())
            file.name = path.name
            uploads.append(file)
        app = AppTest.from_string(wrapper, default_timeout=90)
        app.session_state['test_uploads'] = uploads
        app.run()
        assert not app.exception, (case, str(app.exception))
        app.selectbox(key='profile_category').select(category).run()
        if case != 'multipage':
            app.text_input(key='profile_name').input('Fictional Aster').run()
        if case.startswith('branch_'):
            app.selectbox(key='experiment_branch').select(case[-1]).run()
        if case == 'learned':
            app.selectbox(key='experiment_classifier').select('S05 learned classifier (trusted local model)').run()
        app.button[1].click().run()
        assert not app.exception, (case, str(app.exception))
        run = app.session_state['local_run']
        result = run.result
        actual = (result.overall_state, result.completeness)
        assert actual == expected, (case, expected, actual)
        destination = output / case / 'ui'
        shutil.copytree(run.output, destination)
        (destination / 'download.json').write_bytes(result_json(result))
        (destination / 'findings.csv').write_bytes(findings_csv(result))
        assert ApplicationResult.model_validate_json((destination / 'download.json').read_bytes()) == result
        rows = list(csv.DictReader(io.StringIO((destination / 'findings.csv').read_text(encoding='utf-8-sig'))))
        assert len(rows) == len(result.requirements) + len(result.issues)
        assert sum('Download' in e.proto.label for e in app.get('download_button')) == 2
        assert app.get('image'), (case, 'original/processed evidence images not emitted')
        page_counts = [len(d.pages) for d in result.documents]
        if case == 'multipage':
            assert page_counts == [2]
            page_widget = next(s for s in app.selectbox if s.label == 'Page')
            page_widget.select_index(1).run()
            assert not app.exception
            assert 'Page 2' in ' '.join(c.value for c in app.caption)
            checks.append('multipage page-2 navigation')
        # Reproduce with exact same config, attributes, hint-free files and model.
        # Input-only bundle is authored from user inputs, never annotations.
        bundle = output / case / 'cli.inputs.json'
        write_json(bundle, dict(scenario_id=case, files=[str(p.relative_to(output)) for p in paths],
            profile=json.loads((destination / 'applicant.json').read_text()), declared_type_hints={}))
        command = [sys.executable, '-m', 'scholarready', 'analyze', '--bundle', str(bundle),
            '--input-root', str(output), '--branch', case[-1] if case.startswith('branch_') else 'A',
            '--output', str(output / case / 'cli')]
        if case == 'learned':
            command += ['--classifier', str(ROOT / 'artifacts/runs/s05-classification-final/model')]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (output / case / 'cli.stdout.txt').write_text(proc.stdout)
        (output / case / 'cli.stderr.txt').write_text(proc.stderr)
        assert proc.returncode == (1 if case == 'corrupt' else 0), (case, proc.stderr)
        cli = ApplicationResult.model_validate_json((output / case / 'cli/result.json').read_text())
        assert semantic(cli.model_dump(mode='json')) == semantic(result.model_dump(mode='json')), case
        if case == 'complete':
            old_root = run.root
            app.selectbox(key='profile_category').select('Unknown').run()
            assert 'local_run' not in app.session_state and not old_root.exists()
            assert not app.get('download_button')
            app.button[1].click().run()
            assert not app.exception
            new = app.session_state['local_run']
            assert new.result.overall_state == 'needs_review' and new.result.completeness is None
            shutil.copytree(new.output, output / 'conditional_unknown' / 'ui')
            app.selectbox(key='profile_category').select('No').run()
            assert not new.root.exists() and 'local_run' not in app.session_state
            app.button[1].click().run()
            false_run = app.session_state['local_run']
            assert false_run.result.overall_state == 'ready'
            assert false_run.result.requirements[-1].state == 'not_applicable'
            shutil.copytree(false_run.output, output / 'conditional_false' / 'ui')
            checks += ['category true/unknown/false rerun + cleanup + export invalidation']
            # Hint change also invalidates rather than reusing a stale result.
            hint_widget = next(s for s in app.selectbox if s.label.startswith('Type hint'))
            hint_widget.select('other').run()
            assert not false_run.root.exists() and 'local_run' not in app.session_state
            app.button[1].click().run()
            hint_run = app.session_state['local_run']
            assert hint_run.result.documents[0].declared_type_hint == 'other'
            assert hint_run.result.documents[0].prediction.document_type == 'marksheet'
            checks.append('hint retained as unverified input; automatic class preserved')
        # Explicit reset removes current pages, profiles, and widget upload generation.
        current_root = app.session_state['local_run'].root
        app.button[0].click().run()
        assert not current_root.exists() and 'local_run' not in app.session_state
        assert app.selectbox(key='profile_category').value == 'Unknown'
        assert not app.exception
        index.append(dict(case=case, expected=expected, actual=actual, ui_run_id=result.run_id,
            cli_run_id=cli.run_id, cli_command=command, cli_exit=proc.returncode,
            semantic_equivalence=True, pages=page_counts))
        print(f'{case}: {actual}; CLI semantic equality, rendering, export bytes and reset PASS', flush=True)
    hashes = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in output.rglob('*') if p.is_file()}
    write_json(output / 'audit.json', dict(status='PASS_HEADLESS_ONLY', cases=index, extra_checks=checks,
        code_snapshot=code_snapshot(), artifact_hashes=hashes, final_test_consumed=False,
        browser_verified=False, method='Streamlit AppTest with file_uploader substituted; actual OCR/CLI runs. Does not prove native browser upload, visual layout or downloads.'))
    print('PASS: headless flow only; actual browser evidence remains separately required.', flush=True)


if __name__ == '__main__':
    main()
