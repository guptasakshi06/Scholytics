#!/usr/bin/env python3
"""S06 development-only true-type versus keyword/learned routed field extraction.

Reuse hash-bound real S05 OCR, including original PageImage geometry/provenance.
Reference field annotations are opened only after all inference has been saved.
No layout-probe evaluation, training, model tuning or final-test data consumption.
"""
import argparse
from collections import Counter
from importlib.metadata import version
import platform
import json
from pathlib import Path
import shlex
import sys
from time import perf_counter

from scholarready.classification import LearnedClassifier, classify
from scholarready.dataset import sha256, resolve_inside, PageAnnotation
from scholarready.evaluation.field_metrics import field_metrics
from scholarready.extraction import extract, normalize, VERSION, NORMALIZATION_VERSION
from scholarready.pipeline import code_snapshot, write_json
from scholarready.schemas import ApplicationResult, SplitRecord
from scholarready.splitting import context, validate_splits


def audit_fields(fields, ocr):
    tokens = {t.token_id: t for t in ocr.tokens}
    count = 0
    for field in fields:
        for evidence in [field] + field.candidates:
            if evidence.page_id is None:
                continue
            assert evidence.page_id == ocr.page_id
            assert evidence.boxes == [tokens[t].box for t in evidence.token_references]
            assert {tokens[t].coordinate_space for t in evidence.token_references} == {evidence.coordinate_space}
            if evidence.validation_state == 'valid':
                assert normalize(field.field_name, evidence.raw_text) == evidence.normalized_value
                assert evidence.raw_text in ' '.join(tokens[t].text for t in evidence.token_references)
                assert field.normalization_rule == f'{NORMALIZATION_VERSION}:{field.field_name}'
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ocr-run', type=Path, default=Path('artifacts/runs/s05-classification'))
    parser.add_argument('--model', type=Path, default=Path('artifacts/runs/s05-classification-final/model'))
    args = parser.parse_args(); started = perf_counter(); root = Path.cwd()
    manifest = root / 'data/manifests/pilot.jsonl'; split_path = root / 'data/manifests/pilot.splits.jsonl'
    records, metadata, groups, bundles = context(manifest, root)
    splits = [SplitRecord.model_validate_json(s) for s in split_path.read_text().splitlines()]
    if any(r.development_role != 'development_only' for r in records) or any(s.split != 'development_only' for s in splits):
        raise ValueError('S06 only accepts development_only records; protected roles are forbidden')
    split_check = validate_splits(records, splits, groups, sha256(manifest))
    partitions = {s.sample_id: s.development_partition for s in splits}
    selected = [r for r in records if partitions[r.sample_id] in {'train', 'validation'}]
    args.output.mkdir(parents=True, exist_ok=False)
    model = LearnedClassifier.load(args.model)
    feature_meta = json.loads((args.ocr_run / 'ocr_features.metadata.json').read_text())
    if sha256(args.ocr_run / 'ocr_features.jsonl') != feature_meta['features_sha256']:
        raise ValueError('Feature cache hash mismatch')
    cached = {f['sample_id']: f for line in (args.ocr_run / 'ocr_features.jsonl').read_text().splitlines() if (f := json.loads(line))}
    by_page = {}; input_hashes = {}; source_results = {}
    for batch in sorted((args.ocr_run / 'ocr_runs').iterdir()):
        result_path = batch / 'result.json'
        result = ApplicationResult.model_validate_json(result_path.read_text())
        source_results[str(result_path)] = sha256(result_path)
        inputs = json.loads((batch / 'inputs.json').read_text())['files']
        for entry, doc in zip(inputs, result.documents):
            relative = str(Path(entry['input_path']).relative_to(root))
            if relative not in {r.relative_path for r in selected}:
                continue
            input_hashes[relative] = sha256(root / relative)
            assert input_hashes[relative] == doc.source_sha256 == feature_meta['input_hashes'][relative] == metadata['artifact_hashes'][relative]
            for page, ocr in zip(doc.pages, doc.ocr):
                by_page[relative, page.page_index] = (page, ocr)
    predictions = []; evidence_checked = 0
    for r in selected:
        page, ocr = by_page[r.relative_path, r.page_index]
        assert ocr.model_dump(mode='json') == cached[r.sample_id]['ocr']
        true = extract(r.document_type, [page], [ocr])
        keyword = classify([ocr], [])
        learned = model.classify([ocr], [])
        routes = {'true_type': true, 'keyword_type': extract(keyword.document_type, [page], [ocr]),
                  'learned_type': extract(learned.document_type, [page], [ocr])}
        for fields in routes.values():
            evidence_checked += audit_fields(fields, ocr)
        predictions.append(dict(sample_id=r.sample_id, document_type=r.document_type, partition=partitions[r.sample_id],
            variant=r.variant_id, layout=r.layout_id, page=page.model_dump(mode='json'),
            routes={key: [f.model_dump(mode='json') for f in values] for key, values in routes.items()},
            keyword=keyword.model_dump(mode='json'), learned=learned.model_dump(mode='json')))
    # This boundary is deliberate: persist all inference before opening any reference annotation.
    write_json(args.output / 'predictions.json', predictions)
    references = {r.sample_id: PageAnnotation.model_validate_json(resolve_inside(root, r.annotation_path).read_text()) for r in selected}
    annotation_hashes = {r.annotation_path: sha256(root / r.annotation_path) for r in selected}
    assert all(h == metadata['artifact_hashes'][p] for p, h in annotation_hashes.items())
    def score(items):
        return {route: field_metrics([dict(sample_id=p['sample_id'], document_type=p['document_type'],
            reference={k: v.model_dump(mode='json') for k, v in references[p['sample_id']].fields.items()},
            predictions=p['routes'][route]) for p in items]) for route in ('true_type', 'keyword_type', 'learned_type')}
    validation = [p for p in predictions if p['partition'] == 'validation']
    metrics = dict(validation_all=score(validation), validation_clean=score([p for p in validation if p['variant'] == 'clean']),
        validation_by_variant={v: score([p for p in validation if p['variant'] == v]) for v in sorted({p['variant'] for p in validation})},
        train_diagnostic=score([p for p in predictions if p['partition'] == 'train']))
    write_json(args.output / 'metrics.json', metrics)
    write_json(args.output / 'code_snapshot.json', code_snapshot())
    write_json(args.output / 'run.json', dict(run_id=args.output.name, extraction_version=VERSION,
        normalization_version=NORMALIZATION_VERSION, python_version=platform.python_version(),
        library_versions={name: version(name) for name in ('pydantic', 'Pillow', 'scikit-learn', 'numpy')},
        inference_settings=feature_meta['inference_settings'], engine_versions=sorted({cached[r.sample_id]['ocr']['engine_version'] for r in selected}), dataset_version=metadata['dataset_version'],
        manifest_sha256=sha256(manifest), splits_sha256=sha256(split_path), model_sha256=model.metadata['model_sha256'],
        features_sha256=feature_meta['features_sha256'], input_hashes=input_hashes, annotation_hashes=annotation_hashes,
        original_ocr_result_hashes=source_results, code_snapshot_sha256=sha256(args.output / 'code_snapshot.json'),
        predictions_sha256=sha256(args.output / 'predictions.json'), metrics_sha256=sha256(args.output / 'metrics.json'),
        split_check=split_check, partitions=dict(Counter(p['partition'] for p in predictions)),
        valid_evidence_checks=evidence_checked, final_test_consumed=False, layout_probe_evaluated=False,
        references='provisional synthetic generator annotations; present/unreadable/absent are scored separately',
        scope='page-level; true-type diagnostic uses manifest type only, predicted routes use OCR only; all references opened after saved inference',
        exact_command=shlex.join([sys.executable, *sys.argv]), runtime_seconds=perf_counter()-started,
        timing_scope='cached real OCR read/validation + model reload + extraction/routes/evidence audit + scoring/saves; excludes original OCR time'))
    print(json.dumps({k: m['overall'] for k, m in metrics['validation_all'].items()}, indent=2))


if __name__ == '__main__':
    main()
