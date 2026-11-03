#!/usr/bin/env python3
"""Independently recompute S04 paired metrics and validate saved artifact contracts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from scholarready.evaluation.ocr_metrics import aggregate, score
from scholarready.pipeline import write_json
from scholarready.schemas import ApplicationResult, RunMetadata


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(run):
    def read(path):
        return json.loads((run / path).read_text())
    hashes = read('artifact_hashes.json')
    for name, expected in hashes.items():
        assert sha(run / name) == expected, name
    summary = read('comparison.json')
    matrix = read('matrix.json')
    assert summary['comparison_id'] == matrix['comparison_id']
    assert summary['manifest_sha256'] == sha(Path('data/manifests/pilot.jsonl'))
    assert len(matrix['variants']) == len(summary['variants']) == 12
    names = [v['name'] for v in summary['variants']]
    assert names == [v['name'] for v in matrix['variants']]
    originals, qualities, inputs = {}, {}, {}
    seen_pages, stage_count = set(), 0
    for variant, spec in zip(summary['variants'], matrix['variants']):
        name = variant['name']
        result = ApplicationResult.model_validate_json((run / name / 'result.json').read_text())
        meta = RunMetadata.model_validate_json((run / name / 'metadata.json').read_text())
        report = read(f'{name}/ocr_evaluation.json')
        settings = read(f'{name}/settings.json')
        assert settings['ocr'] == matrix['ocr'] and settings['branch'] == spec['branch']
        assert read(f'{name}/preprocessing.json') == spec['config']
        assert report['run_id'] == result.run_id == meta.run_id
        assert meta.tesseract_version == read('A/metadata.json')['tesseract_version']
        assert set(r['sample_id'] for r in report['samples']) == set(summary['selected_sample_ids'])
        assert report['scored_pages'] == len(report['samples']) == variant['scored_pages']
        for path in meta.output_paths:
            assert (run / name / path).exists(), path
        for quality in result.quality_findings:
            raw = quality.model_dump(mode='json')
            if quality.page_id in qualities:
                assert raw == qualities[quality.page_id]
            qualities[quality.page_id] = raw
        for doc in result.documents:
            for page, proc, ocr in zip(doc.pages, doc.processing, doc.ocr):
                seen_pages.add(page.page_id)
                key = page.page_id
                original_hash = sha(run / name / page.original_image_path)
                assert key not in originals or original_hash == originals[key]
                originals[key] = original_hash
                assert proc.transform.source_space == page.coordinate_space
                assert np.isfinite(np.linalg.inv(np.asarray(proc.transform.matrix))).all()
                for stage in proc.stages:
                    stage_count += 1
                    with Image.open(run / name / stage.image_path) as image:
                        assert image.size == (proc.width, proc.height)
                assert ocr.branch_id == spec['branch']
                assert ocr.settings == matrix['ocr'] and ocr.engine_version == meta.tesseract_version
                for token in ocr.tokens:
                    assert token.coordinate_space == proc.transform.target_space
                    x, y, w, h = token.box
                    assert 0 <= x < x + w <= proc.width and 0 <= y < y + h <= proc.height
                for field in doc.fields:
                    if field.page_id == page.page_id:
                        assert field.coordinate_space == proc.transform.target_space
        for row in report['samples']:
            assert row['metrics'] == score(row['reference_text'], row['prediction_text'])
            doc = next(d for d in result.documents if d.document_id == row['document_id'])
            ocr = next((o for o in doc.ocr if o.page_id == row['page_id']), None)
            assert (ocr.text if ocr else '') == row['prediction_text']
            signature = (row['input_sha256'], row['reference_sha256'], row['reference_text'])
            assert row['sample_id'] not in inputs or inputs[row['sample_id']] == signature
            inputs[row['sample_id']] = signature
        metrics = aggregate([row['metrics'] for row in report['samples']])
        assert report['aggregate'] == variant['aggregate'] == metrics
        assert report['failure_count'] == variant['failure_count'] == sum(row['ocr_status'] == 'error' for row in report['samples'])
        for key in ('preprocessing_seconds', 'ocr_seconds'):
            rowkey = 'ocr_seconds' if key == 'ocr_seconds' else key
            assert abs(report[key] - sum(row[rowkey] for row in report['samples'])) < 1e-7
    return dict(status='passed', comparison_id=summary['comparison_id'], variants=len(names),
        paired_scored_pages=len(inputs), processed_page_ids=len(seen_pages), stage_instances=stage_count,
        verified_artifact_hashes=len(hashes), manifest_sha256=summary['manifest_sha256'],
        final_test_consumed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=Path('artifacts/runs/s04-comparison'))
    parser.add_argument('--evidence', type=Path, default=Path('docs/verification/s04'))
    parser.add_argument('--snapshot', action='store_true', help='copy compact JSON evidence, not bulk media')
    args = parser.parse_args()
    acceptance = verify(args.run)
    args.evidence.mkdir(parents=True, exist_ok=True)
    write_json(args.evidence / 'acceptance.json', acceptance)
    if args.snapshot:
        for source in args.run.rglob('*.json'):
            target = args.evidence / 'runs' / source.relative_to(args.run)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    print(json.dumps(acceptance, indent=2))


if __name__ == '__main__':
    main()
