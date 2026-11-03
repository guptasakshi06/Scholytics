"""Spatial, conservative labelled-field extraction; inference never opens references."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
import re
import unicodedata

from .schemas import ExtractedField, FieldEvidence, FIELD_CATALOG, OCRResult, PageImage

VERSION = 'spatial-s06-1.0'
NORMALIZATION_VERSION = 'field-normalization-s06-1.0'
ANCHORS = {
    'student_name': r'(?:Student(?:[’\']s)? name|Name of (?:the )?student|Learner name)',
    'applicant_name': r'(?:Applicant(?:[’\']s)? name|Name of (?:the )?applicant)',
    'guardian_name': r'(?:Guardian name|Parent name|Father(?:[’\']s)? name|Mother(?:[’\']s)? name)',
    'institution': r'(?:Institution(?: name)?|College name|Name of (?:the )?(?:college|institution))',
    'academic_year': r'(?:Academic year|Academic session|Session)',
    'course': r'(?:Course(?: name)?|Programme|Program)',
    'annual_income': r'(?:(?:Annual|Monthly|Yearly) (?:family )?income(?:\s*\([^)]+\))?|Family income(?:\s*\([^)]+\))?)',
    'issue_date': r'(?:Issue date|Date of issue|Issued on)',
    'domicile_region': r'(?:Domicile region|State of domicile|Domicile state)',
    'stated_category': r'(?:Stated category|Category|Social category)',
    'stated_total': r'(?:Stated total|Total marks|Marks obtained|Grand total)',
    'stated_percentage': r'(?:Stated percentage|Percentage(?: obtained)?|Overall percentage)',
}
MIN_FIELD_ENGINE_SCORE = 50.0  # uncalibrated development heuristic
ABSENT_MARKERS = {'not stated', 'not provided', 'not applicable', 'n/a'}


class AmbiguousValue(ValueError):
    """Readable text admits multiple interpretations; no value is selected."""


def normalize(field: str, value: str):
    """Strict semantic normalization. No OCR spelling repair, fuzzy matching or defaults."""
    value = ' '.join(unicodedata.normalize('NFC', value).split())
    if field == 'issue_date':
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return date.fromisoformat(value).isoformat()
        # English month names are unambiguous; numeric local dates are not guessed.
        months = ('january february march april may june july august september october november december').split()
        match = re.fullmatch(r'(\d{1,2}) ([A-Za-z]+) (\d{4})', value)
        if match:
            month = match[2].casefold()
            choices = [i for i, name in enumerate(months, 1) if month in {name, name[:3]}]
            if choices:
                return date(int(match[3]), choices[0], int(match[1])).isoformat()
        if re.fullmatch(r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}', value):
            raise AmbiguousValue('Numeric local date order is unsupported; provide ISO or English month')
        raise ValueError('Invalid date; supported ISO YYYY-MM-DD or day English-month YYYY')
    if field == 'academic_year':
        match = re.fullmatch(r'(\d{4})\s*[-–/]\s*(\d{4})', value)
        if not match or int(match[2]) != int(match[1]) + 1:
            raise ValueError('Expected explicit consecutive YYYY-YYYY academic years')
        return f'{match[1]}-{match[2]}'
    if field in {'annual_income', 'stated_total', 'stated_percentage'}:
        if field == 'annual_income':
            value = re.sub(r'^(?:INR|Rs\.?|₹)\s*', '', value, flags=re.I)
        if field == 'stated_percentage':
            value = re.sub(r'\s*%$', '', value)
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?', value):
            raise ValueError('Expected a nonnegative explicit number with valid grouping; no guessed denominator')
        number = Decimal(value.replace(',', ''))
        if field == 'stated_percentage' and number > 100:
            raise ValueError('Printed percentage outside 0..100; decimal points are never reconstructed')
        if field == 'annual_income' and number == number.to_integral():
            return int(number)
        return format(number.normalize(), 'f')
    if field in {'student_name', 'applicant_name', 'guardian_name'}:
        if not any(c.isalpha() for c in value) or any(not (c.isalpha() or c in " .'-’") for c in value):
            raise ValueError('Unsupported name characters; no guessed OCR correction')
    return value


def _box(tokens):
    x, y = min(t.box[0] for t in tokens), min(t.box[1] for t in tokens)
    return [x, y, max(t.box[0] + t.box[2] for t in tokens) - x,
            max(t.box[1] + t.box[3] for t in tokens) - y]


def _role(field):
    return 'guardian' if field == 'guardian_name' else 'applicant' if field in {'student_name', 'applicant_name'} else None


def _segments(tokens):
    """Locate labels by text offsets, retaining exact originating word tokens."""
    text = ' '.join(t.text for t in tokens)
    anchors = []
    for field, pattern in ANCHORS.items():
        for m in re.finditer(r'(?<!\w)(?:' + pattern + r')(?=\s*:|\s*$)', text, re.I):
            anchors.append((m.start(), m.end(), field))
    # Nested synonyms (e.g. Category within Social category) belong to the longest anchor.
    anchors = [a for a in anchors if not any(b[0] <= a[0] and b[1] >= a[1] and b != a for b in anchors)]
    anchors.sort()
    offsets, pos = [], 0
    for token in tokens:
        offsets.append((pos, pos + len(token.text), token)); pos += len(token.text) + 1
    for index, (start, end, field) in enumerate(anchors):
        stop = anchors[index + 1][0] if index + 1 < len(anchors) else len(text)
        raw = text[end:stop].strip().lstrip(':').strip()
        evidence = [t for left, right, t in offsets if right > start and left < stop]
        yield field, text[start:end], raw, evidence, len(anchors)


def _income_unit(label, raw):
    full = label + ' ' + raw
    annual = bool(re.search(r'\b(?:annual|yearly|year)\b', full, re.I))
    monthly = bool(re.search(r'\b(?:monthly|month)\b', full, re.I))
    currency = bool(re.search(r'\bINR\b|\bRs\.?|₹', full, re.I))
    if annual == monthly or not currency:
        raise AmbiguousValue('Income needs one explicit annual/monthly period and INR currency; no annualization')
    return 'INR/' + ('year' if annual else 'month')


def extract(document_type: str | None, pages: list[PageImage], results: list[OCRResult],
            requested_fields: list[str] | None = None) -> list[ExtractedField]:
    """Default catalog for a resolved type; optional explicit requests return unsupported states."""
    supported = FIELD_CATALOG.get(document_type, set())
    requested = set(requested_fields) if requested_fields is not None else supported
    page_map = {p.page_id: p for p in pages}
    candidates = defaultdict(list)
    incomplete = {r.page_id for r in results} != set(page_map) or any(r.status == 'error' for r in results) or len(results) != len(pages)
    for result in results:
        if result.status != 'ok':
            continue
        page = page_map[result.page_id]
        groups = defaultdict(list)
        for token in result.tokens:
            if token.page_id != result.page_id:
                raise ValueError('Token page does not match OCR page')
            groups[(token.coordinate_space, token.block_id, token.line_id)].append(token)
        lines = []
        for (_, _, line_id), ts in groups.items():
            if line_id is not None:
                lines.append(sorted(ts, key=lambda t: (t.box[0], t.token_id)))
                continue
            # Fallback for OCR providers without line IDs: physical rows, in one space/block.
            rows = []
            for token in sorted(ts, key=lambda t: (t.box[1] + t.box[3] / 2, t.box[0])):
                cy = token.box[1] + token.box[3] / 2
                if rows and abs(cy - (rows[-1][0].box[1] + rows[-1][0].box[3] / 2)) <= max(token.box[3], rows[-1][0].box[3]) * .6:
                    rows[-1].append(token)
                else:
                    rows.append([token])
            lines.extend(sorted(row, key=lambda t: (t.box[0], t.token_id)) for row in rows)
        lines.sort(key=lambda ts: (_box(ts)[1], _box(ts)[0]))
        for tokens in lines:
            for field, label, raw, evidence, anchor_count in _segments(tokens):
                if field not in supported & requested:
                    continue
                method = 'same-line label/value'
                spatial_ambiguous = any(
                    right.box[0] - left.box[0] - left.box[2] > page.width * .12
                    for left, right in zip(evidence, evidence[1:]))
                if not raw:
                    lb = _box(evidence)
                    nearby = []
                    for other in lines:
                        if other is tokens or other[0].coordinate_space != tokens[0].coordinate_space:
                            continue
                        vb = _box(other); gap = vb[1] - lb[1] - lb[3]
                        # Bounded aligned region; never walk to an arbitrary next TSV line/column.
                        if (0 <= gap <= min(page.height * .06, lb[3] * 3)
                                and abs(vb[0] - lb[0]) <= page.width * .04):
                            txt = ' '.join(t.text for t in other)
                            nearby.append((other, txt))
                    # A label/unknown colon heading blocks region inference; do not skip over it.
                    if len(nearby) == 1 and not list(_segments(nearby[0][0])) and ':' not in nearby[0][1] and anchor_count == 1:
                        raw = nearby[0][1]; evidence += nearby[0][0]; method = 'bounded aligned below-label region'
                    elif nearby:
                        spatial_ambiguous = True
                score_values = [t.engine_score for t in evidence]
                score = min(score_values) if score_values and all(s is not None for s in score_values) else None
                normalized, unit = None, None
                state, reason = 'valid', method
                if spatial_ambiguous:
                    state, reason = 'ambiguous', 'Nearby region has competing lines/labels; no value selected'
                elif not raw:
                    state, reason = 'unreadable', 'Label seen without a supported readable value'
                elif raw.casefold() in ABSENT_MARKERS:
                    state, reason = 'absent', 'Explicit printed absence marker; no inferred physical absence'
                else:
                    try:
                        normalized = normalize(field, raw)
                        if field == 'annual_income':
                            unit = _income_unit(label, raw)
                            reason += '; printed period retained without annualization'
                        elif field == 'stated_percentage':
                            unit = '%'
                    except AmbiguousValue as exc:
                        state, reason = 'ambiguous', str(exc)
                    except ValueError as exc:
                        state, reason = 'invalid', str(exc)
                if score is None or score < MIN_FIELD_ENGINE_SCORE:
                    state, reason = 'unreadable', 'Missing/low OCR token score under development heuristic (50)'
                candidates[field].append(FieldEvidence(field_name=field, person_role=_role(field),
                    raw_text=raw or None, normalized_value=normalized if state == 'valid' else None, unit=unit,
                    page_id=result.page_id, filename=page.original_filename,
                    token_references=[t.token_id for t in evidence], boxes=[t.box for t in evidence],
                    coordinate_space=evidence[0].coordinate_space, engine_score=score,
                    validation_state=state, reason=reason))
    fields = []
    for field in sorted(requested):
        found = candidates[field]
        if found:
            chosen = found[0].model_dump(exclude={'schema_version'})
            signatures = {(str(f.normalized_value), f.unit, f.validation_state, f.raw_text if f.validation_state != 'valid' else None) for f in found}
            if len(signatures) > 1:
                chosen.update(normalized_value=None, validation_state='ambiguous',
                              reason='Conflicting repeated labels; all candidates retained, no first-value choice')
            elif len(found) > 1:
                chosen['reason'] += '; repeated agreeing values, all candidates retained'
            if incomplete:
                chosen.update(normalized_value=None, validation_state='unreadable', reason='Incomplete OCR pages could contain conflicting evidence')
        else:
            chosen = dict(field_name=field, person_role=_role(field), raw_text=None, normalized_value=None,
                unit=None, page_id=None, filename=None, token_references=[], boxes=[],
                coordinate_space=None, engine_score=None, validation_state='unreadable' if field in supported else 'unsupported',
                reason='No supported readable label/value; physical absence cannot be inferred' if field in supported else 'Field is outside the resolved document type catalog')
        fields.append(ExtractedField(**chosen, extraction_version=VERSION,
            normalization_rule=f'{NORMALIZATION_VERSION}:{field}',
            score_source='minimum OCR token engine score (uncalibrated); engine provenance in OCRResult', candidates=found))
    return fields
