"""Contract tests for the image-based region proposal step (sunset-rmx.15).

The regional route must discover initial regions from rendered page pixels
WITHOUT any OCR run (add-iterative-document-digitization design step 1: do
not require OCR to discover initial regions). The detector is a deterministic
layout tool proposing initial geometry: it emits detections in the recorded
config format consumed by digitization.pipeline (id / kind / bbox with
nonnegative integer y-down page points, width/height nonzero, inside the page
frame). Recognitions are NOT its business — the crop-OCR adapter fills those
per proposed region in a later slice.
"""

import subprocess
import sys
from pathlib import Path

import pymupdf

from digitization.detect import detect_regions
from digitization.render import render_page

ROOT = Path(__file__).resolve().parents[2]


def make_pdf(path, blocks, width=300, height=400):
    """Blocks are (x, y, text) tuples in page points, well separated."""
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=width, height=height)
        for x, y, text in blocks:
            page.insert_text((x, y), text)
        pdf.save(path)
    return path


def rendered(path, dpi=96):
    png, meta = render_page(Path(path).read_bytes(), 1, dpi)
    return png, meta


def test_two_separated_blocks_propose_two_disjoint_regions(tmp_path):
    source = make_pdf(tmp_path / 'two-blocks.pdf',
                      [(30, 40, 'Primer parrafo con texto'),
                       (30, 300, 'Segundo parrafo distante')])
    png, meta = rendered(source)
    detections = detect_regions(png, meta)
    assert len(detections) == 2
    first, second = detections
    # each proposal covers the ink of exactly one inserted block
    # (blocks inserted at y=40 and y=300 page points)
    assert first['bbox'][1] < meta['height_pt'] / 2 < second['bbox'][1]
    for box in (first, second):
        assert box['kind']
        assert box['id']


def test_boxes_are_nonnegative_integer_ydown_points_inside_frame(tmp_path):
    source = make_pdf(tmp_path / 'frame.pdf', [(20, 30, 'Caja acotada')])
    png, meta = rendered(source)
    for box in detect_regions(png, meta):
        x, y, w, h = box['bbox']
        assert all(type(v) is int and v >= 0 for v in (x, y, w, h))
        assert w >= 1 and h >= 1
        assert x + w <= meta['width_pt']
        assert y + h <= meta['height_pt']


def test_detector_runs_no_ocr_no_subprocess(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError('detector must not invoke any subprocess/OCR')
    monkeypatch.setattr(subprocess, 'run', explode)
    source = make_pdf(tmp_path / 'quiet.pdf', [(30, 40, 'Solo tinta')])
    png, meta = rendered(source)
    assert detect_regions(png, meta)


def test_blank_page_proposes_nothing(tmp_path):
    source = make_pdf(tmp_path / 'blank.pdf', [])
    png, meta = rendered(source)
    assert detect_regions(png, meta) == []


def test_reading_order_ids_top_to_bottom(tmp_path):
    source = make_pdf(tmp_path / 'order.pdf',
                      [(30, 40, 'Arriba'),
                       (30, 150, 'Medio'),
                       (30, 300, 'Abajo')])
    png, meta = rendered(source)
    detections = detect_regions(png, meta)
    assert [d['id'] for d in detections] == ['det-1', 'det-2', 'det-3']
    ys = [d['bbox'][1] for d in detections]
    assert ys == sorted(ys)


def test_deterministic_identical_output(tmp_path):
    source = make_pdf(tmp_path / 'stable.pdf', [(30, 40, 'Igual')])
    png, meta = rendered(source)
    assert detect_regions(png, meta) == detect_regions(png, meta)


def test_horizontal_neighbors_split_into_columns(tmp_path):
    source = make_pdf(tmp_path / 'columns.pdf',
                      [(30, 180, 'Columna izquierda'),
                       (200, 180, 'Columna derecha')], width=300, height=400)
    png, meta = rendered(source)
    detections = detect_regions(png, meta)
    assert len(detections) == 2
    left, right = detections
    assert left['bbox'][0] < right['bbox'][0]
    assert left['bbox'][0] + left['bbox'][2] <= right['bbox'][0] + 1
