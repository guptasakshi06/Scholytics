#!/usr/bin/env python3
"""Train on new clean train pages; choose LR C/uncertainty using validation only."""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shlex
import sys

import joblib

from scholarready.classification import LearnedClassifier, build_estimator
from scholarready.dataset import sha256
from scholarready.evaluation.classification_metrics import classification_metrics
from scholarready.evaluation.experiment import infer_pages
from scholarready.evaluation.freeze import audit_dataset
from scholarready.ocr import OCRSettings
from scholarready.pipeline import code_snapshot, write_json
from scholarready.preprocessing import PreprocessingConfig
from scholarready.splitting import load_records


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reuse-inference',type=Path,help='Resume complete hash/settings/code-checked batches, never incomplete outputs')
    args=parser.parse_args(); root=Path.cwd(); args.output.mkdir(parents=True,exist_ok=False)
    manifest=root/'data/manifests/expanded.jsonl'; splits=root/'data/manifests/expanded.splits.jsonl'
    write_json(args.output/'split_audit.json',audit_dataset(root,manifest,splits))
    records=load_records(manifest)
    train=[r for r in records if r.development_role=='train' and r.variant_id=='clean']
    val=[r for r in records if r.development_role=='validation']
    plan=dict(C=[.5,4.,16.],probabilities=[.3,.4,.5,.6],margins=[.05,.1,.2],coverage=.1,
        selection='Maximize validation macro-F1, fewer wrong accepted, stricter probability/margin, smaller C; no test inference.',
        train_ids=[r.sample_id for r in train],validation_ids=[r.sample_id for r in val],seed=2026,
        inference=dict(branch='A',ocr=asdict(OCRSettings()),pdf_dpi=300,preprocessing=PreprocessingConfig().model_dump(mode='json')))
    write_json(args.output/'plan_before_inference.json',plan)
    docs,origins,_=infer_pages(root,train+val,args.output/'inference','A',PreprocessingConfig(),shlex.join([sys.executable,*sys.argv]),args.reuse_inference)
    def text(r): return '\n'.join(o.text for o in docs[r.relative_path].ocr)
    if any(docs[r.relative_path].errors or not text(r).strip() for r in train): raise ValueError('Unusable training input')
    trials=[]; models={}
    metadata=dict(model_version='tfidf-lr-s09-1.0',thresholds={},inference_settings=plan['inference'],seed=2026,
        dependency_versions={n:version(n) for n in ('scikit-learn','numpy','scipy','joblib')},
        manifest_sha256=sha256(manifest),splits_sha256=sha256(splits),training_sample_ids=plan['train_ids'],
        validation_sample_ids=plan['validation_ids'],feature_policy='Unchanged feature_text; OCR text only, no metadata/reference features.',
        training_text_sha256=hashlib.sha256(json.dumps([text(r) for r in train]).encode()).hexdigest(),
        code_snapshot=code_snapshot(),exact_command=shlex.join([sys.executable,*sys.argv]),final_test_consumed=False)
    for c in plan['C']:
        estimator=build_estimator(2026); estimator.set_params(logistic__C=c)
        estimator.fit([text(r) for r in train],[r.document_type for r in train]); models[c]=estimator
        for probability in plan['probabilities']:
            for margin in plan['margins']:
                thresholds=dict(minimum_probability=probability,minimum_margin=margin,minimum_vocabulary_coverage=.1)
                model=LearnedClassifier(estimator,dict(metadata,thresholds=thresholds))
                predictions=[model.classify(docs[r.relative_path].ocr,docs[r.relative_path].errors) for r in val]
                metric=classification_metrics([r.document_type for r in val],predictions)
                wrong=sum(p.decision=='classified' and p.document_type!=r.document_type for r,p in zip(val,predictions))
                trials.append(dict(C=c,thresholds=thresholds,macro_f1=metric['macro_f1'],wrong_accepted=wrong,unresolved=metric['unresolved']))
    best=max(trials,key=lambda t:(t['macro_f1'],-t['wrong_accepted'],t['thresholds']['minimum_probability'],t['thresholds']['minimum_margin'],-t['C']))
    metadata.update(thresholds=best['thresholds'],C=best['C'],classes=list(models[best['C']].classes_),selection=plan['selection'])
    folder=args.output/'model'; folder.mkdir(); joblib.dump(models[best['C']],folder/'model.joblib')
    metadata['model_sha256']=sha256(folder/'model.joblib'); write_json(folder/'metadata.json',metadata)
    reloaded=LearnedClassifier.load(folder); before=LearnedClassifier(models[best['C']],metadata)
    assert [p.model_dump() for p in [before.predict_text(text(r)) for r in val]]==[p.model_dump() for p in [reloaded.predict_text(text(r)) for r in val]]
    write_json(args.output/'selection.json',dict(selected=best,trials=trials,reload_identical=True,
        actual_inference_sample_ids=[r.sample_id for r in train+val],final_test_consumed=False))
    print(json.dumps(best))


if __name__=='__main__': main()
