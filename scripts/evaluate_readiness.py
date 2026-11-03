#!/usr/bin/env python3
"""Replay specified development token scenarios; open references after saved inference."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shlex
import sys

from scholarready.config import load_config
from scholarready.evaluation.readiness_scenarios import predict_fixture
from scholarready.evaluation.readiness_metrics import readiness_metrics
from scholarready.pipeline import code_snapshot, write_json
from scholarready.requirements import ENGINE_VERSION

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='new run directory')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    fixture=ROOT/'tests/fixtures/readiness'
    inputs=json.loads((fixture/'inputs.json').read_text())
    config=load_config(ROOT/'configs/scholarship_demo.json')
    predictions={}
    for spec in inputs['scenarios']:
        result=predict_fixture(spec, inputs['base_documents'],config)
        predictions[spec['scenario_id']]=result
    write_json(args.output/'predictions.json',{k:v.model_dump(mode='json') for k,v in predictions.items()})
    # First reference open occurs after all inference was saved.
    references=json.loads((fixture/'references.json').read_text())
    assert references['review']['status'].startswith('reviewed')
    assert set(predictions)=={r['scenario_id'] for r in references['scenarios']}
    rows=[]; differences=[]
    for ref in references['scenarios']:
        result=predictions[ref['scenario_id']]
        predicted=dict(overall_state=result.overall_state, completeness=result.completeness,
            requirements={r.requirement_id:r.state for r in result.requirements})
        expected={k:ref[k] for k in ('overall_state','completeness','requirements')}
        rows.append(dict(scenario_id=ref['scenario_id'],reference=expected,predicted=predicted))
        if expected!=predicted:
            differences.append(dict(scenario_id=ref['scenario_id'],reference=expected,predicted=predicted))
    write_json(args.output/'rows.json',rows)
    write_json(args.output/'metrics.json',readiness_metrics(rows))
    write_json(args.output/'differences.json',differences)
    write_json(args.output/'run.json',dict(scope='deterministic fictional token development fixtures only; no OCR acquisition',
        engine=ENGINE_VERSION,python=platform.python_version(), exact_command=shlex.join([sys.executable,*sys.argv]),
        code_snapshot=code_snapshot(), hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [fixture/'inputs.json',fixture/'references.json',ROOT/'configs/scholarship_demo.json',ROOT/'requirements.lock.txt']},
        reference_review=references['review'], final_test_consumed=False))
    print(json.dumps(dict(scenarios=len(rows),differences=differences,metrics=str(args.output/'metrics.json')),indent=2))
    if differences:
        raise SystemExit(1)

if __name__=='__main__':
    main()
