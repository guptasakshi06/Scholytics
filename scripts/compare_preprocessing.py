#!/usr/bin/env python3
"""Paired DEVELOPMENT-ONLY A/B/C OCR and fixed step/kernel ablations; no test use."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys
import uuid

from scholarready.config import load_config
from scholarready.dataset import PageAnnotation, resolve_inside
from scholarready.evaluation.ocr_metrics import aggregate, score
from scholarready.ocr import OCRSettings
from scholarready.pipeline import analyze, write_json
from scholarready.preprocessing import load_preprocessing, PreprocessingConfig
from scholarready.schemas import ApplicantProfile, DatasetRecord


def matrix(config):
    def changed(**kwargs):
        return PreprocessingConfig.model_validate(config.model_dump(mode='json') | kwargs)
    return [('A', 'A', config), ('B', 'B', config), ('C', 'C', config),
        ('C_no_deskew', 'C', changed(deskew=False)),
        ('C_no_clahe', 'C', changed(clahe=False)),
        ('C_no_filter', 'C', changed(denoise='none')),
        ('C_no_threshold_or_morphology', 'C', changed(threshold='none', morphology='none')),
        ('C_no_morphology', 'C', changed(morphology='none')),
        ('C_gray_only', 'C', changed(deskew=False, clahe=False, denoise='none', threshold='none', morphology='none')),
        *[(f'C_kernel_{h}x{w}', 'C', changed(kernel=[h, w])) for h, w in [(1, 2), (2, 1), (2, 2)]]]


def run(manifest, samples, root, profile, output, preprocessing, exact_command):
    records = [DatasetRecord.model_validate_json(line) for line in manifest.read_text().splitlines() if line.strip()]
    wanted = set(samples)
    chosen = [r for r in records if r.sample_id in wanted]
    if len(samples) != len(wanted) or len(chosen) != len(wanted):
        raise ValueError('Unknown/duplicate sample IDs')
    if any(r.development_role != 'development_only' for r in chosen):
        raise ValueError('S04 accepts development_only records; final test is forbidden')
    paths = list(dict.fromkeys(resolve_inside(root, r.relative_path) for r in chosen))
    specs = matrix(preprocessing)
    output.mkdir(parents=True, exist_ok=False)
    comparison_id = 's04-comparison-' + uuid.uuid4().hex
    write_json(output / 'matrix.json', dict(comparison_id=comparison_id, exact_command=exact_command,
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(), selected_sample_ids=samples,
        ocr=OCRSettings().__dict__, stage_order=['grayscale', 'deskew', 'clahe', 'filter', 'threshold', 'morphology'],
        variants=[dict(name=name, branch=branch, config=conf.model_dump(mode='json')) for name, branch, conf in specs]))
    # No reference text or fields opened until ALL inference variants are complete.
    results = {}
    for name, branch, conf in specs:
        results[name] = analyze(paths, config=load_config(profile),
            applicant=ApplicantProfile(applicant_reference='development-dip-comparison'),
            output=output / name, branch=branch, preprocessing=conf, exact_command=exact_command)
        print(f'Completed inference: {name} ({results[name].run_id})', flush=True)
    reports = []
    for name, branch, conf in specs:
        result = results[name]
        folder = output / name
        inputs = json.loads((folder / 'inputs.json').read_text())['files']
        docs = {item['input_path']: d for item, d in zip(inputs, result.documents)}
        rows = []
        for record in chosen:
            ref_path = resolve_inside(root, record.annotation_path)
            reference = PageAnnotation.model_validate_json(ref_path.read_text())
            if reference.sample_id != record.sample_id:
                raise ValueError('Reference sample ID mismatch')
            doc = docs[str(resolve_inside(root, record.relative_path))]
            page = next((p for p in doc.pages if p.page_index == record.page_index), None)
            prediction = next((o for o in doc.ocr if page and o.page_id == page.page_id), None)
            processing = next((p for p in doc.processing if page and p.page_id == page.page_id), None)
            rows.append(dict(sample_id=record.sample_id, source_document_id=record.source_document_id,
                applicant_id=record.applicant_id, variant_id=record.variant_id, run_id=result.run_id,
                document_id=doc.document_id, page_id=page.page_id if page else None,
                page_index=record.page_index, input_sha256=doc.source_sha256,
                reference_sha256=hashlib.sha256(ref_path.read_bytes()).hexdigest(),
                reference_status=reference.reference_status, reference_text=reference.full_text,
                prediction_text=prediction.text if prediction else '', ocr_status=prediction.status if prediction else 'error',
                errors=doc.errors, metrics=score(reference.full_text, prediction.text if prediction else ''),
                ocr_seconds=prediction.runtime_seconds if prediction else 0.,
                preprocessing_seconds=sum(s.runtime_seconds + float(s.parameters.get('estimation_seconds', 0))
                    for s in processing.stages) if processing else 0.))
        report = dict(comparison_id=comparison_id, name=name, branch=branch, run_id=result.run_id,
            dataset_role='development_only', scored_pages=len(rows),
            processed_pages=sum(len(d.pages) for d in result.documents),
            failure_count=sum(r['ocr_status'] == 'error' for r in rows),
            aggregate=aggregate([r['metrics'] for r in rows]), samples=rows,
            preprocessing_seconds=sum(r['preprocessing_seconds'] for r in rows),
            ocr_seconds=sum(r['ocr_seconds'] for r in rows), end_to_end_seconds=result.runtime_seconds)
        write_json(folder / 'ocr_evaluation.json', report)
        reports.append(report)
    summary = dict(comparison_id=comparison_id, dataset_role='development_only',
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(), selected_sample_ids=samples,
        limitations='Selected provisional synthetic development references, no held-out/generalization claim. All failures retained. Sequential wall times include saves; hardware/cache/load not controlled. No per-page winner selection.',
        variants=[{k: v for k, v in r.items() if k != 'samples'} for r in reports])
    write_json(output / 'comparison.json', summary)
    # Hash all run artifacts, including images, for later independent verification.
    write_json(output / 'artifact_hashes.json', {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file()})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--samples', nargs='+', required=True)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--profile', type=Path, default=Path('configs/scholarship_demo.json'))
    parser.add_argument('--preprocessing', type=Path, default=Path('configs/preprocessing.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = run(args.manifest, args.samples, args.root, args.profile, args.output,
            load_preprocessing(args.preprocessing), shlex.join([sys.executable, *sys.argv]))
        print(json.dumps(summary, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Comparison error: {exc}\n')


if __name__ == '__main__':
    main()
