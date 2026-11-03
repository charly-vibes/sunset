"""Contract tests for OCR recorded configs (sunset-9op).

tesseract (pinned, spa) reads the rasterized page PNGs; its TSV line boxes
(pixel space, y-down) become detections converted to page points, and its
line text becomes recorded recognitions. The config targets the image-only
PDF produced by digitization.rasterize, so the recorded pipeline can export
geometry-bearing OCR descriptors for image PDFs — the region-recognition
half of the ground-truth comparison loop.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from digitization.rasterize import rasterize
from dsc03 import validator

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cli(*args):
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization.ocr_config', *map(str, args)],
        cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.fixture
def rasterized(tmp_path):
    source = tmp_path / 'source.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Resumen Caja de Ahorro')
        page.insert_text((30, 60), 'SALDO ANTERIOR 1.234,56')
        pdf.save(source)
    result = rasterize(source, tmp_path / 'raster', dpi=150)
    return source, tmp_path / 'raster', result


def test_ocr_config_shape_and_provider_pin(rasterized, tmp_path):
    source, raster_dir, raster_result = rasterized
    image_pdf = raster_dir / raster_result['image_pdf']
    out = tmp_path / 'ocr.json'
    code, result = cli('--image-pdf', image_pdf, '--pages-dir', raster_dir,
                       '--dpi', '150', '--output', out)
    assert code == 0 and result['status'] == 'ocr-config'
    assert result['provider'] == 'tesseract-ocr'
    config = json.loads(out.read_text())
    assert config['version'] == '1'
    assert config['source_sha256'] == sha(image_pdf.read_bytes())
    assert config['provider']['kind'] == 'recorded'
    assert config['provider']['id'] == 'tesseract-ocr'
    assert config['render'] == {'dpi': 150}
    assert sorted(config['pages']) == ['1']
    page = config['pages']['1']
    assert page['detections'], 'OCR must claim the visible text'
    line_text = ' '.join(r['raw_text'] for r in page['recognitions'].values()).lower()
    assert 'resumen' in line_text and 'saldo' in line_text
    for detection in page['detections']:
        x, y, w, h = detection['bbox']
        assert type(x) is int and w > 0 and h > 0
        assert x + w <= 300 and y + h <= 400
        assert detection['kind'] == 'text-line'
    assert set(page['recognitions']) == {d['id'] for d in page['detections']}


def test_ocr_config_runs_the_real_pipeline_on_the_image_pdf(rasterized, tmp_path):
    source, raster_dir, raster_result = rasterized
    image_pdf = raster_dir / raster_result['image_pdf']
    config_path = tmp_path / 'ocr.json'
    code, _ = cli('--image-pdf', image_pdf, '--pages-dir', raster_dir,
                  '--dpi', '150', '--output', config_path)
    assert code == 0
    out = tmp_path / 'run-ocr'
    r = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization', 'run', '--source', image_pdf,
         '--pages', '1', '--config', config_path, '--output', out],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    manifest = json.loads((out / 'manifest.json').read_text())
    descriptor = validator.load(out / manifest['descriptor']['path'])
    assert validator.validate(descriptor) == []
    claimed = [rg for rg in descriptor['regions'] if 'geometry' in rg]
    assert claimed, 'OCR config must yield geometry-bearing claims'
    texts = ' '.join(c['value'] for c in descriptor['contents'] if c['kind'] == 'text').lower()
    assert 'saldo' in texts
