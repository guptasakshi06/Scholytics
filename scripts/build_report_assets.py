#!/usr/bin/env python3
"""Build S10 tables and figures from preserved frozen predictions; no inference."""
import argparse
from collections import Counter
from difflib import SequenceMatcher
import csv
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from scholarready.dataset import sha256
from scholarready.evaluation.classification_metrics import classification_metrics
from scholarready.evaluation.field_metrics import field_metrics
from scholarready.evaluation.ocr_metrics import aggregate, normalize
from scholarready.geometry import map_points
from scholarready.pipeline import write_json
from scholarready.schemas import DocumentPrediction
from scholarready.splitting import load_records


def read(path):
    return json.loads(path.read_text())


def csv_table(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def field_rows(rows, references, route):
    return [dict(sample_id=r['sample_id'], document_type=r['target'],
                 reference=references[r['sample_id']]['fields'], predictions=r[route]) for r in rows]


def subset_metrics(rows, references):
    return dict(pages=len(rows), sources=len({r['source_document_id'] for r in rows}),
        groups=len({r['applicant_id'] for r in rows}),
        ocr=aggregate([r['ocr_metrics'] for r in rows]),
        classification=classification_metrics([r['target'] for r in rows],
            [DocumentPrediction.model_validate(r['prediction']) for r in rows]),
        fields_predicted_type=field_metrics(field_rows(rows, references, 'fields')),
        fields_true_type=field_metrics(field_rows(rows, references, 'true_type_fields')))


def summary_row(report):
    p, r = report['page_metrics'], report['readiness']
    f = p['fields_predicted_type']['overall']
    return dict(variant=report['name'], route=report['route'], pages=p['classification']['samples'],
        character_edits=p['ocr']['character_edits'], reference_characters=p['ocr']['reference_characters'],
        cer=p['ocr']['cer'], word_edits=p['ocr']['word_edits'], reference_words=p['ocr']['reference_words'],
        wer=p['ocr']['wer'], macro_f1=p['classification']['macro_f1'], unresolved=p['classification']['unresolved'],
        exact_fields=f['exact_value_unit_role'], present_fields=f['present_support'],
        field_exact=f['normalized_exact_match'], field_missing=f['missing_prediction'], field_wrong_nonnull=f['wrong_nonnull'],
        true_type_exact_fields=p['fields_true_type']['overall']['exact_value_unit_role'],
        unreadable_reference_fields=f['unreadable_reference_support'],
        application_matches=r['application']['agreement_count'], applications=r['scenarios'],
        requirement_matches=r['requirements']['agreement_count'], requirement_items=r['requirement_items'],
        completeness_matches=r['completeness_matches'],
        missing_precision=r['requirements']['missing_positive']['precision'],
        missing_recall=r['requirements']['missing_positive']['recall'], missing_f1=r['requirements']['missing_positive']['f1'],
        false_ready=r['application']['false_ready_count'], reference_nonready=r['application']['reference_non_ready_count'],
        false_ready_rate=r['application']['false_ready_rate'], predicted_ready=r['application']['predicted_ready_count'],
        page_errors=p['errors'], empty_predictions=p['ocr']['empty_prediction_count'],
        page_seconds=report['end_to_end_page_seconds'], ocr_seconds=p['ocr_seconds'],
        preprocessing_seconds=p['preprocessing_seconds'], bundle_rule_seconds=report['bundle_replay_rule_seconds'])


def markdown_tables(output, table, per_class, fields, breakdowns):
    lines=['# Generated final-test tables', '',
        'Source: [original run metadata](run/run.json), [summary](run/summary.json), '
        '[provenance](provenance.json). Each variant links to its exact metric artifact. '
        'All rows use the same 52 pages / 24 sources / four applicant groups; synthetic only. '
        'Rates shown as percentages are rounded for display; JSON/CSV retain full values.', '',
        '## OCR, classification and extraction', '',
        '| Variant / route | Character edits / 14900 | CER % | Word edits / 2092 | WER % | Macro-F1 | Exact fields / 164 | Missing / wrong nonnull |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in table:
        label=f'[{r["variant"]} / {r["route"]}](run/{r["variant"]}/{r["route"]}_metrics.json)'
        lines.append(f'| {label} | {r["character_edits"]} | {100*r["cer"]:.4f} | {r["word_edits"]} | {100*r["wer"]:.4f} | '
            f'{r["macro_f1"]:.6f} | {r["exact_fields"]} | {r["field_missing"]} / {r["field_wrong_nonnull"]} |')
    lines+=['', 'Four unreadable-reference income amounts are separate from the 164 present targets. '
        'True-type and predicted-type exact counts agree on these data for all routes; full separate '
        '[per-field results](fields_per_type.csv) include states and support. This equality does not establish classification-independent extraction in general.', '',
        '## Application and requirement outcomes', '',
        '| Variant / route | Headlines / 24 | Item states / 120 | Completeness / 24 | Missing P / R / F1 | False ready / 16 | Predicted ready |',
        '| --- | ---: | ---: | ---: | --- | ---: | ---: |']
    for r in table:
        lines.append(f'| {r["variant"]} / {r["route"]} | {r["application_matches"]} | {r["requirement_matches"]} | {r["completeness_matches"]} | '
            f'{r["missing_precision"]:.4f} / {r["missing_recall"]:.4f} / {r["missing_f1"]:.4f} | {r["false_ready"]} / {r["reference_nonready"]} | {r["predicted_ready"]} |')
    lines+=['', 'All 120 items remain in the confirmed-missing binary accounting. Unreadable/review '
        'states are retained separately in the original confusion matrices; a zero false-ready count '
        'does not imply that all ready applications were accepted.', '', '## Recorded timing', '',
        '| Variant / route | Page batch s | OCR s | Preprocessing s | Cached bundle rules s |',
        '| --- | ---: | ---: | ---: | ---: |']
    for r in table:
        lines.append(f'| {r["variant"]} / {r["route"]} | {r["page_seconds"]:.3f} | {r["ocr_seconds"]:.3f} | '
            f'{r["preprocessing_seconds"]:.3f} | {r["bundle_rule_seconds"]:.3f} |')
    lines+=['', 'A learned uses the same measured A page inference, rather than another fresh page run. '
        'Page batches include ingestion/rendering, saving stages, quality, DIP, OCR and baseline downstream work; '
        'exclude model load/final JSON. Cached bundle rules exclude upload/OCR. Timings are observed once, '
        'with uncontrolled OS caching/scheduling; no speed superiority claim.', '',
        '## Core layout and degradation support', '',
        '| Route | Breakdown | Pages | Sources | Groups | Character edits | Exact / present fields |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for key in ('A/keyword','A/learned','B/keyword','C/keyword'):
        for dim in ('layout_status','degradation'):
            for group, m in breakdowns[key][dim].items():
                f=m['fields_predicted_type']['overall']
                lines.append(f'| {key} | {dim}: {group} | {m["pages"]} | {m["sources"]} | {m["groups"]} | '
                    f'{m["ocr"]["character_edits"]} | {f["exact_value_unit_role"]} / {f["present_support"]} |')
    lines+=['', 'Breakdowns overlap across dimensions. Within each dimension the pages partition the same 52 items. '
        'All [breakdowns](breakdowns.json) include the fixed six-class metric; a stratum containing only income '
        'has macro-F1 1/6 even when every income prediction is correct, because absent classes have F1=0. '
        'Use its class supports rather than interpreting that as an overall collapse.', '',
        '## Per-class classification and per-field extraction', '',
        '[Per-class precision/recall/F1/support](classification_per_class.csv), '
        '[true-type and predicted-type per-field counts](fields_per_type.csv), '
        '[all page rows](pages.csv), [all bundle rows](bundles.csv), '
        '[all errors with evidence](errors.json), [figure source index](figure_index.json).', '']
    (output/'tables.md').write_text('\n'.join(lines))


def document_for(root, run, variant, record):
    index = read(run/variant/'inference/inference_index.json')
    origin = index['origins'][record.relative_path]
    path = root/origin['result_path']
    assert sha256(path) == origin['result_sha256']
    result = read(path)
    docs = [d for d in result['documents'] if d['source_sha256'] == index['input_hashes'][record.relative_path]]
    assert len(docs) == 1
    return docs[0], path.parent, origin


def figures(root, run, output, reports, rows_by_route, records):
    footer = f'{run.relative_to(root)} | evaluation-s09-1.1 | 52 pages / 24 sources / 4 groups'
    keywords = [r for r in reports if r['route'] == 'keyword']
    fig, ax = plt.subplots(figsize=(11, 6.5))
    labels = [r['name'] for r in keywords]
    values = [r['page_metrics']['ocr']['character_edits'] for r in keywords]
    ax.barh(labels[::-1], values[::-1], color=['#4f7096' if s in ('A','B','C') else '#8a9fa9' for s in labels[::-1]])
    for y, v in enumerate(values[::-1]):
        ax.text(v + max(values)*.012, y, str(v), va='center', fontsize=9)
    ax.set_xlim(0, max(values)*1.18 + 1)
    ax.set_xlabel('Character edits (same reference denominator; lower is better)')
    ax.set_title('Frozen paired preprocessing comparison — all declared variants')
    fig.text(.015, .015, footer, fontsize=8)
    fig.tight_layout(rect=(0,.035,1,1)); fig.savefig(output/'ocr_ablations.png', dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for ax, route in zip(axes, ('keyword', 'learned')):
        m = next(r for r in reports if r['name']=='A' and r['route']==route)['page_metrics']['classification']
        matrix = np.asarray(m['confusion_matrix'])
        ax.imshow(matrix, cmap='Blues', vmin=0, vmax=12)
        names = [x.replace('_certificate','').replace('__unresolved__','unresolved') for x in m['column_labels']]
        ax.set_xticks(range(7), names, rotation=40, ha='right', fontsize=8)
        ax.set_yticks(range(6), names[:6], fontsize=8)
        ax.set_xlabel('Predicted'); ax.set_ylabel('Reference')
        ax.set_title(f'A / {route} — macro-F1 {m["macro_f1"]:.4f}')
        for (i,j), value in np.ndenumerate(matrix):
            ax.text(j,i,str(value),ha='center',va='center',color='white' if value>6 else '#192c3d')
    fig.text(.015,.015,footer,fontsize=8); fig.tight_layout(rect=(0,.035,1,1))
    fig.savefig(output/'classification_A.png',dpi=150); plt.close(fig)

    base = {r['sample_id']:r for r in rows_by_route['A/keyword']}
    cases = []
    success = next(r for r in rows_by_route['A/keyword'] if r['variant_id']=='clean' and
                   r['target']=='marksheet' and r['ocr_metrics']['character_edits']==0)
    cases.append(('success', success['sample_id'], ['A','B','C']))
    for variant, label in [('C','C_largest_change'), ('C_kernel_2x2','kernel_largest_change')]:
        chosen = max(rows_by_route[variant+'/keyword'], key=lambda r:
            (r['ocr_metrics']['character_edits']-base[r['sample_id']]['ocr_metrics']['character_edits'], r['sample_id']))
        cases.append((label, chosen['sample_id'], ['A',variant]))
    unreadable = next(r for r in rows_by_route['A/keyword'] if r['variant_id']=='no_amount')
    cases.append(('erased_amount', unreadable['sample_id'], ['A','C']))
    index = []
    for label, sample_id, variants in cases:
        record=records[sample_id]
        entries=[]
        fig, axes=plt.subplots(1,len(variants),figsize=(5*len(variants),7.8),squeeze=False)
        for ax, variant in zip(axes[0],variants):
            doc, batch, origin=document_for(root,run,variant,record)
            page=next(p for p in doc['pages'] if p['page_index']==record.page_index)
            proc=next(p for p in doc['processing'] if p['page_id']==page['page_id'])
            stage=proc['stages'][-1]
            path=batch/stage['image_path']
            with Image.open(path) as img:
                ax.imshow(img.copy(),cmap='gray',vmin=0,vmax=255)
            row=next(r for r in rows_by_route[variant+'/keyword'] if r['sample_id']==sample_id)
            ax.set_title(f'{variant}: {row["ocr_metrics"]["character_edits"]} character edits\n'
                         f'{row["prediction"]["decision"]}: {row["prediction"]["document_type"]}',fontsize=10)
            ax.axis('off')
            entries.append(dict(variant=variant,source_image=path.relative_to(root).as_posix(),image_sha256=sha256(path),
                origin=origin,ocr=row['ocr_metrics'],text=row['text'],prediction=row['prediction']))
        fig.suptitle(f'{sample_id} | {label.replace("_"," ")}',fontsize=12)
        fig.text(.015,.012,footer,fontsize=7); fig.tight_layout(rect=(0,.035,1,.96))
        filename=label+'.png'; fig.savefig(output/filename,dpi=150); plt.close(fig)
        index.append(dict(case=label,sample_id=sample_id,figure=filename,entries=entries))

    # Full C stage sequence on the paired harm example; all stages retained locally.
    harm=next(c for c in index if c['case']=='C_largest_change')
    doc,batch,origin=document_for(root,run,'C',records[harm['sample_id']])
    stages=doc['processing'][0]['stages']
    fig,axes=plt.subplots(2,4,figsize=(15,10))
    stage_index=[]
    for ax,stage in zip(axes.flat,stages):
        path=batch/stage['image_path']
        with Image.open(path) as img: ax.imshow(img.copy(),cmap='gray',vmin=0,vmax=255)
        ax.set_title(stage['name'],fontsize=11);ax.axis('off')
        stage_index.append(dict(name=stage['name'],path=path.relative_to(root).as_posix(),sha256=sha256(path),parameters=stage['parameters']))
    for ax in list(axes.flat)[len(stages):]: ax.axis('off')
    fig.suptitle(f'C stage sequence | {harm["sample_id"]}',fontsize=13)
    fig.text(.015,.01,footer,fontsize=8);fig.tight_layout(rect=(0,.03,1,.96))
    fig.savefig(output/'C_stages.png',dpi=150);plt.close(fig)
    # Reference boxes locate illustrative crops only after evaluation; they never
    # enter inference. Scale annotation pixels to ingested pixels, then transform.
    details=[]
    for bad,good in [('C','A'),('C_kernel_2x2','C')]:
        good_rows={r['sample_id']:r for r in rows_by_route[good+'/keyword']}
        chosen=None
        for row in rows_by_route[bad+'/keyword']:
            reference=read(root/records[row['sample_id']].annotation_path)
            bad_fields={f['field_name']:f for f in row['fields']}
            good_fields={f['field_name']:f for f in good_rows[row['sample_id']]['fields']}
            for name,target in reference['fields'].items():
                a,b=bad_fields.get(name),good_fields.get(name)
                exact=lambda f:f is not None and f['validation_state']=='valid' and all(f[k]==target[k] for k in ('normalized_value','unit','person_role'))
                if target['state']=='present' and exact(b) and not exact(a):
                    chosen=(row['sample_id'],name,reference,target);break
            if chosen:break
        if not chosen:continue
        sample_id,name,reference,target=chosen
        line=next((l for l in reference['lines'] if target['raw_text'] in l['text']),None)
        annotation_box=line['box'] if line else target['box']
        fig,axes=plt.subplots(1,3,figsize=(15,3.5));entries=[]
        for ax,variant in zip(axes,('A','C','C_kernel_2x2')):
            doc,batch,origin=document_for(root,run,variant,records[sample_id]);page=doc['pages'][0];proc=doc['processing'][0]
            x,y,w,h=annotation_box
            points=np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]])*np.array([page['width']/reference['width'],page['height']/reference['height']])
            mapped=map_points(points,proc['transform']['matrix'])
            lower=np.floor(mapped.min(axis=0)-[20,15]).astype(int);upper=np.ceil(mapped.max(axis=0)+[20,15]).astype(int)
            crop=[max(0,int(lower[0])),max(0,int(lower[1])),min(proc['width'],int(upper[0])),min(proc['height'],int(upper[1]))]
            path=batch/proc['stages'][-1]['image_path']
            with Image.open(path) as img:ax.imshow(img.crop(crop),cmap='gray',vmin=0,vmax=255)
            row=next(r for r in rows_by_route[variant+'/keyword'] if r['sample_id']==sample_id)
            pred=next((f for f in row['fields'] if f['field_name']==name),None)
            value=pred['normalized_value'] if pred else None
            ax.set_title(f'{variant}: {value!s}\n'+(pred['validation_state'] if pred else 'no field'),fontsize=10);ax.axis('off')
            entries.append(dict(variant=variant,image=path.relative_to(root).as_posix(),image_sha256=sha256(path),
                processed_crop_xyxy=crop,coordinate_space=proc['transform']['target_space'],prediction=pred))
        fig.suptitle(f'{sample_id} / {name} | reference: {target["normalized_value"]}',fontsize=11)
        fig.text(.015,.015,footer,fontsize=7);fig.tight_layout(rect=(0,.05,1,.9))
        filename='field_detail_'+bad+'.png';fig.savefig(output/filename,dpi=150);plt.close(fig)
        details.append(dict(sample_id=sample_id,field=name,reference=target,figure=filename,entries=entries))
    write_json(output/'figure_index.json',dict(run=run.relative_to(root).as_posix(),cases=index,C_stages=stage_index,field_details=details,
        selection='Post-evaluation illustrative cases only; largest paired edit increase, first clean marksheet success and first erased amount. No method selection or retuning.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=Path.cwd();run=args.run.resolve();output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    metadata=read(run/'run.json');summary=read(run/'summary.json');reports=summary['reports']
    assert metadata['partition']=='test' and metadata['suite']=='all' and metadata['final_test_consumed']
    config=read(root/'configs/evaluation.json')
    assert metadata['selected_sample_ids']==config['sample_ids']['test']
    original_hashes=read(run/'artifact_hashes.json')
    for path,h in original_hashes.items(): assert sha256(run/path)==h,path
    records={r.sample_id:r for r in load_records(root/config['manifest']) if r.development_role=='test'}
    refs={s:read(root/r.annotation_path) for s,r in records.items()}
    rows_by_route={};breakdowns={};field_errors=[];class_errors=[];bundle_errors=[];ocr_errors=[]
    per_class=[];fields=[];table=[];page_table=[];bundle_table=[];distribution=[]
    for report in reports:
        name,route=report['name'],report['route'];key=name+'/'+route
        rows=read(run/name/(route+'_scored_pages.json'))
        bundles=read(run/name/(route+'_scored_bundles.json'))
        assert [r['sample_id'] for r in rows]==metadata['selected_sample_ids']
        assert len(bundles)==24
        rows_by_route[key]=rows;table.append(summary_row(report))
        distribution.append(dict(variant=name,route=route,
            cer_quantiles=dict(zip(('min','q25','median','q75','max'),np.quantile([r['ocr_metrics']['cer'] for r in rows],[0,.25,.5,.75,1]).tolist())),
            pages_with_character_edits=sum(r['ocr_metrics']['character_edits']>0 for r in rows)))
        dimensions=dict(layout=lambda r:r['layout_id'],layout_status=lambda r:'reserved' if r['layout_id']=='expanded_layout_3' else 'known',
                        degradation=lambda r:r['variant_id'],document_type=lambda r:r['target'],applicant=lambda r:r['applicant_id'])
        breakdowns[key]={dim:{v:subset_metrics([r for r in rows if label(r)==v],refs)
                        for v in sorted({label(r) for r in rows})} for dim,label in dimensions.items()}
        for label,metrics in report['page_metrics']['classification']['per_class'].items():
            per_class.append(dict(variant=name,route=route,label=label,**metrics))
        for field_route in ('fields_predicted_type','fields_true_type'):
            for field,metrics in report['page_metrics'][field_route]['by_type_field'].items():
                fields.append(dict(variant=name,route=route,field_route=field_route,field=field,
                    **{k:metrics[k] for k in ('present_support','exact_value_unit_role','normalized_exact_match','missing_prediction','wrong_nonnull','unreadable_reference_support','absent_support','extra_nonnull_output')}))
        for row in rows:
            sample_id=row['sample_id'];rec=records[sample_id];p=row['prediction']
            page_table.append(dict(variant=name,route=route,sample_id=sample_id,source_id=row['source_document_id'],applicant_id=row['applicant_id'],
                layout=row['layout_id'],degradation=row['variant_id'],target=row['target'],prediction=p['document_type'],decision=p['decision'],
                **{k:row['ocr_metrics'][k] for k in ('character_edits','reference_characters','cer','word_edits','reference_words','wer')},
                ocr_status=row['ocr_status'],reference_path=rec.annotation_path,input_path=rec.relative_path,reference_sha256=row['reference_sha256']))
            if p['decision']!='classified' or p['document_type']!=row['target']:
                class_errors.append(dict(variant=name,route=route,sample_id=sample_id,target=row['target'],prediction=p))
            if row['ocr_metrics']['character_edits']:
                ref,pred=normalize(refs[sample_id]['full_text']),normalize(row['text'])
                changes=[dict(operation=tag,reference=ref[a:b],prediction=pred[c:d],reference_span=[a,b],prediction_span=[c,d])
                    for tag,a,b,c,d in SequenceMatcher(None,ref,pred,autojunk=False).get_opcodes() if tag!='equal']
                ocr_errors.append(dict(variant=name,route=route,sample_id=sample_id,metrics=row['ocr_metrics'],changes=changes))
            for field_route in ('fields','true_type_fields'):
                predictions={p['field_name']:p for p in row[field_route]}
                for field,ref in refs[sample_id]['fields'].items():
                    pred=predictions.get(field)
                    valid=pred is not None and pred['validation_state']=='valid'
                    exact=valid and all(pred[k]==ref[k] for k in ('normalized_value','unit','person_role'))
                    if (ref['state']=='present' and not exact) or (ref['state']=='absent' and valid) or ref['state']=='unreadable':
                        kind=('unreadable_reference' if ref['state']=='unreadable' else
                              'extra_nonnull' if ref['state']=='absent' else 'wrong_nonnull' if valid else 'missing_prediction')
                        field_errors.append(dict(variant=name,route=route,field_route=field_route,sample_id=sample_id,
                            field=field,kind=kind,reference=ref,prediction=pred))
        for row in bundles:
            ref,pred=row['reference'],row['predicted']
            mismatch={k:dict(reference=v,predicted=pred['requirements'][k]) for k,v in ref['requirements'].items() if v!=pred['requirements'][k]}
            bundle_table.append(dict(variant=name,route=route,scenario_id=row['scenario_id'],reference=ref['overall_state'],prediction=pred['overall_state'],
                completeness_reference=ref['completeness'],completeness_prediction=pred['completeness'],item_mismatches=len(mismatch),
                input_path=pred['input_path'],reference_sha256=row['reference_sha256']))
            if mismatch or ref['overall_state']!=pred['overall_state'] or ref['completeness']!=pred['completeness']:
                bundle_errors.append(dict(variant=name,route=route,**row,item_mismatches=mismatch))
    csv_table(output/'summary.csv',table);csv_table(output/'classification_per_class.csv',per_class)
    csv_table(output/'fields_per_type.csv',fields);csv_table(output/'pages.csv',page_table);csv_table(output/'bundles.csv',bundle_table)
    write_json(output/'breakdowns.json',breakdowns);write_json(output/'ocr_distributions.json',distribution)
    write_json(output/'errors.json',dict(fields=field_errors,classification=class_errors,bundles=bundle_errors,ocr=ocr_errors))
    markdown_tables(output,table,per_class,fields,breakdowns)
    figures(root,run,output,reports,rows_by_route,records)
    # Preserve byte-identical non-media outputs outside ignored run directories.
    compact=output/'run';compact.mkdir();copies={}
    for source in sorted(run.rglob('*.json')):
        dest=compact/source.relative_to(run);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        copies[dest.relative_to(root).as_posix()]=dict(source=source.relative_to(root).as_posix(),sha256=sha256(source))
    write_json(output/'compact_artifacts.json',copies)
    write_json(output/'provenance.json',dict(run=run.relative_to(root).as_posix(),run_sha256=sha256(run/'run.json'),
        freeze_sha256=metadata['freeze_sha256'],config_sha256=sha256(root/'configs/evaluation.json'),
        summary_sha256=sha256(run/'summary.json'),builder_sha256=sha256(Path(__file__)),
        original_hash_checks=len(original_hashes),reports=len(reports),page_rows=len(page_table),bundle_rows=len(bundle_table),
        compact_files=len(copies),source_counts=dict(pages=len(records),sources=len({r.source_document_id for r in records.values()}),
            groups=len({r.applicant_id for r in records.values()})),
        breakdown_scope='Synthetic only; reserved layout is one applicant/6 sources/13 pages, known is 3 applicants/18 sources/39 pages. No CI: four groups. No real-data stratum.',
        input_status_counts={k:dict(Counter(r['ocr_status'] for r in rows)) for k,rows in rows_by_route.items()},
        errors=dict(classification=len(class_errors),field_records=len(field_errors),bundle_disagreements=len(bundle_errors)),
        figure_timing='Reporting only. Original OCR/page timing retained in summary; report generation time is excluded.'))
    write_json(output/'asset_hashes.json',{p.relative_to(output).as_posix():sha256(p) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(dict(status='complete',output=str(output),reports=len(reports),compact_files=len(copies))))


if __name__=='__main__': main()
