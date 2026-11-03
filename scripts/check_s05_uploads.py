#!/usr/bin/env python3
"""Exercise actual OCR on clearly fictional low-content/unknown/conflicting uploads."""
import argparse
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont
import reportlab
from scholarready.classification import LearnedClassifier
from scholarready.config import load_config
from scholarready.pipeline import analyze, write_json
from scholarready.schemas import ApplicantProfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new run directory')
    parser.add_argument('--model', type=Path, default=Path('artifacts/runs/s05-classification-final/model'))
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    classifier = LearnedClassifier.load(args.model)
    args.output.mkdir(parents=True, exist_ok=False)
    fixtures = args.output / 'fixtures'; fixtures.mkdir()
    font_path = str(Path(reportlab.__file__).parent / 'fonts/Vera.ttf')
    font, small = ImageFont.truetype(font_path, 28), ImageFont.truetype(font_path, 18)
    texts = {'watermark_only': [], 'unsupported': ['ZXQVV QQQQQ XYYZZ', 'QZZXX ZZXQQ QVXXZ'],
             'ambiguous': ['INCOME CERTIFICATE', 'DOMICILE CERTIFICATE', 'Applicant name: Fictional Aster']}
    observed = {}
    for name, lines in texts.items():
        image = Image.new('RGB', (1200, 800), 'white'); draw = ImageDraw.Draw(image)
        draw.text((40, 40), 'SYNTHETIC - FOR ACADEMIC DEMONSTRATION', fill='black', font=small)
        for i, line in enumerate(lines):
            draw.text((40, 150 + i * 65), line, fill='black', font=font)
        path = fixtures / (name + '.png'); image.save(path)
        result = analyze([path], config=load_config('configs/scholarship_demo.json'),
            applicant=ApplicantProfile(applicant_reference='fictional-stress', category_certificate_required=True),
            output=args.output / name, classifier=classifier)
        observed[name] = dict(prediction=result.documents[0].prediction.model_dump(mode='json'),
                             ocr_text=result.documents[0].ocr[0].text, overall_state=result.overall_state)
        assert not result.documents[0].errors
        assert result.documents[0].prediction.decision == ('unreadable' if name == 'watermark_only' else 'uncertain')
        assert result.overall_state == 'needs_review'
    write_json(args.output / 'upload_stress.json', observed)
    if args.snapshot:
        args.snapshot.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.output / 'upload_stress.json', args.snapshot / 'upload_stress.json')
        shutil.copytree(fixtures, args.snapshot / 'fixtures', dirs_exist_ok=True)
    print({name: (x['prediction']['decision'], x['overall_state']) for name, x in observed.items()})


if __name__ == '__main__':
    main()
