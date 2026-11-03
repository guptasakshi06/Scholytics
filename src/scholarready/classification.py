"""Literal title keyword baseline. Only OCR text is a feature."""
import re
from .schemas import DocumentPrediction, OCRResult

KEYWORDS = {
    'marksheet': ('academic marksheet', 'marksheet'),
    'income_certificate': ('income certificate',),
    'bonafide_certificate': ('bonafide certificate',),
    'domicile_certificate': ('domicile certificate',),
    'category_certificate': ('category certificate',),
    'other': ('library notice', 'bus notice', 'laboratory notice', 'club notice', 'reading notice'),
}


def classify(results: list[OCRResult], errors: list[str]) -> DocumentPrediction:
    common = dict(method='literal_title_keywords', model_version='keyword-1.0',
                  score_kind='keyword_score')
    if errors or any(r.status == 'error' for r in results):
        return DocumentPrediction(**common, document_type=None, decision='error', scores={},
                                  reason='A document page/input failed; inventory remains unresolved')
    text = re.sub(r'\s+', ' ', ' '.join(r.text for r in results)).casefold()
    if not text.strip():
        return DocumentPrediction(**common, document_type=None, decision='unreadable', scores={},
                                  reason='No OCR words; type cannot be resolved')
    scores = {label: float(any(re.search(r'\b' + re.escape(phrase) + r'\b', text)
                             for phrase in phrases)) for label, phrases in KEYWORDS.items()}
    matches = [label for label, score in scores.items() if score]
    if len(matches) != 1:
        return DocumentPrediction(**common, document_type=None, decision='uncertain', scores=scores,
                                  reason='No unique supported title keyword; unsupported/ambiguous inventory')
    return DocumentPrediction(**common, document_type=matches[0], decision='classified', scores=scores,
                              reason='One literal title family matched; heuristic score is not a probability')
