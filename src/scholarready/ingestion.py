"""Bounded local decoding. Saved image paths are relative to the run directory."""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from threading import RLock
import warnings

from PIL import Image, ImageOps
import pypdfium2 as pdfium

from .schemas import PageImage

PDFIUM_LOCK = RLock()  # Every runtime PDFium call must hold this process-wide lock.
SUPPORTED = {'.png', '.jpg', '.jpeg', '.pdf'}


@dataclass(frozen=True)
class IngestionLimits:
    max_files: int = 20
    max_pages: int = 40  # per application, including failed/omitted page slots
    max_file_bytes: int = 25 * 1024 * 1024
    max_page_pixels: int = 20_000_000
    max_total_pixels: int = 100_000_000
    pdf_dpi: int = 300

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in vars(self).values()):
            raise ValueError('ingestion limits must be positive integers')
        if self.pdf_dpi > 600:
            raise ValueError('PDF DPI must be at most 600')


@dataclass
class IngestedDocument:
    document_id: str
    source_filename: str
    source_sha256: str | None
    pages: list[PageImage]
    errors: list[str]
    ingestion_details: list[dict]


def _rgb(image: Image.Image) -> Image.Image:
    if image.mode in {'RGBA', 'LA'} or 'transparency' in image.info:
        rgba = image.convert('RGBA')
        background = Image.new('RGBA', rgba.size, 'white')
        return Image.alpha_composite(background, rgba).convert('RGB')
    return image.convert('RGB').copy()


def ingest(paths: list[Path], output: Path, limits: IngestionLimits) -> list[IngestedDocument]:
    """Preserve failures and partial PDFs; never silently truncate the inventory."""
    if len(paths) > limits.max_files:
        raise ValueError(f'file count {len(paths)} exceeds max_files={limits.max_files}')
    documents = []
    used_pages = used_pixels = 0
    occurrences: dict[str, int] = {}
    for path in paths:
        content = None
        error = None
        try:
            if path.stat().st_size > limits.max_file_bytes:
                raise ValueError(f'file exceeds {limits.max_file_bytes} byte limit')
            # Read only bounded bytes even if the file grows between stat and read.
            with path.open('rb') as handle:
                content = handle.read(limits.max_file_bytes + 1)
            if len(content) > limits.max_file_bytes:
                content = None
                raise ValueError('file grew beyond byte limit')
        except (OSError, ValueError) as exc:
            error = str(exc)
        digest = hashlib.sha256(content).hexdigest() if content is not None else None
        identity = digest or hashlib.sha256(str(path).encode()).hexdigest()
        occurrences[identity] = occurrences.get(identity, 0) + 1
        document_id = f'doc-{identity[:20]}-{occurrences[identity]}'
        doc = IngestedDocument(document_id, path.name, digest, [], [], [])
        documents.append(doc)

        def save_page(image, index, dpi):
            nonlocal used_pages, used_pixels
            width, height = image.size
            rel = f'pages/{document_id}/p{index:03d}/original.png'
            destination = output / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination)
            page_id = f'{document_id}-p{index:03d}'
            doc.pages.append(PageImage(
                document_id=document_id, page_id=page_id, page_index=index,
                original_filename=path.name, width=width, height=height, color_space='RGB',
                rasterization_dpi=dpi, original_image_path=rel,
                coordinate_space=f'{page_id}:original_pixels'))
            used_pages += 1
            used_pixels += width * height

        def check_budget(width, height):
            if width <= 0 or height <= 0 or width * height > limits.max_page_pixels:
                raise ValueError(f'page dimensions {width}x{height} exceed pixel limit')
            if used_pages >= limits.max_pages:
                raise ValueError('application page limit reached; remaining pages unresolved')
            if used_pixels + width * height > limits.max_total_pixels:
                raise ValueError('application total pixel limit reached; remaining pages unresolved')

        try:
            if error:
                raise ValueError(error)
            if path.suffix.lower() not in SUPPORTED:
                raise ValueError('unsupported input; use PNG, JPG/JPEG or PDF')
            if path.suffix.lower() == '.pdf':
                with PDFIUM_LOCK, pdfium.PdfDocument(content) as pdf:
                    # Reject even empty-password encrypted PDFs; no authentication workflow.
                    if pdfium.raw.FPDF_GetSecurityHandlerRevision(pdf.raw) != -1:
                        raise ValueError('encrypted PDF unsupported; supply an unencrypted local copy')
                    count = len(pdf)
                    if count == 0:
                        raise ValueError('PDF has no pages')
                    # Never iterate an unbounded page inventory.
                    allowance = limits.max_pages - used_pages
                    for number in range(min(count, allowance)):
                        try:
                            page = pdf[number]
                            try:
                                width, height = page.get_size()
                                check_budget(math.ceil(width * limits.pdf_dpi / 72),
                                             math.ceil(height * limits.pdf_dpi / 72))
                                bitmap = page.render(scale=limits.pdf_dpi / 72)
                                try:
                                    image = _rgb(bitmap.to_pil())
                                finally:
                                    bitmap.close()
                                check_budget(*image.size)
                                save_page(image, number + 1, limits.pdf_dpi)
                                doc.ingestion_details.append(dict(page_index=number + 1,
                                    pdf_size_points=[width, height], dpi=limits.pdf_dpi,
                                    pixel_size=list(image.size), point_origin='top_left',
                                    points_to_original_pixels_scale=limits.pdf_dpi / 72,
                                    alpha_background='white', color_conversion='RGB'))
                                image.close()
                            finally:
                                page.close()
                        except Exception as exc:
                            doc.errors.append(f'PDF page {number + 1}: {type(exc).__name__}: {exc}')
                            # Failed pages consume a slot, preventing unbounded render attempts.
                            used_pages += 1
                    if count > allowance:
                        doc.errors.append(f'PDF has {count} pages; {count - allowance} omitted by application page limit')
            else:
                import io
                with warnings.catch_warnings():
                    warnings.simplefilter('error', Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(content)) as raw:
                        if raw.format not in {'PNG', 'JPEG'}:
                            raise ValueError('decoded format is not PNG/JPEG')
                        if getattr(raw, 'n_frames', 1) != 1:
                            raise ValueError('animated/multiframe images unsupported; use a PDF')
                        check_budget(*raw.size)
                        raw_size, orientation = raw.size, raw.getexif().get(274, 1)
                        had_alpha = raw.mode in {'RGBA', 'LA'} or 'transparency' in raw.info
                        oriented = ImageOps.exif_transpose(raw)
                        image = _rgb(oriented)
                        check_budget(*image.size)
                        save_page(image, 1, None)
                        doc.ingestion_details.append(dict(page_index=1, decoded_size=list(raw_size),
                            exif_orientation=orientation, exif_transpose_applied=True,
                            pixel_size=list(image.size), had_alpha=had_alpha,
                            alpha_background='white', color_conversion='RGB'))
                        image.close()
        except Exception as exc:
            doc.errors.append(f'Input {path.name}: {type(exc).__name__}: {exc}')
    return documents
