#!/usr/bin/env python3
"""Verify saved S03 acceptance runs, preserving IDs/hashes in a compact report."""
import argparse
import hashlib
import json
from pathlib import Path

from scholarready.evaluation.ocr_metrics import aggregate, score
from scholarready.pipeline import write_json
from scholarready.schemas import ApplicationResult, RunMetadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=Path('artifacts/runs'))
    parser.add_argument('--output', type=Path, default=Path('docs/verification/s03/acceptance.json'))
    args = parser.parse_args()
    # Independent literal scenario expectations; never used by inference.
    expected = {'s03-complete': ('ready', 100.), 's03-missing': ('incomplete', 80.),
        's03-unreadable': ('needs_review', 80.), 's03-conditional': ('ready', 100.),
        's03-mismatch': ('needs_review', 100.), 's03-demo-final': ('ready', 100.),
        's03-corrupt': ('needs_review', None), 's03-timeout': ('needs_review', None)}
    checked = {}
    for name, outcome in expected.items():
        root = args.runs / name
        result = ApplicationResult.model_validate_json((root / 'result.json').read_text())
        meta = RunMetadata.model_validate_json((root / 'metadata.json').read_text())
        assert (result.overall_state, result.completeness) == outcome, name
        assert result.run_id == meta.run_id
        assert all((root / path).exists() for path in meta.output_paths)
        for doc in result.documents:
            page_by_id = {p.page_id: p for p in doc.pages}
            tokens = {t.token_id: t for o in doc.ocr for t in o.tokens}
            for ocr in doc.ocr:
                page = page_by_id[ocr.page_id]
                for token in ocr.tokens:
                    x, y, width, height = token.box
                    assert x + width <= page.width and y + height <= page.height
            for field in doc.fields:
                if field.validation_state == 'valid':
                    assert set(field.token_references) <= tokens.keys()
                    assert all(tokens[t].page_id == field.page_id for t in field.token_references)
        states = {r.requirement_id: r.state for r in result.requirements}
        if name == 's03-missing':
            assert states['income'] == 'missing'
        if name == 's03-unreadable':
            assert states['income'] == 'unreadable' and 'missing' not in states.values()
            assert result.documents[1].prediction.document_type is None
        if name == 's03-conditional':
            assert states['category'] == 'not_applicable'
        if name in {'s03-corrupt', 's03-timeout'}:
            assert result.documents[0].errors and meta.exceptions
        checked[name] = dict(run_id=result.run_id, overall_state=result.overall_state,
            completeness=result.completeness, requirement_states=states,
            result_sha256=hashlib.sha256((root / 'result.json').read_bytes()).hexdigest(),
            exact_command=meta.exact_command, runtime_seconds=meta.runtime_seconds)
    root = args.runs / 's03-multipage'
    multipage = ApplicationResult.model_validate_json((root / 'result.json').read_text()).documents[0]
    assert [p.page_index for p in multipage.pages] == [1, 2]
    assert len(multipage.ocr) == 2 and all(o.status == 'ok' for o in multipage.ocr)
    assert all(p.width == 2500 and p.height == 3334 and p.rasterization_dpi == 300 for p in multipage.pages)
    assert not multipage.errors
    root = args.runs / 's03-ocr-baseline-expanded'
    evaluation = json.loads((root / 'ocr_evaluation.json').read_text())
    assert len(evaluation['samples']) == 14 and evaluation['failure_count'] == 0
    assert len({s['sample_id'] for s in evaluation['samples']}) == 14
    assert all(s['run_id'] == evaluation['run_id'] for s in evaluation['samples'])
    for sample in evaluation['samples']:
        assert score(sample['reference_text'], sample['prediction_text']) == sample['metrics']
    assert aggregate([s['metrics'] for s in evaluation['samples']]) == evaluation['aggregate']
    fixture_root = Path('tests/fixtures/pilot')
    fixtures = json.loads((fixture_root / 'inventory.json').read_text())['files']
    assert len(fixtures) == 9
    for entry in fixtures:
        assert hashlib.sha256((fixture_root / entry['file']).read_bytes()).hexdigest() == entry['sha256']
    report = dict(status='passed', scenarios=checked,
        multipage=dict(document_id=multipage.document_id, page_count=2, dimensions=[2500, 3334], dpi=300),
        ocr_evaluation=dict(run_id=evaluation['run_id'], **evaluation['aggregate']),
        fixture_hashes_checked=len(fixtures), final_test_consumed=False)
    write_json(args.output, report)
    print('PASS: eight scenario/failure runs, real two-page PDF provenance, OCR metrics recomputed, nine fixture hashes; final test untouched.')


if __name__ == '__main__':
    main()
