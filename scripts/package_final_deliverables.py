#!/usr/bin/env python3
"""Package the local S12 companion to the preserved S11 core archive, without upload."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['HANDOFF.md','README.md','docs/SPRINT_HISTORY.md','docs/CONTRIBUTIONS.md',
       'docs/VIVA_NOTES.md','docs/REPRODUCIBILITY.md','docs/SUBMISSION_INVENTORY.md','docs/verification/S12.md',
       'scripts/build_final_report.py','scripts/build_final_slides.mjs','scripts/export_final_slides.mjs',
       'scripts/run_demo.py','scripts/verify_final_deliverables.py','scripts/package_final_deliverables.py']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    paths=set(ROOT/name for name in FILES)
    paths.update(p for p in (ROOT/'output').rglob('*') if p.is_file())
    paths.update(p for p in (ROOT/'docs/verification/s12').rglob('*') if p.is_file())
    assert all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT) for p in paths)
    assert not any(p.is_relative_to(out) for p in paths)
    inventory={str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(paths)}
    manifest=dict(format='scholarready-s12-companion-1',files=inventory,
                  scope='Companion academic deliverables. Extract alongside the original S11 core and separate wheels.',
                  core_unchanged=True,final_test_consumed=True,private_data=False,training=False)
    (out/'inventory.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=out/'scholarready-s12-companion.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for source in sorted(paths):z.write(source,'ScholarReady/'+str(source.relative_to(ROOT)))
        z.write(out/'inventory.json','ScholarReady/S12_MANIFEST.json')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for relative,entry in inventory.items():
            data=z.read('ScholarReady/'+relative)
            assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
    report=dict(status='passed',archive=str(archive.relative_to(ROOT)),files=len(inventory),
                bytes=archive.stat().st_size,sha256=digest(archive),all_archived_bytes_verified=True)
    (out/'package.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
