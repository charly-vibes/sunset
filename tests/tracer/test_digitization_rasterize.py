"""Contract tests for the text-PDF -> image-only-PDF rasterizer (sunset-9op).

Ground-truth OCR experiments need an image-only derivative of a text PDF:
same page geometry, pixels only, no text layer — so OCR region claims can be
compared against the native truth and reviewed over the rasterized render.
"""

import json
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization.rasterize', *map(str, args)],
        cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def make_text_pdf(path, pages=2):
    with pymupdf.open() as pdf:
        for n in range(pages):
            page = pdf.new_page(width=300, height=400)
            page.insert_text((30, 40), f'Pagina {n + 1} con texto nativo')
            page.insert_text((30, 60), 'SALDO ANTERIOR 1.234,56')
        pdf.save(path)
    return path


def test_rasterize_produces_textless_image_pdf(tmp_path):
    from digitization.rasterize import rasterize

    source = make_text_pdf(tmp_path / 'source.pdf')
    assert 'texto nativo' in pymupdf.open(source)[0].get_text()

    result = rasterize(source, tmp_path / 'raster', dpi=150)
    image_pdf = tmp_path / 'raster' / result['image_pdf']
    assert image_pdf.is_file()
    assert result['dpi'] == 150
    assert sorted(int(p) for p in result['pages']) == [1, 2]
    for ref in result['pages'].values():
        assert (tmp_path / 'raster' / ref['path']).is_file()

    with pymupdf.open(image_pdf) as doc:
        assert doc.page_count == 2
        for i, page in enumerate(doc, start=1):
            assert page.get_text().strip() == '', f'page {i} grew a text layer'
            assert page.get_images(), f'page {i} has no image'
            assert abs(page.rect.width - 300) < 1 and abs(page.rect.height - 400) < 1


def test_rasterize_cli_reports_typed_result(tmp_path):
    source = make_text_pdf(tmp_path / 'source.pdf')
    code, result = cli('--source', source, '--output-dir', tmp_path / 'raster',
                       '--dpi', '150')
    assert code == 0
    assert result['status'] == 'rasterized'
    assert sorted(int(k) for k in result['pages']) == [1, 2]
    assert (tmp_path / 'raster' / 'image.pdf').is_file()


def test_rasterize_rejects_unreadable_source(tmp_path):
    bogus = tmp_path / 'bogus.pdf'
    bogus.write_bytes(b'not a pdf')
    code, result = cli('--source', bogus, '--output-dir', tmp_path / 'raster')
    assert code == 3
    assert result['status'] == 'invalid-input'
