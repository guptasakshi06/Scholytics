#!/usr/bin/env python3
"""Run a hash-verified frozen experiment; test requires explicit consumption tracking."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shlex
import sys
from time import perf_counter
import uuid

from scholarready.classification import LearnedClassifier
from scholarready.dataset import sha256
from scholarready.evaluation.experiment import (infer_pages, load_inference, page_predictions, score_pages,
                                               bundle_predictions, score_bundles)
from scholarready.evaluation.freeze import selected_records, validate_freeze
from scholarready.pipeline import write_json
from scholarready.preprocessing import PreprocessingConfig


def authorize_partition(partition,consume_test):
    if partition=='test' and not consume_test:
        raise ValueError('Test is protected. S10 must explicitly use --consume-test; consumption is recorded before inference.')
    if consume_test and partition!='test': raise ValueError('--consume-test requires --partition test')


def run(args):
    authorize_partition(args.partition,args.consume_test)
    if args.replay_from is not None:
        args.replay_from=args.replay_from.resolve()
    root=Path.cwd(); config,frozen,audit=validate_freeze(root,args.config)
    if args.verify_only:
        print(json.dumps(dict(status='passed',freeze_sha256=sha256(root/config['freeze_record']),dataset=audit))); return
    output=args.output.resolve(); output.mkdir(parents=True,exist_ok=False)
    records=selected_records(root,config,args.partition)
    metadata=json.loads((root/config['manifest']).with_suffix('.metadata.json').read_text())
    bundles=[b for b in metadata['bundles'] if b['partition']==args.partition]
    specs=[s for s in config['variants'] if args.suite=='all' or s['name'] in ('A','B','C')]
    command=shlex.join([sys.executable,*sys.argv]); started=perf_counter()
    signature=dict(freeze_sha256=sha256(root/config['freeze_record']),partition=args.partition,suite=args.suite,
        selected_sample_ids=[r.sample_id for r in records],selected_bundle_paths=[b['input_path'] for b in bundles])
    if args.replay_from:
        prior=json.loads((args.replay_from/'run.json').read_text())
        if any(prior[k]!=v for k,v in signature.items()): raise ValueError('Replay partition/freeze/suite mismatch')
    if args.partition=='test':
        # Append a durable start record even when a later OCR/scoring operation fails.
        registry=root/'docs/verification/s10/test_consumption'; registry.mkdir(parents=True,exist_ok=True)
        write_json(registry/(uuid.uuid4().hex+'.json'),dict(signature,started_utc=datetime.now(timezone.utc).isoformat(),
            command=command,output=str(output),status='started_test_consumed',replay=args.replay_from is not None))
        handoff=root/'HANDOFF.md'
        if handoff.exists():
            text=handoff.read_text(); text=text.replace('| Final test consumed | NO |','| Final test consumed | YES — see docs/verification/s10/test_consumption |',1)
            handoff.write_text(text)
    write_json(output/'selection_before_inference.json',signature)
    model=LearnedClassifier.load(root/config['model'])
    pending=[]
    for spec in specs:
        folder=output/spec['name']; folder.mkdir()
        if args.replay_from:
            docs,index=load_inference(root,args.replay_from/spec['name']/'inference')
            if index['selected_sample_ids']!=signature['selected_sample_ids'] or index['branch']!=spec['branch'] or index['preprocessing']!=spec['preprocessing']:
                raise ValueError('Replay settings/sample IDs mismatch')
            source=args.replay_from/spec['name']/'inference'
            seconds=None
        else:
            source=folder/'inference'
            docs,index,seconds=infer_pages(root,records,source,spec['branch'],PreprocessingConfig.model_validate(spec['preprocessing']),command)
        routes=[('keyword',None)]+([('learned',model)] if spec['name']=='A' else [])
        for route,classifier in routes:
            pages=page_predictions(records,docs,classifier)
            apps,rule_seconds=bundle_predictions(root,bundles,docs,classifier)
            write_json(folder/(route+'_pages_before_references.json'),pages)
            write_json(folder/(route+'_bundles_before_references.json'),apps)
            pending.append((spec,route,folder,pages,apps,seconds,rule_seconds,source))
    # Ground truth is used for scoring only after ALL selected variants finish prediction.
    reports=[]
    for spec,route,folder,pages,apps,seconds,rule_seconds,source in pending:
        metrics,rows=score_pages(root,records,pages)
        readiness,bundle_rows=score_bundles(root,bundles,apps)
        report=dict(name=spec['name'],route=route,page_metrics=metrics,readiness=readiness,
            end_to_end_page_seconds=seconds,bundle_replay_rule_seconds=rule_seconds,
            inference_index=source.relative_to(root).as_posix()+'/inference_index.json')
        write_json(folder/(route+'_scored_pages.json'),rows)
        write_json(folder/(route+'_scored_bundles.json'),bundle_rows)
        write_json(folder/(route+'_metrics.json'),report); reports.append(report)
    write_json(output/'summary.json',dict(partition=args.partition,reports=reports,final_test_consumed=args.partition=='test'))
    write_json(output/'run.json',dict(signature,command=command,python=platform.python_version(),platform=platform.platform(),
        library_versions={n:version(n) for n in ('numpy','scikit-learn','Pillow','opencv-python-headless','pytesseract','pypdfium2')},
        cpu=platform.processor(),cpu_description=Path('/proc/cpuinfo').read_text().split('model name',1)[-1].split('\n',1)[0].strip(': '),
        total_wall_seconds=perf_counter()-started,cache_replay=args.replay_from is not None,
        timing_scope=config['timing_scope'],final_test_consumed=args.partition=='test'))
    write_json(output/'artifact_hashes.json',{p.relative_to(output).as_posix():sha256(p) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(dict(output=str(output),partition=args.partition,reports=len(reports))))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True); p.add_argument('--partition',choices=['validation','test'],required=True)
    p.add_argument('--suite',choices=['core','all'],default='core'); p.add_argument('--output',type=Path,default=Path('artifacts/runs/frozen-experiment'))
    p.add_argument('--consume-test',action='store_true'); p.add_argument('--verify-only',action='store_true')
    p.add_argument('--replay-from',type=Path,help='Recompute predictions/scores from a hash-verified prior run; runtime is not comparable to fresh OCR')
    args=p.parse_args()
    try: run(args)
    except (ValueError,OSError) as exc: p.exit(1,f'Frozen experiment error: {exc}\n')


if __name__=='__main__': main()
