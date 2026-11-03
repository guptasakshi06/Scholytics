"""Render OCR evidence only on the matching coordinate-space image."""
from PIL import Image, ImageDraw


def draw_evidence(image: Image.Image, fields, *, page_id: str, coordinate_space: str) -> Image.Image:
    canvas = image.convert('RGB').copy()
    draw = ImageDraw.Draw(canvas)
    for field in fields:
        evidence = field.candidates or [field]
        for candidate in evidence:
            if candidate.page_id != page_id:
                continue
            if candidate.coordinate_space != coordinate_space:
                raise ValueError('Evidence/image coordinate space mismatch; map geometry explicitly before overlay')
            color = '#087830' if field.validation_state == candidate.validation_state == 'valid' else '#b22323'
            for x, y, w, h in candidate.boxes:
                if x + w > canvas.width or y + h > canvas.height:
                    raise ValueError('Evidence box outside image')
                draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
    return canvas
