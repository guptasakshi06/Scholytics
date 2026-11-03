"""Fixed six-label macro-F1; abstentions remain false negatives in denominators."""
from collections import Counter
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from ..dataset import LABELS


def classification_metrics(truth, predictions):
    if len(truth) != len(predictions) or set(truth) - set(LABELS):
        raise ValueError('Classification targets must align and use the six fixed labels')
    guessed = [p.document_type if p.decision == 'classified' else '__unresolved__' for p in predictions]
    if truth:
        precision, recall, f1, support = precision_recall_fscore_support(
            truth, guessed, labels=list(LABELS), zero_division=0)
    else:
        precision, recall, f1, support = ([0] * len(LABELS) for _ in range(4))
    columns = [*LABELS, '__unresolved__']
    matrix = confusion_matrix(truth, guessed, labels=columns)[:len(LABELS)].tolist() if truth else [[0] * len(columns) for _ in LABELS]
    return dict(samples=len(truth), macro_f1=float(f1.mean()) if truth else None,
                accuracy=sum(t == p for t, p in zip(truth, guessed)) / len(truth) if truth else None,
                per_class={label: dict(precision=float(p), recall=float(r), f1=float(f), support=int(n))
                           for label, p, r, f, n in zip(LABELS, precision, recall, f1, support)},
                confusion_matrix=matrix, row_labels=list(LABELS), column_labels=columns,
                decisions=dict(Counter(p.decision for p in predictions)),
                unresolved=sum(d.decision != 'classified' for d in predictions))
