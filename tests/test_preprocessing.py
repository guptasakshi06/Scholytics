"""DIP behavior, real geometry, conservative edge cases and real OCR integration."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytest

from scholarready.config import load_config
from scholarready.geometry import estimate_skew, map_points, rotation_matrix
from scholarready.ingestion import ingest, IngestionLimits
from scholarready.pipeline import analyze
from scholarready.preprocessing import PreprocessingConfig, morph, ocr_page, process
from scholarready.quality import measure, QualityConfig
from scholarready.schemas import ApplicantProfile, ApplicationResult

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/pilot/src-001.png'


def test_coordinate_rotation_matches_actual_pixels_and_inverse():
    image = np.full((80, 100), 255, np.uint8)
    image[25, 30] = 0
    matrix = rotation_matrix(100, 80, 4.)
    warped = cv2.warpAffine(image, matrix[:2], (100, 80), flags=cv2.INTER_NEAREST, borderValue=255)
    expected = map_points([[30, 25]], matrix)[0]
    ys, xs = np.where(warped == 0)
    assert len(xs) and np.min(np.linalg.norm(np.column_stack([xs, ys]) - expected, axis=1)) < 1
    assert map_points([expected], np.linalg.inv(matrix))[0] == pytest.approx([30, 25])
    assert map_points([[49.5, 39.5]], matrix)[0] == pytest.approx([49.5, 39.5])


@pytest.mark.parametrize('angle', [-4., -2., 2., 4.])
def test_known_document_skew_correction(angle):
    with Image.open(FIXTURE) as original:
        rotated = np.asarray(original.convert('L').rotate(angle, fillcolor=255))
    estimate = estimate_skew(rotated)
    assert estimate['applied'], estimate
    assert estimate['correction_degrees'] == pytest.approx(-angle, abs=.5)


@pytest.mark.parametrize('shape', [(1, 1), (2, 20), (80, 80)])
def test_blank_small_and_noisy_pages_do_not_pretend_readability(tmp_path, shape):
    rng = np.random.default_rng(42)
    for name, array in [('blank', np.full(shape, 255, np.uint8)),
                        ('noise', rng.integers(0, 256, size=shape, dtype=np.uint8))]:
        path = tmp_path / f'{name}.png'
        Image.fromarray(array).save(path)
        output = tmp_path / name
        output.mkdir()
        page = ingest([path], output, IngestionLimits())[0].pages[0]
        quality = measure(Image.fromarray(array), page.page_id, QualityConfig())
        assert quality.width == shape[1] and quality.height == shape[0]
        assert 'readable' not in quality.model_dump_json()
        if name == 'blank':
            assert quality.blur_measure == quality.contrast == 0
            assert quality.heuristic_flags
        estimate = estimate_skew(array)
        assert not estimate['applied']
        result = process(page, output, 'C', PreprocessingConfig())
        assert not result.errors
        assert all((output / s.image_path).exists() for s in result.stages)


def test_quality_original_values_and_configurable_thresholds():
    image = Image.fromarray(np.array([[0, 255], [0, 255]], dtype=np.uint8))
    result = measure(image, 'p', QualityConfig(dark_mean_below=200., low_contrast_std_below=128.))
    assert result.brightness == result.contrast == 127.5
    assert result.blur_measure > 0
    assert 'dark_image_heuristic' in result.heuristic_flags


def test_morphology_can_erase_decimal_and_join_strokes():
    binary = np.full((16, 24), 255, np.uint8)
    binary[4:12, 3:7] = 0
    binary[4:12, 8:12] = 0  # 1-pixel gap
    binary[11, 17] = 0      # decimal-sized isolated dot
    assert np.array_equal(binary, morph(binary, 'open_close', [1, 1]))
    for kernel in [[1, 2], [2, 1], [2, 2]]:
        assert morph(binary, 'open', kernel)[11, 17] == 255
    before = cv2.connectedComponents(255 - binary)[0]
    after = cv2.connectedComponents(255 - morph(binary, 'close', [1, 2]))[0]
    assert after < before


def test_config_rejects_bad_or_ambiguous_choices():
    for kwargs in [dict(filter_size=4), dict(adaptive_block_size=2), dict(kernel=[0, 2]),
                   dict(kernel=[True, 2]), dict(threshold='none'), dict(deskew=1)]:
        with pytest.raises(ValueError):
            PreprocessingConfig(**kwargs)
    assert PreprocessingConfig(threshold='none', morphology='none')


def test_noop_and_branch_b_pixels(tmp_path):
    page = ingest([FIXTURE], tmp_path, IngestionLimits())[0].pages[0]
    original = (tmp_path / page.original_image_path).read_bytes()
    a = process(page, tmp_path, 'A', PreprocessingConfig())
    b = process(page, tmp_path, 'B', PreprocessingConfig())
    c = process(page, tmp_path, 'C', PreprocessingConfig(deskew=False, clahe=False,
        denoise='none', threshold='none', morphology='none'))
    with Image.open(tmp_path / b.stages[-1].image_path) as image:
        assert set(np.unique(image)) <= {0, 255}
    with Image.open(tmp_path / c.stages[-1].image_path) as image, Image.open(FIXTURE) as source:
        assert np.array_equal(np.asarray(image), cv2.cvtColor(np.asarray(source.convert('RGB')), cv2.COLOR_RGB2GRAY))
    assert [s.name for s in b.stages] == ['ingested_original', 'grayscale', 'otsu']
    assert a.transform.source_space == a.transform.target_space
    assert c.transform.target_space != page.coordinate_space
    assert ocr_page(page, c).original_image_path != page.original_image_path
    assert original == (tmp_path / page.original_image_path).read_bytes()


@pytest.mark.parametrize('branch', ['B', 'C'])
def test_real_branch_ocr_evidence_spaces_and_no_reference_access(tmp_path, monkeypatch, branch):
    # Prevent accidental runtime use of labels; the inference path has no manifest.
    original_open = Path.open
    def guarded(path, *args, **kwargs):
        assert not {'annotations', 'manifests'} & set(path.parts)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    result = analyze([FIXTURE], config=load_config(ROOT / 'configs/scholarship_demo.json'),
        applicant=ApplicantProfile(applicant_reference='fictional'), output=tmp_path / 'run', branch=branch)
    doc = result.documents[0]
    assert doc.ocr[0].status == 'ok' and doc.ocr[0].branch_id == branch
    assert 'MARKSHEET' in doc.ocr[0].text
    space = doc.processing[0].transform.target_space
    assert all(t.coordinate_space == space for t in doc.ocr[0].tokens)
    assert all(f.coordinate_space == space for f in doc.fields if f.normalized_value is not None)
    assert result.quality_findings[0].page_id == doc.pages[0].page_id
    assert ApplicationResult.model_validate_json((tmp_path / 'run/result.json').read_text()) == result
    metadata = json.loads((tmp_path / 'run/metadata.json').read_text())
    assert all((tmp_path / 'run' / p).exists() for p in metadata['output_paths'])


def test_preprocessing_failure_is_explicit_not_ready(tmp_path, monkeypatch):
    def broken(*args):
        raise cv2.error('controlled stage failure')
    monkeypatch.setattr(cv2, 'createCLAHE', broken)
    result = analyze([FIXTURE], config=load_config(ROOT / 'configs/scholarship_demo.json'),
        applicant=ApplicantProfile(applicant_reference='fictional'), output=tmp_path / 'run', branch='C')
    assert result.documents[0].processing[0].errors
    assert result.documents[0].ocr[0].status == 'error'
    assert result.documents[0].errors and result.overall_state == 'needs_review'


def test_low_text_abstains_and_gaussian_otsu_choice_runs(tmp_path):
    image = np.full((100, 180), 255, np.uint8)
    cv2.putText(image, 'Hi', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1., 0, 2)
    assert not estimate_skew(image)['applied']
    path = tmp_path / 'low-text.png'
    Image.fromarray(image).save(path)
    page = ingest([path], tmp_path, IngestionLimits())[0].pages[0]
    result = process(page, tmp_path, 'C', PreprocessingConfig(denoise='gaussian', threshold='otsu', morphology='close', kernel=[2, 1]))
    assert not result.errors
    assert 'gaussian' in [s.name for s in result.stages]


def test_real_blank_tiny_noise_c_pipeline_remains_unresolved(tmp_path):
    paths = []
    arrays = [np.full((1, 1), 255, np.uint8), np.full((80, 80), 255, np.uint8),
              np.random.default_rng(42).integers(0, 256, (80, 80), dtype=np.uint8)]
    for index, array in enumerate(arrays):
        path = tmp_path / f'unknown-{index}.png'
        Image.fromarray(array).save(path)
        paths.append(path)
    result = analyze(paths, config=load_config(ROOT / 'configs/scholarship_demo.json'),
        applicant=ApplicantProfile(applicant_reference='fictional'), output=tmp_path / 'run', branch='C')
    assert result.overall_state == 'needs_review'
    assert len(result.documents) == len(result.quality_findings) == 3
    assert all(o.status in {'empty', 'error'} for d in result.documents for o in d.ocr)
