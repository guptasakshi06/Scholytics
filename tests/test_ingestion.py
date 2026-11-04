"""Real decoder/render behavior, limits and source geometry."""
from pathlib import Path

from PIL import Image
import pytest
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas

from scholarready.ingestion import ingest, IngestionLimits

FIXTURES = Path(__file__).parent / 'fixtures/pilot'


def test_exif_alpha_and_content_ids(tmp_path):
    rgba = Image.new('RGBA', (12, 8), (255, 0, 0, 0))
    exif = Image.Exif()
    exif[274] = 6
    path = tmp_path / 'oriented.png'
    rgba.save(path, exif=exif)
    docs = ingest([path], tmp_path / 'run', IngestionLimits())
    p = docs[0].pages[0]
    assert (p.width, p.height) == (8, 12)
    with Image.open(tmp_path / 'run' / p.original_image_path) as decoded:
        assert decoded.getpixel((0, 0)) == (255, 255, 255)
    renamed = tmp_path / 'unrelated.png'
    renamed.write_bytes(path.read_bytes())
    again = ingest([renamed], tmp_path / 'run2', IngestionLimits())[0]
    assert again.document_id == docs[0].document_id
    assert again.pages[0].page_id == p.page_id
    assert again.pages[0].original_filename == 'unrelated.png'


def test_multipage_pdf_300dpi_and_lifetime(tmp_path):
    doc = ingest([FIXTURES / 'src-025.pdf'], tmp_path, IngestionLimits())[0]
    assert not doc.errors
    assert [p.page_index for p in doc.pages] == [1, 2]
    assert len({p.document_id for p in doc.pages}) == 1
    assert len({p.page_id for p in doc.pages}) == 2
    for p in doc.pages:
        assert (p.width, p.height) == (2500, 3334)
        assert p.rasterization_dpi == 300
        with Image.open(tmp_path / p.original_image_path) as im:
            assert im.mode == 'RGB'
            assert im.getextrema() != ((255, 255),) * 3


def test_failed_pages_and_other_files_are_explicit(tmp_path):
    corrupt = tmp_path / 'bad.png'; corrupt.write_bytes(b'broken')
    unsupported = tmp_path / 'bad.txt'; unsupported.write_text('not a document')
    encrypted = tmp_path / 'locked.pdf'
    c = canvas.Canvas(str(encrypted), encrypt=StandardEncryption('secret')); c.drawString(20, 20, 'fictional'); c.save()
    docs = ingest([corrupt, unsupported, encrypted, tmp_path / 'missing.pdf'], tmp_path / 'run', IngestionLimits())
    assert all(d.errors and not d.pages for d in docs)
    assert 'unsupported' in docs[1].errors[0]
    assert 'password' in docs[2].errors[0].lower() or 'encrypt' in docs[2].errors[0].lower()


def test_empty_password_encrypted_is_also_rejected(tmp_path):
    path = tmp_path / 'encrypted.pdf'
    c = canvas.Canvas(str(path), encrypt=StandardEncryption('', ownerPassword='owner'))
    c.drawString(20, 20, 'fictional'); c.save()
    doc = ingest([path], tmp_path / 'run', IngestionLimits())[0]
    assert doc.errors and 'encrypted' in doc.errors[0]


def test_page_pixel_file_and_inventory_budgets(tmp_path):
    pdf = FIXTURES / 'src-025.pdf'
    partial = ingest([pdf], tmp_path / 'partial', IngestionLimits(max_pages=1))[0]
    assert len(partial.pages) == 1 and any('omitted' in e for e in partial.errors)
    giant = ingest([pdf], tmp_path / 'giant', IngestionLimits(max_page_pixels=100))[0]
    assert not giant.pages and len(giant.errors) == 2
    small = ingest([FIXTURES / 'src-001.png'], tmp_path / 'size', IngestionLimits(max_file_bytes=2))[0]
    assert small.errors and not small.pages
    total = ingest([FIXTURES / 'src-001.png', FIXTURES / 'src-002.png'], tmp_path / 'total',
                   IngestionLimits(max_total_pixels=1_920_000))
    assert len(total[0].pages) == 1 and not total[1].pages and total[1].errors
    with pytest.raises(ValueError, match='max_files'):
        ingest([pdf, pdf], tmp_path / 'count', IngestionLimits(max_files=1))


@pytest.mark.parametrize('kwargs', [dict(max_pages=0), dict(max_page_pixels=-1), dict(pdf_dpi=601)])
def test_invalid_limits(kwargs):
    with pytest.raises(ValueError):
        IngestionLimits(**kwargs)


def test_corrupt_decode_error_is_stable(tmp_path):
    path = tmp_path / 'broken.png'
    path.write_bytes(b'fictional corrupt image')
    first = ingest([path], tmp_path / 'run1', IngestionLimits())[0]
    second = ingest([path], tmp_path / 'run2', IngestionLimits())[0]
    assert first.errors == second.errors == [
        'Input broken.png: UnidentifiedImageError: cannot decode as PNG/JPEG']
    assert first.pages == second.pages == []
