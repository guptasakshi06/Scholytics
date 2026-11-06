#!/usr/bin/env python3
"""Rehearse four fictional development cases using the real shared CLI, without final-test access."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    'complete':('ready',100.,{}),
    'missing':('incomplete',80.,{'income':'missing'}),
    'unreadable':('needs_clearer_upload',80.,{'income':'unreadable'}),
    'name_mismatch':('needs_review',0.,dict.fromkeys(['marksheet','income','bonafide','domicile','category'],'needs_review')),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New rehearsal directory')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    all_rows=[];start=time.perf_counter()
    for name,(state,score,changes) in EXPECTED.items():
        cmd=[sys.executable,'-m','scholarready','analyze','--bundle',str(ROOT/f'output/demo/{name}.inputs.json'),
             '--input-root',str(ROOT/'output/demo'),'--branch','A','--profile',str(ROOT/'configs/scholarship_demo.json'),
             '--output',str(out/name)]
        tick=time.perf_counter();proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=180)
        (out/(name+'.log')).write_text(proc.stdout+proc.stderr)
        row=dict(case=name,argv=cmd,cwd=str(ROOT),exit_code=proc.returncode,seconds=time.perf_counter()-tick)
        all_rows.append(row)
        try:
            result=json.loads((out/name/'result.json').read_text())
            expected_items=dict.fromkeys(['marksheet','income','bonafide','domicile','category'],'satisfied')|changes
            actual={r['requirement_id']:r['state'] for r in result['requirements']}
            row.update(state=result['overall_state'],completeness=result['completeness'],requirements=actual,
                       passed=proc.returncode==0 and result['overall_state']==state and result['completeness']==score and actual==expected_items)
        except (OSError,ValueError,KeyError) as exc:
            row.update(passed=False,error=str(exc))
        print(json.dumps(row),flush=True)
    report=dict(passed=all(r['passed'] for r in all_rows),cases=all_rows,seconds=time.perf_counter()-start,
                scope='Actual CLI/OCR demonstration, fictional development fixtures, branch A keyword, no manual corrections',
                final_test_access=False,training=False)
    (out/'rehearsal.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()
