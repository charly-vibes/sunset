"""Shared test bootstrap and builders for the tracer suites (rule-of-5
EXCL-001: one pinned poppler RenderConfig builder and one synthetic-carrier
builder, instead of per-file copies)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pymupdf

from dsc03.visual import render
from dsc03.visual.render import Binarization, RenderConfig

CARRIERS = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"


def poppler_executable():
    return shutil.which("pdftoppm") or "/usr/bin/pdftoppm"


def render_config(*, page=1, dpi=72, enabled=True, threshold=128,
                  simplification="ink-dilation-2px", extractor="pymupdf",
                  renderer="poppler", executable=None):
    """The pinned real-render configuration used by the oracle suites.

    Deliberately detects the installed poppler; mapping-only suites
    (frames, variant matrix) keep their own fake-pinned configs on purpose.
    """
    exe = executable or poppler_executable()
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=exe,
        renderer_version=render.detect_renderer_version(exe),
        dpi=dpi,
        page=page,
        binarization=Binarization(enabled=enabled, method="fixed-threshold",
                                  threshold=threshold),
        source_simplification=simplification,
        extractor_lineage=extractor,
        renderer_lineage=renderer,
    )


def make_carrier(tmp_path, name, rects, width=612, height=792,
                 blank_pages_after=0, white_rects=()):
    """White page + filled black rects (fitz coords) -> saved PDF path.

    ``white_rects`` are filled white AFTER the black rects (punches holes in
    the ink); ``blank_pages_after`` appends that many genuinely blank
    trailing pages (used to render a real blank page 2 of the same document).
    """
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    for rect in rects:
        page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))
    for rect in white_rects:
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    for _ in range(blank_pages_after):
        doc.new_page(width=width, height=height)
    path = tmp_path / name
    doc.save(str(path))
    return path
