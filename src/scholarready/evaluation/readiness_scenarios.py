"""Development-only deterministic token fixtures; never called by upload inference."""
from copy import deepcopy

from ..classification import classify
from ..config import ScholarshipConfig
from ..extraction import extract
from ..requirements import evaluate, ENGINE_VERSION
from ..schemas import (ApplicantProfile, ApplicationResult, DocumentResult, OCRResult,
                       OCRToken, PageImage, ProcessingResult, GeometricTransform)


def fixture_document(doc_id, pages, *, failure=False, nested_failure=False, hint=None):
    images, ocr = [], []
    for index, lines in enumerate(pages, 1):
        page_id = f'{doc_id}-p{index}'
        image = PageImage(document_id=doc_id, page_id=page_id, page_index=index,
            original_filename=f'{doc_id}.fictional.png', width=1200, height=1600,
            color_space='RGB', rasterization_dpi=None, original_image_path=f'{page_id}.png',
            coordinate_space=f'{page_id}:original')
        tokens = []
        for line_no, text in enumerate(lines, 1):
            x = 60.
            for word in text.split():
                width = float(len(word)*8)
                tokens.append(OCRToken(token_id=f'{page_id}-t{len(tokens)}', text=word,
                    box=[x, float(60+line_no*45), width, 22.], page_id=page_id,
                    coordinate_space=image.coordinate_space, line_id=line_no, block_id=1, engine_score=95.))
                x += width+8
        images.append(image)
        ocr.append(OCRResult(page_id=page_id, branch_id='A', text='\n'.join(lines), tokens=tokens,
            engine='deterministic fictional fixture', engine_version='s07-fixture-1.0', language='eng',
            settings={}, runtime_seconds=0., status='ok' if tokens else 'empty',
            reason=None if tokens else 'Explicit blank token fixture'))
    errors = ['Explicit simulated processing failure'] if failure else []
    prediction = classify(ocr, errors)
    processing = []
    if nested_failure:
        p=images[0]
        processing=[ProcessingResult(page_id=p.page_id, branch_id='A', stages=[], width=p.width, height=p.height,
            transform=GeometricTransform(source_space=p.coordinate_space, target_space=p.coordinate_space,
                matrix=[[1,0,0],[0,1,0],[0,0,1]]), errors=['Explicit simulated unpromoted processing failure'])]
    return DocumentResult(document_id=doc_id, pages=images, processing=processing, ocr=ocr,
        prediction=prediction, fields=extract(prediction.document_type, images, ocr), errors=errors, declared_type_hint=hint)


def predict_fixture(spec: dict, base: list[list[str]], config: ScholarshipConfig) -> ApplicationResult:
    """Input-only specification. Expected outputs are deliberately not an argument."""
    config = config.model_dump(mode='json')
    config['config_version'] = 's07-fixture-config-1.0'
    if spec.get('empty_config'):
        config['requirements'] = []
    if spec.get('only_category'):
        config['requirements'] = config['requirements'][-1:]
    if spec.get('extra_constraints'):
        changed = {(c['field_name'], c['kind']) for c in spec['extra_constraints']}
        config['requirements'][1]['constraints'] = [c for c in config['requirements'][1]['constraints']
            if (c['field_name'], c['kind']) not in changed] + spec['extra_constraints']
    if spec.get('add_required'):
        config['requirements'][0]['required_fields'].append(spec['add_required'])
    config = ScholarshipConfig.model_validate(config)
    lines = deepcopy(base)
    for key, value in spec.get('replace_document', {}).items():
        lines[int(key)] = value
    for key, changes in spec.get('replace_lines', {}).items():
        for line_no, text in changes.items():
            lines[int(key)][int(line_no)] = text
    docs = []
    for index, content in enumerate(lines):
        if index in spec.get('remove', []):
            continue
        pages = [content]
        if spec.get('multipage') == index:
            pages = [content[:2], content[2:] + spec.get('page_append', [])]
        docs.append(fixture_document(f'd{index}', pages, failure=spec.get('failure') == index,
            nested_failure=spec.get('nested_failure') == index, hint=spec.get('hints', {}).get(str(index))))
    if 'duplicate' in spec:
        index = spec['duplicate']
        content = deepcopy(lines[index])
        for line_no, text in spec.get('duplicate_replace', {}).items():
            content[int(line_no)] = text
        docs.append(fixture_document('duplicate', [content]))
    for index, content in enumerate(spec.get('append', [])):
        docs.append(fixture_document(f'extra{index}', [content]))
    profile = ApplicantProfile(applicant_reference='fictional-s07', expected_name='Fictional Aster',
        category_certificate_required=spec.get('category', True))
    requirements, issues, overall, score, reason = evaluate(config, profile, docs)
    return ApplicationResult(requirement_engine_version=ENGINE_VERSION, config_version=config.config_version,
        run_id='fixture-'+spec['scenario_id'], documents=docs, requirements=requirements, issues=issues,
        overall_state=overall, completeness=score, completeness_reason=reason, quality_findings=[], runtime_seconds=0.)
