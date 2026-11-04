#!/usr/bin/env python3
"""Audit preserved S08 development outputs and compact evidence; no inference."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil

from scholarready.schemas import ApplicationResult
from scholarready.pipeline import write_json
from verify_s08 import semantic

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT / 'artifacts/runs/s08-headless-complete')
    parser.add_argument('--evidence', type=Path, default=ROOT / 'docs/verification/s08')
    args = parser.parse_args()
    run, evidence = args.run.resolve(), args.evidence.resolve()
    audit = json.loads((run / 'audit.json').read_text())
    for name, digest in audit['artifact_hashes'].items():
        assert sha(run / name) == digest, name
    assert len(audit['cases']) == 10 and all(c['semantic_equivalence'] for c in audit['cases'])
    assert not audit['final_test_consumed']
    for case in audit['cases']:
        for route in ('ui', 'cli'):
            source = run / case['case'] / route
            result = ApplicationResult.model_validate_json((source / 'result.json').read_bytes())
            assert (result.overall_state, result.completeness) == tuple(case['expected'])
            dest = evidence / 'headless' / case['case'] / route
            dest.mkdir(parents=True, exist_ok=True)
            for path in source.glob('*'):
                if path.suffix in {'.json', '.csv'}:
                    shutil.copyfile(path, dest / path.name)
        assert semantic(json.loads((run / case['case'] / 'ui/result.json').read_text())) == semantic(
            json.loads((run / case['case'] / 'cli/result.json').read_text()))
    for case in ('conditional_unknown', 'conditional_false'):
        dest = evidence / 'headless' / case / 'ui'
        dest.mkdir(parents=True, exist_ok=True)
        for path in (run / case / 'ui').glob('*.json'):
            shutil.copyfile(path, dest / path.name)
    for name in ('audit.json', 'specifications_before_inference.json'):
        shutil.copyfile(run / name, evidence / ('headless_' + name))
    browser = ApplicationResult.model_validate_json((evidence / 'browser_download.json').read_bytes())
    cli = ApplicationResult.model_validate_json((evidence / 'browser_cli_result.json').read_bytes())
    assert semantic(browser.model_dump(mode='json')) == semantic(cli.model_dump(mode='json'))
    assert browser.overall_state == 'ready' and browser.completeness == 100
    rows = list(csv.DictReader(io.StringIO((evidence / 'browser_download.csv').read_text(encoding='utf-8-sig'))))
    assert len(rows) == 5 and all(r['state'] == 'satisfied' for r in rows)
    final_pdf = ApplicationResult.model_validate_json((evidence / 'browser_pdf_download.json').read_bytes())
    assert final_pdf.overall_state == 'needs_review' and final_pdf.completeness is None
    assert [len(d.pages) for d in final_pdf.documents] == [2, 0]
    assert final_pdf.documents[1].errors
    assert all(p.branch_id == 'C' for p in final_pdf.documents[0].processing)
    final_state = (evidence / 'browser_pdf_final.txt').read_text()
    assert 'Unknown' in final_state and 'Unresolved' in final_state and 'cannot decode as PNG/JPEG' in final_state
    reset_state = (evidence / 'browser_reset_final.txt').read_text()
    assert 'Value: Unknown' in reset_state and 'Prior fictional applicant' not in reset_state
    assert 'Download application JSON' not in reset_state
    page_state = (evidence / 'browser_pdf_page2_final.txt').read_text()
    assert 'Page 2' in page_state and 'PDF DPI: 300' in page_state
    for name, token in [('browser_missing.txt', 'Overall: incomplete'),
                        ('browser_unreadable.txt', 'Overall: needs_clearer_upload'),
                        ('browser_mismatch.txt', 'Overall: needs_review'),
                        ('browser_other.txt', 'Overall: incomplete')]:
        assert token in (evidence / name).read_text(), name
    protected = ['requirements.lock.txt', 'pyproject.toml', 'configs/preprocessing.json',
                 'configs/scholarship_demo.json', 'src/scholarready/classification.py',
                 'src/scholarready/extraction.py', 'src/scholarready/requirements.py',
                 'data/manifests/pilot.jsonl', 'data/manifests/pilot.splits.jsonl',
                 'artifacts/runs/s05-classification-final/model/model.joblib']
    # The read-only S07 snapshot records exact previous executable/data/model hashes.
    previous = json.loads((ROOT / 'docs/verification/s07/source_snapshot.json').read_text())
    # Inspect format explicitly rather than assuming all older audit formats alike.
    model_name = protected[-1]
    previous[model_name] = json.loads((ROOT / 'docs/verification/s07/acceptance.json').read_text())['model_sha256']
    for name in protected:
        assert name in previous, f'S07 snapshot lacks {name}'
        assert sha(ROOT / name) == previous[name], name
    changed = ['app/streamlit_app.py', 'src/scholarready/ui.py', 'src/scholarready/pipeline.py',
               'src/scholarready/ingestion.py', 'tests/test_ui.py', 'tests/test_ingestion.py',
               'scripts/verify_s08.py', 'scripts/audit_s08.py']
    write_json(evidence / 'source_snapshot.json', {name: sha(ROOT / name) for name in changed + protected})
    write_json(evidence / 'acceptance.json', dict(status='PASS', headless_cases=10,
        headless_artifact_hash_checks=len(audit['artifact_hashes']),
        actual_browser_cases=['complete', 'missing', 'unreadable', 'mismatch', 'other',
                              'conditional_unknown', 'multipage_pdf_plus_corrupt', 'reset'],
        native_downloads_validated=['application_json', 'findings_csv', 'pdf_error_json'],
        browser_cli_semantic_equivalence=True, final_test_consumed=False,
        protected_unchanged=protected, final_reset='explicit defaults; actual browser verified',
        note='Development regression evidence; no final-test or population performance claim. Headless run predates final reset/display-only fixes; final focused tests and native browser verify those fixes.'))
    print(f'PASS: 10 headless CLI/UI pairs; {len(audit["artifact_hashes"])} hashes; actual browser/download evidence; {len(protected)} protected hashes unchanged.')


if __name__ == '__main__':
    main()
