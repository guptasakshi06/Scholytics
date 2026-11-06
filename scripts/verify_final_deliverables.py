#!/usr/bin/env python3
"""Audit S12 document/slide tables against frozen CSVs and check local deliverables."""
import csv
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tables(root,kind):
    tag='w' if kind=='docx' else 'a'
    return [[[ ''.join(t.text or '' for t in tc.findall(f'.//{tag}:t',NS))
               for tc in tr.findall(f'{tag}:tc',NS)] for tr in tb.findall(f'{tag}:tr',NS)]
            for tb in root.findall(f'.//{tag}:tbl',NS)]


def main():
    rows=list(csv.DictReader((ROOT/'docs/verification/s10/assets/summary.csv').open()))
    evidence=json.loads((ROOT/'docs/verification/s12/report_evidence.json').read_text())
    assert evidence['metrics']==rows
    core=[r for r in rows if r['variant'] in ['A','B','C']]
    report=ROOT/'output/report/ScholarReady_Report.docx'
    with zipfile.ZipFile(report) as z:
        xml=ET.fromstring(z.read('word/document.xml'));dt=tables(xml,'docx')
        assert len(xml.findall('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath'))==3
        assert not xml.findall('.//w:pBdr',NS)
        report_images=[n for n in z.namelist() if n.startswith('word/media/')]
        assert len(report_images)==6
    checks=[]
    def check(name,actual,expected):
        assert actual==expected,(name,actual,expected)
        checks.append(name)
    check('report core OCR/fields',dt[5][1:],[[r['variant']+'/'+r['route'],r['character_edits'],f"{float(r['cer'])*100:.4f}",r['word_edits'],f"{float(r['wer'])*100:.4f}",r['exact_fields']] for r in core])
    check('report classification/application',dt[6][1:],[[r['variant']+'/'+r['route'],f"{float(r['macro_f1']):.6f}",r['unresolved'],r['application_matches'],r['requirement_matches']] for r in core])
    check('report per-type field counts',dt[7][1:],[[str(v) for v in r] for r in evidence['field_type_A']])
    check('report all ablation counts',[r[1:] for r in dt[8][1:]],[[r['character_edits'],r['word_edits'],r['exact_fields'],r['application_matches']] for r in rows if r['route']=='keyword'])
    check('report false-ready counts',dt[10][1:],[[r['variant']+'/'+r['route'],r['application_matches']+'/24',r['predicted_ready'],r['false_ready']+'/'+r['reference_nonready']] for r in core])
    check('report runtime',dt[11][1:],[[r['variant'],f"{float(r['page_seconds']):.3f}",f"{float(r['ocr_seconds']):.3f}",f"{float(r['preprocessing_seconds']):.3f}"] for r in core if r['route']=='keyword'])
    pptx=ROOT/'output/presentation/ScholarReady_Slides.pptx'
    with zipfile.ZipFile(pptx) as z:
        st={n:tables(ET.fromstring(z.read(f'ppt/slides/slide{n}.xml')),'pptx') for n in range(1,13)}
        assert len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])==12
        assert len([n for n in z.namelist() if n.startswith('ppt/media/')])==6
        assert all(f'ppt/notesSlides/notesSlide{n}.xml' in z.namelist() for n in range(1,13))
        check('slides core OCR/fields',st[6][0][1:],[[r['variant']+'/'+r['route'],r['character_edits'],r['word_edits'],r['exact_fields']] for r in core])
        check('slides all ablation counts',[r[1:] for t in st[8] for r in t[1:]],[[r['character_edits'],r['exact_fields']] for r in rows if r['route']=='keyword'])
        check('slides false-ready counts',st[9][0][1:],[[r['variant']+'/'+r['route'],r['application_matches'],r['predicted_ready'],r['false_ready']+'/'+r['reference_nonready']] for r in core])
        check('slides split counts',st[3][0][1:],[['Train','10','60','130'],['Validation','4','24','52'],['Test','4','24','52']])
    pdf_counts={}
    for rel,n in [('output/report/ScholarReady_Report.pdf',18),('output/presentation/ScholarReady_Slides.pdf',12)]:
        reader=PdfReader(ROOT/rel);assert len(reader.pages)==n
        assert all(page.extract_text().strip() for page in reader.pages)
        pdf_counts[rel]=len(reader.pages)
    fallback=ROOT/'output/demo/rehearsal_results'
    rehearsal=json.loads((fallback/'rehearsal.json').read_text());assert rehearsal['passed']
    assert len(rehearsal['cases'])==4 and all(r['passed'] for r in rehearsal['cases'])
    for row in rehearsal['cases']:
        result=json.loads((fallback/(row['case']+'.json')).read_text())
        assert result['overall_state']==row['state'] and result['completeness']==row['completeness']
    links=0
    for path in list((ROOT/'output').rglob('*.md'))+[ROOT/'docs/VIVA_NOTES.md']:
        text=path.read_text();assert text.count('```')%2==0
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links+=1
    protected=json.loads((ROOT/'docs/verification/s12/protected_before.json').read_text())
    assert all((ROOT/p).is_file() and digest(ROOT/p)==sha for p,sha in protected.items())
    report=dict(status='passed',table_comparisons=checks,pdf_pages=pdf_counts,report_figures=6,
                native_math=3,slides=12,native_slide_tables=sum(len(v) for v in st.values()),
                pptx_embedded_images=6,pptx_speaker_notes=12,demo_cases=4,local_links=links,
                protected_files_unchanged=len(protected),
                limitations='Table/data/package checks complement recorded visual and narrative review. No native PowerPoint or student sign-off claim.')
    (ROOT/'docs/verification/s12/deliverable_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
