#!/usr/bin/env python3
"""Prepare source-only visual review sheets and duplicate diagnostics; no OCR."""
import argparse
from collections import Counter
from difflib import SequenceMatcher
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from scholarready.dataset import PageAnnotation, read_page, sha256
from scholarready.evaluation.freeze import audit_dataset
from scholarready.pipeline import write_json
from scholarready.splitting import load_records


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    root=Path.cwd(); args.output.mkdir(parents=True,exist_ok=False)
    records=load_records(root/'data/manifests/expanded.jsonl')
    write_json(args.output/'integrity.json',audit_dataset(root,root/'data/manifests/expanded.jsonl',root/'data/manifests/expanded.splits.jsonl'))
    # A sheet is one source plus its derivatives, at 900x1200 pixels per page.
    index={}; pixels={}; texts={}
    for r in records:
        image=read_page(root/r.relative_path,r.page_index)
        ref=PageAnnotation.model_validate_json((root/r.annotation_path).read_text())
        if image.size!=(ref.width,ref.height): raise ValueError('Wrong annotation dimensions')
        if r.variant_id=='clean':
            pixels[r.sample_id]=np.asarray(image.convert('L').resize((96,128)),dtype=float)
            texts[r.sample_id]=ref.full_text
        if r.development_role!='test': continue
        index.setdefault(r.source_document_id,[]).append(r)
    sheets=[]
    for source,items in index.items():
        sheet=Image.new('RGB',(900*len(items),1250),'#e5e7eb'); draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(items):
            image=read_page(root/r.relative_path,1).resize((900,1200))
            sheet.paste(image,(900*i,50)); draw.text((900*i+12,10),r.sample_id,fill='black')
        path=args.output/(source+'.png'); sheet.save(path)
        sheets.append(dict(path=path.as_posix(),sample_ids=[r.sample_id for r in items]))
    candidates=[]; exact_pixels=[]; high_text=[]; ids=list(pixels)
    by_id={r.sample_id:r for r in records}
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if by_id[a].applicant_id==by_id[b].applicant_id: continue
            distance=float(np.mean(np.abs(pixels[a]-pixels[b])))/255
            ratio=SequenceMatcher(None,texts[a],texts[b],autojunk=False).ratio()
            if distance==0: exact_pixels.append([a,b])
            if distance<.01: candidates.append(dict(a=a,b=b,mean_absolute_pixel_distance=distance,text_similarity=ratio,
                cross_partition=by_id[a].development_role!=by_id[b].development_role))
            if ratio>=.98: high_text.append(dict(a=a,b=b,ratio=ratio))
    if exact_pixels or high_text: raise ValueError('Exact image or >=.98 near-text duplicate requires grouping review')
    write_json(args.output/'review_index.json',dict(sheets=sheets,pages=sum(len(v) for v in index.values()),
        reference_transcripts={r.sample_id:json.loads((root/r.annotation_path).read_text()) for r in records if r.development_role=='test'}))
    write_json(args.output/'duplicates.json',dict(exact_reduced_image_pairs=exact_pixels,near_text_threshold=.98,
        high_text_pairs=high_text,pixel_candidate_threshold=.01,pixel_candidates=candidates,
        method='All 108 clean images, 96x128 grayscale mean absolute difference /255; full visible text SequenceMatcher, no OCR. Applicant-matched pairs excluded (already grouped). Candidate similarity is not proof of document identity.',
        candidate_count=len(candidates),cross_partition_candidates=sum(c['cross_partition'] for c in candidates)))
    print(json.dumps(dict(sheets=len(sheets),test_pages=sum(len(v) for v in index.values()),pixel_candidates=len(candidates))))


if __name__=='__main__': main()
