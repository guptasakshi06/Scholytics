#!/usr/bin/env python3
"""Fresh visibly fictional adversarial OCR uploads and coordinate-correct evidence figures."""
import argparse
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont
import reportlab

from scholarready.config import load_config
from scholarready.dataset import sha256
from scholarready.evidence import draw_evidence
from scholarready.pipeline import analyze, write_json
from scholarready.schemas import ApplicantProfile

# Expectations are deliberately specified here, before inference, from printed fixture content.
CASES = {
    'roles_dates_monthly': dict(title='INCOME CERTIFICATE', lines=[
        "Father's name: Fictional Birch", 'Name of applicant: Fictional Aster',
        'Date of birth: 2004-01-01', 'Issued on: 15 January 2026',
        'Expiry date: 2027-01-15', 'Monthly income (INR/month): 8,000'],
        checks={'applicant_name': ('valid', 'Fictional Aster', None),
                'guardian_name': ('valid', 'Fictional Birch', None),
                'annual_income': ('valid', 8000, 'INR/month'), 'issue_date': ('valid', '2026-01-15', None)}),
    'conflicting_dates': dict(title='DOMICILE CERTIFICATE', lines=[
        'Applicant name: Fictional Aster', 'Domicile state: Fictional Region',
        'Issued on: 2026-01-15', 'Issue date: 2026-02-15'],
        checks={'issue_date': ('ambiguous', None, None)}),
    'cropped_label': dict(title='ACADEMIC MARKSHEET', lines=[
        'udent name: Fictional Aster', 'Institution: Fictional College',
        'Academic session: 2025-2026', 'Percentage: 72.5'],
        checks={'student_name': ('unreadable', None, None), 'stated_total': ('unreadable', None, None)}),
    'unfamiliar_layout': dict(title='BONAFIDE CERTIFICATE', lines=[
        'Learner designation: Fictional Aster', 'Education provider: Fictional College',
        'Study period: 2025-2026', 'Programme: Fictional Science'],
        checks={'student_name': ('unreadable', None, None), 'institution': ('unreadable', None, None),
                'academic_year': ('unreadable', None, None), 'course': ('valid', 'Fictional Science', None)}),
    'explicit_absence': dict(title='ACADEMIC MARKSHEET', lines=[
        'Learner name: Fictional Aster', 'College name: Fictional College',
        'Academic session: 2025-2026', 'Stated total: not stated', 'Percentage: 72.5 %'],
        checks={'stated_total': ('absent', None, None), 'stated_percentage': ('valid', '72.5', '%')}),
    'numeric_date': dict(title='CATEGORY CERTIFICATE', lines=[
        'Applicant name: Fictional Aster', 'Social category: DEMO GROUP A', 'Date of issue: 01/02/2026'],
        checks={'stated_category': ('valid', 'DEMO GROUP A', None), 'issue_date': ('ambiguous', None, None)}),
    'below_label': dict(title='BONAFIDE CERTIFICATE', lines=[
        'Name of student', 'Fictional Aster', 'College name', 'Fictional College',
        'Programme', 'Fictional Science', 'Academic session', '2025-2026'],
        checks={'student_name': ('valid', 'Fictional Aster', None), 'institution': ('valid', 'Fictional College', None)}),
    'printed_total': dict(title='ACADEMIC MARKSHEET', lines=[
        'Student name: Fictional Aster', 'Institution: Fictional College', 'Academic year: 2025-2026',
        'Marks obtained: 400'], checks={'stated_total': ('valid', '400', None),
                                     'stated_percentage': ('unreadable', None, None)}),
    # Actual faint dot observation: no pretense that OCR must fail or that a score always detects damage.
    'faint_decimal': dict(title='ACADEMIC MARKSHEET', lines=[
        'Student name: Fictional Aster', 'Institution: Fictional College', 'Academic year: 2025-2026',
        'Stated percentage: 72.5'], checks={}),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--snapshot', type=Path, default=Path('docs/verification/s06'))
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    fixtures = args.output / 'fixtures'; fixtures.mkdir()
    font_path = Path(reportlab.__file__).parent / 'fonts/Vera.ttf'
    font = ImageFont.truetype(str(font_path), 28)
    small = ImageFont.truetype(str(font_path), 22)
    for name, case in CASES.items():
        image = Image.new('RGB', (1400, 1300), 'white'); draw = ImageDraw.Draw(image)
        draw.text((70, 30), 'SYNTHETIC - FOR ACADEMIC DEMONSTRATION', font=small, fill='black')
        draw.text((70, 100), case['title'], font=font, fill='black')
        y = 210
        for text in case['lines']:
            if name == 'faint_decimal' and text.startswith('Stated percentage'):
                left, right = text.split('.')
                draw.text((90, y), left, font=font, fill='black')
                x = 90 + draw.textlength(left, font=font)
                draw.text((x, y), '.', font=font, fill=(245, 245, 245))
                draw.text((x + draw.textlength('.', font=font), y), right, font=font, fill='black')
            else:
                draw.text((90, y), text, font=font, fill='black')
            # Below-label fixture pairs close lines; larger gaps separate the fields.
            y += (44 if name == 'below_label' and text in {'Name of student', 'College name', 'Programme', 'Academic session'} else 100)
        draw.text((70, 1200), 'Fictional teaching sample - document readiness only', font=small, fill='black')
        image.save(fixtures / (name + '.png'))
    write_json(args.output / 'fixture_specifications.json', CASES)
    result = analyze([fixtures / (name + '.png') for name in CASES],
        config=load_config(Path('configs/scholarship_demo.json')),
        applicant=ApplicantProfile(applicant_reference='fictional-s06', category_certificate_required=True),
        output=args.output / 'run')
    observations = []; checks = 0
    for (name, case), document in zip(CASES.items(), result.documents):
        values = {f.field_name: f for f in document.fields}
        for field, expected in case['checks'].items():
            actual = values[field]
            assert (actual.validation_state, actual.normalized_value, actual.unit) == expected, (name, field, actual)
            checks += 1
        observations.append(dict(case=name, prediction=document.prediction.model_dump(mode='json'),
            ocr_text=document.ocr[0].text, fields=[f.model_dump(mode='json') for f in document.fields]))
        if name in {'roles_dates_monthly', 'conflicting_dates', 'faint_decimal', 'below_label'}:
            page = document.pages[0]
            with Image.open(args.output / 'run' / page.original_image_path) as image:
                # A uses ingested originals; per-token boxes stay in that exact space.
                overlay = draw_evidence(image, document.fields, page_id=page.page_id, coordinate_space=page.coordinate_space)
                overlay.save(args.output / (name + '_evidence.png'))
    # C supplies a separate real processed-space check, with no original-image box reuse.
    processed = analyze([fixtures / 'roles_dates_monthly.png'], config=load_config(Path('configs/scholarship_demo.json')),
        applicant=ApplicantProfile(applicant_reference='fictional-s06-C'), branch='C', output=args.output / 'run-C')
    doc = processed.documents[0]; processing = doc.processing[0]
    with Image.open(args.output / 'run-C' / processing.stages[-1].image_path) as image:
        space = doc.ocr[0].tokens[0].coordinate_space
        assert space != doc.pages[0].coordinate_space
        overlay = draw_evidence(image, doc.fields, page_id=doc.pages[0].page_id, coordinate_space=space)
        overlay.save(args.output / 'processed_C_evidence.png')
        try:
            draw_evidence(image, doc.fields, page_id=doc.pages[0].page_id, coordinate_space=doc.pages[0].coordinate_space)
        except ValueError:
            wrong_space_rejected = True
        else:
            raise AssertionError('Wrong coordinate space was accepted')
    write_json(args.output / 'observations.json', observations)
    write_json(args.output / 'acceptance.json', dict(fixture_checks=checks, fresh_A_pages=len(CASES), fresh_C_pages=1,
        wrong_space_rejected=wrong_space_rejected, overall=result.overall_state,
        font_sha256=sha256(font_path), synthetic=True, expected_content_defined_before_inference=True,
        faint_decimal='Observation only; deterministic low-score and 725 rejection are separate unit fixtures'))
    args.snapshot.mkdir(parents=True, exist_ok=True)
    for name in ('fixture_specifications.json', 'observations.json', 'acceptance.json'):
        shutil.copyfile(args.output / name, args.snapshot / name)
    for image in args.output.glob('*_evidence.png'):
        shutil.copyfile(image, args.snapshot / image.name)
    write_json(args.snapshot / 'upload_artifact_hashes.json', {str(p.relative_to(args.output)): sha256(p) for p in sorted(args.output.rglob('*')) if p.is_file()})
    print(json.dumps(json.loads((args.output / 'acceptance.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
