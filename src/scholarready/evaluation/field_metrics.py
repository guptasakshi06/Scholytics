"""Exact semantic field metrics; all present reference targets stay in the denominator."""
from collections import Counter, defaultdict

from ..schemas import ExtractedField


def field_metrics(rows: list[dict]) -> dict:
    """Rows contain sample_id, document_type, reference fields and actual predicted fields.

    Reference state present/absent is supplied only after inference. Values are already
    canonical annotations; scoring never fuzzy-matches or repairs a wrong OCR value.
    """
    groups = defaultdict(Counter)
    totals = Counter()
    seen = set()
    for row in rows:
        if row['sample_id'] in seen:
            raise ValueError('Duplicate field metric sample')
        seen.add(row['sample_id'])
        predictions = [ExtractedField.model_validate(p) if isinstance(p, dict) else p for p in row['predictions']]
        names = [p.field_name for p in predictions]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate field prediction')
        predictions = {p.field_name: p for p in predictions}
        references = row['reference']
        for name in sorted(set(references) | set(predictions)):
            counts = Counter()
            ref, pred = references.get(name), predictions.get(name)
            valid = pred is not None and pred.validation_state == 'valid'
            if ref is None:
                counts['extra_schema_output'] += 1
                counts['extra_nonnull_output'] += int(valid)
            else:
                if ref['state'] not in {'present', 'absent', 'unreadable'}:
                    raise ValueError('Reference field must explicitly be present, absent or unreadable')
                if ref['state'] == 'present':
                    if ref['normalized_value'] is None:
                        raise ValueError('Present reference requires a normalized value')
                    counts['present_support'] += 1
                    counts['missing_prediction'] += int(not valid)
                    counts['exact_value'] += int(valid and pred.normalized_value == ref['normalized_value'])
                    counts['exact_value_unit_role'] += int(valid and pred.normalized_value == ref['normalized_value']
                        and pred.unit == ref['unit'] and pred.person_role == ref['person_role'])
                    counts['wrong_nonnull'] += int(valid and not (pred.normalized_value == ref['normalized_value']
                        and pred.unit == ref['unit'] and pred.person_role == ref['person_role']))
                elif ref['state'] == 'absent':
                    counts['absent_support'] += 1
                    counts['extra_nonnull_output'] += int(valid)
                    counts['explicit_absent_correct'] += int(pred is not None and pred.validation_state == 'absent')
                else:
                    counts['unreadable_reference_support'] += 1
                counts['no_field_output'] += int(pred is None)
            if pred is not None:
                counts['state_' + pred.validation_state] += 1
            groups[row['document_type'] + ':' + name].update(counts)
            totals.update(counts)
    keys = ('unreadable_reference_support', 'present_support', 'absent_support', 'exact_value', 'exact_value_unit_role', 'missing_prediction',
            'wrong_nonnull', 'extra_nonnull_output', 'extra_schema_output', 'explicit_absent_correct', 'no_field_output')
    def report(counts):
        result = {k: counts[k] for k in keys}
        result.update({k: v for k, v in sorted(counts.items()) if k.startswith('state_')})
        support = counts['present_support']
        result['normalized_exact_match'] = counts['exact_value_unit_role'] / support if support else None
        return result
    return dict(samples=len(rows), overall=report(totals), by_type_field={k: report(v) for k, v in sorted(groups.items())})
