"""Semantic adversarial token fixtures; actual Tesseract is checked separately."""
from copy import deepcopy
import pytest
from PIL import Image
from scholarready.evidence import draw_evidence
from scholarready.extraction import extract, normalize, AmbiguousValue
from scholarready.evaluation.field_metrics import field_metrics
from scholarready.schemas import ExtractedField
from test_baselines import page_and_ocr


def fields(kind, lines):
    page, ocr = page_and_ocr(lines)
    return {f.field_name: f for f in extract(kind, [page], [ocr])}


@pytest.mark.parametrize('field,raw,expected', [
    ('issue_date', '15 January 2026', '2026-01-15'),
    ('issue_date', '15 Jan 2026', '2026-01-15'),
    ('academic_year', '2025 / 2026', '2025-2026'),
    ('annual_income', 'INR 1,20,000', 120000),
    ('stated_percentage', '72.50 %', '72.5'),
    ('student_name', "  Fictional  O’Neil  ", 'Fictional O’Neil'),
])
def test_normalization(field, raw, expected):
    assert normalize(field, raw) == expected


@pytest.mark.parametrize('field,raw', [('issue_date', '2026-02-30'), ('issue_date', '01/02/2026'),
    ('academic_year', '2026-2025'), ('stated_percentage', '725'), ('stated_percentage', '72..5'),
    ('stated_total', '400/500'), ('annual_income', '12,00'), ('student_name', 'A5ter')])
def test_no_guessed_repair(field, raw):
    with pytest.raises(ValueError):
        normalize(field, raw)


def test_roles_synonyms_and_multiple_dates():
    result = fields('income_certificate', ["Father's name: Fictional Guardian", 'Name of applicant: Fictional Aster',
        'Date of birth: 2004-01-01', 'Issued on: 15 Jan 2026', 'Expiry date: 2027-01-15',
        'Yearly family income (INR/year): 1,20,000'])
    assert result['applicant_name'].normalized_value == 'Fictional Aster'
    assert result['guardian_name'].person_role == 'guardian'
    assert result['issue_date'].normalized_value == '2026-01-15'
    assert result['annual_income'].unit == 'INR/year'
    assert result['annual_income'].normalized_value == 120000


def test_two_columns_same_line_and_different_tsv_blocks():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster Guardian name: Fictional Birch'])
    values = extract('income_certificate', [page], [ocr])
    assert {f.field_name: f.normalized_value for f in values}['applicant_name'] == 'Fictional Aster'
    assert next(f for f in values if f.field_name == 'guardian_name').normalized_value == 'Fictional Birch'
    page, ocr = page_and_ocr(['Applicant name:', 'Fictional Aster', 'Guardian name: Fictional Birch'])
    # Deliberately equal line IDs in different blocks must not merge names.
    for token in ocr.tokens:
        token.block_id = token.line_id
        token.line_id = 1
    assert next(f for f in extract('income_certificate', [page], [ocr]) if f.field_name == 'applicant_name').normalized_value == 'Fictional Aster'


def test_missing_summary_cropped_label_and_unfamiliar_layout():
    result = fields('marksheet', ['Subject marks: 80', 'Total pages: 2', 'udent name: Fictional Aster',
        'Learner designation: Fictional Aster', 'Percentage: 72.5'])
    assert result['stated_total'].validation_state == 'unreadable'
    assert result['student_name'].normalized_value is None
    assert result['stated_percentage'].normalized_value == '72.5'


def test_absence_is_only_printed_marker_and_unsupported_is_explicit():
    assert fields('marksheet', ['Stated total: not stated'])['stated_total'].validation_state == 'absent'
    assert fields('marksheet', [])['stated_total'].validation_state == 'unreadable'
    page, ocr = page_and_ocr(['Student name: Fictional Aster'])
    assert extract('other', [page], [ocr], ['student_name'])[0].validation_state == 'unsupported'
    assert extract('marksheet', [page], [ocr], ['issue_date'])[0].validation_state == 'unsupported'


def test_conflicts_preserve_all_pages_and_candidates():
    page, ocr = page_and_ocr(['Issued on: 2026-01-15', 'Issue date: 2026-02-15'])
    field = next(f for f in extract('domicile_certificate', [page], [ocr]) if f.field_name == 'issue_date')
    assert field.normalized_value is None and field.validation_state == 'ambiguous'
    assert [c.raw_text for c in field.candidates] == ['2026-01-15', '2026-02-15']
    page2, ocr2 = deepcopy(page), deepcopy(ocr)
    page2.page_id = 'p2'
    data = ocr2.model_dump(); data['page_id'] = 'p2'
    for t in data['tokens']:
        t['page_id'] = 'p2'; t['token_id'] += '-p2'; t['coordinate_space'] = 'p2:processed'
    ocr2 = type(ocr2).model_validate(data)
    page2.original_filename = 'second.png'
    field = next(f for f in extract('domicile_certificate', [page, page2], [ocr, ocr2]) if f.field_name == 'issue_date')
    assert {c.filename for c in field.candidates} == {'arbitrary.png', 'second.png'}
    assert len(field.candidates) == 4


def test_competing_below_label_regions_are_ambiguous():
    page, ocr = page_and_ocr(['Applicant name', 'Fictional Aster', 'Fictional Birch'])
    for t in ocr.tokens:
        if t.line_id == 3:
            t.box[1] = 110
    field = next(f for f in extract('income_certificate', [page], [ocr]) if f.field_name == 'applicant_name')
    assert field.normalized_value is None and field.validation_state == 'ambiguous'


def test_incomplete_page_does_not_hide_conflict():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster'])
    page2 = deepcopy(page); page2.page_id = 'p2'
    field = next(f for f in extract('income_certificate', [page, page2], [ocr]) if f.field_name == 'applicant_name')
    assert field.validation_state == 'unreadable' and field.normalized_value is None


@pytest.mark.parametrize('label,state,unit', [
    ('Monthly income (INR/month)', 'valid', 'INR/month'),
    ('Annual income (INR/month)', 'ambiguous', None),
    ('Annual income', 'ambiguous', None),
    ('Family income (INR)', 'ambiguous', None),
])
def test_income_unit_never_guessed(label, state, unit):
    field = fields('income_certificate', [label + ': 8000'])['annual_income']
    assert field.validation_state == state and field.unit == unit
    assert field.normalized_value == (8000 if state == 'valid' else None)


def test_low_score_faint_decimal_is_null_and_cannot_be_repaired():
    page, ocr = page_and_ocr(['Stated percentage: 72.5'])
    ocr.tokens[-1].engine_score = 20
    field = next(f for f in extract('marksheet', [page], [ocr]) if f.field_name == 'stated_percentage')
    assert field.raw_text == '72.5' and field.validation_state == 'unreadable'
    assert fields('marksheet', ['Stated percentage: 725'])['stated_percentage'].validation_state == 'invalid'


def test_metric_denominator_extra_and_units_roles():
    pred = fields('income_certificate', ['Applicant name: Fictional Aster', 'Monthly income (INR/month): 8000'])
    reference = {name: dict(state='present', normalized_value=value, unit=unit, person_role=role)
        for name, value, unit, role in [('applicant_name', 'Fictional Aster', None, 'applicant'),
            ('annual_income', 8000, 'INR/year', None), ('issue_date', '2026-01-15', None, None)]}
    reference['guardian_name'] = dict(state='absent', normalized_value=None, unit=None, person_role='guardian')
    metric = field_metrics([dict(sample_id='s', document_type='income_certificate', reference=reference, predictions=list(pred.values()))])['overall']
    assert metric['present_support'] == 3 and metric['exact_value_unit_role'] == 1
    assert metric['exact_value'] == 2 and metric['wrong_nonnull'] == 1 and metric['missing_prediction'] == 1
    assert field_metrics([])['overall']['normalized_exact_match'] is None
    reference['annual_income']['state'] = 'absent'
    metric = field_metrics([dict(sample_id='s', document_type='income_certificate', reference=reference, predictions=list(pred.values()))])['overall']
    assert metric['extra_nonnull_output'] == 1
    with pytest.raises(ValueError, match='Duplicate field'):
        field_metrics([dict(sample_id='s', document_type='income_certificate', reference=reference, predictions=[pred['annual_income']] * 2)])


def test_overlay_refuses_wrong_space_and_boxes_trace_to_exact_tokens():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster'])
    values = extract('income_certificate', [page], [ocr]); field = values[0]
    token_map = {t.token_id: t for t in ocr.tokens}
    assert field.boxes == [token_map[t].box for t in field.token_references]
    assert field.extraction_version and field.normalization_rule and field.score_source
    assert ExtractedField.model_validate_json(field.model_dump_json()) == field
    with pytest.raises(ValueError, match='coordinate space'):
        draw_evidence(Image.new('RGB', (1200, 1600)), values, page_id=page.page_id, coordinate_space='wrong')
    assert draw_evidence(Image.new('RGB', (1200, 1600)), values, page_id=page.page_id, coordinate_space=page.coordinate_space).size == (1200, 1600)


def test_category_title_is_not_a_field_anchor():
    result = fields('category_certificate', ['CATEGORY CERTIFICATE', 'Category: DEMO GROUP A'])
    assert result['stated_category'].normalized_value == 'DEMO GROUP A'
    assert len(result['stated_category'].candidates) == 1


def test_missing_line_ids_use_geometry_and_far_columns_are_unresolved():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster', 'Guardian name: Fictional Birch'])
    for token in ocr.tokens:
        token.line_id = None
    actual = {f.field_name: f for f in extract('income_certificate', [page], [ocr])}
    assert actual['applicant_name'].normalized_value == 'Fictional Aster'
    assert actual['guardian_name'].normalized_value == 'Fictional Birch'
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster'])
    for token in ocr.tokens[2:]:
        token.box[0] += 800
    actual = next(f for f in extract('income_certificate', [page], [ocr]) if f.field_name == 'applicant_name')
    assert actual.validation_state == 'ambiguous' and actual.normalized_value is None


def test_routing_abstention_keeps_present_target_denominator():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster'])
    reference = {'applicant_name': dict(state='present', normalized_value='Fictional Aster', unit=None, person_role='applicant')}
    def score(kind):
        return field_metrics([dict(sample_id='s', document_type='income_certificate', reference=reference,
            predictions=extract(kind, [page], [ocr], ['applicant_name']) if kind else [])])['overall']
    assert score('income_certificate')['exact_value_unit_role'] == 1
    assert score(None)['present_support'] == score('income_certificate')['present_support'] == 1
    assert score(None)['missing_prediction'] == score(None)['no_field_output'] == 1
    assert score(None)['normalized_exact_match'] == 0


def test_conflicting_candidates_are_drawn_as_unresolved():
    page, ocr = page_and_ocr(['Issue date: 2026-01-15', 'Issue date: 2026-02-15'])
    values = extract('domicile_certificate', [page], [ocr])
    image = draw_evidence(Image.new('RGB', (1200, 1600)), values,
        page_id=page.page_id, coordinate_space=page.coordinate_space)
    assert image.getpixel((80, 50)) == (178, 35, 35)
