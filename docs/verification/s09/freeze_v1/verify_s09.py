#!/usr/bin/env python3
"""Audit freeze, train-only fitting, replay, CLI agreement and untouched test inventory."""
from difflib import SequenceMatcher
import json
from pathlib import Path

import numpy as np

from scholarready.classification import LearnedClassifier, build_estimator
from scholarready.dataset import sha256
from scholarready.evaluation.experiment import load_inference, page_predictions
from scholarready.evaluation.freeze import validate_freeze
from scholarready.pipeline import write_json
from scholarready.schemas import ApplicationResult
from scholarready.splitting import load_records


def semantic(value):
    if isinstance(value,dict):
        return {k:semantic(v) for k,v in value.items() if k not in (
            'ocr_seconds','preprocessing_seconds','end_to_end_page_seconds','bundle_replay_rule_seconds','inference_index')}
    if isinstance(value,list): return [semantic(v) for v in value]
    return value


def main():
    root=Path.cwd(); output=root/'docs/verification/s09'
    config,frozen,support=validate_freeze(root,root/'configs/evaluation.json')
    records=load_records(root/config['manifest']); test={r.sample_id for r in records if r.development_role=='test'}
    train=[r for r in records if r.development_role=='train' and r.variant_id=='clean']
    val=[r for r in records if r.development_role=='validation']
    folder=root/config['model']; model=LearnedClassifier.load(folder)
    assert model.metadata['training_sample_ids']==[r.sample_id for r in train]
    docs,index=load_inference(root,root/'artifacts/runs/s09-training-complete/inference')
    refit=build_estimator(2026); refit.set_params(logistic__C=model.metadata['C'])
    refit.fit(['\n'.join(o.text for o in docs[r.relative_path].ocr) for r in train],[r.document_type for r in train])
    np.testing.assert_array_equal(refit.named_steps['logistic'].coef_,model.estimator.named_steps['logistic'].coef_)
    np.testing.assert_array_equal(refit.named_steps['logistic'].intercept_,model.estimator.named_steps['logistic'].intercept_)
    assert refit.named_steps['tfidf'].vocabulary_==model.estimator.named_steps['tfidf'].vocabulary_
    actual_ocr=set(index['selected_sample_ids'])
    tuning=root/'artifacts/runs/s09-dip-tuning-complete'
    for spec in config['variants']:
        ix=json.loads((tuning/spec['name']/'inference_index.json').read_text())
        actual_ocr.update(ix['selected_sample_ids'])
        assert all(s.startswith('exp-10-') for s in ix['selected_sample_ids'])
    assert not (actual_ocr & test)
    assert not list((root/'docs/verification/s10').glob('test_consumption/*.json'))
    fresh=root/'artifacts/runs/s09-validation'; replay=root/'artifacts/runs/s09-validation-replay'
    summary=json.loads((fresh/'summary.json').read_text())
    repeated=json.loads((replay/'summary.json').read_text())
    assert semantic(summary)==semantic(repeated)
    fresh_pages=json.loads((fresh/'A/keyword_pages_before_references.json').read_text())
    assert semantic(fresh_pages)==semantic(page_predictions(val,docs))
    hashes_checked=0
    for run in (fresh,replay):
        for p,h in json.loads((run/'artifact_hashes.json').read_text()).items():
            assert sha256(run/p)==h; hashes_checked+=1
        meta=json.loads((run/'run.json').read_text()); assert not meta['final_test_consumed']
        assert not set(meta['selected_sample_ids']) & test
    # The same validation bundle is also exercised through the actual public CLI.
    cli=ApplicationResult.model_validate_json((root/'artifacts/runs/s09-cli-validation/result.json').read_text())
    bundle_preds=json.loads((fresh/'A/learned_bundles_before_references.json').read_text())
    pred=bundle_preds['expanded-10-complete']
    assert (cli.overall_state,cli.completeness,cli.issues)==(pred['overall_state'],pred['completeness'],pred['issues'])
    assert [r.model_dump(mode='json') for r in cli.requirements]==pred['evidence']
    # Cross-pilot duplicate check: pilot remains excluded even if shared templates look similar.
    pilot=load_records(root/'data/manifests/pilot.jsonl')
    source_new=[r for r in records if r.variant_id=='clean']; source_old=[r for r in pilot if r.variant_id=='clean']
    old_text={r.sample_id:json.loads((root/r.annotation_path).read_text())['full_text'] for r in source_old}
    pairs=[]; maximum=0.
    for r in source_new:
        text=json.loads((root/r.annotation_path).read_text())['full_text']
        for old in source_old:
            ratio=SequenceMatcher(None,text,old_text[old.sample_id],autojunk=False).ratio(); maximum=max(maximum,ratio)
            if ratio>=.98 or r.source_hash==old.source_hash: pairs.append([r.sample_id,old.sample_id,ratio])
    assert not pairs
    # Pixel candidates arise from sparse common templates. Verify different visible content,
    # then retain the candidate list and known-layout caveat rather than declaring zero similarity.
    dup=json.loads((output/'source_review_final/duplicates.json').read_text())
    by_id={r.sample_id:r for r in records}
    texts={r.sample_id:json.loads((root/r.annotation_path).read_text())['full_text'] for r in source_new}
    for pair in dup['pixel_candidates']:
        a,b=pair['a'],pair['b']
        assert by_id[a].applicant_id!=by_id[b].applicant_id and texts[a]!=texts[b]
        assert pair['text_similarity']<.98
    write_json(output/'acceptance.json',dict(status='passed',freeze_sha256=sha256(root/config['freeze_record']),
        frozen_artifacts=len(frozen['artifact_hashes']),run_artifact_hashes_checked=hashes_checked,support=support,
        independent_review=dict(test_pages=52,test_bundles=24,same_agent=True,student_signoff=False),
        no_test_inference=True,actual_training_and_tuning_ocr_ids=sorted(actual_ocr),test_consumption_records=0,
        model_refit_weights_vocabulary_identical=True,validation_replay_semantically_identical=True,
        fresh_A_OCR_vs_training_validation_semantically_identical=True,actual_CLI_bundle_equals_cached_assembly=True,
        cross_pilot_duplicate_check=dict(compared_pairs=len(source_new)*len(source_old),near_text_threshold=.98,
            maximum_text_similarity=maximum,flagged_pairs=pairs),
        sparse_template_candidates=dict(count=dup['candidate_count'],cross_partition=dup['cross_partition_candidates'],
            disposition='Different visible filled content in every candidate; known template/layout reuse allowed and reported. Pixel metric mostly measures blank paper. This is not evidence of independent document styles.'),
        generation_reproducible=json.loads((output/'generation_reproducibility.json').read_text())['all_equal']))
    print(json.dumps(dict(status='passed',hash_checks=hashes_checked,final_test_consumed=False)))


if __name__=='__main__': main()
