"""Meaningful leakage, uncertainty, persistence and shared-runtime regressions."""
from dataclasses import asdict
from importlib.metadata import version
import json
from pathlib import Path

import joblib
import pytest

from scholarready.classification import LearnedClassifier, build_estimator, feature_text
from scholarready.config import load_config
from scholarready.dataset import LABELS, sha256
from scholarready.evaluation.classification_metrics import classification_metrics
from scholarready.ocr import OCRSettings
from scholarready.pipeline import analyze, write_json
from scholarready.preprocessing import PreprocessingConfig
from scholarready.schemas import ApplicantProfile, DocumentPrediction
from scholarready.splitting import connected_groups, context, make_development_splits, validate_splits

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/manifests/pilot.jsonl'


def setup_split():
    records, meta, groups, _ = context(MANIFEST, ROOT)
    splits = make_development_splits(records, groups, sha256(MANIFEST), meta['dataset_version'])
    return records, groups, splits


def test_pilot_connected_split_reproducible_and_development_only():
    records, groups, splits = setup_split()
    assert len(set(groups.values())) == 4  # mismatch links applicant 4 and applicant 5
    assert groups['src-019-p01-clean'] == groups['src-026-p01-clean']
    assert groups['src-025-p02-rotation'] == groups['src-025-p01-clean']
    assert all(s.split == 'development_only' for s in splits)
    assert [s.model_dump() for s in splits] == [s.model_dump() for s in setup_split()[2]]
    report = validate_splits(records, splits, groups, sha256(MANIFEST))
    assert report['final_test_consumed'] is False
    train = [r for r, s in zip(records, splits) if s.development_partition == 'train']
    assert {r.layout_id for r in train} == {'layout_a'}
    assert {r.document_type for r in train} == set(LABELS)


@pytest.mark.parametrize('defect', ['partition', 'group', 'missing', 'duplicate', 'hash', 'test', 'protected'])
def test_split_rejects_leakage_and_stale_inputs(defect):
    records, groups, splits = setup_split()
    if defect == 'partition':
        splits[0].development_partition = 'validation'
    elif defect == 'group':
        splits[0].group_id = 'fake-group'
    elif defect == 'missing':
        splits.pop()
    elif defect == 'duplicate':
        splits[-1] = splits[0]
    elif defect == 'hash':
        splits[0].manifest_hash = '0' * 64
    elif defect == 'test':
        splits[0].split = 'test'
    else:
        records[0].development_role = 'test'
    with pytest.raises(ValueError):
        validate_splits(records, splits, groups, sha256(MANIFEST))


def test_grouping_transitive_applicant_hash_source_and_bundle():
    records, _, _ = setup_split()
    # Four otherwise unrelated sources joined by exact hash, source reuse and a bundle.
    selected = [r.model_copy(deep=True) for r in records if r.sample_id in {
        'src-001-p01-clean', 'src-007-p01-clean', 'src-013-p01-clean', 'src-019-p01-clean'}]
    selected[1].source_hash = selected[0].source_hash
    selected[2].source_document_id = selected[1].source_document_id
    groups = connected_groups(selected, [[selected[2].sample_id, selected[3].sample_id]])
    assert len(set(groups.values())) == 1
    with pytest.raises(ValueError, match='unknown'):
        connected_groups(selected, [['nonexistent']])


def test_tiny_connected_dataset_does_not_force_split():
    records, _, _ = setup_split()
    groups = {r.sample_id: 'same' for r in records}
    with pytest.raises(ValueError, match='three'):
        make_development_splits(records, groups, sha256(MANIFEST), 'pilot-1.0')


@pytest.fixture
def model(tmp_path):
    texts = ['academic marksheet student marks result percentage',
             'income certificate annual income rupees guardian',
             'bonafide certificate student course institution year',
             'domicile certificate applicant residence region date',
             'category certificate applicant category date',
             'library notice books reading notice meeting']
    estimator = build_estimator()
    estimator.fit(texts, list(LABELS))
    # This word appears only in held-out transform; fitting a vectorizer before split leaks it.
    before = estimator.named_steps['tfidf'].vocabulary_.copy()
    estimator.predict_proba(['heldoutuniquesentinel income certificate'])
    assert estimator.named_steps['tfidf'].vocabulary_ == before
    assert 'heldoutuniquesentinel' not in before
    model_dir = tmp_path / 'model'; model_dir.mkdir()
    joblib.dump(estimator, model_dir / 'model.joblib')
    metadata = dict(model_version='test-only', classes=list(estimator.classes_),
        manifest_sha256='a' * 64, splits_sha256='b' * 64,
        thresholds=dict(minimum_probability=.3, minimum_margin=.05, minimum_vocabulary_coverage=.1),
        inference_settings=dict(branch='A', ocr=asdict(OCRSettings()), pdf_dpi=300,
                                preprocessing=PreprocessingConfig().model_dump(mode='json')),
        dependency_versions={n: version(n) for n in ('scikit-learn', 'numpy', 'scipy', 'joblib')},
        model_sha256=sha256(model_dir / 'model.joblib'))
    write_json(model_dir / 'metadata.json', metadata)
    return model_dir, LearnedClassifier.load(model_dir)


def test_conservative_empty_unknown_ambiguous_and_other(model):
    _, classifier = model
    assert classifier.predict_text('  ').decision == 'unreadable'
    assert classifier.predict_text('SYNTHETIC - FOR ACADEMIC DEMONSTRATION').decision == 'unreadable'
    assert classifier.predict_text('zxqv xyzzzz qqqqq').decision == 'uncertain'
    assert classifier.predict_text('income certificate domicile certificate').decision == 'uncertain'
    result = classifier.predict_text('library notice books reading notice meeting')
    assert result.document_type == 'other' and result.score_kind == 'model_probability'
    assert classifier.predict_text('income certificate', errors=['failed page']).decision == 'error'
    classifier.metadata['thresholds']['minimum_probability'] = 1.
    assert classifier.predict_text('income certificate annual income').decision == 'uncertain'


def test_reload_scores_identical_and_hash_dependency_threshold_errors(model):
    directory, classifier = model
    text = 'income certificate annual income rupees guardian'
    assert classifier.predict_text(text) == LearnedClassifier.load(directory).predict_text(text)
    path = directory / 'metadata.json'; saved = json.loads(path.read_text())
    for key, value, match in [('model_sha256', '0' * 64, 'hash'),
                              ('dependency_versions', {**saved['dependency_versions'], 'scikit-learn': 'invalid'}, 'dependency'),
                              ('thresholds', {**saved['thresholds'], 'minimum_margin': float('nan')}, 'threshold')]:
        path.write_text(json.dumps({**saved, key: value}))
        with pytest.raises(ValueError, match=match):
            LearnedClassifier.load(directory)
    path.write_text(json.dumps(saved))


def test_metrics_keep_unresolved_false_negatives_and_other():
    prediction = DocumentPrediction(document_type=None, decision='uncertain', method='test',
        model_version='test', scores={}, score_kind='none', reason='unknown')
    result = classification_metrics(['income_certificate'], [prediction])
    assert result['macro_f1'] == 0 and result['unresolved'] == 1
    assert result['per_class']['income_certificate']['support'] == 1
    assert sum(map(sum, result['confusion_matrix'])) == 1
    assert result['confusion_matrix'][list(LABELS).index('income_certificate')][-1] == 1
    assert classification_metrics([], [])['macro_f1'] is None
    with pytest.raises(ValueError):
        classification_metrics(['other'], [])


def test_shared_real_ocr_with_reloaded_model_without_reference_access(model, tmp_path, monkeypatch):
    _, classifier = model
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert 'annotations' not in path.parts and 'manifests' not in path.parts
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    result = analyze([ROOT / 'tests/fixtures/pilot/src-002.png'],
        config=load_config(ROOT / 'configs/scholarship_demo.json'),
        applicant=ApplicantProfile(applicant_reference='arbitrary'), output=tmp_path / 'run', classifier=classifier)
    assert not result.documents[0].errors
    assert result.documents[0].prediction.method == 'tfidf_logistic_regression'
    assert (tmp_path / 'run/classifier.json').exists()
    metadata = json.loads((tmp_path / 'run/metadata.json').read_text())
    assert metadata['dataset_hash'] is None and metadata['split_hash'] is None
    assert metadata['model_hash'] == classifier.metadata['model_sha256']
    assert 'classifier.json' in metadata['output_paths']
    with pytest.raises(ValueError, match='settings mismatch'):
        analyze([], config=load_config(ROOT / 'configs/scholarship_demo.json'),
            applicant=ApplicantProfile(applicant_reference='x'), branch='C',
            output=tmp_path / 'mismatch', classifier=classifier)
    assert not (tmp_path / 'mismatch').exists()


def test_feature_policy_removes_common_watermark():
    assert feature_text('SYNTHETIC - FOR ACADEMIC DEMONSTRATION\nIncome   Certificate') == 'income certificate'
