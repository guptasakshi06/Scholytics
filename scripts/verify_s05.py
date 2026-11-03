#!/usr/bin/env python3
"""Audit actual S05 partitions, training-only fit, saved predictions and model reload."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from scholarready.classification import LearnedClassifier, build_estimator
from scholarready.dataset import sha256
from scholarready.pipeline import write_json
from scholarready.schemas import SplitRecord, ApplicationResult
from scholarready.splitting import context, make_development_splits, validate_splits
from train_classifier import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=Path('artifacts/runs/s05-classification-final'))
    parser.add_argument('--snapshot', type=Path, default=Path('docs/verification/s05'))
    parser.add_argument('--ocr-run', type=Path, default=Path('artifacts/runs/s05-classification'))
    args = parser.parse_args()
    root = Path.cwd(); run = args.run
    manifest = root / 'data/manifests/pilot.jsonl'
    split_path = root / 'data/manifests/pilot.splits.jsonl'
    records, dataset, groups, bundle_hashes = context(manifest, root)
    splits = [SplitRecord.model_validate_json(line) for line in split_path.read_text().splitlines()]
    report = validate_splits(records, splits, groups, sha256(manifest))
    assert splits == make_development_splits(records, groups, sha256(manifest), dataset['dataset_version'], splits[0].seed)
    split_meta = json.loads(split_path.with_suffix('.metadata.json').read_text())
    assert split_meta['bundle_hashes'] == bundle_hashes and split_meta['split_hash'] == sha256(split_path)
    by_id = {s.sample_id: s for s in splits}
    features = {f['sample_id']: f for line in (run / 'ocr_features.jsonl').read_text().splitlines() if (f := json.loads(line))}
    assert set(features) == {r.sample_id for r in records}
    feature_meta = json.loads((run / 'ocr_features.metadata.json').read_text())
    assert feature_meta['features_sha256'] == sha256(run / 'ocr_features.jsonl')
    for path, expected in feature_meta['input_hashes'].items():
        assert sha256(root / path) == expected == dataset['artifact_hashes'][path]
    # Bind the reused cache to genuine shared-pipeline OCR results, not just a self hash.
    by_page = {}
    for batch in sorted((args.ocr_run / 'ocr_runs').iterdir()):
        result = ApplicationResult.model_validate_json((batch / 'result.json').read_text())
        inputs = json.loads((batch / 'inputs.json').read_text())['files']
        qualities = {q.page_id: q.model_dump(mode='json') for q in result.quality_findings}
        for entry, document in zip(inputs, result.documents):
            relative = str(Path(entry['input_path']).relative_to(root))
            assert document.source_sha256 == feature_meta['input_hashes'][relative]
            for page, ocr in zip(document.pages, document.ocr):
                by_page[relative, page.page_index] = dict(ocr=ocr.model_dump(mode='json'), quality=qualities[page.page_id])
                assert (batch / page.original_image_path).exists()
    for record in records:
        cached = features[record.sample_id]
        assert {k: cached[k] for k in ('ocr', 'quality')} == by_page[record.relative_path, record.page_index]
    classifier = LearnedClassifier.load(run / 'model')
    metadata = classifier.metadata
    assert metadata['manifest_sha256'] == sha256(manifest) and metadata['splits_sha256'] == sha256(split_path)
    assert metadata['features_sha256'] == sha256(run / 'ocr_features.jsonl')
    assert metadata['code_snapshot_sha256'] == sha256(run / 'code_snapshot.json')
    train = [r for r in records if by_id[r.sample_id].development_partition == 'train' and r.variant_id == 'clean']
    assert metadata['training_sample_ids'] == [r.sample_id for r in train]
    texts = [features[r.sample_id]['ocr']['text'] for r in train]
    assert metadata['training_text_sha256'] == hashlib.sha256(json.dumps(texts).encode()).hexdigest()
    replay = build_estimator(metadata['seed'])
    replay.fit(texts, [r.document_type for r in train])
    assert replay.named_steps['tfidf'].vocabulary_ == classifier.estimator.named_steps['tfidf'].vocabulary_
    np.testing.assert_allclose(replay.named_steps['logistic'].coef_, classifier.estimator.named_steps['logistic'].coef_, rtol=0, atol=1e-12)
    validation = [r for r in records if by_id[r.sample_id].development_partition == 'validation']
    saved = json.loads((run / 'evaluation.json').read_text())
    expected_rows = []
    for name, selected in [('validation_all_variants', validation), ('validation_clean', [r for r in validation if r.variant_id == 'clean'])]:
        metric, rows = compare(classifier, selected, features)
        assert metric == saved[name]
        if name == 'validation_all_variants':
            expected_rows += [dict(row, partition='validation') for row in rows]
    for variant in {r.variant_id for r in validation}:
        assert compare(classifier, [r for r in validation if r.variant_id == variant], features)[0] == saved['validation_by_variant'][variant]
    probe = [r for r in records if by_id[r.sample_id].development_partition == 'layout_probe' and r.variant_id == 'clean']
    if probe:
        untuned_meta = deepcopy(metadata)
        untuned_meta['thresholds'] = dict(minimum_probability=.4, minimum_margin=.1, minimum_vocabulary_coverage=.1)
        metric, rows = compare(LearnedClassifier(classifier.estimator, untuned_meta), probe, features)
        assert metric == saved['untuned_unseen_layout_probe']
        expected_rows = [dict(row, partition='layout_probe_untuned') for row in rows] + expected_rows
        assert {r.layout_id for r in train}.isdisjoint({r.layout_id for r in probe})
        assert {groups[r.sample_id] for r in train}.isdisjoint({groups[r.sample_id] for r in probe})
    assert expected_rows == json.loads((run / 'predictions.json').read_text())
    reloaded = LearnedClassifier.load(run / 'model')
    for r in records:
        text = features[r.sample_id]['ocr']['text']
        assert classifier.predict_text(text) == reloaded.predict_text(text)
    assert metadata['final_test_consumed'] is False
    args.snapshot.mkdir(parents=True, exist_ok=True)
    for name in ('eda.json', 'evaluation.json', 'predictions.json', 'run.json', 'split_check.json',
                 'ocr_features.metadata.json', 'code_snapshot.json', 'eda.png', 'confusion.png'):
        shutil.copyfile(run / name, args.snapshot / name)
    shutil.copyfile(run / 'model/metadata.json', args.snapshot / 'model_metadata.json')
    # Compact visible OCR and original qualities; full token evidence remains in generated runs.
    (args.snapshot / 'development_texts.jsonl').write_text('\n'.join(json.dumps(dict(sample_id=sid,
        text=f['ocr']['text'], status=f['ocr']['status'], reason=f['ocr']['reason'], quality=f['quality']), ensure_ascii=False)
        for sid, f in features.items()) + '\n')
    inventory = {str(p.relative_to(run)): sha256(p) for p in sorted(run.rglob('*')) if p.is_file()}
    write_json(args.snapshot / 'artifact_hashes.json', inventory)
    ocr_inventory = {str(p.relative_to(args.ocr_run)): sha256(p) for p in sorted(args.ocr_run.rglob('*')) if p.is_file()}
    write_json(args.snapshot / 'ocr_artifact_hashes.json', ocr_inventory)
    write_json(args.snapshot / 'acceptance.json', dict(report, training_clean_pages=len(train),
        training_only_fit_replayed=True, reloaded_predictions_identical=len(records),
        validation_metrics_recomputed=True, prediction_rows_verified=len(expected_rows),
        input_hashes_verified=len(feature_meta['input_hashes']), artifact_hashes=len(inventory),
        cache_pages_bound_to_actual_ocr=len(records), ocr_artifact_hashes=len(ocr_inventory)))
    print(json.dumps(json.loads((args.snapshot / 'acceptance.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
