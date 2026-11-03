"""Readiness metrics with explicit supports; references are post-inference only."""
from collections import Counter

REQUIREMENT_STATES = ('satisfied', 'missing', 'unreadable', 'needs_review', 'not_applicable')
OVERALL_STATES = ('ready', 'incomplete', 'needs_clearer_upload', 'needs_review')


def readiness_metrics(rows: list[dict]) -> dict:
    """Each row: scenario_id, reference/predicted overall and requirement-state maps.

    Exact same item IDs are required: dropping a failed prediction is an error.
    Confirmed missing is positive. All five reference states stay in accounting,
    including conditional/review cases; they are not silently excluded negatives.
    """
    seen = set()
    app = {a: {b: 0 for b in OVERALL_STATES} for a in OVERALL_STATES}
    req = {a: {b: 0 for b in REQUIREMENT_STATES} for a in REQUIREMENT_STATES}
    counts = Counter()
    for row in rows:
        key = row['scenario_id']
        if key in seen:
            raise ValueError('Duplicate readiness scenario')
        seen.add(key)
        reference, predicted = row['reference'], row['predicted']
        a, b = reference['overall_state'], predicted['overall_state']
        if a not in app or b not in app:
            raise ValueError('Unknown application outcome')
        app[a][b] += 1
        counts['agreement'] += int(a == b)
        counts['reference_non_ready'] += int(a != 'ready')
        counts['false_ready'] += int(a != 'ready' and b == 'ready')
        counts['predicted_ready'] += int(b == 'ready')
        if set(reference['requirements']) != set(predicted['requirements']):
            raise ValueError('Requirement IDs differ; failed/missing outputs must remain in accounting')
        for item, actual in reference['requirements'].items():
            guess = predicted['requirements'][item]
            if actual not in req or guess not in req:
                raise ValueError('Unknown requirement state')
            req[actual][guess] += 1
            counts['items'] += 1
            counts['item_agreement'] += int(actual == guess)
            counts['tp'] += int(actual == 'missing' and guess == 'missing')
            counts['fp'] += int(actual != 'missing' and guess == 'missing')
            counts['fn'] += int(actual == 'missing' and guess != 'missing')
            counts['tn'] += int(actual != 'missing' and guess != 'missing')
    def ratio(n, d):
        return n / d if d else None
    tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
    return dict(
        scenarios=len(rows), requirement_items=counts['items'],
        application=dict(agreement_count=counts['agreement'], agreement=ratio(counts['agreement'], len(rows)),
            confusion=app, reference_support={a: sum(v.values()) for a, v in app.items()},
            false_ready_count=counts['false_ready'], reference_non_ready_count=counts['reference_non_ready'],
            false_ready_rate=ratio(counts['false_ready'], counts['reference_non_ready']),
            predicted_ready_count=counts['predicted_ready'],
            false_ready_share_among_predicted_ready=ratio(counts['false_ready'], counts['predicted_ready'])),
        requirements=dict(agreement_count=counts['item_agreement'], agreement=ratio(counts['item_agreement'], counts['items']),
            confusion=req, reference_support={a: sum(v.values()) for a, v in req.items()},
            predicted_support={b: sum(req[a][b] for a in req) for b in req},
            missing_positive=dict(tp=tp, fp=fp, fn=fn, tn=counts['tn'],
                reference_missing_count=tp+fn, predicted_missing_count=tp+fp,
                precision=ratio(tp, tp+fp), recall=ratio(tp, tp+fn), f1=ratio(2*tp, 2*tp+fp+fn))),
        zero_denominator='null means not estimable; raw counts retained',
        scope='Specified development scenarios, not population performance; unresolved and conditional states retained')
