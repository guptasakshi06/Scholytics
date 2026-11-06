#!/usr/bin/env python3
"""Build the S12 academic DOCX from preserved S10 evidence. Use bundled document Python."""
import csv
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/verification/s10/assets'
OUT = ROOT / 'output/report'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin = sec.bottom_margin = Inches(.72)
    sec.left_margin = sec.right_margin = Inches(.8)
    for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption']:
        st = doc.styles[name]
        st.font.name = 'DejaVu Sans'
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.space_after = Pt(8)
    doc.styles['Normal'].font.size = Pt(10)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.13
    doc.styles['Title'].font.size = Pt(27)
    doc.styles['Heading 1'].font.size = Pt(19)
    doc.styles['Heading 2'].font.size = Pt(12)
    doc.styles['Caption'].font.size = Pt(8)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('ScholarReady 042  |  ')
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); footer._p.append(field)
    for r in footer.runs:
        r.font.size = Pt(8)
    source = []
    def p(text, style=None):
        source.append(text)
        return doc.add_paragraph(text, style)
    def h(text):
        source.append(text)
        doc.add_heading(text, 2)
    def fraction(label, numerator, denominator):
        # Native editable Word math, rendered through the normal DOCX QA path.
        para=doc.add_paragraph()
        mathpara=OxmlElement('m:oMathPara');math=OxmlElement('m:oMath')
        def run(parent,text):
            r=OxmlElement('m:r');t=OxmlElement('m:t');t.text=text;r.append(t);parent.append(r)
        run(math,label+' = ')
        frac=OxmlElement('m:f')
        for tag,value in [('num',numerator),('den',denominator)]:
            e=OxmlElement('m:'+tag);run(e,value);frac.append(e)
        math.append(frac);mathpara.append(math);para._p.append(mathpara)
        source.append(f'{label} = ({numerator}) / ({denominator})')
    def page(title):
        if doc.paragraphs:
            doc.add_page_break()
        source.append('\n# ' + title)
        doc.add_heading(title, 1)
    def table(headers, rows, widths=None, size=9):
        t = doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        if widths:
            for col, w in zip(t.columns, widths): col.width=Inches(w)
        for cell, value in zip(t.rows[0].cells, headers): cell.text=str(value)
        for row in rows:
            for cell, value in zip(t.add_row().cells, row): cell.text=str(value)
        for i, row in enumerate(t.rows):
            trpr=row._tr.get_or_add_trPr()
            if i == 0: trpr.append(OxmlElement('w:tblHeader'))
            no_split=OxmlElement('w:cantSplit'); trpr.append(no_split)
            for j, cell in enumerate(row.cells):
                if widths: cell.width=Inches(widths[j])
                cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                pr=cell._tc.get_or_add_tcPr()
                sh=OxmlElement('w:shd'); sh.set(qn('w:fill'), '203B54' if i==0 else ('F1F4F7' if i%2 else 'FFFFFF'));pr.append(sh)
                borders=OxmlElement('w:tcBorders')
                for edge in ['top','left','bottom','right']:
                    b=OxmlElement('w:'+edge);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
                pr.append(borders)
                margins=OxmlElement('w:tcMar')
                for edge in ['top','left','bottom','right']:
                    e=OxmlElement('w:'+edge);e.set(qn('w:w'),'90');e.set(qn('w:type'),'dxa');margins.append(e)
                pr.append(margins)
                for para in cell.paragraphs:
                    para.paragraph_format.space_after=Pt(2)
                    para.paragraph_format.space_before=Pt(2)
                    para.paragraph_format.line_spacing=1.05
                    if j>0:para.alignment=WD_ALIGN_PARAGRAPH.CENTER
                    for r in para.runs:
                        r.font.size=Pt(size);r.bold=i==0;r.font.color.rgb=RGBColor.from_string('FFFFFF' if i==0 else '000000')
        source.append('\n'+' | '.join(headers))
        source.extend(' | '.join(map(str,r)) for r in rows)
        doc.add_paragraph().paragraph_format.space_after=Pt(1)
    def fig(name, caption, maxh=4.4):
        path=ASSETS/name
        with Image.open(path) as im:w,hg=im.size
        width=min(6.55, maxh*w/hg)
        para=doc.add_paragraph();para.alignment=WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next=True
        pic=para.add_run().add_picture(str(path), width=Inches(width))
        pic._inline.docPr.set('descr',caption)
        p(caption, 'Caption')
    rows=list(csv.DictReader((ASSETS/'summary.csv').open()))
    core=[r for r in rows if r['variant'] in ['A','B','C']]

    p('ScholarReady', 'Title')
    p('Scholarship Document Readiness and Missing Requirement Detection using Digital Image Processing and Data Science', 'Subtitle')
    p('Digital Image Processing course project 042')
    p('Project team: Sakshi Gupta and Jigisha Baiswar\nReport date: 6 November 2026')
    p('Roll numbers: NOT PROVIDED\nInstitution and supervisor: NOT PROVIDED\nInstitutional template and final deadline: NOT PROVIDED')
    h('Abstract')
    p('ScholarReady is a local system for checking the readiness of printed English scholarship documents. It rasterizes images and PDFs, compares explicit image preprocessing branches, runs Tesseract OCR, classifies document types, extracts evidence linked to tokens, and applies a fictional configurable checklist. Its outputs describe missing or unresolved requirements and requests for human review. Certificate authentication and scholarship decisions lie outside its scope.')
    p('The frozen synthetic test contains 52 pages from 24 sources in four applicant groups. Original-image branch A, Otsu branch B and full alternative C produced 3, 22 and 50 character edits over 14,900 reference characters. Exact field matches were 161, 153 and 158 of 164 present targets. All routes produced zero false-ready outcomes among 16 reference non-ready bundles. These results support retaining negative preprocessing findings and conservative uncertainty handling. They do not establish accuracy on real applicants.')
    p('Implementation, experiments and this report were prepared with Codex assistance. Actual student review, independent student contributions and sign-off remain unreported. A simple A4 academic format is recommended pending an institutional template.')

    page('1 Problem scope and objectives')
    p('An applicant may supply the wrong document, omit a required item, upload a page whose important text cannot be read, or provide conflicting personal details. A useful readiness checker must distinguish these situations. A plausible OCR value is evidence to inspect, rather than proof that a document is correct.')
    p('The course reference identifies Project 042 as a DIP-linked document-readiness application. The substantive contribution here is an inspectable comparison of image processing alternatives and their downstream effects. This report pairs methods and intermediate images with measured OCR, extraction and application outcomes. The preserved course PDF is the source for course requirements, not for invented dataset sizes or performance targets.')
    h('Implemented scope')
    p('Inputs are local JPG, PNG and PDF documents containing printed English. Supported types are marksheet, income certificate, bonafide certificate, domicile certificate and category certificate. The other class covers observed unsupported examples. An unresolved prediction remains a separate decision state. One fictional scholarship profile requires the first four types and conditionally requires category evidence.')
    h('Research questions')
    p('First, how do A, B and C change OCR and downstream readiness when the keyword classifier, extraction and rules stay fixed? Second, how does the frozen TF-IDF and Logistic Regression classifier compare with keyword classification on exactly the same A OCR? The second comparison changes a downstream component and cannot be attributed to DIP.')
    h('System architecture')
    p('Local files enter bounded ingestion and original-image quality measurement. A selected preprocessing branch yields saved stages and geometry. Tesseract returns text, tokens and boxes. Classification selects supported field rules, extraction retains evidence and normalization decisions, and the JSON checklist assembles requirement states and issues. CLI, evaluation and Streamlit use this same pipeline and ApplicationResult schema.')
    p('No external applicant-document upload, paid inference API, certificate authenticity test, eligibility calculation or award prediction is part of the implemented workflow. The interface exports JSON and a findings CSV. It does not generate this academic report for applicants.')

    page('2 Related work and method foundations')
    p('Otsu introduced histogram-based threshold selection using class separability [1]. This gives a reproducible global binarization baseline. It does not establish that every document benefits from binarization. ScholarReady compares it directly with original-image OCR on the same held-out pages.')
    p('OpenCV documents adaptive thresholding using local neighborhoods [2], local histogram equalization with contrast limiting [3], and morphology with explicit foreground and kernel conventions [4]. These descriptions motivate the alternative chain and its controls. In ScholarReady their utility is an experimental question, assessed using task errors rather than visual darkness alone.')
    p('Smith describes the historical Tesseract OCR architecture [5]. That paper provides background rather than a complete description of the installed 5.3.4 engine. Current Tesseract guidance discusses internal preprocessing, resolution, skew, noise and segmentation choices [6]. Internal processing offers one reason why extra external enhancement may fail to improve OCR, but the present experiment does not isolate its internal mechanisms.')
    p('The scikit-learn documentation explains TF-IDF text features [7], Logistic Regression classification [8], and leakage risks when preprocessing learns from held-out data [9]. ScholarReady fits both vocabulary and weights on clean training-page OCR only. Applicant and source grouping additionally prevents related variants from appearing in separate partitions.')
    h('Position of this project')
    p('This is an academic implementation and bounded evaluation of established components, with explicit uncertainty and evidence tracing. It contributes a shared local pipeline, synthetic provenance, grouped partitions, fixed experiments and negative-result analysis. It does not introduce a new thresholding algorithm or claim superiority over commercial document-processing products. No external scholarship-system benchmark was measured.')
    h('Source interpretation')
    p('References [1] and [5] are research sources. References [2-4] and [6-9] are official implementation guidance. Live OpenCV documentation redirects to a 4.x tutorial while the exercised package is OpenCV headless 5.0.0.93. Algorithm descriptions and the exact tested software environment are distinct. References were checked on 6 November 2026.')

    page('3 Dataset provenance and split design')
    p('Every page is fictional and visibly labelled for academic demonstration. The pilot has 30 sources and 156 pages, including deterministic variants, and remains development-only. The expanded dataset expanded-s09-1.0 adds 108 sources across 18 applicant groups and 234 pages. There are 138 sources in total across both datasets, rather than 390 independent examples.')
    table(['Expanded partition','Applicant groups','Sources','Pages'],[['Train',10,60,130],['Validation',4,24,52],['Test',4,24,52],['Total',18,108,234]],[2.7,1.25,1.1,1.1])
    p('Expanded sources comprise 36 PNG, 36 JPEG and 36 single-page PDF documents. The expanded pages include 108 clean originals, 54 low-contrast variants, 54 rotation variants and 18 erased-amount variants. Four closely related layout families and five kinds of unsupported content provide bounded diversity. The data are smaller and less varied than a real document collection.')
    p('Connected components combine applicant, source and reused content relationships. A source and every derivative retain one partition. The heavily inspected pilot is excluded from the expanded model and experiment. The split predates tuning. TF-IDF and classifier fitting use only 60 clean training pages, with seed 2026.')
    h('Reference review')
    p('All 52 test-page references and 24 bundle expectations received a separate source-only review before production test inference. The same Codex agent inspected visible text, selected fields, roles, units and scenario definitions, without treating pipeline predictions as answers. This is separate checking by one agent, not a second annotator or student sign-off. The other 182 expanded development references remain provisional.')
    p('The test contains 24 clean, 12 low-contrast, 12 rotation and four erased-amount pages. Three known-layout groups supply 39 pages. One reserved-layout group supplies 13 pages from six sources. That reserved layout is a close template variant. Four applicant groups and correlated scenarios do not support population confidence intervals or broad unseen-layout claims. No real or private applicant data are included.')
    p('Evidence: data/manifests/expanded.jsonl, expanded.splits.jsonl, expanded.metadata.json, data/annotations/expanded_review.json and docs/verification/s09/source_review_final/.')

    page('4 Digital image processing methods')
    p('Common ingestion decodes images, applies EXIF orientation, composites transparency onto white, and rasterizes PDF pages at 300 DPI. A preserves that ingested original. Original-image brightness, grayscale standard deviation and Laplacian variance are quality indicators. Their thresholds are heuristics, separate from readiness and completeness.')
    table(['Branch','Enabled sequence'],[['A','Ingested original, OCR'],['B','Grayscale, global Otsu threshold, OCR'],['C','Grayscale, conservative deskew, CLAHE, median filter, Gaussian adaptive threshold, opening then closing, OCR']],[.7,5.85])
    table(['C parameter','Frozen setting'],[['Deskew search','±6 degrees, 0.25 degree step, gain floor 1.05'],['CLAHE','Clip limit 2, 8 by 8 tile grid'],['Median filter','3 by 3 neighborhood'],['Adaptive threshold','31 pixel block, constant 15'],['Morphology','Opening then closing, identity 1 by 1 kernel']],[2,4.55])
    p('Otsu selects one histogram threshold [1,2]. Adaptive thresholding compares intensity with a local Gaussian-weighted mean minus the constant [2]. CLAHE limits local contrast amplification [3]. Median filtering replaces a pixel with its neighborhood median. These operations can remove faint punctuation or change strokes as well as suppress artifacts.')
    p('Morphology operates on inverted white ink internally [4]. Opening is erosion then dilation, and closing is dilation then erosion. Kernel dimensions are height by width. The identity kernel and no-morphology branch are controls. Fixed alternatives use 1 by 2, 2 by 1 and 2 by 2 kernels. Even kernels can shift strokes through their anchor behavior.')
    p('Deskew scores near-horizontal dark text using row projections on a thumbnail and abstains on insufficient or ambiguous evidence. It retains a same-size canvas, so edge content may be cropped. Its homogeneous matrix maps ingested original pixel coordinates to processed coordinates. OCR and field overlays belong on the processed stage. Perspective correction and arbitrary page orientation are outside this method.')

    page('5 Intermediate image evidence')
    fig('C_stages.png','Figure 1. Saved C stages for exp-16-5-rotation. Original, grayscale, deskew, CLAHE, filtering, threshold and morphology remain tied to the S10 run and figure_index.json.',maxh=3.7)
    p('The sequence shows what changed before OCR rather than presenting a single enhanced output. On this receipt A produced zero character edits and C produced four. This associates the error increase with the full chain. It does not establish a separate cause for each character, nor does the darker binary image imply better readability.')
    fig('field_detail_C.png','Figure 2. Processed-coordinate income crop for exp-14-1-rotation. The printed amount remains visible while the C field output is null because its token-score heuristic fails.',maxh=1.8)
    p('A extracted 183914 INR/year for this case. C returned a null value with an explicit review reason. The crop uses reference boxes only for post-evaluation illustration, scaled and mapped through saved geometry. Reference regions are never inference inputs. Full originals, stages, tokens and transforms remain under artifacts/runs/s10-final/.')

    page('6 OCR classification and extraction')
    p('Tesseract 5.3.4 runs locally with English data, OEM 3, PSM 3 and a 20 second page timeout. The comparison keeps these settings and input pages identical. The wrapper preserves ordered text, token boxes, engine scores, language, version, settings, timing and explicit errors. Engine scores are not calibrated probabilities of field correctness.')
    p('The literal-title keyword baseline accepts a single recognized title family, retains ambiguity and recognizes a limited vocabulary for other content. The optional frozen tfidf-lr-s09-1.0 classifier uses word TF-IDF and Logistic Regression with C=4. Validation selected a probability threshold of 0.6 and top-two margin of 0.2. Only clean training A OCR fits vocabulary and weights. No branch-specific retraining occurs.')
    p('The classifier consumes OCR text, not filenames, applicant IDs, layouts or annotation labels. Empty, conflicting or weak predictions retain an unresolved state. The class other covers observed unsupported examples and cannot guarantee rejection of every future unknown. Saved model hashes and dependency versions bind the experiment.')
    h('Evidence linked field extraction')
    p('Label anchors and bounded nearby regions identify candidates using token and line geometry. Type-specific rules normalize dates, names, academic years, amounts and percentages. Each output retains raw text, normalized value or null, unit, person role, page, token references, box, score source and validation reason. Competing candidates remain visible. A generic first-date or first-name fallback is deliberately avoided.')
    table(['Type','Selected fields'],[['Marksheet','Student, institution, academic year, stated total and percentage'],['Income','Applicant and guardian roles, income with unit, issue date'],['Bonafide','Student, institution, course, academic year'],['Domicile','Applicant, region, issue date'],['Category','Applicant, printed category, issue date']],[1.2,5.35])
    p('Monthly amounts stay monthly, ambiguous numeric dates remain unresolved, and missing values never become zero. Extraction coverage is broader than the configured required subset. Optional course errors can lower field accuracy without changing readiness. The separate true-type diagnostic reveals routing effects, even when its counts happen to agree with end-to-end extraction.')

    page('7 Requirements and uncertainty')
    p('The fictional demo JSON defines five named items. Marksheet, income, bonafide and domicile are mandatory. Category applies only when the explicit applicant attribute is true. False makes it not applicable. Unknown preserves a review requirement and an unresolved completeness denominator. No real income limit, certificate expiry or award policy is inferred.')
    table(['Requirement state','Meaning'],[['satisfied','Resolved supported evidence covers configured required checks'],['missing','Inventory supports confirmed absence'],['unreadable','A relevant required value cannot be resolved'],['needs_review','Ambiguity, conflicts, unresolved inventory or applicability'],['not_applicable','A condition explicitly resolves to false']],[1.35,5.2])
    p('An unclassified upload might be the needed document, so it must not automatically establish absence. User-declared type hints remain recorded hints. Conflicting duplicate values require review. Separate incomplete files are not spliced into invented complete evidence. Matching person roles matters: a guardian name must not be compared as an applicant name.')
    h('Scores and precedence')
    fraction('Completeness','100 × satisfied applicable items','applicable items')
    p('Only resolved not-applicable items leave the denominator. Unknown applicability or an empty unresolved denominator produces null with an explanation. Quality flags do not increase completeness. A high score cannot override an unresolved required check.')
    p('The headline precedence is needs_review, then needs_clearer_upload, then incomplete, then ready. Every item and issue remains visible beneath that headline. Thus several problems can coexist. A processing failure remains explicit rather than silently becoming an empty successful result.')
    p('The default checklist requires a documented field subset: see configs/scholarship_demo.json for the complete authoritative definition. Readiness means that this fictional checklist is resolved under the implemented evidence rules. It does not certify truth, identity, eligibility or approval.')

    page('8 Experimental protocol and metrics')
    p('The immutable evaluation-s09-1.1 freeze binds 780 artifacts including configuration, source, model, splits, references and environment. The final test was consumed on 4 November 2026 at 22:11:17 Asia/Kolkata. S10 preserved a fresh all-variant experiment and a separate replay from saved OCR. S12 reports those results without retuning or replacing them.')
    p('All 12 preprocessing variants use the same 52 test pages. The primary routes fix keyword-1.0, spatial-s06-1.0 and requirements-s07-1.0. The A learned route adds the separate classification comparison, giving 13 routes. Every route evaluates the same 24 correlated bundle scenarios and 120 requirement items. Failed or empty outputs would remain in denominators. None occurred in this final set.')
    h('Definitions')
    fraction('CER','character edit distance','reference characters')
    fraction('WER','word edit distance','reference words')
    p('Normalization is NFC, case folding and collapsed whitespace, fixed before test inference. An empty-reference rate is null, while its edits remain in corpus totals. Rates can exceed one if insertions dominate.')
    p('Classification macro-F1 averages F1 over six fixed classes. Unresolved predictions remain false negatives and appear as a separate confusion column. A missing class has zero F1 under the frozen zero-division convention. Field accuracy requires exact normalized value, unit and person role over every present target. Missing, wrong nonnull, absent, extra and unreadable-reference cases are distinct.')
    p('Confirmed missing is the positive label for requirement precision, recall and F1. Other requirement states remain in the complete state-confusion table. Application agreement compares the full four-state headline. False-ready rate = reference non-ready applications predicted ready / all reference non-ready applications. Empty denominators mean not estimable. Raw counts accompany every rate.')
    p('Page timings include decode/render, quality, stages and saves, OCR and baseline downstream work, excluding model load and final JSON writes. Bundle timings reuse OCR and measure rules rather than upload latency. Sequential single observations with uncontrolled OS cache cannot establish speed superiority. No confidence interval or significance test is claimed from four groups.')
    p('Freeze SHA256: 40d9bc375ed4240d7a0ef3b66e904157ae81f07329261208081856617ec53773. Full provenance: docs/verification/s09/freeze.json and docs/verification/s10/run_registry.json.')

    page('9 Core frozen results')
    table(['Route','Char edits','CER %','Word edits','WER %','Fields /164'],[[r['variant']+'/'+r['route'],r['character_edits'],f"{100*float(r['cer']):.4f}",r['word_edits'],f"{100*float(r['wer']):.4f}",r['exact_fields']] for r in core],[1.45,.8,.85,.8,.85,1.4])
    p('Table 1. Identical 52 pages, 14,900 reference characters and 2,092 words. The A learned route reuses exactly the same A OCR. All figures come from the original S10 summary.csv and route metric JSONs.', 'Caption')
    p('A has the fewest OCR edits among the three core branches. C increases character and word errors relative to A. A and A learned have 161 exact present fields, two missing or invalid outputs, and one wrong nonnull output. B has 153 exact, nine missing and two wrong. C has 158 exact, six missing and zero wrong nonnull. Four erased income amounts are unreadable references outside the 164 present-target denominator.')
    table(['Route','Macro F1','Unresolved /52','Headlines /24','Items /120'],[[r['variant']+'/'+r['route'],f"{float(r['macro_f1']):.6f}",r['unresolved'],r['application_matches'],r['requirement_matches']] for r in core],[1.55,1.05,1.3,1.25,1.0])
    p('Table 2. Unresolved classification remains in macro-F1 accounting. Full per-class and outcome confusions remain in the original metric files.', 'Caption')
    p('The learned model improves the observed unsupported classification cases but leaves field extraction unchanged. Keyword abstentions concern unsupported documents without supported field targets, explaining why true-type and predicted-type field exact counts agree here. This equality is dataset-specific.')
    p('Headline agreement alone hides field errors: A and C agree on every bundle headline despite imperfect extraction. The wrong course capitalization is optional under the configured checklist. A future policy that required more fields could behave differently and would need separate evaluation.')

    page('10 Classification and field support')
    fig('classification_A.png','Figure 3. Frozen A keyword and learned confusion matrices. Rows are reference classes and columns are predictions, including unresolved. Source classification_A.png and per-class CSV.',maxh=3.1)
    p('Supported page counts are marksheet 8, income 12, bonafide 8, domicile 8 and category 8. The other class has eight pages. Keywords resolve all 44 supported pages and four other pages. Four unsupported title cases abstain, leaving other recall 0.5 and F1 0.666667. Learned A resolves all eight observed other pages. These limited examples cannot calibrate open-set rejection.')
    fieldrows=list(csv.DictReader((ASSETS/'fields_per_type.csv').open()))
    names=['marksheet','income_certificate','bonafide_certificate','domicile_certificate','category_certificate']
    ft=[]
    for name in names:
        sel=[r for r in fieldrows if r['variant']=='A' and r['route']=='keyword' and r['field_route']=='fields_predicted_type' and r['field'].startswith(name+':')]
        ft.append([name.replace('_certificate',''),sum(int(r['present_support']) for r in sel),sum(int(r['exact_value_unit_role']) for r in sel),sum(int(r['unreadable_reference_support']) for r in sel)])
    table(['A field type','Present targets','Exact','Unreadable refs'],ft,[2.45,1.4,1.05,1.25])
    p('Table 3. Aggregated per-field support for A keyword. Full field-by-field true-type and predicted-type counts, including unit and role checks, remain in fields_per_type.csv.', 'Caption')

    page('11 Ablations and morphology harm')
    labels={'C_no_deskew':'No deskew','C_no_clahe':'No CLAHE','C_no_filter':'No filter','C_no_threshold_or_morphology':'No threshold or morphology','C_no_morphology':'No morphology','C_gray_only':'Grayscale only','C_kernel_1x2':'Kernel 1 by 2','C_kernel_2x1':'Kernel 2 by 1','C_kernel_2x2':'Kernel 2 by 2'}
    ab=[r for r in rows if r['route']=='keyword']
    table(['Preprocessing variant','Char edits','Word edits','Fields /164','Headlines /24'],[[labels.get(r['variant'],r['variant']),r['character_edits'],r['word_edits'],r['exact_fields'],r['application_matches']] for r in ab],[2.6,.85,.85,1.1,.85],size=8)
    p('Table 4. All 12 predeclared preprocessing variants. Removing threshold also removes its dependent binary morphology. This coupled control cannot isolate threshold alone.', 'Caption')
    p('The no-threshold diagnostic has zero edits and all 164 fields correct here. It was not eligible in the bounded validation kernel selection and cannot replace frozen C after test inspection. Any changed method requires development selection and a new confirmatory holdout.')
    p('Identity morphology and no morphology agree exactly. Nonidentity kernels increase errors, with 2 by 2 reducing headlines to 18/24 and fields to 142/164. Removing filtering lowers character edits but increases word edits and reduces headline agreement. Aggregate changes show interactions, not universal benefits for individual steps.')

    page('12 Readiness and false ready analysis')
    table(['Reference headline','Bundles'],[['ready',8],['incomplete',4],['needs_clearer_upload',4],['needs_review',8]],[4.4,2.15])
    table(['Route','Headline agreement','Predicted ready','False ready / nonready'],[[r['variant']+'/'+r['route'],r['application_matches']+'/24',r['predicted_ready'],r['false_ready']+'/'+r['reference_nonready']] for r in core],[1.55,1.55,1.25,2.2])
    p('Table 5. The predeclared false-ready denominator is 16 reference non-ready bundles in every route. Correlated bundle variants from four applicant groups do not give 24 independent applicants.', 'Caption')
    p('All 13 routes have confirmed-missing TP=4, FP=0, FN=0 and TN=116. Precision, recall and F1 are 1.0 across 120 requirement items. This binary result does not capture false unreadable or review outcomes. The complete state and headline confusions must accompany it.')
    p('A keyword, A learned and C match every headline and item state. B matches 22 headlines and 117 item states. In the applicant-17 income example, OCR text is correct but the fixed confidence heuristic rejects the value. Two ready-reference bundles request a clearer upload. A third item disagreement occurs under an already-review headline.')
    p('The no-filter ablation matches 20/24 headlines and 115/120 item states. Kernel 2 by 2 matches 18/24 headlines, 106/120 item states and 16/24 completeness values, while still producing zero false-ready outcomes. Thus zero observed false ready can coexist with excessive rejection and wrong extracted values.')
    p('Zero of 16 is a measured count for these scenarios. It is not a population guarantee, safety certification or evidence that certificates are genuine. The separate share among predicted-ready cases also has zero numerators, but different denominators. An empty denominator would be null rather than a fabricated zero.')

    page('13 Success and failure examples')
    fig('success.png','Figure 4. exp-14-0-clean preserves 79.25 under A, B and C with zero OCR edits. This is an observed agreement case, not an invented C improvement.',maxh=2.6)
    fig('field_detail_C_kernel_2x2.png','Figure 5. exp-14-0-low_contrast after kernel 2 by 2. Academic-year confidence fails and the full-page case changes total 804 into valid-looking 604. Original-to-processed mapped crop, post-evaluation only.',maxh=1.8)
    p('The full kernel panel records zero character edits under A and 12 under kernel 2 by 2 for this low-contrast marksheet. A darker image can still lose characters, break label recognition or create a format-valid incorrect number. The original field output and error row retain this mistake.')
    p('For exp-15-2-rotation, A and B extract BSC Chemistry for printed BSc Chemistry. Frozen exact normalization counts this as one wrong nonnull value. No post-test case folding was added to improve the score. In exp-14-1-no_amount, the surviving text is recognized but the erased amount remains null. OCR agreement on visible text cannot recover erased information.')

    page('14 Runtime limitations and conclusion')
    table(['Core page batch','Batch seconds','OCR seconds','DIP seconds'],[[r['variant'],f"{float(r['page_seconds']):.3f}",f"{float(r['ocr_seconds']):.3f}",f"{float(r['preprocessing_seconds']):.3f}"] for r in core if r['route']=='keyword'],[2,1.5,1.5,1.55])
    p('Table 6. Original S10 observations on the same 52-page batch. The whole fresh all-variant experiment took 327.128 seconds. Bundle-rule times reuse saved OCR and are not full application latency.', 'Caption')
    p('The tested host uses Ubuntu 24.04.4 x86_64 and CPython 3.12.3. Exact environment and processor records are preserved with S10/S11 evidence. Sequential runs did not control cold caches, CPU scheduling or competing workload. The timings support reproducibility and workload description, not a speed ranking.')
    h('Limits and future work')
    p('Only synthetic English printed pages and a small number of related templates were evaluated. There is no final real-document, multipage, corrupt-input, blur or conflicting-duplicate benchmark. Development tests exercise several of those behaviors but cannot replace held-out support. Reference checking used the same agent rather than independent annotators. Most expanded development annotations remain provisional. Confidence scores and image-quality flags remain heuristic.')
    p('Future extensions could collect consented diverse local data, use independent annotation review, assess calibration and abstention costs, and compare revised preprocessing on a new untouched grouped holdout. Perspective, multilingual text and handwritten forms require separate methods and evidence. None of these extensions has been implemented or measured here.')
    h('Conclusion')
    p('ScholarReady demonstrates a reproducible local DIP and Data Science pipeline with evidence-linked readiness findings. The core experiment rejects the assumption that more preprocessing necessarily helps OCR. A performed best among A/B/C on this synthetic test, while learned A improved observed unsupported classification. Conservative rules preserved unresolved evidence and produced zero observed false-ready cases, with visible rejection errors and strict limits on generalization.')

    page('15 Reproduction and handover')
    p('The S11 source and frozen-evidence archive and separate Linux wheel archive remain the reproduction package. The S12 deliverables are a companion bundle containing this report, the slides, fictional demo inputs and viva notes. The original S11 archive predates these academic deliverables. Source-only Git omits required large model and media artifacts.')
    h('Local commands from the project root')
    for cmd in [
        '.venv/bin/python scripts/check_environment.py',
        'MPLCONFIGDIR=/tmp/scholarready-matplotlib .venv/bin/python scripts/reproduce.py --mode smoke',
        '.venv/bin/python scripts/reproduce.py --mode final',
        '.venv/bin/python scripts/run_demo.py --output artifacts/runs/my-demo',
        '.venv/bin/python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --server.port 8501',
    ]:
        para=p(cmd);para.paragraph_format.line_spacing=1
        for r in para.runs:r.font.name='DejaVu Sans Mono';r.font.size=Pt(8)
    p('Use a new output directory for each run. Smoke runs real development OCR and loads the frozen model without final-test access. Final mode checks existing artifacts and recomputes all 13 routes from saved OCR. It neither trains nor creates a new final performance experiment. Final test consumed remains YES. See docs/REPRODUCIBILITY.md for exact offline installation and verified OS constraints.')
    h('Contributions and pending administration')
    p('Codex performed the recorded implementation, synthetic-data generation, experiment execution, verification and academic artifact preparation. Sakshi Gupta and Jigisha Baiswar are the project team. No completed student implementation, review, reproduction, mastery or approval has been reported. Suggested learning leads are DIP/geometry for Sakshi and classification/extraction/rules for Jigisha, with both reviewing the entire system.')
    p('Both students receive the full-pipeline viva notes and a timed demo script. They should check the evidence, run the demo, explain the negative results in their own words and record actual contributions before submission. Roll numbers, institution, supervisor, final template, approved-title refinements and deadline remain NOT PROVIDED. No project artifact has been published or submitted externally.')

    page('16 References and evidence index')
    refs=[
        '[1] N. Otsu. A Threshold Selection Method from Gray-Level Histograms. IEEE Transactions on Systems, Man, and Cybernetics 9(1), 62-66, 1979. doi:10.1109/TSMC.1979.4310076. https://ieeexplore.ieee.org/document/4310076',
        '[2] OpenCV. Image Thresholding. Official tutorial. https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html',
        '[3] OpenCV. Histograms 2 Histogram Equalization. Official tutorial, CLAHE section. https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html',
        '[4] OpenCV. Morphological Transformations. Official tutorial. https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html',
        '[5] R. Smith. An Overview of the Tesseract OCR Engine. ICDAR 2007, 629-633. https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/',
        '[6] Tesseract. Improving the quality of the output. Official tessdoc. https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html',
        '[7] Scikit-learn. Feature extraction, text features and TF-IDF. https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction',
        '[8] Scikit-learn. Logistic regression. https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression',
        '[9] Scikit-learn. Common pitfalls and recommended practices. https://scikit-learn.org/stable/common_pitfalls.html',
    ]
    for ref in refs:
        para=p(ref);para.paragraph_format.space_after=Pt(6)
        for run in para.runs:run.font.size=Pt(8.5)
    p('Research and official documentation checked 6 November 2026. These sources support method explanations, not the project performance numbers. Otsu metadata and an accessible copy of the original paper were checked. No related-work benchmark number is reused as a ScholarReady result.', 'Caption')
    h('Local evidence index')
    p('Course: docs/reference/DIP_Course_Project_Guidelines_2026.pdf. Protocol: docs/EVALUATION_PROTOCOL.md and configs/evaluation.json. Results: docs/verification/s10/assets/summary.csv, tables.md, classification_per_class.csv, fields_per_type.csv, pages.csv, bundles.csv and errors.json. Figure origins and hashes: figure_index.json and asset_hashes.json in that directory. Interpretation: docs/ERROR_ANALYSIS.md. Reproduction: docs/REPRODUCIBILITY.md. Review/contributions: docs/CONTRIBUTIONS.md. Continuation: HANDOFF.md.')
    page('Appendix A Bounding box evidence')
    path=ROOT/'docs/verification/s06/processed_C_evidence.png'
    para=doc.add_paragraph();para.alignment=WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.keep_with_next=True
    pic=para.add_run().add_picture(str(path),width=Inches(5.6))
    pic._inline.docPr.set('descr','Green OCR evidence boxes on processed C fictional development income page')
    p('Figure 6. Processed C development image with green OCR-token evidence boxes. Source docs/verification/s06/processed_C_evidence.png, documented in docs/verification/S06.md. This is development evidence, separate from the frozen final-test results.', 'Caption')
    p('The visible page distinguishes the father from the applicant, date of birth from issue and expiry dates, and monthly from annual income. Green boxes identify selected evidence on the processed image. A box identifies where OCR evidence came from, not whether the text is correct. Preserve the original-to-processed mapping when interpreting any overlay.')
    p('The printed monthly amount stays monthly. The extractor does not silently annualize it or compare the guardian role as if it were the applicant. Full candidates and normalization reasons accompany fields in the structured result. No annotation region or expected value supplied this inference.')
    doc.core_properties.title='ScholarReady document readiness report'
    doc.core_properties.author='Codex assisted preparation for Sakshi Gupta and Jigisha Baiswar'
    doc.core_properties.subject='Project 042 synthetic evaluation and reproducible local pipeline'
    # The bundled default Word template may carry a blue paragraph rule in Title.
    for tree in [doc._element, doc.styles.element]:
        for border in tree.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    doc.save(OUT/'ScholarReady_Report.docx')
    (OUT/'report_source.txt').write_text('\n\n'.join(source)+'\n',encoding='utf-8')
    evidence={'summary_sha256':hashlib.sha256((ASSETS/'summary.csv').read_bytes()).hexdigest(),
              'metrics':rows,'field_type_A':ft,'report_sections':16,'expected_pages':18,
              'source':'artifacts/runs/s10-final','test_consumed':True,'new_experiment':False}
    (ROOT/'docs/verification/s12/report_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(OUT/'ScholarReady_Report.docx')


if __name__=='__main__':
    build()
