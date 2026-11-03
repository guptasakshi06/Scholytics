#!/usr/bin/env python3
"""S05 local development OCR, EDA, train-only TF-IDF/LR and paired comparison."""
import argparse
import hashlib
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shlex
import sys
from time import perf_counter

import joblib
import numpy as np

from scholarready.classification import LearnedClassifier, build_estimator, classify, feature_text
from scholarready.config import load_config
from scholarready.dataset import LABELS, resolve_inside, sha256
from scholarready.evaluation.classification_metrics import classification_metrics
from scholarready.ocr import OCRSettings
from scholarready.pipeline import analyze, code_snapshot, write_json
from scholarready.preprocessing import load_preprocessing, PreprocessingConfig
from scholarready.schemas import ApplicantProfile, OCRResult, SplitRecord
from scholarready.splitting import context, validate_splits

DEFAULT_THRESHOLDS = dict(minimum_probability=.4, minimum_margin=.1, minimum_vocabulary_coverage=.1)


def summary(values):
    return dict(zip(('min', 'q25', 'median', 'q75', 'max'), map(float, np.percentile(values, [0, 25, 50, 75, 100])))) if values else None


def prepare_features(records, root, output, inference, cache=None):
    paths = sorted({r.relative_path for r in records})
    hashes = {p: sha256(resolve_inside(root, p)) for p in paths}
    snapshot = code_snapshot()
    ocr_code = {k: v for k, v in snapshot.items() if k in {'ocr.py', 'ingestion.py', 'preprocessing.py', 'quality.py', 'geometry.py'}}
    signature = dict(inference_settings=inference, input_hashes=hashes, ocr_code=ocr_code)
    if cache:
        meta = json.loads(cache.with_suffix('.metadata.json').read_text())
        if any(meta[k] != v for k, v in signature.items()) or meta['features_sha256'] != sha256(cache):
            raise ValueError('Stale/tampered OCR feature cache')
        features = [json.loads(line) for line in cache.read_text().splitlines()]
    else:
        by_page = {}
        for offset in range(0, len(paths), 10):
            selected = paths[offset:offset + 10]
            run = output / 'ocr_runs' / f'batch-{offset // 10:03d}'
            result = analyze([resolve_inside(root, p) for p in selected], output=run,
                config=load_config(root / 'configs/scholarship_demo.json'),
                applicant=ApplicantProfile(applicant_reference='fictional-development'),
                branch=inference['branch'], settings=OCRSettings(**inference['ocr']),
                preprocessing=PreprocessingConfig.model_validate(inference['preprocessing']))
            qualities = {q.page_id: q.model_dump(mode='json') for q in result.quality_findings}
            for path, document in zip(selected, result.documents):
                for page, ocr in zip(document.pages, document.ocr):
                    by_page[path, page.page_index] = dict(ocr=ocr.model_dump(mode='json'), quality=qualities.get(page.page_id))
                if not document.pages:
                    for r in records:
                        if r.relative_path == path:
                            by_page[path, r.page_index] = dict(ocr=OCRResult(page_id='failed-input', branch_id=inference['branch'],
                                text='', tokens=[], engine='Tesseract', engine_version='not invoked', language='eng',
                                settings=inference['ocr'], runtime_seconds=0, status='error',
                                reason='; '.join(document.errors)).model_dump(mode='json'), quality=None)
            print(f'OCR {min(offset + 10, len(paths))}/{len(paths)} input files', flush=True)
        features = [dict(sample_id=r.sample_id, **by_page[r.relative_path, r.page_index]) for r in records]
    if len(features) != len(records) or {f['sample_id'] for f in features} != {r.sample_id for r in records}:
        raise ValueError('OCR cache must cover every sample exactly once')
    for f in features:
        ocr = OCRResult.model_validate(f['ocr'])
        if ocr.settings != inference['ocr'] or ocr.branch_id != inference['branch']:
            raise ValueError('OCR feature settings mismatch')
    target = output / 'ocr_features.jsonl'
    target.write_text('\n'.join(json.dumps(f, ensure_ascii=False) for f in features) + '\n')
    write_json(target.with_suffix('.metadata.json'), dict(signature, features_sha256=sha256(target),
        engine_versions=sorted({f['ocr']['engine_version'] for f in features}),
        cache_reused=cache is not None))
    return {f['sample_id']: f for f in features}


def eda(records, splits, groups, features):
    clean = [r for r in records if r.variant_id == 'clean']
    return dict(samples=len(records), clean_pages=len(clean), augmented_pages=len(records) - len(clean),
        independent_source_documents=len({r.source_document_id for r in records}),
        applicants=len({r.applicant_id for r in records}), connected_groups=len(set(groups.values())),
        missing_labels=sum(not r.document_type for r in records),
        source_documents_by_class={label: len({r.source_document_id for r in clean if r.document_type == label}) for label in LABELS},
        clean_pages_by_class=dict(Counter(r.document_type for r in clean)),
        all_pages_by_class=dict(Counter(r.document_type for r in records)),
        clean_pages_by_layout=dict(Counter(r.layout_id for r in clean)),
        pages_by_degradation=dict(Counter(r.degradation.type for r in records)),
        partitions={p: dict(samples=len(items := [r for r in records if splits[r.sample_id].development_partition == p]),
            clean_pages=sum(r.variant_id == 'clean' for r in items), sources=len({r.source_document_id for r in items}),
            groups=len({groups[r.sample_id] for r in items}), applicants=sorted({r.applicant_id for r in items}),
            layouts=sorted({r.layout_id for r in items})) for p in ('train', 'validation', 'layout_probe')},
        distributions_by_variant={variant: dict(
            samples=len(items := [features[r.sample_id] for r in records if r.variant_id == variant]),
            ocr_text_characters=summary([len(f['ocr']['text']) for f in items]),
            ocr_body_characters=summary([len(feature_text(f['ocr']['text'])) for f in items]),
            statuses=dict(Counter(f['ocr']['status'] for f in items)),
            quality={key: summary([f['quality'][key] for f in items if f['quality']])
                     for key in ('brightness', 'contrast', 'blur_measure', 'width', 'height')})
            for variant in sorted({r.variant_id for r in records})})


def predictions(classifier, items, features):
    return [classifier.classify([OCRResult.model_validate(features[r.sample_id]['ocr'])], []) for r in items]


def compare(classifier, items, features):
    learned = predictions(classifier, items, features)
    keyword = [classify([OCRResult.model_validate(features[r.sample_id]['ocr'])], []) for r in items]
    truth = [r.document_type for r in items]
    return dict(learned=classification_metrics(truth, learned), keyword=classification_metrics(truth, keyword)), [dict(
        sample_id=r.sample_id, target=r.document_type, learned=p.model_dump(mode='json'), keyword=k.model_dump(mode='json'))
        for r, p, k in zip(items, learned, keyword)]


def plot(output, eda_report, evaluation):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = [label.replace('_certificate', '').replace('_', ' ') for label in LABELS]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    axes[0, 0].bar(labels, list(eda_report['source_documents_by_class'].values()))
    axes[0, 0].set_title('Independent source documents per class (30 total)')
    axes[0, 0].tick_params(axis='x', rotation=20)
    axes[0, 1].bar(eda_report['clean_pages_by_layout'].keys(), eda_report['clean_pages_by_layout'].values())
    axes[0, 1].set_title('Clean pages per layout (31 pages)')
    distributions = eda_report['distributions_by_variant']
    variants = list(distributions)
    for ax, key, title in ((axes[1, 0], 'ocr_text_characters', 'OCR text length by variant (median / range)'),
                           (axes[1, 1], 'contrast', 'Original grayscale contrast (median / range)')):
        data = [distributions[v][key] if key == 'ocr_text_characters' else distributions[v]['quality'][key] for v in variants]
        ax.errorbar(range(len(variants)), [d['median'] for d in data],
                    yerr=[[d['median'] - d['min'] for d in data], [d['max'] - d['median'] for d in data]], fmt='o')
        ax.set_xticks(range(len(variants)), [v.replace('_', '\n') for v in variants], fontsize=8)
        ax.set_title(title)
    fig.suptitle('S05 fictional development EDA — 156 samples, 125 augmented; 4 connected groups')
    fig.savefig(output / 'eda.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    for ax, method in zip(axes, ('keyword', 'learned')):
        metric = evaluation['validation_all_variants'][method]
        ax.imshow(metric['confusion_matrix'], cmap='Blues', vmin=0)
        ax.set_xticks(range(7), [*labels, 'unresolved'], rotation=40, ha='right')
        ax.set_yticks(range(6), labels)
        for y, row in enumerate(metric['confusion_matrix']):
            for x, count in enumerate(row):
                ax.text(x, y, str(count), ha='center', va='center')
        ax.set_title(f'{method}: macro-F1 {metric["macro_f1"]:.3f}, n={metric["samples"]}')
        ax.set_xlabel('Predicted'); ax.set_ylabel('Reference class (provisional)')
    fig.suptitle('Same development validation pages; unresolved retained as false negatives')
    fig.savefig(output / 'confusion.png', dpi=150); plt.close(fig)


def run(args):
    started = perf_counter()
    root = args.root.resolve()
    records, dataset_meta, groups, bundle_hashes = context(args.manifest, root)
    for path in {r.relative_path for r in records}:
        if sha256(resolve_inside(root, path)) != dataset_meta['artifact_hashes'][path]:
            raise ValueError(f'Dataset input hash mismatch: {path}')
    splits = [SplitRecord.model_validate_json(line) for line in args.splits.read_text().splitlines()]
    split_meta = json.loads(args.splits.with_suffix('.metadata.json').read_text())
    if split_meta['split_hash'] != sha256(args.splits) or split_meta['bundle_hashes'] != bundle_hashes:
        raise ValueError('Stale split/bundle hash')
    overlap = validate_splits(records, splits, groups, sha256(args.manifest))
    if any(s.manifest_version != dataset_meta['dataset_version'] for s in splits):
        raise ValueError('Split dataset version mismatch')
    inference = dict(branch=args.branch, ocr=asdict(OCRSettings()), pdf_dpi=300,
                     preprocessing=load_preprocessing(args.preprocessing).model_dump(mode='json'))
    by_id = {s.sample_id: s for s in splits}
    train = [r for r in records if by_id[r.sample_id].development_partition == 'train' and r.variant_id == 'clean']
    validation = [r for r in records if by_id[r.sample_id].development_partition == 'validation']
    if {r.document_type for r in train} != set(LABELS) or not validation:
        raise ValueError('Need all six training labels and nonempty validation')
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / 'split_check.json', overlap)
    write_json(args.output / 'code_snapshot.json', code_snapshot())
    features = prepare_features(records, root, args.output, inference, args.features)
    train_errors = [r.sample_id for r in train if features[r.sample_id]['ocr']['status'] != 'ok' or not feature_text(features[r.sample_id]['ocr']['text'])]
    if train_errors:
        raise ValueError(f'Unusable training OCR; no silent exclusions: {train_errors}')
    estimator = build_estimator(args.seed)
    estimator.fit([features[r.sample_id]['ocr']['text'] for r in train], [r.document_type for r in train])
    metadata = dict(model_version='tfidf-lr-s05-1.0', classes=list(estimator.classes_),
        thresholds=DEFAULT_THRESHOLDS.copy(), dependency_versions={name: version(name) for name in ('scikit-learn', 'numpy', 'scipy', 'joblib')},
        inference_settings=inference, seed=args.seed, dataset_version=dataset_meta['dataset_version'],
        manifest_sha256=sha256(args.manifest), splits_sha256=sha256(args.splits),
        feature_policy='NFC/casefold/whitespace; remove common synthetic watermark; OCR body words/unigrams+bigrams only. No paths, IDs, labels, references, layout or quality features.',
        estimator_policy='TF-IDF min_df=1, sublinear_tf; LR C=4 max_iter=1000. Fixed before outcomes; no hyperparameter search with only two training groups.',
        training_sample_ids=[r.sample_id for r in train], training_source_documents=sorted({r.source_document_id for r in train}),
        training_text_sha256=hashlib.sha256(json.dumps([features[r.sample_id]['ocr']['text'] for r in train]).encode()).hexdigest(),
        training_labels_sha256=hashlib.sha256(json.dumps([(r.sample_id, r.document_type) for r in train]).encode()).hexdigest(),
        validation_sample_ids=[r.sample_id for r in validation],
        features_sha256=sha256(args.output / 'ocr_features.jsonl'), python_version=platform.python_version(),
        tesseract_versions=sorted({f['ocr']['engine_version'] for f in features.values()}),
        preprocessing_dependency_versions={n: version(n) for n in ('Pillow', 'pypdfium2', 'pytesseract', 'opencv-python-headless')},
        code_snapshot_sha256=sha256(args.output / 'code_snapshot.json'),
        ocr_cache_reused=args.features is not None,
        exact_command=shlex.join([sys.executable, *sys.argv]), final_test_consumed=False)
    classifier = LearnedClassifier(estimator, metadata)
    # Probe precedes tuning and uses predeclared thresholds. No later model/threshold changes use probe outcomes.
    probe = [r for r in records if by_id[r.sample_id].development_partition == 'layout_probe' and r.variant_id == 'clean']
    evaluation, rows = {}, []
    if probe:
        evaluation['untuned_unseen_layout_probe'], probe_rows = compare(classifier, probe, features)
        rows += [dict(p, partition='layout_probe_untuned') for p in probe_rows]
    trials = []
    for probability in (.3, .4, .5, .6):
        for margin in (.05, .1, .2):
            metadata['thresholds'] = dict(minimum_probability=probability, minimum_margin=margin, minimum_vocabulary_coverage=.1)
            pred = predictions(classifier, validation, features)
            metric = classification_metrics([r.document_type for r in validation], pred)
            wrong = sum(p.decision == 'classified' and p.document_type != r.document_type for r, p in zip(validation, pred))
            trials.append(dict(thresholds=metadata['thresholds'].copy(), macro_f1=metric['macro_f1'], wrong_accepted=wrong,
                               unresolved=metric['unresolved']))
    selected = max(trials, key=lambda t: (t['macro_f1'], -t['wrong_accepted'], t['thresholds']['minimum_probability'], t['thresholds']['minimum_margin']))
    metadata['thresholds'] = selected['thresholds']
    metadata['threshold_selection'] = 'Validation all variants only; maximize six-class macro-F1, then fewer wrong acceptances, then stricter probability/margin. Coverage=.1 and dual-title guard fixed a priori. Not calibrated.'
    for name, items in [('validation_all_variants', validation), ('validation_clean', [r for r in validation if r.variant_id == 'clean'])]:
        evaluation[name], compared = compare(classifier, items, features)
        if name == 'validation_all_variants':
            rows += [dict(p, partition='validation') for p in compared]
    evaluation['validation_by_variant'] = {v: compare(classifier, [r for r in validation if r.variant_id == v], features)[0]
                                            for v in sorted({r.variant_id for r in validation})}
    evaluation['threshold_trials'] = trials
    evaluation['probe_policy'] = 'Only layout_a clean pages fit model; layout_b-only component probed with fixed .4/.1 thresholds before validation tuning. Validation contains both layouts. Tiny synthetic diagnostic, not independent generalization or final test.'
    model_dir = args.output / 'model'; model_dir.mkdir()
    joblib.dump(estimator, model_dir / 'model.joblib')
    metadata['model_sha256'] = sha256(model_dir / 'model.joblib')
    metadata['validation_results'] = evaluation['validation_all_variants']
    write_json(model_dir / 'metadata.json', metadata)
    reloaded = LearnedClassifier.load(model_dir)
    assert [p.model_dump() for p in predictions(classifier, validation, features)] == [p.model_dump() for p in predictions(reloaded, validation, features)]
    eda_report = eda(records, by_id, groups, features)
    write_json(args.output / 'eda.json', eda_report)
    write_json(args.output / 'evaluation.json', evaluation)
    write_json(args.output / 'predictions.json', rows)
    plot(args.output, eda_report, evaluation)
    write_json(args.output / 'run.json', dict(metadata, reload_predictions_identical=True,
        runtime_seconds=perf_counter() - started, timing_scope='Cache validation or real OCR, EDA/training/evaluation/figures/reload; cache_reused records mode. No controlled timing benchmark.'))
    print(json.dumps(dict(output=str(args.output), model=str(model_dir), validation=evaluation['validation_all_variants'], thresholds=selected), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--splits', type=Path, required=True)
    parser.add_argument('--branch', choices=['A', 'B', 'C'], required=True)
    parser.add_argument('--preprocessing', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--features', type=Path, help='reuse a hash/settings/code-checked OCR cache')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Classifier development error: {exc}\n')


if __name__ == '__main__':
    main()
