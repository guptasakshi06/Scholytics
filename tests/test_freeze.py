"""Protect held-out selection, stale references and immutable method contracts."""
import importlib.util
import json
from pathlib import Path

import pytest

from scholarready.dataset import sha256
from scholarready.evaluation import freeze
from scholarready.evaluation.experiment import load_inference, infer_pages
from scholarready.pipeline import write_json
from scholarready.preprocessing import PreprocessingConfig
from scholarready.splitting import load_records

ROOT=Path(__file__).resolve().parents[1]


def driver():
    spec=importlib.util.spec_from_file_location('experiment_driver',ROOT/'scripts/run_experiments.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def test_test_partition_requires_explicit_consumption():
    with pytest.raises(ValueError,match='protected'): driver().authorize_partition('test',False)
    with pytest.raises(ValueError,match='requires'): driver().authorize_partition('validation',True)
    driver().authorize_partition('validation',False)
    driver().authorize_partition('test',True)


def test_expanded_group_review_support_and_test_selection():
    review=json.loads((ROOT/'data/annotations/expanded_review.json').read_text())
    report=freeze.audit_dataset(ROOT,ROOT/'data/manifests/expanded.jsonl',ROOT/'data/manifests/expanded.splits.jsonl',review)
    assert report['connected_groups']==18
    assert [report['partitions'][p]['pages'] for p in ('train','validation','test')]==[130,52,52]
    assert report['partitions']['test']['sources']==24
    records=load_records(ROOT/'data/manifests/expanded.jsonl')
    config=dict(manifest='data/manifests/expanded.jsonl',sample_ids={p:[r.sample_id for r in records if r.development_role==p] for p in ('train','validation','test')})
    chosen=freeze.selected_records(ROOT,config,'validation')
    assert len(chosen)==52 and all(r.development_role=='validation' for r in chosen)
    config['sample_ids']['validation'].append(config['sample_ids']['test'][0])
    with pytest.raises(ValueError,match='selection changed'): freeze.selected_records(ROOT,config,'validation')


@pytest.mark.parametrize('defect',['unreviewed','stale_page','stale_bundle','wrong_split'])
def test_unreviewed_or_stale_test_cannot_freeze(defect):
    review=json.loads((ROOT/'data/annotations/expanded_review.json').read_text())
    if defect=='unreviewed': review['pages']['exp-14-0-clean']['status']='provisional'
    elif defect=='stale_page': review['pages']['exp-14-0-clean']['annotation_sha256']='0'*64
    elif defect=='stale_bundle': review['bundles'][next(iter(review['bundles']))]['reference_sha256']='0'*64
    else: review['splits_sha256']='0'*64
    with pytest.raises(ValueError,match='review|Unchecked|stale'):
        freeze.audit_dataset(ROOT,ROOT/'data/manifests/expanded.jsonl',ROOT/'data/manifests/expanded.splits.jsonl',review)


def test_connected_group_cannot_cross_final_roles(monkeypatch):
    original=freeze.context
    def broken(manifest,root):
        records,meta,groups,hashes=original(manifest,root)
        # Simulate two applicant families linked by hidden source reuse.
        for r in records:
            if r.applicant_id=='expanded-14': groups[r.sample_id]=groups[records[0].sample_id]
        return records,meta,groups,hashes
    monkeypatch.setattr(freeze,'context',broken)
    with pytest.raises(ValueError,match='forged group'):
        freeze.audit_dataset(ROOT,ROOT/'data/manifests/expanded.jsonl',ROOT/'data/manifests/expanded.splits.jsonl')


def mini_freeze(tmp_path,monkeypatch):
    (tmp_path/'src').mkdir(); code=tmp_path/'src/engine.py'; code.write_text('method = 1\n')
    write_json(tmp_path/'review.json',{})
    config=dict(freeze_record='freeze.json',review='review.json',manifest='manifest.jsonl',splits='split.jsonl')
    write_json(tmp_path/'evaluation.json',config)
    write_json(tmp_path/'freeze.json',dict(artifact_hashes={'src/engine.py':sha256(code)},
        implementation_files=['src/engine.py'],evaluation_config_sha256=sha256(tmp_path/'evaluation.json')))
    monkeypatch.setattr(freeze,'audit_dataset',lambda *args:{'status':'passed'})
    return code


@pytest.mark.parametrize('defect',['code','new_module','config'])
def test_frozen_hashes_inventory_and_config_reject_change(tmp_path,monkeypatch,defect):
    code=mini_freeze(tmp_path,monkeypatch)
    assert freeze.validate_freeze(tmp_path,tmp_path/'evaluation.json')[2]['status']=='passed'
    if defect=='code': code.write_text('method = 2\n')
    elif defect=='new_module': (tmp_path/'src/leak.py').write_text('new behavior\n')
    else:
        config=json.loads((tmp_path/'evaluation.json').read_text()); config['tuned_after_test']=True
        write_json(tmp_path/'evaluation.json',config)
    with pytest.raises(ValueError,match='changed'):
        freeze.validate_freeze(tmp_path,tmp_path/'evaluation.json')


def test_language_data_hash_is_part_of_environment(tmp_path,monkeypatch):
    import platform
    from scholarready.ocr import engine_version
    mini_freeze(tmp_path,monkeypatch)
    language=tmp_path/'eng.traineddata'; language.write_bytes(b'fixture-language-data')
    record=json.loads((tmp_path/'freeze.json').read_text())
    record['environment']=dict(python=platform.python_version(),tesseract=engine_version(),libraries={},
        external_files={'eng':dict(path=str(language),sha256=sha256(language))})
    write_json(tmp_path/'freeze.json',record)
    freeze.validate_freeze(tmp_path,tmp_path/'evaluation.json')
    language.write_bytes(b'changed-language-data')
    with pytest.raises(ValueError,match='language data changed'):
        freeze.validate_freeze(tmp_path,tmp_path/'evaluation.json')


def test_inference_reads_images_without_reference_access(tmp_path,monkeypatch):
    from scholarready import pipeline
    from scholarready.schemas import ApplicationResult
    # Use actual real OCR on a tiny existing fictional PNG; guard all annotation reads.
    selected=[load_records(ROOT/'data/manifests/pilot.jsonl')[0].model_copy(deep=True)]
    selected[0].relative_path='tests/fixtures/pilot/src-001.png'
    selected[0].annotation_path='data/annotations/DO_NOT_OPEN.json'
    original=Path.read_text
    def guard(path,*args,**kwargs):
        if 'annotations' in path.parts: raise AssertionError('Reference accessed during inference')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',guard)
    # Output needs a portable pointer relative to the task root.
    import uuid
    output=ROOT/'artifacts/runs'/('pytest-no-reference-'+uuid.uuid4().hex)
    docs,origins,_=infer_pages(ROOT,selected,output,'A',PreprocessingConfig(),'pytest actual OCR no references')
    assert docs[selected[0].relative_path].ocr[0].status=='ok'
    reloaded,index=load_inference(ROOT,output)
    assert reloaded[selected[0].relative_path].model_dump()==docs[selected[0].relative_path].model_dump()
    index['input_hashes'][selected[0].relative_path]='0'*64
    write_json(output/'inference_index.json',index)
    with pytest.raises(ValueError,match='hash changed'): load_inference(ROOT,output)


def test_cached_bundle_assembly_equals_actual_shared_pipeline(tmp_path):
    from scholarready.config import load_config
    from scholarready.pipeline import analyze
    from scholarready.schemas import ApplicantProfile, BundleInput
    from scholarready.evaluation.experiment import bundle_predictions
    paths=[f'tests/fixtures/pilot/src-{i:03d}.png' for i in range(1,6)]
    profile=ApplicantProfile(applicant_reference='fictional-regression',expected_name='Fictional Aster',category_certificate_required=True)
    result=analyze([ROOT/p for p in paths],config=load_config(ROOT/'configs/scholarship_demo.json'),
                   applicant=profile,output=tmp_path/'fresh')
    inputs=BundleInput(scenario_id='cache-regression',profile=profile,files=paths,declared_type_hints={})
    write_json(tmp_path/'inputs.json',inputs)
    predictions,_=bundle_predictions(ROOT,[dict(input_path=str(tmp_path/'inputs.json'))],dict(zip(paths,result.documents)))
    pred=predictions['cache-regression']
    assert pred['overall_state']==result.overall_state=='ready'
    assert pred['completeness']==result.completeness==100.
    assert pred['issues']==result.issues
    assert pred['evidence']==[r.model_dump(mode='json') for r in result.requirements]
