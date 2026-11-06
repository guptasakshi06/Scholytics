// S12 slide authoring for Artifact Session. Runtime-only dependency, no application changes.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ASSETS=path.join(ROOT,'docs/verification/s10/assets');
export async function buildSlides(pres) {
  const summary=JSON.parse(await fs.readFile(path.join(ROOT,'docs/verification/s12/report_evidence.json'),'utf8'));
  const rows=summary.metrics;
  const core=rows.filter(r=>['A','B','C'].includes(r.variant));
  const font='DejaVu Sans';
  pres.theme.defaultFont=font;
  const text=(s,value,x,y,w,h,size=28,color='#142D41',bold=false)=>{
    const q=s.shapes.add({geometry:'textbox',name:value.slice(0,45),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
    q.text=value;q.text.style={typeface:font,fontSize:size,color,bold};return q;
  };
  const slide=(title,notes)=>{
    const s=pres.slides.add();s.background.fill='#FFFFFF';
    text(s,title,64,40,1152,100,44,'#142D41',true);
    text(s,String(pres.slides.items.length).padStart(2,'0'),1150,674,65,27,18,'#556674');
    s.speakerNotes.text=notes;return s;
  };
  const table=(s,values,x,y,w,h,widths,size=25)=>{
    const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
    t.borders.assign({fill:'#CCD6DF',width:1,style:'solid'});
    for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
      const cell=t.getCell(r,c);cell.fill=r===0?'#183B54':(r%2?'#F0F4F7':'#FFFFFF');
      cell.text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':'#142D41',bold:r===0};
    }
    return t;
  };
  const image=async(s,name,x,y,w,h)=>{
    const data=await fs.readFile(path.join(ASSETS,name));
    s.images.add({blob:data,contentType:'image/png',alt:'Preserved S10 evidence '+name,fit:'contain',position:{left:x,top:y,width:w,height:h}});
  };
  let s=slide('ScholarReady','20 seconds. Project 042. Full title: Scholarship Document Readiness and Missing-Requirement Detection using Digital Image Processing and Data Science. Team: Sakshi Gupta and Jigisha Baiswar. Codex assisted implementation and preparation. Student review/sign-off unreported. Roll numbers, institution, supervisor and deadline NOT PROVIDED. Source: HANDOFF.md, docs/CONTRIBUTIONS.md.');
  text(s,'Scholarship document readiness',64,208,1100,88,56,'#142D41',true);
  text(s,'Digital Image Processing and Data Science\nProject 042',64,319,1050,108,32);
  text(s,'Sakshi Gupta and Jigisha Baiswar\n6 November 2026',64,505,1050,100,26,'#41576A');

  s=slide('Local evidence and readiness','35 seconds. Explain input to result. Shared source: src/scholarready/pipeline.py, schemas.py, requirements.py and app/streamlit_app.py. No UI-only requirement rules. No manual OCR correction. This fictional checklist describes readiness and does not authenticate certificates, determine eligibility or predict awards.');
  text(s,'1  Image or PDF ingestion and original quality measures\n2  Selected DIP branch and local Tesseract OCR\n3  Document class and spatial field evidence\n4  JSON requirements and unresolved issues\n5  Shared CLI, evaluation and Streamlit result',64,170,1150,330,32);
  text(s,'Printed English, five supported types and other\nFictional checklist with explicit category applicability',64,542,1140,95,27,'#41576A');

  s=slide('Synthetic data and grouped partitions','40 seconds. Source: data/manifests/expanded.metadata.json, expanded.splits.jsonl, data/annotations/expanded_review.json. Expanded-s09-1.0 has108 sources/234 pages/18 applicants. Original pilot30 sources/156 pages remains development-only. Every source/variant/applicant component keeps one split. 60 clean training pages fit TF-IDF and LR. Test52 pages/24 sources/four groups source-reviewed in a separate same-agent pass, no second annotator/student sign-off. Reserved layout13 pages/one close-template group.');
  table(s,[['Partition','Groups','Sources','Pages'],['Train','10','60','130'],['Validation','4','24','52'],['Test','4','24','52']],64,167,1150,278,[430,240,240,240],30);
  text(s,'All test references checked before inference\n24 correlated bundle scenarios across four applicants\nOne reserved layout family is a close template variant',64,484,1145,140,28);

  s=slide('Fixed image processing branches','45 seconds. Source: configs/evaluation.json and src/scholarready/preprocessing.py. Otsu global threshold versus adaptive local Gaussian mean minus constant: https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html. CLAHE clip2/grid8, median3, adaptive31/C15, identity1x1 opening then closing. Deskew±6 degrees with0.25 steps and heuristic abstention. https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html and https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html. Black ink is inverted internally. Pixel matrix maps original to processed.');
  table(s,[['Branch','Enabled operations'],['A','Ingested original'],['B','Grayscale and Otsu threshold'],['C','Grayscale, deskew, CLAHE, median,\nadaptive threshold, opening then closing']],64,166,1150,320,[145,1005],27);
  text(s,'Same 52 pages and OCR settings\nTesseract 5.3.4, eng, OEM 3, PSM 3\n300 DPI PDF rendering and 20 second OCR timeout',64,520,1145,130,27);

  s=slide('Saved processing stages','30 seconds. Source: docs/verification/s10/assets/figure_index.json C_stages. Four upper-page crops of seven original saved stages for exp-16-5-rotation. Full seven-stage sheet is in the report. Cropping is display-only, same region for all stages, no inference annotation. A0 edits/C4. Both keyword predictions unresolved. Resampling and binarization can change small print. The panel associates the full processing chain with errors and does not isolate each character cause.');
  const stageIndex=JSON.parse(await fs.readFile(path.join(ASSETS,'figure_index.json'),'utf8')).C_stages;
  for(const [i,j] of [0,2,3,5].entries()){
    const name=['Original','Deskew','CLAHE','Adaptive'][i];
    text(s,name,64+i*294,161,266,42,27,'#142D41',true);
    const data=await fs.readFile(path.join(ROOT,stageIndex[j].path));
    s.images.add({blob:data,contentType:'image/png',alt:name+' upper-page crop, same display region',fit:'contain',crop:{left:.04,right:.25,top:.02,bottom:.58},position:{left:64+i*294,top:215,width:266,height:285}});
  }
  text(s,'Four of seven saved stages, receipt exp-16-5-rotation\nA has 0 character edits, C has 4\nDarker text does not establish better OCR',64,542,1145,116,27);

  s=slide('C increased OCR errors on this test','45 seconds. Source: docs/verification/s10/assets/summary.csv, run/{A,B,C}/*_metrics.json. Identical14900 characters/2092 words, no processing failures or empty predictions. CER percent: A0.0201 B0.1477 C0.3356. WER percent:A0.1912 B1.0516 C2.1989. Exact field matches include value/unit/role. Four unreadable reference amounts excluded from164 present targets and retained separately. Learned A uses same OCR and fields.');
  table(s,[['Route','Char edits','Word edits','Fields /164'],...core.map(r=>[r.variant+'/'+r.route,r.character_edits,r.word_edits,r.exact_fields])],64,164,1150,325,[370,260,260,260],29);
  text(s,'14,900 reference characters and 2,092 words\nA/B/C CER  0.0201% / 0.1477% / 0.3356%\n52 synthetic pages from 24 sources and four groups',64,525,1145,135,27);

  s=slide('Classification and field evidence','45 seconds. Six fixed labels include other. Source: docs/verification/s10/assets/classification_per_class.csv, fields_per_type.csv. Keyword macro-F1 .944444, learned1.0. All44 supported pages classified, keyword other4/8 correct and4 unresolved; learned8/8. True-type and predicted-type field totals agree because unsupported abstentions lack supported targets. Learned model train-only60 clean pages, C4,p0.6/margin0.2. No calibrated probability claim. Figure field_detail_C.png exp-14-1-rotation, reference crop for post-evaluation illustration only.');
  text(s,'Keyword macro-F1 0.944444\nLearned A macro-F1 1.000000\nOther recall rises from 4/8 to 8/8',64,163,1150,145,31);
  await image(s,'field_detail_C.png',64,330,1150,175);
  text(s,'A extracts 183914 INR/year\nC leaves the value null after its token-score check\nModel and OCR scores remain uncalibrated',64,535,1145,116,27);

  const labels={C_no_deskew:'No deskew',C_no_clahe:'No CLAHE',C_no_filter:'No filter',C_no_threshold_or_morphology:'No threshold or morphology',C_no_morphology:'No morphology',C_gray_only:'Grayscale only',C_kernel_1x2:'Kernel 1 by 2',C_kernel_2x1:'Kernel 2 by 1',C_kernel_2x2:'Kernel 2 by 2'};
  s=slide('Every predeclared ablation remains visible','50 seconds. Source: summary.csv. Twelve preprocessing variants plus A learned give13 routes. Every row has same52 pages. No-threshold-or-morphology is coupled, not threshold alone. Diagnostic0 edits/164 fields is not promoted to frozen C after testing. Requires fresh development selection and confirmatory holdout. Identity1x1 and no morphology match. No per-page oracle.');
  const ab=rows.filter(r=>r.route==='keyword').map(r=>[labels[r.variant]??r.variant,r.character_edits,r.exact_fields]);
  table(s,[['Variant','Edits','Fields'],...ab.slice(0,6)],64,164,550,390,[340,95,115],23);
  table(s,[['Variant','Edits','Fields'],...ab.slice(6)],664,164,550,390,[340,95,115],23);
  text(s,'Character edits / 14,900 and exact fields / 164\nZero-edit diagnostic needs a new untouched evaluation',64,604,1110,70,24);

  s=slide('False ready is zero in 16 nonready bundles','45 seconds. Source: summary.csv and each route readiness JSON. Reference8 ready/4 incomplete/4 clearer/8 review. All13 routes false-ready0/16. Missing TP4 FP0 FN0 TN116 across120 items; P/R/F1 all1 but these ignore false unreadable/review. B22/24, no-filter20/24, kernel2x218/24 headline agreement. Zero false ready does not establish population safety. Unknown category yields review/null denominator.');
  table(s,[['Route','Headlines /24','Predicted ready','False ready'],...core.map(r=>[r.variant+'/'+r.route,r.application_matches,r.predicted_ready,r.false_ready+'/'+r.reference_nonready])],64,164,1150,305,[350,270,280,250],27);
  text(s,'Missing precision, recall and F1 are 1.0 on 120 items\nKernel 2 by 2 still agrees on only 18/24 headlines\nCorrelated synthetic cases do not establish real-world risk',64,515,1145,142,27);

  s=slide('Morphology can discard readable fields','35 seconds. Source: field_detail_C_kernel_2x2.png and kernel_largest_change.png; exp-14-0-low_contrast. A0 character edits and kernel2x212. This crop shows the academic year token-score rejection. The separate full-page case also changes printed total804 into604. Selected after evaluation for explanation, not a representative frequency estimate. Other failure: frozen normalization counts BSC vs BSc Chemistry wrong, no post-test fix.');
  await image(s,'field_detail_C_kernel_2x2.png',64,170,1150,310);
  text(s,'Kernel 2 by 2 rejects the readable academic year\nStroke changes can also corrupt numeric values\nRaw text, boxes and uncertainty stay inspectable',64,526,1145,120,29);

  s=slide('Four minute fictional demonstration','20 second introduction, then four minute CLI walkthrough. See output/demo/DEMO_SCRIPT.md. Real rehearsal artifacts/runs/s12-demo-rehearsal,4/4 outcomes passed in9.327s computation. Allocation includes narration and evidence inspection. BranchA keyword, category true, expected name Fictional Aster. No OCR correction, no final-test input. Saved results are a labelled fallback, not live inference or a prerecorded video. Student timing not measured.');
  table(s,[['Case','Automatic headline','Completeness'],['Complete','ready','100%'],['Missing income','incomplete','80%'],['Unreadable amount','needs_clearer_upload','80%'],['Applicant mismatch','needs_review','0%']],64,166,1150,340,[390,475,285],28);
  text(s,'Run scripts/run_demo.py with a new output folder\nInspect result.json, field evidence and item states\nNo manual correction or hidden reference input',64,542,1145,107,27);

  s=slide('Reproduction and remaining limits','40 seconds. Source: docs/REPRODUCIBILITY.md, docs/CONTRIBUTIONS.md, docs/ERROR_ANALYSIS.md. S11 two fresh Python venvs on same Ubuntu host, not clean OS tests. Source and frozen assets archive plus separate Linux wheels. S12 companion academic deliverables. Smoke real development OCR, final saved-OCR verification all13 routes. Test permanently consumed since4Nov2026 22:11:17 IST. No real final benchmark, no calibrated scores, single-agent reference review,4 groups. Actual student contributions/sign-off/roll numbers/institution/template/deadline unknown. No submission/publication occurred.');
  text(s,'Smoke runs real development OCR\nFinal mode verifies preserved OCR and all 13 routes\nFinal test consumed remains YES',64,171,1150,160,32);
  text(s,'Synthetic English pages and closely related templates\nFour final applicant groups and correlated bundles\nHeuristic uncertainty and single-agent reference review\nStudent review and administrative details remain pending',64,382,1150,210,29);
  const spec=pres.slides.items.map((q,i)=>({slide:i+1,notes:q.speakerNotes.text}));
  await fs.writeFile(path.join(ROOT,'output/presentation/speaker_notes.json'),JSON.stringify(spec,null,2)+'\n');
  return {slides:pres.slides.items.length,tableSlides:[3,4,6,8,9,11],font};
}
