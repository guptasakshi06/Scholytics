"""Shared upload -> OCR -> baseline fields -> checklist pipeline. No labels loaded."""
from dataclasses import asdict
import hashlib
from importlib.metadata import version as distribution_version
import json
from pathlib import Path
import platform
from time import perf_counter
import uuid

from .classification import classify
from .config import ScholarshipConfig
from .extraction import extract
from .ingestion import ingest, IngestionLimits
from .ocr import engine_version, OCRSettings, recognize
from .requirements import evaluate
from .preprocessing import PreprocessingConfig, process, ocr_page
from .quality import measure
from .schemas import (ApplicantProfile, ApplicationResult, DocumentResult, RunMetadata, OCRResult)


def write_json(path: Path, value):
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def code_snapshot() -> dict[str, str]:
    root = Path(__file__).parent
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.py'))}


def analyze(paths: list[Path], *, config: ScholarshipConfig, applicant: ApplicantProfile,
            output: Path, settings: OCRSettings | None = None,
            limits: IngestionLimits | None = None, hints: dict[str, str] | None = None,
            branch: str = 'A', preprocessing: PreprocessingConfig | None = None,
            exact_command: str = 'Python API scholarready.pipeline.analyze') -> ApplicationResult:
    """Create a fresh portable run. Paths may be arbitrary local user-selected files."""
    started = perf_counter()
    if branch not in {'A', 'B', 'C'}:
        raise ValueError('branch must be A/B/C')
    preprocessing = PreprocessingConfig.model_validate((preprocessing or PreprocessingConfig()).model_dump(mode='json'))
    # Revalidate at the shared boundary, including mutable nested models.
    config = ScholarshipConfig.model_validate(config.model_dump(mode='json'))
    applicant = ApplicantProfile.model_validate(applicant.model_dump(mode='json'))
    settings, limits, hints = settings or OCRSettings(), limits or IngestionLimits(), hints or {}
    if len(paths) > limits.max_files:
        raise ValueError(f'file count exceeds max_files={limits.max_files}; reduce the inventory')
    paths = [Path(p).resolve() for p in paths]
    if set(hints) - {str(p) for p in paths} or set(hints.values()) - {
            'marksheet', 'income_certificate', 'bonafide_certificate', 'domicile_certificate', 'category_certificate', 'other'}:
        raise ValueError('Hints must identify an input path and a supported type; hints are unverified')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    run_id = 's04-' + uuid.uuid4().hex
    write_json(output / 'config.json', config)
    write_json(output / 'applicant.json', applicant)
    write_json(output / 'settings.json', dict(ingestion=asdict(limits), ocr=asdict(settings), branch=branch))
    write_json(output / 'preprocessing.json', preprocessing)
    snapshot = code_snapshot()
    write_json(output / 'code_snapshot.json', snapshot)
    version = engine_version()
    documents, quality_findings = [], []
    ingested = ingest(paths, output, limits)
    write_json(output / 'ingestion.json', [dict(document_id=d.document_id, pages=d.ingestion_details,
        errors=d.errors) for d in ingested])
    for item in ingested:
        ocr_results, processing = [], []
        for page in item.pages:
            from PIL import Image
            with Image.open(output / page.original_image_path) as original:
                quality_findings.append(measure(original, page.page_id, preprocessing.quality))
            processed = process(page, output, branch, preprocessing)
            processing.append(processed)
            if processed.errors:
                ocr_results.append(OCRResult(page_id=page.page_id, branch_id=branch,
                    text='', tokens=[], engine='Tesseract', engine_version=version,
                    language=settings.language, settings=asdict(settings), runtime_seconds=0.,
                    status='error', reason='Preprocessing failed: ' + '; '.join(processed.errors)))
            else:
                ocr_results.append(recognize(ocr_page(page, processed), output, settings, version, branch))
        errors = item.errors + [f'{o.page_id}: {o.reason}' for o in ocr_results if o.status == 'error']
        prediction = classify(ocr_results, errors)
        fields = extract(prediction.document_type, item.pages, ocr_results)
        hint = hints.get(str(paths[len(documents)]))
        documents.append(DocumentResult(document_id=item.document_id, source_filename=item.source_filename,
            source_sha256=item.source_sha256, declared_type_hint=hint, pages=item.pages,
            processing=processing, ocr=ocr_results, prediction=prediction, fields=fields, errors=errors))
    requirements, issues, overall, completeness, explanation = evaluate(config, applicant, documents)
    result = ApplicationResult(config_version=config.config_version, run_id=run_id, documents=documents,
        requirements=requirements, issues=issues, overall_state=overall, completeness=completeness,
        completeness_reason=explanation, quality_findings=quality_findings, runtime_seconds=perf_counter() - started)
    write_json(output / 'result.json', result)
    write_json(output / 'inputs.json', dict(files=[dict(
        input_path=str(path), document_id=d.document_id, source_sha256=d.source_sha256,
        declared_type_hint=d.declared_type_hint) for path, d in zip(paths, documents)]))
    exceptions = [e for d in documents for e in d.errors]
    metadata = RunMetadata(run_id=run_id, dataset_hash=None, split_hash=None,
        config_hash=hashlib.sha256(config.model_dump_json().encode()).hexdigest(), model_hash=None,
        code_version='sha256:' + hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
        python_version=platform.python_version(),
        library_versions={name: distribution_version(name) for name in ('Pillow', 'pypdfium2', 'pytesseract', 'pydantic', 'numpy', 'opencv-python-headless')},
        tesseract_version=version, seeds={}, exact_command=exact_command,
        timing_scope='Sequential ingestion/decode/render/save + original quality + preprocessing/stage saves + OCR + keyword/field/checklist + initial snapshots; excludes final JSON/metadata writes and CLI discovery. Stage runtimes include image saves; deskew estimation_seconds is additional. OCR includes wrapper/image serialization.',
        runtime_seconds=result.runtime_seconds,
        output_paths=['result.json', 'metadata.json', 'inputs.json', 'settings.json', 'config.json',
                      'applicant.json', 'code_snapshot.json', 'ingestion.json', 'preprocessing.json']
            + list(dict.fromkeys(stage.image_path for d in documents for p in d.processing for stage in p.stages)),
        exceptions=exceptions)
    write_json(output / 'metadata.json', metadata)
    return result
