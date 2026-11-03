"""Semantic/adversarial OCR token fixtures, separate from actual OCR integration."""
import pytest
from scholarready.classification import classify
from scholarready.extraction import extract
from scholarready.schemas import OCRToken, OCRResult, PageImage


def page_and_ocr(lines):
    page = PageImage(document_id='doc', page_id='p1', page_index=1, original_filename='arbitrary.png',
        width=1200, height=1600, color_space='RGB', rasterization_dpi=None,
        original_image_path='p1.png', coordinate_space='p1:original')
    tokens = []
    for line_id, text in enumerate(lines, 1):
        x = 80.
        for word in text.split():
            tokens.append(OCRToken(token_id=f't{len(tokens)}', text=word, box=[x, float(line_id * 50), 30., 20.],
                page_id='p1', coordinate_space='p1:original', line_id=line_id, block_id=1, engine_score=95.))
            x += 35.
    result = OCRResult(page_id='p1', branch_id='A', text='\n'.join(lines), tokens=tokens,
        engine='fixture', engine_version='fixture-1', language='eng', settings={}, runtime_seconds=0.,
        status='ok' if tokens else 'empty', reason=None if tokens else 'Blank fixture')
    return page, result


@pytest.mark.parametrize('lines,decision,label', [
    ([], 'unreadable', None), (['random unfamiliar document'], 'uncertain', None),
    (['INCOME CERTIFICATE', 'DOMICILE CERTIFICATE'], 'uncertain', None),
    (['INCOME CERTIFICATE'], 'classified', 'income_certificate'),
    (['LIBRARY NOTICE'], 'classified', 'other'),
])
def test_classification_never_uses_filename(lines, decision, label):
    _, ocr = page_and_ocr(lines)
    prediction = classify([ocr], [])
    assert (prediction.decision, prediction.document_type) == (decision, label)
    assert prediction.score_kind == 'keyword_score'
    assert classify([ocr], ['page failed']).decision == 'error'


def test_anchors_roles_units_and_no_defaults():
    page, ocr = page_and_ocr(['INCOME CERTIFICATE', 'Guardian name: Fictional Guardian',
        'Applicant name: Fictional Applicant', 'Monthly income (INR/month): 8,000', 'Issue date: 2026-01-15'])
    fields = {f.field_name: f for f in extract('income_certificate', [page], [ocr])}
    assert fields['guardian_name'].person_role == 'guardian'
    assert fields['applicant_name'].normalized_value == 'Fictional Applicant'
    assert fields['annual_income'].normalized_value == 8000
    assert fields['annual_income'].unit == 'INR/month'
    assert all(f.token_references and f.boxes for f in fields.values())
    _, other_ocr = page_and_ocr(['INCOME CERTIFICATE', 'Guardian name: Someone', 'A date 2026-01-15'])
    unresolved = {f.field_name: f for f in extract('income_certificate', [page], [other_ocr])}
    assert unresolved['applicant_name'].normalized_value is None
    assert unresolved['issue_date'].normalized_value is None


def test_two_line_layout_duplicate_and_invalid_dates():
    page, ocr = page_and_ocr(['DOMICILE CERTIFICATE', 'Applicant name', 'Fictional Aster',
        'Domicile region', 'Fictional Region', 'Issue date: 2026-02-30'])
    fields = {f.field_name: f for f in extract('domicile_certificate', [page], [ocr])}
    assert fields['applicant_name'].normalized_value == 'Fictional Aster'
    assert fields['issue_date'].validation_state == 'invalid'
    assert fields['issue_date'].normalized_value is None
    page, ocr = page_and_ocr(['Applicant name: Aster', 'Applicant name: Birch'])
    field = next(f for f in extract('income_certificate', [page], [ocr]) if f.field_name == 'applicant_name')
    assert field.validation_state == 'ambiguous' and field.normalized_value is None


def test_empty_anchor_does_not_steal_another_label_or_distant_line():
    page, ocr = page_and_ocr(['Student name', 'Institution', 'College', 'Academic year', '2025-2026'])
    fields = {f.field_name: f for f in extract('marksheet', [page], [ocr])}
    assert fields['student_name'].normalized_value is None
    assert fields['institution'].normalized_value == 'College'
    page, ocr = page_and_ocr(['Student name', 'Far footer'])
    for token in ocr.tokens:
        if token.line_id == 2:
            token.box[1] = 1500.
    assert next(f for f in extract('marksheet', [page], [ocr]) if f.field_name == 'student_name').normalized_value is None


def test_low_score_remains_null():
    page, ocr = page_and_ocr(['Applicant name: Fictional Aster'])
    ocr.tokens[-1].engine_score = 10.
    field = next(f for f in extract('income_certificate', [page], [ocr]) if f.field_name == 'applicant_name')
    assert field.validation_state == 'unreadable' and field.normalized_value is None
