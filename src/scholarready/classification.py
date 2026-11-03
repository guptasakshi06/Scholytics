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


def feature_text(text: str) -> str:
    """Visible OCR text only; remove the common synthetic watermark, preserve body."""
    import unicodedata
    text = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text).casefold()).strip()
    return text.replace('synthetic - for academic demonstration', '').strip()


def build_estimator(seed=42):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    return Pipeline([
        ('tfidf', TfidfVectorizer(preprocessor=feature_text, lowercase=False,
                                  ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ('logistic', LogisticRegression(C=4.0, max_iter=1000, random_state=seed)),
    ])


class LearnedClassifier:
    """Text-only adapter shared by offline evaluation, CLI and the future UI."""
    def __init__(self, estimator, metadata):
        self.estimator = estimator
        self.metadata = metadata

    def predict_text(self, text, *, errors=()):
        common = dict(method='tfidf_logistic_regression', model_version=self.metadata['model_version'],
                      score_kind='model_probability')
        if errors:
            return DocumentPrediction(**common, document_type=None, decision='error', scores={},
                                      reason='A page/input failed; inventory remains unresolved')
        text = feature_text(text)
        if not text:
            return DocumentPrediction(**common, document_type=None, decision='unreadable', scores={},
                                      reason='No body OCR text after common watermark removal')
        probabilities = self.estimator.predict_proba([text])[0]
        scores = dict(zip(self.estimator.classes_, map(float, probabilities)))
        ordered = sorted(scores, key=scores.get, reverse=True)
        vectorizer = self.estimator.named_steps['tfidf']
        words = re.findall(r'(?u)\b\w\w+\b', text)
        coverage = sum(word in vectorizer.vocabulary_ for word in words) / max(1, len(words))
        families = sum(any(re.search(r'\b' + re.escape(phrase) + r'\b', text) for phrase in phrases)
                       for phrases in KEYWORDS.values())
        policy = self.metadata['thresholds']
        reason = None
        if families > 1:
            reason = 'Multiple title families; ambiguous document requires review'
        elif coverage < policy['minimum_vocabulary_coverage']:
            reason = 'Too little known vocabulary; unsupported text requires review'
        elif scores[ordered[0]] < policy['minimum_probability'] or scores[ordered[0]] - scores[ordered[1]] < policy['minimum_margin']:
            reason = 'Model score/margin below development-selected threshold'
        if reason:
            return DocumentPrediction(**common, document_type=None, decision='uncertain', scores=scores, reason=reason)
        return DocumentPrediction(**common, document_type=ordered[0], decision='classified', scores=scores,
                                  reason='TF-IDF/Logistic Regression; uncalibrated model probability, limited synthetic development support')

    def classify(self, results, errors):
        failures = list(errors) + [r.reason or 'OCR failed' for r in results if r.status == 'error']
        return self.predict_text('\n'.join(r.text for r in results), errors=failures)

    @classmethod
    def load(cls, directory):
        """Load only a locally trusted generated artifact: joblib uses pickle semantics."""
        import hashlib
        import json
        from pathlib import Path
        import joblib
        from importlib.metadata import version
        from .dataset import LABELS
        directory = Path(directory)
        metadata = json.loads((directory / 'metadata.json').read_text())
        model = directory / 'model.joblib'
        if hashlib.sha256(model.read_bytes()).hexdigest() != metadata['model_sha256']:
            raise ValueError('Classifier model hash mismatch')
        for name in ('scikit-learn', 'numpy', 'scipy', 'joblib'):
            if metadata['dependency_versions'][name] != version(name):
                raise ValueError(f'Classifier dependency mismatch: {name}; use the recorded environment')
        thresholds = metadata['thresholds']
        if set(thresholds) != {'minimum_probability', 'minimum_margin', 'minimum_vocabulary_coverage'} or any(
                type(v) not in (float, int) or not 0 <= v <= 1 for v in thresholds.values()):
            raise ValueError('Invalid classifier thresholds')
        estimator = joblib.load(model)
        if set(estimator.classes_) != set(LABELS) or list(estimator.classes_) != metadata['classes']:
            raise ValueError('Classifier class mapping mismatch')
        return cls(estimator, metadata)
