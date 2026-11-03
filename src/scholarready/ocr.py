"""Real Tesseract TSV words; text follows TSV block/paragraph/line order."""
from dataclasses import asdict, dataclass
from pathlib import Path
import math
import subprocess
from time import perf_counter

from PIL import Image
import pytesseract

from .schemas import OCRResult, OCRToken, PageImage


@dataclass(frozen=True)
class OCRSettings:
    language: str = 'eng'
    psm: int = 3
    oem: int = 3
    timeout_seconds: float = 20.0

    def __post_init__(self):
        if (self.language != 'eng' or type(self.psm) is not int or type(self.oem) is not int
                or self.psm not in range(14) or self.oem not in range(4)):
            raise ValueError('use eng, PSM 0..13 and OEM 0..3')
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 120:
            raise ValueError('OCR timeout must be finite and in (0, 120] seconds')


def engine_version() -> str:
    """Bound the executable probe too; failures remain visible on OCR pages."""
    try:
        result = subprocess.run([pytesseract.pytesseract.tesseract_cmd, '--version'],
                                capture_output=True, text=True, timeout=5, check=True)
        return result.stdout.splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError) as exc:
        return f'unavailable ({type(exc).__name__})'


def recognize(page: PageImage, output: Path, settings: OCRSettings, version: str, branch: str = 'A') -> OCRResult:
    started = perf_counter()
    common = dict(page_id=page.page_id, branch_id=branch, engine='Tesseract',
                  engine_version=version, language=settings.language, settings=asdict(settings))
    try:
        with Image.open(output / page.original_image_path) as image:
            data = pytesseract.image_to_data(
                image, lang=settings.language, config=f'--oem {settings.oem} --psm {settings.psm}',
                output_type=pytesseract.Output.DICT, timeout=settings.timeout_seconds)
        tokens = []
        lines: dict[tuple[int, int, int], list[str]] = {}
        for index, raw in enumerate(data['text']):
            text = raw.strip()
            if not text:
                continue
            x, y, width, height = [int(data[k][index]) for k in ('left', 'top', 'width', 'height')]
            if min(x, y) < 0 or width <= 0 or height <= 0 or x + width > page.width or y + height > page.height:
                raise ValueError('OCR returned a box outside its page')
            key = tuple(int(data[k][index]) for k in ('block_num', 'par_num', 'line_num'))
            if key not in lines:
                lines[key] = []
            lines[key].append(text)
            score = float(data['conf'][index])
            tokens.append(OCRToken(
                token_id=f'{page.page_id}:{branch}:t{len(tokens):05d}', text=text,
                box=[float(x), float(y), float(width), float(height)], page_id=page.page_id,
                coordinate_space=page.coordinate_space, line_id=list(lines).index(key) + 1,
                block_id=key[0], engine_score=score if math.isfinite(score) and 0 <= score <= 100 else None))
        text = '\n'.join(' '.join(words) for words in lines.values())
        return OCRResult(**common, text=text, tokens=tokens,
                         runtime_seconds=perf_counter() - started,
                         status='ok' if tokens else 'empty',
                         reason=None if tokens else 'Tesseract returned no word tokens')
    except Exception as exc:
        return OCRResult(**common, text='', tokens=[], status='error',
                         reason=f'{type(exc).__name__}: {exc}', runtime_seconds=perf_counter() - started)
