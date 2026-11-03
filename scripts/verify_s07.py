#!/usr/bin/env python3
"""Run real local CLI scenarios and audit readiness evidence. No final-test inputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
import reportlab

from scholarready.evaluation.readiness_metrics import readiness_metrics
from scholarready.pipeline import write_json, code_snapshot
from scholarready.requirements import ENGINE_VERSION
from scholarready.schemas import ApplicationResult

ROOT=Path(__file__).resolve().parents[1]

# Manually derived from the visible fictional inputs; never from pipeline predictions.
# Four required types + conditional category. Every mapping is the full denominator.
SAT=dict.fromkeys(['marksheet','income','bonafide','domicile','category'],'satisfied')
CASES={
    'complete':dict(overall='ready',score=100.,states={}),
    'missing':dict(overall='incomplete',score=80.,states={'income':'missing'}),
    'unreadable':dict(overall='needs_clearer_upload',score=80.,states={'income':'unreadable'}),
    'unknown':dict(overall='needs_review',score=80.,states={'income':'needs_review'}),
    'hinted_blank':dict(overall='needs_review',score=80.,states={'income':'unreadable'}),
    'conditional_false':dict(overall='ready',score=100.,states={'category':'not_applicable'}),
    'conditional_unknown':dict(overall='needs_review',score=None,states={'category':'needs_review'}),
    'name_mismatch':dict(overall='needs_review',score=0.,states=dict.fromkeys(SAT,'needs_review')),
    'agreeing_duplicate':dict(overall='ready',score=100.,states={}),
    'conflicting_duplicate':dict(overall='needs_review',score=80.,states={'income':'needs_review'}),
    'processing_failure':dict(overall='needs_review',score=80.,states={'income':'needs_review'},exit_code=1),
    'other_document':dict(overall='incomplete',score=80.,states={'income':'missing'}),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=False)
    fixtures=output/'fixtures'; fixtures.mkdir()
    font_path=Path(reportlab.__file__).parent/'fonts/Vera.ttf'
    font=ImageFont.truetype(str(font_path),28)
    contents={
        'unreadable':['INCOME CERTIFICATE','Applicant name: Fictional Aster','Guardian name: Fictional Guardian A','Issue date: 2026-01-15'],
        'unknown':['UNFAMILIAR RECORD','Fictional teaching content'],
        'name_mismatch':['INCOME CERTIFICATE','Applicant name: Fictional Birch','Guardian name: Fictional Guardian A','Annual income (INR/year): 96000','Issue date: 2026-01-15'],
        'conflicting_duplicate':['INCOME CERTIFICATE','Applicant name: Fictional Aster','Guardian name: Fictional Guardian A','Annual income (INR/year): 97000','Issue date: 2026-01-15'],
        'other_document':['LIBRARY NOTICE','Fictional reading hours: 09:00 to 17:00'],
    }
    write_json(output/'printed_fixture_specifications.json',contents)
    for name,lines in contents.items():
        image=Image.new('RGB',(1400,1300),'white');draw=ImageDraw.Draw(image)
        draw.text((60,30),'SYNTHETIC - FOR ACADEMIC DEMONSTRATION',font=font,fill='black')
        for index,line in enumerate(lines):draw.text((60,130+index*130),line,font=font,fill='black')
        image.save(fixtures/f'{name}.png')
    Image.new('RGB',(400,300),'white').save(fixtures/'blank.png')
    (fixtures/'corrupt.png').write_bytes(b'Explicit fictional corrupt PNG fixture')
    for n in range(1,6):shutil.copyfile(ROOT/f'tests/fixtures/pilot/src-{n:03d}.png',fixtures/f'upload-{n}.png')
    shutil.copyfile(fixtures/'upload-2.png',fixtures/'income-copy.png')
    expected={name:dict(overall_state=c['overall'],completeness=c['score'],requirements=SAT|c['states']) for name,c in CASES.items()}
    write_json(output/'references_before_inference.json',dict(
        reviewer='Codex agent manual scenario specification, not student sign-off',
        method='Source contact sheet inspected independently; printed fixture lines and edits manually checked against documented rules. Expected states specified before CLI inference; no production predictions used.',
        scope='Development scenarios only; not a final test or reviewed final benchmark',expected=expected))
    rows=[]; results={}; logs=[]
    for name,case in CASES.items():
        paths=[fixtures/f'upload-{n}.png' for n in range(1,6)]
        category=True; hints={}
        if name in {'missing','unreadable','unknown','hinted_blank','name_mismatch','processing_failure','other_document'}:
            paths.pop(1)
        if name in {'unreadable','unknown','name_mismatch','other_document'}:paths.append(fixtures/f'{name}.png')
        if name=='hinted_blank':
            paths.append(fixtures/'blank.png');hints['fixtures/blank.png']='income_certificate'
        if name=='processing_failure':paths.append(fixtures/'corrupt.png')
        if name=='agreeing_duplicate':paths.append(fixtures/'income-copy.png')
        if name=='conflicting_duplicate':paths.append(fixtures/'conflicting_duplicate.png')
        if name.startswith('conditional_'):
            paths.pop(4); category=False if name.endswith('false') else None
        bundle=dict(scenario_id='s07-'+name,files=[str(p.relative_to(output)) for p in paths],
            profile=dict(applicant_reference='fictional-s07',category_certificate_required=category,
                expected_name='Fictional Aster'),declared_type_hints=hints)
        bundle_path=output/f'{name}.inputs.json';write_json(bundle_path,bundle)
        run=output/name
        command=[sys.executable,'-m','scholarready','analyze','--bundle',str(bundle_path),
            '--input-root',str(output),'--profile',str(ROOT/'configs/scholarship_demo.json'),'--output',str(run)]
        proc=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        (output/f'{name}.stdout.txt').write_text(proc.stdout)
        (output/f'{name}.stderr.txt').write_text(proc.stderr)
        assert proc.returncode==case.get('exit_code',0),(name,proc.returncode,proc.stderr)
        result=ApplicationResult.model_validate_json((run/'result.json').read_text())
        results[name]=result
        predicted=dict(overall_state=result.overall_state,completeness=result.completeness,
            requirements={r.requirement_id:r.state for r in result.requirements})
        assert predicted==expected[name],(name,expected[name],predicted)
        assert result.requirement_engine_version==ENGINE_VERSION
        if name=='agreeing_duplicate':
            income=next(r for r in result.requirements if r.requirement_id=='income')
            assert len(income.document_references)==2
        if name=='processing_failure': assert any(d.errors for d in result.documents)
        rows.append(dict(scenario_id=name,reference=expected[name],predicted=predicted))
        logs.append(dict(name=name,command=command,exit_code=proc.returncode,run_id=result.run_id))
        print(f'{name}: {result.overall_state}, {result.completeness}',flush=True)
    write_json(output/'rows.json',rows)
    write_json(output/'metrics.json',readiness_metrics(rows))
    hashes={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output/'audit.json',dict(status='PASS',scenarios=len(rows),runs=logs,code_snapshot=code_snapshot(),
        final_test_consumed=False,input_scope='versioned pilot fixtures + fresh visibly fictional development fixtures',
        metadata_note='Each CLI run records actual engine/settings/Python/library versions, input hashes and config/code hashes',
        outcome_counts=dict(Counter(r.overall_state for r in results.values())),artifact_hashes=hashes))
    print(f'PASS: {len(rows)} real CLI scenarios; {len(hashes)} artifact hashes',flush=True)

if __name__=='__main__':main()
