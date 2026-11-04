"""Experiments reuse shared inference/extraction/rules, then open references to score."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from ..classification import classify
from ..config import load_config
from ..dataset import PageAnnotation, resolve_inside, sha256
from ..extraction import extract
from ..ocr import OCRSettings
from ..pipeline import analyze, code_snapshot, write_json
from ..preprocessing import PreprocessingConfig
from ..requirements import evaluate
from ..schemas import ApplicantProfile, BundleInput, ApplicationResult
from .classification_metrics import classification_metrics
from .field_metrics import field_metrics
from .ocr_metrics import aggregate, score
from .readiness_metrics import readiness_metrics


def infer_pages(root, records, output, branch, preprocessing, command, reuse=None):
    """Only image paths and explicit settings enter analyze; no annotations/labels."""
    root=Path(root).resolve(); output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    paths=list(dict.fromkeys(r.relative_path for r in records)); documents={}; origins={}; runtimes=[]
    for offset in range(0,len(paths),6):
        chosen=paths[offset:offset+6]; run=output/f'batch-{offset//6:03d}'
        prior=Path(reuse).resolve()/run.name if reuse else None
        if prior and (prior/'metadata.json').exists():
            old_settings=json.loads((prior/'settings.json').read_text())
            old_code=json.loads((prior/'code_snapshot.json').read_text())
            current=code_snapshot()
            if any(old_code.get(n)!=h for n,h in current.items() if '/' not in n):
                raise ValueError('Reused OCR implementation changed')
            if old_settings['branch']!=branch or old_settings['ocr']!=asdict(OCRSettings()) or old_settings['ingestion']['pdf_dpi']!=300 or json.loads((prior/'preprocessing.json').read_text())!=preprocessing.model_dump(mode='json'):
                raise ValueError('Reused OCR settings changed')
            old_inputs=json.loads((prior/'inputs.json').read_text())['files']
            if [p['input_path'] for p in old_inputs]!=[str(resolve_inside(root,p)) for p in chosen] or any(p['source_sha256']!=sha256(Path(p['input_path'])) for p in old_inputs):
                raise ValueError('Reused OCR input changed')
            result=ApplicationResult.model_validate_json((prior/'result.json').read_text())
            # Preserve original evidence paths, run IDs and image pointers.
            run=prior
        else:
            result=analyze([resolve_inside(root,p) for p in chosen],config=load_config(root/'configs/scholarship_demo.json'),
                applicant=ApplicantProfile(applicant_reference='fictional-experiment'),output=run,branch=branch,
                settings=OCRSettings(),preprocessing=preprocessing,exact_command=command)
        runtimes.append(result.runtime_seconds)
        for path,document in zip(chosen,result.documents):
            documents[path]=document; origins[path]=dict(result_path=(run/'result.json').relative_to(root).as_posix(),
                run_id=result.run_id,result_sha256=sha256(run/'result.json'))
        print(f'{branch}: {min(offset+6,len(paths))}/{len(paths)} inputs',flush=True)
    write_json(output/'inference_index.json',dict(origins=origins,selected_sample_ids=[r.sample_id for r in records],
        input_hashes={p:sha256(root/p) for p in paths},branch=branch,ocr=asdict(OCRSettings()),
        preprocessing=preprocessing.model_dump(mode='json'),end_to_end_seconds=sum(runtimes),
        reuse_source=str(reuse) if reuse else None))
    return documents,origins,sum(runtimes)


def load_inference(root, folder):
    index=json.loads((folder/'inference_index.json').read_text()); documents={}; loaded={}
    for path,origin in index['origins'].items():
        if sha256(root/path)!=index['input_hashes'][path] or sha256(root/origin['result_path'])!=origin['result_sha256']:
            raise ValueError('Inference input/result hash changed')
        if origin['result_path'] not in loaded:
            loaded[origin['result_path']]=ApplicationResult.model_validate_json((root/origin['result_path']).read_text())
        found=[d for d in loaded[origin['result_path']].documents if d.source_sha256==index['input_hashes'][path]]
        if len(found)!=1: raise ValueError('Ambiguous cached input identity')
        documents[path]=found[0]
    return documents,index


def page_predictions(records, documents, classifier=None):
    """All predictions precede any reference-field/text reads in score_pages."""
    predictions={}
    for r in records:
        doc=documents[r.relative_path]
        page=next((p for p in doc.pages if p.page_index==r.page_index),None)
        ocr=next((o for o in doc.ocr if page is not None and o.page_id==page.page_id),None)
        results=[ocr] if ocr else []
        pred=classifier.classify(results,doc.errors) if classifier else classify(results,doc.errors)
        routed=extract(pred.document_type,[page] if page else [],results)
        # True-type routing is an explicitly separate diagnostic, never used for readiness.
        true_fields=extract(r.document_type,[page] if page else [],results)
        predictions[r.sample_id]=dict(prediction=pred.model_dump(mode='json'),
            fields=[f.model_dump(mode='json') for f in routed],true_type_fields=[f.model_dump(mode='json') for f in true_fields],
            text=ocr.text if ocr else '',ocr_status=ocr.status if ocr else 'error',errors=doc.errors,
            ocr_seconds=ocr.runtime_seconds if ocr else 0.,preprocessing_seconds=sum(
                s.runtime_seconds+float(s.parameters.get('estimation_seconds',0)) for proc in doc.processing for s in proc.stages))
    return predictions


def score_pages(root, records, predictions):
    if set(predictions)!={r.sample_id for r in records}: raise ValueError('Predictions must retain every sample')
    rows=[]; routed=[]; true=[]
    for r in records:
        ref=PageAnnotation.model_validate_json((root/r.annotation_path).read_text()); p=predictions[r.sample_id]
        rows.append(dict(sample_id=r.sample_id,source_document_id=r.source_document_id,applicant_id=r.applicant_id,
            layout_id=r.layout_id,variant_id=r.variant_id,reference_sha256=sha256(root/r.annotation_path),
            target=r.document_type,**p,ocr_metrics=score(ref.full_text,p['text'])))
        common=dict(sample_id=r.sample_id,document_type=r.document_type,reference={k:v.model_dump() for k,v in ref.fields.items()})
        routed.append(dict(common,predictions=p['fields'])); true.append(dict(common,predictions=p['true_type_fields']))
    from ..schemas import DocumentPrediction
    metric=dict(ocr=aggregate([r['ocr_metrics'] for r in rows]),
        classification=classification_metrics([r['target'] for r in rows],[DocumentPrediction.model_validate(r['prediction']) for r in rows]),
        fields_predicted_type=field_metrics(routed),fields_true_type=field_metrics(true),
        errors=sum(r['ocr_status']=='error' for r in rows),ocr_seconds=sum(r['ocr_seconds'] for r in rows),
        preprocessing_seconds=sum(r['preprocessing_seconds'] for r in rows),
        by_variant={v:aggregate([r['ocr_metrics'] for r in rows if r['variant_id']==v]) for v in sorted({r['variant_id'] for r in rows})})
    return metric,rows


def bundle_predictions(root,bundles,documents,classifier=None):
    predictions={}; inference_seconds=0.
    for b in bundles:
        inputs=BundleInput.model_validate_json((root/b['input_path']).read_text())
        docs=[documents[p].model_copy(deep=True) for p in inputs.files]
        started=perf_counter()
        for path,doc in zip(inputs.files,docs):
            doc.declared_type_hint=inputs.declared_type_hints.get(path)
            doc.prediction=classifier.classify(doc.ocr,doc.errors) if classifier else classify(doc.ocr,doc.errors)
            doc.fields=extract(doc.prediction.document_type,doc.pages,doc.ocr)
        requirements,issues,overall,completeness,reason=evaluate(load_config(root/'configs/scholarship_demo.json'),inputs.profile,docs)
        inference_seconds+=perf_counter()-started
        predictions[inputs.scenario_id]=dict(overall_state=overall,requirements={r.requirement_id:r.state for r in requirements},
            completeness=completeness,completeness_reason=reason,issues=list(issues),
            evidence=[r.model_dump(mode='json') for r in requirements],document_ids=[d.document_id for d in docs],input_path=b['input_path'])
    return predictions,inference_seconds


def score_bundles(root,bundles,predictions):
    rows=[]; completeness_matches=0
    for b in bundles:
        ref=json.loads((root/b['reference_path']).read_text()); pred=predictions[ref['scenario_id']]
        rows.append(dict(scenario_id=ref['scenario_id'],reference=ref,predicted=pred,
            reference_sha256=sha256(root/b['reference_path'])))
        completeness_matches+=int(ref['completeness']==pred['completeness'])
    if len(rows)!=len(predictions): raise ValueError('Unexpected/dropped bundle')
    metrics=readiness_metrics(rows)
    metrics['scope']='Fictional grouped dataset; correlated scenarios per applicant; synthetic performance only.'
    metrics['completeness_matches']=completeness_matches
    return metrics,rows
