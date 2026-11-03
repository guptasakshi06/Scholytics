#!/usr/bin/env python3
"""Read-only audit plus compact S07 evidence export; never runs inference/test data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from scholarready.pipeline import write_json
from scholarready.schemas import ApplicationResult

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokens',type=Path,default=Path('artifacts/runs/s07-scenarios-final'))
    p.add_argument('--cli',type=Path,default=Path('artifacts/runs/s07-cli'))
    p.add_argument('--demo',type=Path,default=Path('artifacts/runs/s07-learned-demo'))
    p.add_argument('--snapshot',type=Path,default=Path('docs/verification/s07'))
    args=p.parse_args(); snapshot=args.snapshot; snapshot.mkdir(parents=True,exist_ok=True)
    load=lambda path:json.loads(path.read_text())
    hashes=load(args.cli/'audit.json')['artifact_hashes']
    for path,digest in hashes.items():
        assert hashlib.sha256((args.cli/path).read_bytes()).hexdigest()==digest,path
    for path,digest in load(args.tokens/'run.json')['hashes'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    recount={}
    for name,run in [('tokens',args.tokens),('cli',args.cli)]:
        rows=load(run/'rows.json');metrics=load(run/'metrics.json')
        # Direct independent counts, not a second invocation of the metric implementation.
        nonready=sum(r['reference']['overall_state']!='ready' for r in rows)
        false=sum(r['reference']['overall_state']!='ready' and r['predicted']['overall_state']=='ready' for r in rows)
        items=sum(len(r['reference']['requirements']) for r in rows)
        missing=sum(s=='missing' for r in rows for s in r['reference']['requirements'].values())
        assert all(r['reference']==r['predicted'] for r in rows)
        assert metrics['application']['false_ready_count']==false
        assert metrics['application']['reference_non_ready_count']==nonready
        assert metrics['requirement_items']==items
        assert metrics['requirements']['missing_positive']['tp']==missing
        assert all(sum(v.values())==metrics['requirements']['reference_support'][s]
                   for s,v in metrics['requirements']['confusion'].items())
        recount[name]=dict(scenarios=len(rows),items=items,reference_non_ready=nonready,false_ready=false,missing=missing)
        for file in ('rows.json','metrics.json'):
            shutil.copyfile(run/file,snapshot/f'{name}_{file}')
    token_predictions=load(args.tokens/'predictions.json')
    references=load(ROOT/'tests/fixtures/readiness/references.json')
    for key,raw in token_predictions.items():
        result=ApplicationResult.model_validate(raw)
        for r in result.requirements:
            doc_ids={d.document_id for d in result.documents}
            page_ids={p.page_id for d in result.documents for p in d.pages}
            field_ids={f'{d.document_id}:{f.field_name}' for d in result.documents for f in d.fields}
            assert set(r.document_references)<=doc_ids
            assert set(r.page_references)<=page_ids
            assert set(r.field_references)<=field_ids
    write_json(snapshot/'token_results.json',token_predictions)
    for file in ('run.json','differences.json'):
        shutil.copyfile(args.tokens/file,snapshot/f'tokens_{file}')
    initial=Path('artifacts/runs/s07-scenarios/differences.json')
    if initial.exists():
        shutil.copyfile(initial,snapshot/'initial_fixture_differences.json')
    cli_index=[]
    target=snapshot/'cli';target.mkdir(exist_ok=True)
    for row in load(args.cli/'audit.json')['runs']:
        name=row['name']; run=args.cli/name
        result=ApplicationResult.model_validate_json((run/'result.json').read_text())
        for r in result.requirements:
            assert set(r.document_references)<={d.document_id for d in result.documents}
            assert set(r.page_references)<={p.page_id for d in result.documents for p in d.pages}
        dest=target/name;dest.mkdir(exist_ok=True)
        for file in ('result.json','metadata.json','config.json','applicant.json','inputs.json','settings.json','code_snapshot.json'):
            shutil.copyfile(run/file,dest/file)
        shutil.copyfile(args.cli/f'{name}.inputs.json',dest/'bundle.json')
        cli_index.append(dict(name=name,run_id=result.run_id,overall=result.overall_state,score=result.completeness,
                              command=row['command'],exit_code=row['exit_code']))
    for file in ('audit.json','references_before_inference.json','printed_fixture_specifications.json'):
        shutil.copyfile(args.cli/file,snapshot/f'cli_{file}')
    demo=ApplicationResult.model_validate_json((args.demo/'result.json').read_text())
    assert demo.overall_state=='ready' and demo.completeness==100.
    prior=load(ROOT/'docs/verification/s06/source_snapshot.json')
    prior_run=load(ROOT/'docs/verification/s06/run.json')
    prior.update({'data/manifests/pilot.jsonl':prior_run['manifest_sha256'],
                  'data/manifests/pilot.splits.jsonl':prior_run['splits_sha256']})
    protected=['requirements.lock.txt','pyproject.toml','configs/preprocessing.json',
        'src/scholarready/classification.py','src/scholarready/extraction.py',
        'data/manifests/pilot.jsonl','data/manifests/pilot.splits.jsonl']
    for path in protected:
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==prior[path],path
    model_hash=load(args.demo/'classifier.json')['model_sha256']
    assert model_hash==load(ROOT/'docs/verification/s06/run.json')['model_sha256']
    for file in ('result.json','metadata.json','classifier.json'):
        shutil.copyfile(args.demo/file,snapshot/f'learned_demo_{file}')
    sources=[]
    for directory in ('src','tests','scripts','configs'):
        sources += [path for path in (ROOT/directory).rglob('*') if path.is_file() and '__pycache__' not in path.parts
                    and path.suffix in {'.py','.json'}]
    sources += [ROOT/name for name in ('requirements.lock.txt','pyproject.toml','data/manifests/pilot.jsonl','data/manifests/pilot.splits.jsonl')]
    write_json(snapshot/'source_snapshot.json',{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(sources)})
    write_json(snapshot/'run_index.json',cli_index)
    write_json(snapshot/'acceptance.json',dict(status='PASS',recount=recount,cli_artifact_hash_checks=len(hashes),
        token_reference_review=references['review'], token_results_validated=len(token_predictions),
        unchanged_from_s06=protected,model_sha256=model_hash,
        learned_demo=dict(run_id=demo.run_id,state=demo.overall_state,completeness=demo.completeness),
        final_test_consumed=False,
        limitation='Specified related synthetic development fixtures only; no population false-ready/calibration claim. Raw run images are ignored and reproducibly regenerated; compact result/metadata snapshots are retained.'))
    print(json.dumps(load(snapshot/'acceptance.json'),indent=2))

if __name__=='__main__':main()
