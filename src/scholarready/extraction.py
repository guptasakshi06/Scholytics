"""Small label-anchor baseline; no reference files, guessed defaults or global regex scans."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from .schemas import ExtractedField, FIELD_CATALOG, OCRResult, PageImage

ANCHORS = {
    'student_name': r'Student name', 'applicant_name': r'Applicant name',
    'guardian_name': r'Guardian name', 'institution': r'Institution',
    'academic_year': r'Academic year', 'course': r'Course',
    'annual_income': r'(?:Annual|Monthly) income(?:\s*\(([^)]+)\))?',
    'issue_date': r'Issue date', 'domicile_region': r'Domicile region',
    'stated_category': r'Stated category', 'stated_total': r'Stated total',
    'stated_percentage': r'Stated percentage',
}
MIN_FIELD_ENGINE_SCORE = 50.0  # conservative development heuristic, not calibrated


def normalize(field: str, value: str):
    value = ' '.join(value.split())
    if field == 'issue_date':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Only an unambiguous ISO YYYY-MM-DD date is supported')
        return date.fromisoformat(value).isoformat()
    if field == 'academic_year':
        if not re.fullmatch(r'\d{4}-\d{4}', value):
            raise ValueError('Expected explicitly labelled YYYY-YYYY academic year')
    if field in {'annual_income', 'stated_total', 'stated_percentage'}:
        # Accept only explicit numeric values. No guessed denominator or units.
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?', value):
            raise ValueError('Ambiguous/non-numeric labelled amount')
        try:
            number = Decimal(value.replace(',', ''))
        except InvalidOperation as exc:
            raise ValueError('Invalid number') from exc
        if field == 'annual_income' and number == number.to_integral():
            return int(number)
        return format(number.normalize(), 'f')
    return value


def _box(tokens):
    x = min(t.box[0] for t in tokens)
    y = min(t.box[1] for t in tokens)
    return [x, y, max(t.box[0] + t.box[2] for t in tokens) - x,
            max(t.box[1] + t.box[3] for t in tokens) - y]


def extract(document_type: str | None, pages: list[PageImage], results: list[OCRResult]) -> list[ExtractedField]:
    if document_type not in FIELD_CATALOG:
        return []
    page_map = {p.page_id: p for p in pages}
    candidates = defaultdict(list)
    for result in results:
        groups = defaultdict(list)
        for token in result.tokens:
            groups[token.line_id].append(token)
        lines = list(groups.values())
        for index, tokens in enumerate(lines):
            text = ' '.join(t.text for t in tokens)
            for field in FIELD_CATALOG[document_type]:
                match = re.fullmatch(r'\s*' + ANCHORS[field] + r'\s*(?::\s*(.*))?', text, re.I)
                if not match:
                    continue
                value = match.groups()[-1]
                evidence = tokens
                if value is None and index + 1 < len(lines):
                    following = lines[index + 1]
                    label_box, value_box = _box(tokens), _box(following)
                    next_text = ' '.join(t.text for t in following)
                    # Next-line values must be nearby and cannot be another known label.
                    is_label = any(re.fullmatch(pattern + r'\s*:?', next_text, re.I) for pattern in ANCHORS.values())
                    gap = value_box[1] - label_box[1] - label_box[3]
                    if (not is_label and 0 <= gap <= page_map[result.page_id].height * .06
                            and value_box[0] >= label_box[0] - 10):
                        value, evidence = next_text, tokens + following
                if not value or not value.strip():
                    continue
                value = value.strip()
                unit = None
                if field == 'annual_income':
                    unit_match = re.search(r'\((INR/(?:year|month))\)', text, re.I)
                    unit = unit_match.group(1) if unit_match else None
                    if unit:
                        unit = 'INR/' + unit.split('/')[1].lower()
                elif field == 'stated_percentage':
                    unit = '%'
                scores = [t.engine_score for t in evidence if t.engine_score is not None]
                score = min(scores) if scores else None
                state, reason, normalized = 'valid', 'Label anchor; whitespace/field-format normalization only', None
                try:
                    normalized = normalize(field, value)
                except ValueError as exc:
                    state, reason = 'invalid', str(exc)
                if score is None or score < MIN_FIELD_ENGINE_SCORE:
                    state, reason = 'unreadable', 'Missing/low Tesseract score under development field heuristic (50)'
                candidates[field].append(dict(
                    field_name=field, person_role=('guardian' if field == 'guardian_name' else
                        'applicant' if field in {'student_name', 'applicant_name'} else None),
                    raw_text=value, normalized_value=normalized if state == 'valid' else None,
                    unit=unit, page_id=result.page_id, filename=page_map[result.page_id].original_filename,
                    token_references=[t.token_id for t in evidence], boxes=[_box(evidence)],
                    coordinate_space=evidence[0].coordinate_space, engine_score=score,
                    validation_state=state, reason=reason))
    fields = []
    for field in sorted(FIELD_CATALOG[document_type]):
        found = candidates[field]
        if not found:
            fields.append(ExtractedField(
                field_name=field, person_role=('guardian' if field == 'guardian_name' else
                    'applicant' if field in {'student_name', 'applicant_name'} else None),
                raw_text=None, normalized_value=None, unit=None, page_id=None, filename=None,
                token_references=[], boxes=[], coordinate_space=None, engine_score=None,
                validation_state='unreadable',
                reason='No supported readable label/value anchor; absence cannot be inferred from OCR'))
            continue
        chosen = found[0]
        signatures = {(str(f['normalized_value']), f['unit'], f['validation_state']) for f in found}
        if len(signatures) > 1:
            chosen = dict(chosen, normalized_value=None, validation_state='ambiguous',
                          reason='Conflicting/repeated label values across document lines/pages')
        elif len(found) > 1:
            chosen = dict(chosen, reason='Repeated agreeing labelled values; first-page evidence retained')
        fields.append(ExtractedField(**chosen))
    return fields
