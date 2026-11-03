#!/usr/bin/env python3
"""Explicit development-only OCR evaluation. References are opened AFTER inference."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

from scholarready.config import load_config
from scholarready.evaluation.ocr_metrics import aggregate, score
from scholarready.pipeline import analyze, write_json
from scholarready.schemas import ApplicantProfile, DatasetRecord


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--samples', nargs='+', required=True, help='explicit development sample IDs')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--profile', type=Path, default=Path('configs/scholarship_demo.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        from scholarready.dataset import PageAnnotation, resolve_inside
        records = [DatasetRecord.model_validate_json(line) for line in args.manifest.read_text().splitlines() if line.strip()]
        wanted = set(args.samples)
        chosen = [r for r in records if r.sample_id in wanted]
        if len(wanted) != len(args.samples) or len(chosen) != len(wanted):
            raise ValueError('Unknown/duplicate sample IDs')
        if any(r.development_role != 'development_only' for r in chosen):
            raise ValueError('S03 evaluator accepts development_only records; final test is forbidden')
        paths = list(dict.fromkeys(resolve_inside(args.root, r.relative_path) for r in chosen))
        result = analyze(paths, config=load_config(args.profile),
            applicant=ApplicantProfile(applicant_reference='development-ocr-evaluation'),
            output=args.output, exact_command=shlex.join([sys.executable, *sys.argv]))
        inputs = json.loads((args.output / 'inputs.json').read_text())['files']
        doc_by_path = {i['input_path']: d for i, d in zip(inputs, result.documents)}
        rows = []
        for record in chosen:
            # This is the ONLY reference read, strictly after analyze() returned.
            reference_path = resolve_inside(args.root, record.annotation_path)
            reference = PageAnnotation.model_validate_json(reference_path.read_text())
            if reference.sample_id != record.sample_id:
                raise ValueError(f'Reference sample ID mismatch: {record.sample_id}')
            doc = doc_by_path[str(resolve_inside(args.root, record.relative_path))]
            page = next((p for p in doc.pages if p.page_index == record.page_index), None)
            prediction = next((o for o in doc.ocr if page and o.page_id == page.page_id), None)
            text = prediction.text if prediction else ''
            rows.append(dict(sample_id=record.sample_id, run_id=result.run_id,
                document_id=doc.document_id, page_id=page.page_id if page else None,
                page_index=record.page_index, input_sha256=doc.source_sha256,
                reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                reference_status=reference.reference_status, reference_origin=reference.reference_origin,
                reference_text=reference.full_text, prediction_text=text,
                ocr_status=prediction.status if prediction else 'error',
                errors=doc.errors, metrics=score(reference.full_text, text)))
        report = dict(run_id=result.run_id, dataset_role='development_only',
            manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            selected_sample_ids=args.samples, scored_pages=len(rows),
            processed_pages=sum(len(d.pages) for d in result.documents),
            failure_count=sum(r['ocr_status'] == 'error' for r in rows),
            limitations='Provisional synthetic references; selected development pages, no held-out performance claim. Ingestion/OCR failures use empty predictions and remain in denominators.',
            aggregate=aggregate([r['metrics'] for r in rows]), samples=rows)
        write_json(args.output / 'ocr_evaluation.json', report)
        print(json.dumps(dict(run_id=result.run_id, **report['aggregate'], failure_count=report['failure_count'])))
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Evaluation error: {exc}\n')


if __name__ == '__main__':
    main()
