#!/usr/bin/env python3
"""Audit S06 hashes, inference replay, exact denominators and real evidence overlays."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

from PIL import Image
from scholarready.dataset import sha256
from scholarready.evidence import draw_evidence
from scholarready.extraction import extract
from scholarready.pipeline import write_json
from scholarready.schemas import ApplicationResult, ExtractedField, OCRResult, PageImage
from evaluate_fields import audit_fields


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, default=Path('artifacts/runs/s06-fields-complete'))
    p.add_argument('--uploads', type=Path, default=Path('artifacts/runs/s06-uploads-complete'))
    p.add_argument('--demo', type=Path, default=Path('artifacts/runs/s06-learned-demo-final'))
    p.add_argument('--snapshot', type=Path, default=Path('docs/verification/s06'))
    args = p.parse_args(); root = Path.cwd(); args.snapshot.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((args.run / 'run.json').read_text())
    assert not metadata['final_test_consumed'] and not metadata['layout_probe_evaluated']
    for name in ('predictions', 'metrics', 'code_snapshot'):
        assert sha256(args.run / (name + '.json')) == metadata[name + '_sha256']
    hashes = {**metadata['input_hashes'], **metadata['annotation_hashes'], **metadata['original_ocr_result_hashes'],
        'data/manifests/pilot.jsonl': metadata['manifest_sha256'], 'data/manifests/pilot.splits.jsonl': metadata['splits_sha256'],
        'artifacts/runs/s05-classification-final/model/model.joblib': metadata['model_sha256']}
    for path, expected in hashes.items():
        assert sha256(root / path) == expected, path
    rows = json.loads((args.run / 'predictions.json').read_text())
    features = {r['sample_id']: r for line in Path('artifacts/runs/s05-classification/ocr_features.jsonl').read_text().splitlines() if (r := json.loads(line))}
    replayed = audit = 0
    # No references opened in this replay phase.
    for row in rows:
        page, ocr = PageImage.model_validate(row['page']), OCRResult.model_validate(features[row['sample_id']]['ocr'])
        for route in ('true_type', 'keyword_type', 'learned_type'):
            label = row['document_type'] if route == 'true_type' else row[route.split('_')[0]]['document_type']
            values = extract(label, [page], [ocr])
            assert [f.model_dump(mode='json') for f in values] == row['routes'][route]
            audit += audit_fields(values, ocr); replayed += 1
    manifest = {r['sample_id']: r for line in Path('data/manifests/pilot.jsonl').read_text().splitlines() if (r := json.loads(line))}
    failures = []; direct = {route: Counter() for route in ('true_type', 'keyword_type', 'learned_type')}
    for row in rows:
        if row['partition'] != 'validation':
            continue
        references = json.loads(Path(manifest[row['sample_id']]['annotation_path']).read_text())['fields']
        for route in direct:
            fields = {f['field_name']: f for f in row['routes'][route]}
            for name, reference in references.items():
                if reference['state'] != 'present':
                    continue
                direct[route]['support'] += 1
                pred = fields.get(name)
                correct = pred is not None and pred['validation_state'] == 'valid' and all(
                    pred[key] == reference[key] for key in ('normalized_value', 'unit', 'person_role'))
                direct[route]['correct'] += int(correct)
                if not correct and route == 'true_type':
                    failures.append(dict(sample_id=row['sample_id'], field=name, reference=reference, prediction=pred))
    metrics = json.loads((args.run / 'metrics.json').read_text())
    for route, counts in direct.items():
        score = metrics['validation_all'][route]['overall']
        assert counts['support'] == score['present_support'] == 180
        assert counts['correct'] == score['exact_value_unit_role'] == 169
        assert score['normalized_exact_match'] == counts['correct'] / counts['support']
    assert len(failures) == 11
    demo = ApplicationResult.model_validate_json((args.demo / 'result.json').read_text())
    assert demo.overall_state == 'ready' and demo.completeness == 100
    fresh_a = ApplicationResult.model_validate_json((args.uploads / 'run/result.json').read_text())
    fresh_c = ApplicationResult.model_validate_json((args.uploads / 'run-C/result.json').read_text())
    fresh_checks = 0
    for result in (demo, fresh_a, fresh_c):
        for doc in result.documents:
            for ocr in doc.ocr:
                values = [f for f in doc.fields if f.page_id in {ocr.page_id, None}]
                fresh_checks += audit_fields(values, ocr)
    assert fresh_a.overall_state != 'ready'
    # Highlight a real confidently wrong OCR value, not just null/invalid examples.
    bad_row = next(r for r in rows if r['sample_id'] == 'src-019-p01-compression')
    page = PageImage.model_validate(bad_row['page'])
    for result_path in metadata['original_ocr_result_hashes']:
        result = ApplicationResult.model_validate_json(Path(result_path).read_text())
        if any(page.page_id == p.page_id for d in result.documents for p in d.pages):
            with Image.open(Path(result_path).parent / page.original_image_path) as image:
                figure = draw_evidence(image, [ExtractedField.model_validate(f) for f in bad_row['routes']['true_type']],
                    page_id=page.page_id, coordinate_space=page.coordinate_space)
                figure.save(args.snapshot / 'wrong_percentage_evidence.png')
            break
    else:
        raise AssertionError('Missing original OCR image')
    for name in ('metrics.json', 'predictions.json', 'run.json', 'code_snapshot.json'):
        shutil.copyfile(args.run / name, args.snapshot / name)
    for name in ('result.json', 'metadata.json', 'classifier.json'):
        shutil.copyfile(args.demo / name, args.snapshot / ('demo_' + name))
    write_json(args.snapshot / 'failures.json', failures)
    source_paths = [*Path('src').rglob('*.py'), *Path('scripts').glob('*.py'), *Path('tests').glob('*.py'),
                    *Path('configs').glob('*.json'), Path('requirements.lock.txt'), Path('pyproject.toml')]
    write_json(args.snapshot / 'source_snapshot.json', {str(p): sha256(p) for p in sorted(source_paths)})
    write_json(args.snapshot / 'acceptance_audit.json', dict(hash_checks=len(hashes), page_route_replays=replayed,
        valid_evidence_checks=audit, fresh_valid_evidence_checks=fresh_checks, per_route_direct_counts={k:dict(v) for k,v in direct.items()},
        validation_failures=len(failures), clean_present_correct=36, clean_present_support=36,
        demo_state=demo.overall_state, demo_completeness=demo.completeness, final_test_consumed=False,
        layout_probe_evaluated=False, manifest_split_model_unchanged=True))
    print(json.dumps(json.loads((args.snapshot / 'acceptance_audit.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
