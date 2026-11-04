"""Local UI adapter: no readiness rules, no global applicant cache, no references."""
from dataclasses import dataclass
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import ImageDraw

from .classification import LearnedClassifier
from .config import ScholarshipConfig
from .evidence import draw_evidence
from .ingestion import IngestionLimits, SUPPORTED
from .pipeline import analyze, code_snapshot
from .ocr import OCRSettings
from .preprocessing import PreprocessingConfig
from .schemas import ApplicantProfile, ApplicationResult


@dataclass(frozen=True)
class Upload:
    name: str
    content: bytes
    hint: str | None = None


def validate_uploads(uploads, limits=None):
    limits = limits or IngestionLimits()
    if not uploads:
        raise ValueError('Choose at least one PNG, JPG/JPEG or PDF document.')
    if len(uploads) > limits.max_files:
        raise ValueError(f'Choose at most {limits.max_files} files per application.')
    for upload in uploads:
        if (not upload.name or Path(upload.name).name != upload.name
                or '\\' in upload.name or any(ord(c) < 32 for c in upload.name)):
            raise ValueError('Use a plain filename without folders or control characters.')
        if Path(upload.name).suffix.lower() not in SUPPORTED:
            raise ValueError('Choose PNG, JPG/JPEG or PDF documents.')
        if len(upload.content) > limits.max_file_bytes:
            raise ValueError(f'{upload.name}: exceeds the 25 MiB file limit.')
        if upload.hint not in {None, 'marksheet', 'income_certificate', 'bonafide_certificate',
                               'domicile_certificate', 'category_certificate', 'other'}:
            raise ValueError('Unknown document-type hint.')


def request_key(uploads, config, applicant, branch, preprocessing, model_digest=None):
    """Every input influencing inference invalidates the displayed result."""
    payload = dict(uploads=[dict(name=u.name, sha256=hashlib.sha256(u.content).hexdigest(),
                                hint=u.hint) for u in uploads],
                   config=config.model_dump(mode='json'), applicant=applicant.model_dump(mode='json'),
                   branch=branch, preprocessing=preprocessing.model_dump(mode='json'),
                   model_digest=model_digest, ingestion=asdict(IngestionLimits()),
                   ocr=asdict(OCRSettings()), code=code_snapshot())
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class LocalRun:
    """Session-owned disposable disk workspace; cleanup also occurs on garbage collection."""
    def __init__(self):
        self._temporary = TemporaryDirectory(prefix='scholarready-')
        self.root = Path(self._temporary.name)
        self.output = self.root / 'run'
        self.result = None

    def close(self):
        self._temporary.cleanup()
        self.result = None

    def execute(self, uploads: list[Upload], *, config: ScholarshipConfig,
                applicant: ApplicantProfile, branch='A', preprocessing=None,
                classifier: LearnedClassifier | None = None, progress=None) -> ApplicationResult:
        paths, hints = [], {}
        try:
            validate_uploads(uploads)
            for index, upload in enumerate(uploads):
                # Separate indexed directories preserve duplicate original filenames.
                path = self.root / 'uploads' / str(index) / upload.name
                path.parent.mkdir(parents=True)
                path.write_bytes(upload.content)
                paths.append(path)
                if upload.hint:
                    hints[str(path.resolve())] = upload.hint
            self.result = analyze(paths, config=config, applicant=applicant, output=self.output,
                branch=branch, preprocessing=preprocessing, classifier=classifier, hints=hints,
                exact_command='Local Streamlit UI via scholarready.ui.LocalRun.execute',
                progress=progress)
            return self.result
        except Exception:
            self.close()
            raise
        finally:
            # Original upload byte copies are no longer needed after ingestion.
            import shutil
            shutil.rmtree(self.root / 'uploads', ignore_errors=True)


def discard_result(state):
    run = state.pop('local_run', None)
    if run:
        run.close()
    state.pop('result_key', None)


def reset_application(state):
    """Explicit defaults replace browser widget values; deletion can resurrect them."""
    discard_result(state)
    state['upload_epoch'] = state.get('upload_epoch', 0) + 1
    for key in list(state):
        if key.startswith(('hint_', 'page_', 'document_')):
            del state[key]
    state.update(profile_category='Unknown', profile_name='', profile_reference='local-application',
                 experiment_branch='A', experiment_classifier='Keyword baseline')


def invalidate_result(state, current_key):
    if state.get('result_key') != current_key and 'local_run' in state:
        discard_result(state)
        return True
    return False


def result_json(result):
    # Exactly the shared ApplicationResult; no hand-corrected inference fields.
    return (result.model_dump_json(indent=2) + '\n').encode('utf-8')


def findings_csv(result):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['run_id', 'record_type', 'requirement_id', 'state', 'applicable',
                     'included_in_denominator', 'reasons', 'actions', 'documents', 'pages'])
    def safe(value):
        text = str(value)
        # Avoid interpreting names/config/actions as spreadsheet formulas.
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
    for r in result.requirements:
        writer.writerow([safe(v) for v in [result.run_id, 'requirement', r.requirement_id, r.state,
            r.applicable, r.included_in_denominator, ' | '.join(r.reasons), ' | '.join(r.actions),
            ' | '.join(r.document_references), ' | '.join(r.page_references)]])
    for issue in result.issues:
        writer.writerow([safe(v) for v in [result.run_id, 'issue', '', '', '', '', issue, '', '', '']])
    return stream.getvalue().encode('utf-8-sig')


def overlay(image, document, page_id, coordinate_space, show_tokens=True):
    canvas = draw_evidence(image, document.fields, page_id=page_id, coordinate_space=coordinate_space)
    if show_tokens:
        draw = ImageDraw.Draw(canvas)
        for ocr in document.ocr:
            if ocr.page_id != page_id:
                continue
            for token in ocr.tokens:
                if token.coordinate_space != coordinate_space:
                    raise ValueError('OCR/image coordinate space mismatch')
                x, y, w, h = token.box
                if x + w > canvas.width or y + h > canvas.height:
                    raise ValueError('OCR box outside image')
                draw.rectangle((x, y, x+w, y+h), outline='#2864c8', width=1)
    return canvas
