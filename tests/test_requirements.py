"""Reviewed scenario expectations and adversarial requirement/metric contracts."""
import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scholarready.config import load_config, ScholarshipConfig
from scholarready.evaluation.readiness_scenarios import predict_fixture, fixture_document
from scholarready.evaluation.readiness_metrics import readiness_metrics
from scholarready.requirements import evaluate, normalize_name
from scholarready.schemas import ApplicantProfile, ApplicationResult

ROOT=Path(__file__).resolve().parents[1]
INPUTS=json.loads((ROOT/'tests/fixtures/readiness/inputs.json').read_text())
REFERENCES=json.loads((ROOT/'tests/fixtures/readiness/references.json').read_text())
EXPECTED={r['scenario_id']:r for r in REFERENCES['scenarios']}


def config():
    return load_config(ROOT/'configs/scholarship_demo.json')


@pytest.mark.parametrize('spec',INPUTS['scenarios'],ids=lambda s:s['scenario_id'])
def test_reviewed_scenario(spec):
    result=predict_fixture(spec, INPUTS['base_documents'],config())
    ref=EXPECTED[spec['scenario_id']]
    assert result.overall_state==ref['overall_state']
    assert result.completeness==ref['completeness']
    assert {r.requirement_id:r.state for r in result.requirements}==ref['requirements']
    assert ApplicationResult.model_validate_json(result.model_dump_json())==result
    if ref['overall_state']!='ready':
        assert result.overall_state!='ready' and result.issues
    doc_ids={d.document_id for d in result.documents}
    page_ids={p.page_id for d in result.documents for p in d.pages}
    for r in result.requirements:
        assert set(r.document_references)<=doc_ids
        assert set(r.page_references)<=page_ids
        assert bool(r.actions)==(r.state not in {'satisfied','not_applicable'})


def test_names_preserve_person_role_and_spelling():
    assert normalize_name('  FICTIONAL—Aster ')=='fictional aster'
    assert normalize_name('Fictional Jose\u0301')==normalize_name('fictional José')
    assert normalize_name('F. Aster')!=normalize_name('Fictional Aster')
    assert normalize_name('Aster Fictional')!=normalize_name('Fictional Aster')
    assert normalize_name('José')!=normalize_name('Jose')


def test_required_role_cannot_be_guardian_even_with_same_string():
    d=fixture_document('d',[INPUTS['base_documents'][1]])
    f=next(f for f in d.fields if f.field_name=='applicant_name')
    f.person_role='guardian'
    c=config(); c.requirements=c.requirements[1:2]
    result=evaluate(c,ApplicantProfile(applicant_reference='fictional'),[d])
    assert result[0][0].state=='needs_review' and result[2]=='needs_review'


def test_duplicate_occurrence_ids_and_mutable_invalid_config():
    d=fixture_document('d',[INPUTS['base_documents'][1]])
    with pytest.raises(ValueError,match='document IDs'):
        evaluate(config(),ApplicantProfile(applicant_reference='fictional'),[d,d])
    c=config(); c.requirements[0].required_fields.append('annual_income')
    with pytest.raises(ValidationError):
        evaluate(c,ApplicantProfile(applicant_reference='fictional'),[d])


@pytest.mark.parametrize('changes',[
    [('issue_date','date_on_or_after','2026-02-30')],
    [('issue_date','date_on_or_after','20260115')],
    [('applicant_name','date_on_or_before','2026-01-15')],
    [('issue_date','unit_equals','days')],
    [('issue_date','date_on_or_after','2026-02-01'),('issue_date','date_on_or_before','2026-01-01')],
])
def test_config_rejects_bad_date_and_unit_constraints(changes):
    raw=config().model_dump(mode='json')
    raw['requirements'][1]['constraints']=[dict(field_name=n,kind=k,value=v) for n,k,v in changes]
    with pytest.raises(ValidationError): ScholarshipConfig.model_validate(raw)


def test_nested_ocr_failure_and_mixed_issue_preservation():
    d=fixture_document('d',[INPUTS['base_documents'][1]])
    d.ocr[0].reason='Simulated failed page'; d.ocr[0].status='error'
    c=config(); c.requirements=c.requirements[1:2]
    r,issues,state,score,_=evaluate(c,ApplicantProfile(applicant_reference='fictional'),[d])
    assert state=='needs_review' and r[0].state=='needs_review' and score==0.
    assert any('Simulated failed page' in issue for issue in issues)
    spec=next(s for s in INPUTS['scenarios'] if s['scenario_id']=='mixed_precedence')
    result=predict_fixture(spec,INPUTS['base_documents'],config())
    assert any('income:' in i for i in result.issues) and any('category:' in i for i in result.issues)


def test_empty_anchor_beside_another_label_is_review_not_simple_unreadability():
    spec=dict(scenario_id='competing_anchor', replace_lines={'1':{'3':'Annual income (INR/year):'}})
    result=predict_fixture(spec,INPUTS['base_documents'],config())
    field=next(f for f in result.documents[1].fields if f.field_name=='annual_income')
    assert field.validation_state=='ambiguous' and field.normalized_value is None
    assert result.requirements[1].state=='needs_review' and result.overall_state=='needs_review'


def test_metrics_known_confusions_and_false_ready_denominators():
    def row(key,a,b,x,y):
        return dict(scenario_id=key,reference=dict(overall_state=a,requirements={'income':x}),
                    predicted=dict(overall_state=b,requirements={'income':y}))
    rows=[row('a','ready','ready','satisfied','satisfied'),
          row('b','incomplete','ready','missing','satisfied'),
          row('c','needs_review','incomplete','needs_review','missing'),
          row('d','incomplete','incomplete','missing','missing'),
          row('e','needs_clearer_upload','needs_clearer_upload','unreadable','unreadable')]
    metrics=readiness_metrics(rows)
    app=metrics['application']; m=metrics['requirements']['missing_positive']
    assert app['agreement_count']==3 and app['agreement']==3/5
    assert app['false_ready_count']==1 and app['reference_non_ready_count']==4
    assert app['false_ready_rate']==1/4 and app['false_ready_share_among_predicted_ready']==1/2
    assert (m['tp'],m['fp'],m['fn'],m['tn'])==(1,1,1,2)
    assert m['precision']==m['recall']==m['f1']==.5
    assert metrics['requirements']['reference_support']['unreadable']==1
    with pytest.raises(ValueError,match='Duplicate'): readiness_metrics(rows+rows[:1])
    bad=copy.deepcopy(rows); bad[0]['predicted']['requirements']={}
    with pytest.raises(ValueError,match='IDs differ'): readiness_metrics(bad)
    bad=copy.deepcopy(rows); bad[0]['predicted']['overall_state']='approved'
    with pytest.raises(ValueError,match='Unknown'): readiness_metrics(bad)


def test_metric_empty_and_no_positive_support_are_null():
    metrics=readiness_metrics([])
    assert metrics['application']['false_ready_rate'] is None
    assert metrics['application']['agreement'] is None
    assert metrics['requirements']['missing_positive']['f1'] is None
    metrics=readiness_metrics([dict(scenario_id='only_ready',reference=dict(overall_state='ready',requirements={}),
        predicted=dict(overall_state='ready',requirements={}))])
    assert metrics['application']['false_ready_count']==0
    assert metrics['application']['false_ready_rate'] is None
    assert metrics['requirements']['agreement'] is None
