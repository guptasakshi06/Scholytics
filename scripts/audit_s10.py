#!/usr/bin/env python3
"""Verify S10 freeze, complete paired runs, replay, raw counts and report artifacts."""
from collections import Counter
import csv
import json
from pathlib import Path
import shutil

from scholarready.dataset import sha256
from scholarready.evaluation.freeze import validate_freeze
from scholarready.pipeline import write_json
from scholarready.splitting import load_records


def read(path):
    return json.loads(path.read_text())


def semantic(value):
    if isinstance(value, dict):
        return {k:semantic(v) for k,v in value.items() if k not in (
            'ocr_seconds','preprocessing_seconds','end_to_end_page_seconds','bundle_replay_rule_seconds','inference_index')}
    if isinstance(value, list): return [semantic(v) for v in value]
    return value


def main():
    root=Path.cwd();out=root/'docs/verification/s10';assets=out/'assets'
    config,freeze,support=validate_freeze(root,root/'configs/evaluation.json')
    fresh=root/'artifacts/runs/s10-final';replay=root/'artifacts/runs/s10-replay'
    records={r.sample_id:r for r in load_records(root/config['manifest']) if r.development_role=='test'}
    expected_ids=config['sample_ids']['test']
    assert len(expected_ids)==52 and len(records)==52
    expected_routes=[(s['name'],'keyword') for s in config['variants']]+[('A','learned')]
    fresh_summary=read(fresh/'summary.json');repeated=read(replay/'summary.json')
    assert semantic(fresh_summary)==semantic(repeated)
    hash_count=0;run_ids=[];registrations=[]
    for run in (fresh,replay):
        metadata=read(run/'run.json')
        assert metadata['selected_sample_ids']==expected_ids and metadata['partition']=='test'
        assert metadata['suite']=='all' and metadata['final_test_consumed']
        assert metadata['cache_replay']==(run==replay)
        assert metadata['freeze_sha256']==sha256(root/config['freeze_record'])
        for path,h in read(run/'artifact_hashes.json').items():
            assert sha256(run/path)==h,path
            hash_count+=1
        reports=read(run/'summary.json')['reports']
        assert Counter((r['name'],r['route']) for r in reports)==Counter(expected_routes)
        for report in reports:
            name,route=report['name'],report['route']
            rows=read(run/name/(route+'_scored_pages.json'))
            preds=read(run/name/(route+'_pages_before_references.json'))
            bundles=read(run/name/(route+'_scored_bundles.json'))
            assert [r['sample_id'] for r in rows]==expected_ids and set(preds)==set(expected_ids)
            assert len(bundles)==24
            for r in rows:
                record=records[r['sample_id']]
                assert r['reference_sha256']==sha256(root/record.annotation_path)
                assert all(r[k]==v for k,v in preds[r['sample_id']].items())
            p=report['page_metrics'];ocr=p['ocr'];c=p['classification'];r=report['readiness']
            assert c['samples']==52 and ocr['sample_count']==52
            assert sum(sum(v) for v in c['confusion_matrix'])==52
            assert ocr['character_edits']==sum(row['ocr_metrics']['character_edits'] for row in rows)
            assert ocr['word_edits']==sum(row['ocr_metrics']['word_edits'] for row in rows)
            assert ocr['reference_characters']==sum(row['ocr_metrics']['reference_characters'] for row in rows)
            assert ocr['cer']==ocr['character_edits']/ocr['reference_characters']
            for field_route,metric in [('fields','fields_predicted_type'),('true_type_fields','fields_true_type')]:
                raw=Counter()
                by_field={}
                for row in rows:
                    ref=read(root/records[row['sample_id']].annotation_path)['fields']
                    predictions={f['field_name']:f for f in row[field_route]}
                    for name,target in ref.items():
                        if target['state']!='present': continue
                        pred=predictions.get(name)
                        valid=pred is not None and pred['validation_state']=='valid'
                        exact=valid and all(pred[k]==target[k] for k in ('normalized_value','unit','person_role'))
                        counts=Counter(present_support=1,exact_value_unit_role=int(exact),
                            wrong_nonnull=int(valid and not exact),missing_prediction=int(not valid))
                        raw.update(counts);by_field.setdefault(row['target']+':'+name,Counter()).update(counts)
                assert raw['present_support']==164
                for key,value in raw.items(): assert p[metric]['overall'][key]==value
                for name,counts in by_field.items():
                    for key,value in counts.items(): assert p[metric]['by_type_field'][name][key]==value
                assert raw['exact_value_unit_role']+raw['wrong_nonnull']+raw['missing_prediction']==164
            nonready=sum(b['reference']['overall_state']!='ready' for b in bundles)
            false=sum(b['reference']['overall_state']!='ready' and b['predicted']['overall_state']=='ready' for b in bundles)
            assert nonready==16 and r['application']['reference_non_ready_count']==16
            assert r['application']['false_ready_count']==false and r['application']['false_ready_rate']==false/16
            raw=Counter()
            for b in bundles:
                reference=read(root/(Path(b['predicted']['input_path']).parent/'expected.json'))
                assert reference==b['reference']
                assert b['reference_sha256']==sha256(root/(Path(b['predicted']['input_path']).parent/'expected.json'))
                assert set(b['reference']['requirements'])==set(b['predicted']['requirements'])
                raw['application']+=int(b['reference']['overall_state']==b['predicted']['overall_state'])
                raw['completeness']+=int(b['reference']['completeness']==b['predicted']['completeness'])
                for name,actual in b['reference']['requirements'].items():
                    guess=b['predicted']['requirements'][name]
                    raw['items']+=1;raw['agreement']+=int(actual==guess)
                    raw['tp']+=int(actual=='missing' and guess=='missing')
                    raw['fp']+=int(actual!='missing' and guess=='missing')
                    raw['fn']+=int(actual=='missing' and guess!='missing')
                    raw['tn']+=int(actual!='missing' and guess!='missing')
            assert raw['items']==120 and r['requirement_items']==120
            assert r['application']['agreement_count']==raw['application']
            assert r['requirements']['agreement_count']==raw['agreement']
            assert r['completeness_matches']==raw['completeness']
            for key in ('tp','fp','fn','tn'): assert r['requirements']['missing_positive'][key]==raw[key]
        if run==fresh:
            for spec in config['variants']:
                index=read(run/spec['name']/'inference/inference_index.json')
                assert index['selected_sample_ids']==expected_ids
                assert index['branch']==spec['branch'] and index['preprocessing']==spec['preprocessing']
                for origin in index['origins'].values():
                    assert sha256(root/origin['result_path'])==origin['result_sha256']
                    result=read(root/origin['result_path']);run_ids.append(result['run_id'])
                    settings=read((root/origin['result_path']).parent/'settings.json')
                    assert settings['ocr']==config['ocr'] and settings['ingestion']['pdf_dpi']==300
        consumption=[(path,item) for path in (out/'test_consumption').glob('*.json')
                     if (item:=read(path))['output']==str(run)]
        assert len(consumption)==1
        path,record=consumption[0]
        assert record['selected_sample_ids']==expected_ids and record['replay']==(run==replay)
        assert record['started_utc'] and record['status']=='started_test_consumed'
        assert record['freeze_sha256']==metadata['freeze_sha256']
        registrations.append(dict(output=run.relative_to(root).as_posix(),status='completed',replay=record['replay'],
            consumption=path.relative_to(root).as_posix(),consumption_sha256=sha256(path),started_utc=record['started_utc'],
            run_sha256=sha256(run/'run.json'),summary_sha256=sha256(run/'summary.json'),command=metadata['command']))
    for path,h in read(assets/'asset_hashes.json').items(): assert sha256(assets/path)==h,path
    copies=read(assets/'compact_artifacts.json')
    for path,entry in copies.items():
        assert sha256(root/path)==entry['sha256']==sha256(root/entry['source'])
    summary=list(csv.DictReader((assets/'summary.csv').open()))
    assert len(summary)==13
    for row,report in zip(summary,fresh_summary['reports']):
        assert row['variant']==report['name'] and row['route']==report['route']
        assert int(row['character_edits'])==report['page_metrics']['ocr']['character_edits']
        assert int(row['false_ready'])==report['readiness']['application']['false_ready_count']
        assert int(row['reference_nonready'])==16
    breakdowns=read(assets/'breakdowns.json')
    for report in fresh_summary['reports']:
        section=breakdowns[report['name']+'/'+report['route']]
        for dimension,groups in section.items():
            assert sum(g['pages'] for g in groups.values())==52,dimension
            assert sum(g['ocr']['character_edits'] for g in groups.values())==report['page_metrics']['ocr']['character_edits']
            assert sum(g['fields_predicted_type']['overall']['present_support'] for g in groups.values())==164
        assert section['layout_status']['reserved']['pages']==13 and section['layout_status']['reserved']['groups']==1
        assert section['layout_status']['known']['pages']==39 and section['layout_status']['known']['groups']==3
    fig_index=read(assets/'figure_index.json')
    for case in fig_index['cases']:
        for entry in case['entries']: assert sha256(root/entry['source_image'])==entry['image_sha256']
    for stage in fig_index['C_stages']: assert sha256(root/stage['path'])==stage['sha256']
    for detail in fig_index['field_details']:
        for entry in detail['entries']: assert sha256(root/entry['image'])==entry['image_sha256']
    c=read(fresh/'C/keyword_pages_before_references.json')
    no_morph=read(fresh/'C_no_morphology/keyword_pages_before_references.json')
    assert semantic(c)==semantic(no_morph)
    snapshots={}
    replay_dest=out/'replay';replay_dest.mkdir(exist_ok=True)
    for name in ('run.json','summary.json','artifact_hashes.json','selection_before_inference.json'):
        shutil.copyfile(replay/name,replay_dest/name)
        assert sha256(replay/name)==sha256(replay_dest/name)
        snapshots[(replay_dest/name).relative_to(root).as_posix()]=dict(source=(replay/name).relative_to(root).as_posix(),sha256=sha256(replay/name))
    write_json(out/'replay_snapshots.json',snapshots)
    write_json(out/'run_registry.json',dict(freeze_sha256=sha256(root/config['freeze_record']),runs=registrations,
        fresh_batch_run_ids=sorted(set(run_ids)),method_changes_after_test=False,retuning=False,
        replay_purpose='Recompute all predictions and metrics from hash-checked saved OCR; no new OCR or parameter selection.'))
    write_json(out/'acceptance.json',dict(status='passed',frozen_artifacts=len(freeze['artifact_hashes']),
        freeze_sha256=sha256(root/config['freeze_record']),run_hash_checks=hash_count,compact_files=len(copies),
        variants=12,routes=13,pages_per_route=52,bundles_per_route=24,reference_nonready_per_route=16,
        test_consumption_records=len(registrations),replay_semantically_identical=True,
        raw_field_and_readiness_counts_verified=True,paired_supports_and_confusion_totals_verified=True,
        identity_and_no_morphology_semantically_identical=True,
        report_tables_breakdowns_and_image_hashes_verified=True,support=support,
        figure_visual_review='See visual_review.json; required alongside this automated acceptance.'))
    print(json.dumps(dict(status='passed',run_hash_checks=hash_count,compact_files=len(copies),routes=13,
        test_consumed=True,replay_identical=True)))


if __name__=='__main__': main()
