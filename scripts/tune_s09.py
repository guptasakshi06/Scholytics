#!/usr/bin/env python3
"""Bounded predeclared DIP selection on 12 validation pages; never test."""
import argparse
import json
from pathlib import Path
import shlex
import sys

from compare_preprocessing import matrix
from scholarready.evaluation.experiment import infer_pages, page_predictions, score_pages
from scholarready.pipeline import write_json
from scholarready.preprocessing import PreprocessingConfig
from scholarready.splitting import load_records


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reuse-inference',type=Path); args=parser.parse_args()
    root=Path.cwd(); args.output.mkdir(parents=True,exist_ok=False)
    records=[r for r in load_records(root/'data/manifests/expanded.jsonl') if r.development_role=='validation'
             and r.applicant_id=='expanded-10' and r.variant_id!='no_amount']
    specs=matrix(PreprocessingConfig())
    write_json(args.output/'plan_before_inference.json',dict(sample_ids=[r.sample_id for r in records],
        candidates=[dict(name=n,branch=b,config=c.model_dump(mode='json')) for n,b,c in specs],
        selection='Among full C and C_kernel_1x2/2x1/2x2, minimize corpus character edits, then word edits, then original candidate order. Other variants are diagnostics, not candidates. One validation group, narrow tuning support; fixed OCR.'))
    pending=[]
    # Finish all inference before opening reference texts/fields.
    for name,branch,conf in specs:
        docs,_,_=infer_pages(root,records,args.output/name,branch,conf,shlex.join([sys.executable,*sys.argv]),
                            args.reuse_inference/name if args.reuse_inference else None)
        preds=page_predictions(records,docs); write_json(args.output/name/'predictions_before_references.json',preds)
        pending.append((name,branch,conf,preds))
    reports=[]
    for name,branch,conf,preds in pending:
        metrics,rows=score_pages(root,records,preds)
        write_json(args.output/name/'scored_pages.json',rows); write_json(args.output/name/'metrics.json',metrics)
        reports.append(dict(name=name,branch=branch,config=conf.model_dump(mode='json'),metrics=metrics))
    eligible=[r for r in reports if r['name'] in ('C','C_kernel_1x2','C_kernel_2x1','C_kernel_2x2')]
    best=min(eligible,key=lambda r:(r['metrics']['ocr']['character_edits'],r['metrics']['ocr']['word_edits']))
    write_json(args.output/'selection.json',dict(selected=best,variants=reports,final_test_consumed=False))
    print(json.dumps(dict(selected=best['name'],ocr=best['metrics']['ocr'])))


if __name__=='__main__': main()
