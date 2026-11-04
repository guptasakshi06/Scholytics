"""Run locally: .venv/bin/python -m streamlit run app/streamlit_app.py"""
from pathlib import Path

from PIL import Image
import streamlit as st

from scholarready.classification import LearnedClassifier
from scholarready.config import load_config
from scholarready.preprocessing import load_preprocessing
from scholarready.schemas import ApplicantProfile
from scholarready.ui import (Upload, LocalRun, discard_result, reset_application, invalidate_result, request_key,
                             validate_uploads, result_json, findings_csv, overlay)

ROOT = Path(__file__).resolve().parents[1]
TYPE_OPTIONS = ['No hint', 'marksheet', 'income_certificate', 'bonafide_certificate',
                'domicile_certificate', 'category_certificate', 'other']


def main():
    st.set_page_config(page_title='ScholarReady · Document readiness', page_icon='📄', layout='wide')
    st.title('ScholarReady')
    st.caption('Project 042 · Sakshi Gupta and Jigisha Baiswar')
    st.info('Fictional academic checklist · Document readiness only. This does not establish authenticity, eligibility or scholarship approval.')
    st.write('Upload printed English documents, review the evidence, and see what needs attention. Processing stays on this local computer.')
    if 'upload_epoch' not in st.session_state:
        st.session_state.upload_epoch = 0
    if st.button('Clear application'):
        reset_application(st.session_state)
        st.rerun()

    config = load_config(ROOT / 'configs/scholarship_demo.json')
    st.subheader('1 · Documents and profile')
    st.selectbox('Checklist profile', [config.display_name], key='profile_checklist')
    category = st.selectbox('Category certificate required?', ['Unknown', 'Yes', 'No'], key='profile_category',
        help='An explicit attribute of this fictional checklist. Unknown stays unresolved.')
    name = st.text_input('Expected applicant name (optional user input)', key='profile_name')
    if 'profile_reference' not in st.session_state:
        st.session_state.profile_reference = 'local-application'
    reference = st.text_input('Application reference (user input)', key='profile_reference')
    applicant = ApplicantProfile(applicant_reference=reference.strip() or 'local-application',
        category_certificate_required={'Unknown': None, 'Yes': True, 'No': False}[category],
        expected_name=name.strip() or None)
    files = st.file_uploader('Choose documents', type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True, max_upload_size=25, key=f'uploads_{st.session_state.upload_epoch}')
    st.caption('Up to 20 files, 25 MiB each; 40 pages, 20 million pixels/page and 100 million pixels total. PDF pages render at 300 DPI. Large or failed pages remain unresolved.')
    uploads = []
    too_many = len(files or []) > 20
    if too_many:
        discard_result(st.session_state)
        st.error('Choose at most 20 files per application; remove extra files before processing.')
    if files and not too_many:
        with st.expander('Document-type hints (optional, unverified)'):
            st.caption('Hints record your input; they do not replace automatic classification or certify the content.')
            for index, file in enumerate(files):
                import hashlib
                digest = hashlib.sha256(file.getbuffer()).hexdigest()
                hint = st.selectbox(f'Type hint · {index + 1}: {file.name}', TYPE_OPTIONS,
                    key=f'hint_{st.session_state.upload_epoch}_{index}_{digest}_{file.name}')
                uploads.append(Upload(file.name, file.getvalue(), None if hint == 'No hint' else hint))

    preprocessing = load_preprocessing(ROOT / 'configs/preprocessing.json')
    classifier = None
    model_digest = None
    model_error = None
    with st.expander('Academic experiment settings'):
        st.caption('A is the default raw OCR baseline. B and C can damage text; their scores are not evidence of improvement. Model scores and image quality flags are uncalibrated.')
        branch = st.selectbox('DIP branch', ['A', 'B', 'C'], key='experiment_branch')
        method = st.selectbox('Document classifier', ['Keyword baseline', 'S05 learned classifier (trusted local model)'], key='experiment_classifier')
        if method != 'Keyword baseline':
            try:
                classifier = LearnedClassifier.load(ROOT / 'artifacts/runs/s05-classification-final/model')
                model_digest = classifier.metadata
                if branch != classifier.metadata['inference_settings']['branch']:
                    model_error = 'The S05 model requires branch A and its recorded preprocessing/OCR settings. Select A or the keyword baseline.'
            except (OSError, ValueError, KeyError, TypeError) as exc:
                model_error = 'Local model unavailable. Regenerate it using the classification guide, or select the keyword baseline. ' + str(exc)
        st.write(config.description)
        st.dataframe([dict(requirement=r.requirement_id, document=r.document_type,
            required_fields=', '.join(r.required_fields), conditional=r.condition is not None,
            constraints='; '.join(f'{c.field_name}: {c.kind} {c.value}' for c in r.constraints))
            for r in config.requirements], hide_index=True)
        st.caption('Other extracted fields are optional. No manual OCR corrections are applied in this interface.')

    key = request_key(uploads, config, applicant, branch, preprocessing, (model_digest, method))
    if invalidate_result(st.session_state, key):
        st.warning('Inputs or settings changed. Previous results were cleared; analyze again.')
    if model_error:
        discard_result(st.session_state)
        st.error(model_error)
    if st.button('Analyze documents', type='primary', disabled=not files or too_many or bool(model_error)):
        discard_result(st.session_state)
        try:
            validate_uploads(uploads)
            bar = st.progress(0., text='Decoding documents locally…')
            with st.spinner('Reading documents and checking the fictional requirements…'):
                run = LocalRun()
                run.execute(uploads, config=config, applicant=applicant, branch=branch,
                    preprocessing=preprocessing, classifier=classifier,
                    progress=lambda done, total, message: bar.progress(done / total if total else 0., text=message))
            bar.progress(1., text='Finished — review findings below')
            st.session_state.local_run = run
            st.session_state.result_key = key
        except Exception as exc:
            if 'run' in locals():
                run.close()
            st.error(f'Analysis could not finish: {type(exc).__name__}: {exc}. Check the file limits, local Tesseract/eng installation and experiment settings, then retry.')

    run = st.session_state.get('local_run')
    if run and run.result:
        show_result(run)
    st.caption('Clear application removes temporary upload and page files. Closing the session releases its disposable workspace when Streamlit expires the session. Download JSON/CSV first to keep findings.')


def show_result(run):
    result = run.result
    st.subheader('2 · Readiness findings')
    st.markdown(f'**Overall: {result.overall_state}**')
    st.metric('Checklist completeness', 'Unresolved' if result.completeness is None else f'{result.completeness:g}%')
    st.caption(result.completeness_reason)
    st.caption('Completeness counts named requirements. Open issues can still require review at 100%. Image quality is separate.')
    for issue in result.issues:
        st.warning(issue)
    st.dataframe([dict(requirement=r.requirement_id, state=r.state, applicable={None: 'Unknown', True: 'Yes', False: 'No'}[r.applicable],
        in_denominator={None: 'Unknown', True: 'Yes', False: 'No'}[r.included_in_denominator], reasons=' | '.join(r.reasons),
        actions=' | '.join(r.actions)) for r in result.requirements], hide_index=True)
    for r in result.requirements:
        with st.expander(f'{r.requirement_id} · {r.state}'):
            for reason in r.reasons:
                st.write(reason)
            for action in r.actions:
                st.write('Next action: ' + action)
            st.write(dict(documents=r.document_references, fields=r.field_references, pages=r.page_references))
    left, right = st.columns(2)
    left.download_button('Download application JSON', result_json(result), 'scholarready-result.json',
        'application/json', on_click='ignore')
    right.download_button('Download findings CSV', findings_csv(result), 'scholarready-findings.csv',
        'text/csv', on_click='ignore')
    st.caption('JSON uses the shared application schema; image paths refer to this temporary run. CSV includes every requirement and global issue. These exports contain automated findings, without manual corrections.')
    st.subheader('3 · Inspect document evidence')
    document = st.selectbox('Document', result.documents, format_func=lambda d: f'{d.source_filename} · {d.document_id}', key=f'document_{result.run_id}')
    prediction = document.prediction
    st.write(f'Automatic type: {prediction.document_type or "unresolved"} · {prediction.decision}')
    st.write(prediction.reason)
    st.caption(f'User-declared hint: {document.declared_type_hint or "none"} (unverified)')
    for error in document.errors:
        st.error(error)
    st.dataframe([dict(field=f.field_name, role=f.person_role, raw=f.raw_text,
        value=str(f.normalized_value) if f.normalized_value is not None else None,
        unit=f.unit, state=f.validation_state, reason=f.reason, page=f.page_id)
        for f in document.fields], hide_index=True)
    with st.expander('Full field evidence, candidates and classifier scores'):
        st.json(dict(prediction=prediction.model_dump(mode='json'),
                     fields=[f.model_dump(mode='json') for f in document.fields]))
    if not document.pages:
        st.error('No page could be decoded for this document. Replace the failed input and analyze again.')
        return
    page = st.selectbox('Page', document.pages, format_func=lambda p: f'Page {p.page_index}', key=f'page_{result.run_id}_{document.document_id}')
    processing = next(p for p in document.processing if p.page_id == page.page_id)
    ocr = next(o for o in document.ocr if o.page_id == page.page_id)
    quality = next(q for q in result.quality_findings if q.page_id == page.page_id)
    st.caption(f'{page.original_filename} · Page {page.page_index} · {page.width} × {page.height} px · PDF DPI: {page.rasterization_dpi or "image"}')
    st.write('Original-image quality indicators (heuristics):')
    st.json(quality.model_dump(mode='json'), expanded=False)
    left, right = st.columns(2)
    with Image.open(run.output / page.original_image_path) as image:
        left.image(image.copy(), caption='Ingested original', width='stretch')
    if processing.errors:
        for error in processing.errors:
            st.error(error)
    else:
        processed_path = processing.stages[-1].image_path if processing.stages else page.original_image_path
        with Image.open(run.output / processed_path) as image:
            right.image(overlay(image, document, page.page_id, processing.transform.target_space),
                caption='OCR input + field evidence (green valid, red unresolved); OCR tokens in blue. Boxes use processed coordinates.', width='stretch')
    with st.expander('OCR text, DIP stages and geometry'):
        st.write(f'OCR status: {ocr.status}; reason: {ocr.reason or "none"}')
        st.code(ocr.text or '(No text recognized)', language=None)
        st.caption('Tesseract engine scores are not probabilities of correctness.')
        st.json(dict(ocr=ocr.model_dump(mode='json'), processing=processing.model_dump(mode='json')))
        for stage in processing.stages:
            st.image(str(run.output / stage.image_path), caption=stage.name, width='stretch')
    with st.expander('Run provenance'):
        st.json((run.output / 'metadata.json').read_text())
        st.write('Applicant attributes below are user input, not verified OCR:')
        st.json((run.output / 'applicant.json').read_text())


if __name__ == '__main__':
    main()
