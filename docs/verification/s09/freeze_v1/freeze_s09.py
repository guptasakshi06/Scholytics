#!/usr/bin/env python3
"""Bind reviewed data, selections, executable methods and model before final test."""
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess

from compare_preprocessing import matrix
from scholarready.dataset import sha256
from scholarready.evaluation.freeze import audit_dataset
from scholarready.ocr import OCRSettings, engine_version
from scholarready.pipeline import write_json
from scholarready.preprocessing import PreprocessingConfig
from scholarready.splitting import load_records


def main():
    root=Path.cwd(); record=root/'docs/verification/s09/freeze.json'; config_path=root/'configs/evaluation.json'
    if record.exists() or config_path.exists(): raise ValueError('Freeze already exists; never silently overwrite it')
    review=json.loads((root/'data/annotations/expanded_review.json').read_text())
    audit=audit_dataset(root,root/'data/manifests/expanded.jsonl',root/'data/manifests/expanded.splits.jsonl',review)
    if list((root/'docs/verification/s10').glob('test_consumption/*.json')): raise ValueError('Test already consumed')
    training=root/'artifacts/runs/s09-training-complete'; tuning=root/'artifacts/runs/s09-dip-tuning-complete'
    selection=json.loads((tuning/'selection.json').read_text())
    conf=PreprocessingConfig.model_validate(selection['selected']['config'])
    records=load_records(root/'data/manifests/expanded.jsonl')
    config=dict(protocol_version='evaluation-s09-1.0',manifest='data/manifests/expanded.jsonl',splits='data/manifests/expanded.splits.jsonl',
        review='data/annotations/expanded_review.json',freeze_record='docs/verification/s09/freeze.json',
        model='artifacts/runs/s09-training-complete/model',seed=2026,
        sample_ids={p:[r.sample_id for r in records if r.development_role==p] for p in ('train','validation','test')},
        variants=[dict(name=n,branch=b,preprocessing=c.model_dump(mode='json')) for n,b,c in matrix(conf)],
        selected_C_candidate=selection['selected']['name'],ocr=asdict(OCRSettings()),pdf_dpi=300,
        comparison_questions=['DIP A/B/C and ablations with keyword-1.0, spatial-s06-1.0 and requirements-s07-1.0 fixed.',
            'Optional A-only keyword vs frozen A-trained TF-IDF/LR; same OCR and field/rule implementations. No branch retraining or DIP-only attribution of classifier differences.'],
        metrics=dict(ocr='nfc_casefold_collapse_whitespace_v1; corpus edit totals/ref length; empty refs null but edits retained',
            classification='Fixed six labels, unresolved retained in FN, per-class zero divisions=0; empty sample metrics null',
            fields='Exact normalized value+unit+role / every present target; missing/wrong/extra/absent separately; true-type diagnostic separate',
            readiness='Five named items; missing positive; all states retained; false ready / all reference non-ready; zero denominators null',
            uncertainty='No resampling CI with four test groups; report raw supports, known vs unseen layout, per degradation; synthetic only'),
        timing_scope='Sequential page batches: decode/render/save, quality, DIP/stage saves, OCR, keyword/fields/checklist; excludes model load, final JSON writes. OCR and preprocessing reported separately. Bundle assembly reuses page OCR, measures only classification/extraction/rules; not upload latency. Replay durations not fresh OCR. No controlled cold/warm or speed superiority claim; processor/environment recorded.',
        commands=dict(validation='.venv/bin/python scripts/run_experiments.py --config configs/evaluation.json --partition validation --suite core --output artifacts/runs/s09-validation',
            test_S10_only='.venv/bin/python scripts/run_experiments.py --config configs/evaluation.json --partition test --suite all --consume-test --output artifacts/runs/s10-final'))
    write_json(config_path,config)
    # Full authoritative inventories bind inputs and independent attestations as well as executable definitions.
    dataset_meta=json.loads((root/'data/manifests/expanded.metadata.json').read_text())
    paths=set(dataset_meta['artifact_hashes'])
    paths.update(p.relative_to(root).as_posix() for p in (root/'src').rglob('*.py'))
    paths.update(p.relative_to(root).as_posix() for p in (root/'scripts').glob('*.py'))
    paths.update(['requirements.lock.txt','pyproject.toml','configs/preprocessing.json','configs/scholarship_demo.json',
        'configs/evaluation.json','data/manifests/expanded.jsonl','data/manifests/expanded.metadata.json',
        'data/manifests/expanded.splits.jsonl','data/annotations/expanded_review.json','docs/EVALUATION_PROTOCOL.md',
        'docs/verification/s09/source_review_final/duplicates.json'])
    for directory in (training/'model',): paths.update(p.relative_to(root).as_posix() for p in directory.iterdir() if p.is_file())
    for p in (training/'selection.json',training/'plan_before_inference.json',tuning/'selection.json',tuning/'plan_before_inference.json'):
        paths.add(p.relative_to(root).as_posix())
    paths.update(p.relative_to(root).as_posix() for p in (root/'docs/verification/s09/source_review_final').glob('exp-*.png'))
    executable=Path(shutil.which('tesseract')).resolve()
    languages=subprocess.run([str(executable),'--list-langs'],capture_output=True,text=True,check=True).stdout
    tessdata=Path(re.search(r'"([^"]+)"',languages)[1])/'eng.traineddata'
    write_json(record,dict(protocol_version=config['protocol_version'],created_utc=datetime.now(timezone.utc).isoformat(),
        evaluation_config_sha256=sha256(config_path),artifact_hashes={p:sha256(root/p) for p in sorted(paths)},
        implementation_files=sorted(p.relative_to(root).as_posix() for p in (root/'src').rglob('*.py')),
        support=audit,environment=dict(python=platform.python_version(),tesseract=engine_version(),
            libraries={n:version(n) for n in ('numpy','Pillow','pypdfium2','pytesseract','opencv-python-headless','scikit-learn','scipy','joblib','pydantic')},
            external_files={n:dict(path=str(p),sha256=sha256(p)) for n,p in [('tesseract',executable),('eng.traineddata',tessdata)]}),
        final_test_consumed=False,reference_review='same-agent separate source inspection, not student sign-off'))
    print(json.dumps(dict(status='frozen',freeze_sha256=sha256(record),artifacts=len(paths),final_test_consumed=False)))


if __name__=='__main__': main()
