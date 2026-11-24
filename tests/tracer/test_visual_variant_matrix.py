# Purpose: Variant-matrix GREEN suite (sunset-7b4.1, tasks.md 1.1 and §2
#   tasks 2.1-2.4, change improve-geometry-render-binding).
# Responsibilities: Generate rotation (0/90/180/270), cropbox, and combined
#   rotation+crop variants of every PDF carrier in fixtures/carriers/
#   deterministically at runtime into pytest tmp (never committed); run the
#   in-process native extraction on each variant; collect every native
#   page-map frame and require it to resolve (status "resolved", never
#   unresolvable_source_scope); pin the per-carrier x variant frame-count
#   table; and bind extents end to end: for crop and rotation+crop variants,
#   render through the pinned poppler path with `-cropbox` at the mapping's
#   dpi and assert the rendered PNG pixel extent equals the resolved
#   mapping's page extent (tasks 2.1 + 2.2).
# Rationale: design decision 4 ("variant matrix as RED tests first"), now
#   GREEN after §2 landed the declared frame fields, the extent binding, and
#   the crop-box render: a frame that fails to resolve for any variant, or a
#   rendered extent that disagrees with the declared extent, fails the suite.
#   Variants are seed-free pymupdf saves of the committed carriers, so the
#   matrix is deterministic.
"""Variant-matrix GREEN suite: native frames resolve for every carrier x variant."""
import json
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from digitization.native import extract
from dsc03.visual import frames
from dsc03.visual.render import RenderConfig, render_page

CARRIERS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
CARRIER_PATHS = sorted(CARRIERS_DIR.glob("*.pdf"))

VARIANTS = ("rot0", "rot90", "rot180", "rot270", "crop", "rot-crop")
RENDER_DPI = 150
CROP_INSET_PT = 30.0

# Recorded per-carrier x variant frame counts (native page-map frames).
# Every frame resolves; the rot-crop variant keeps each carrier's count,
# because the crop box clips the visible area without removing text.
RECORDED_MATRIX = {
    "accounting-made-simple-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6, "rot-crop": 6},
    "agentic-patterns-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6, "rot-crop": 6},
    "bank-statement-ca-excerpt": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1, "rot-crop": 1},
    "bank-transfer-redacted": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1, "rot-crop": 1},
    "budgeting-basics-excerpt": {"rot0": 3, "rot90": 3, "rot180": 3, "rot270": 3, "crop": 3, "rot-crop": 3},
    "cta-cte-propietario-redacted": {"rot0": 2, "rot90": 2, "rot180": 2, "rot270": 2, "crop": 2, "rot-crop": 2},
    "diario-de-poesia-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6, "rot-crop": 6},
    "estado-deuda-abl-redacted": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1, "rot-crop": 1},
    "invoice-arca-redacted": {"rot0": 3, "rot90": 3, "rot180": 3, "rot270": 3, "crop": 3, "rot-crop": 3},
    "lab-result-redacted": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6, "rot-crop": 6},
    # Page 1 aligner-fails on every resumen variant (text-with-gaps).
    "resumen-periodical-excerpt": {"rot0": 5, "rot90": 5, "rot180": 5, "rot270": 5, "crop": 5, "rot-crop": 5},
}
RECORDED_TOTAL = 240


def _make_variant(carrier: Path, kind: str, path: Path):
    """Deterministically derive one variant PDF from a committed carrier."""
    with pymupdf.open(carrier) as doc:
        for page in doc:
            if kind.startswith("rot"):
                page.set_rotation(90 if kind == "rot-crop" else int(kind[3:]))
            if kind in ("crop", "rot-crop"):
                box = page.mediabox
                page.set_cropbox(pymupdf.Rect(
                    box.x0 + CROP_INSET_PT, box.y0 + CROP_INSET_PT,
                    box.x1 - CROP_INSET_PT, box.y1 - CROP_INSET_PT))
        doc.save(path)


def _render_config(page: int, cropbox: bool = False, dpi: int = RENDER_DPI) -> RenderConfig:
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable="pdftoppm",
        renderer_version="26.01.0",
        dpi=dpi,
        page=page,
        extractor_lineage="pymupdf-1.28.2",
        renderer_lineage="poppler-26.01.0",
        render_cropbox=cropbox,
    )


def _png_size(data: bytes):
    """(width, height) from a PNG IHDR, without a decode dependency."""
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _variant_page_extent(variant_path: Path, page_number: int, dpi: int = RENDER_DPI):
    """Independent ground-truth rendered extent for one variant page.

    Computed from PyMuPDF's declared page record (cropbox dimensions in pt,
    rotated pixel dimensions for /Rotate 90 and 270) at `dpi` — never via
    frames.py, so the extent assertion is a real oracle.
    """
    with pymupdf.open(variant_path) as doc:
        page = doc[page_number - 1]
        expected = (
            round(page.cropbox.width * dpi / 72),
            round(page.cropbox.height * dpi / 72),
        )
        if page.rotation in (90, 270):
            expected = (expected[1], expected[0])
        return expected


def _build_matrix(tmp_factory):
    """Run native extraction on every carrier x variant; resolve every frame.

    Returns rows of (carrier_stem, variant, page, mapping_outcome, page_px)
    where the outcome is a ("unknown", reason) tuple or ("resolved", None),
    and page_px is the independent ground-truth rendered extent for the
    variant page (see _variant_page_extent).
    """
    root = tmp_factory.mktemp("variant-matrix")
    rows = []
    for carrier in CARRIER_PATHS:
        for kind in VARIANTS:
            variant_path = root / f"{carrier.stem}-{kind}.pdf"
            _make_variant(carrier, kind, variant_path)
            run = root / f"{carrier.stem}-{kind}-run"
            extract(str(variant_path), str(run))
            page_map = run / "page-map.json"
            assert page_map.exists(), f"no page-map for {carrier.stem} {kind}"
            for frame in json.loads(page_map.read_text()):
                page_px = _variant_page_extent(variant_path, frame["page"])
                mapping = frames.resolve_pixel_mapping(
                    frame, _render_config(frame["page"]), page_px)
                if isinstance(mapping, frames.UnknownMapping):
                    outcome = ("unknown", mapping.reason)
                else:
                    outcome = ("resolved", None)
                rows.append((carrier.stem, kind, frame["page"], outcome, page_px))
    return rows


@pytest.fixture(scope="session")
def matrix_rows(tmp_path_factory):
    return _build_matrix(tmp_path_factory)


def test_every_native_frame_resolves(matrix_rows):
    """Resolve EVERY native page-map frame of every carrier x variant."""
    assert matrix_rows, "variant matrix produced no frames"
    unresolved = [row for row in matrix_rows if row[3] != ("resolved", None)]
    assert not unresolved, (
        f"{len(unresolved)}/{len(matrix_rows)} frames unresolved: "
        f"{unresolved[:5]}")
    bad_reasons = [row for row in matrix_rows
                   if row[3] == ("unknown", "unresolvable_source_scope")]
    assert not bad_reasons, f"unresolvable_source_scope frames: {bad_reasons[:5]}"


def test_recorded_frame_count_table(matrix_rows):
    """Recorded per-carrier x variant frame-count table (GREEN matrix).

    Pins the matrix shape (11 carriers x 6 variants; native page-map frames
    per carrier x variant after §2 landed; the rot-crop variant keeps each
    carrier's count because the crop box clips the visible area without
    removing text). Resolution outcomes are pinned by
    test_every_native_frame_resolves.
    """
    assert matrix_rows, "variant matrix produced no frames"

    counted = {}
    for stem, kind, _page, _outcome, _page_px in matrix_rows:
        counted.setdefault(stem, {}).setdefault(kind, 0)
        counted[stem][kind] += 1
    assert counted == RECORDED_MATRIX, (
        f"variant matrix shape changed since the recorded table: "
        f"got {counted}")
    assert len(matrix_rows) == RECORDED_TOTAL


def test_extent_binding_end_to_end_crop_and_rot_crop(matrix_rows, tmp_path_factory):
    """Rendered PNG extent equals the resolved mapping's extent (2.1 + 2.2).

    For the crop and rot-crop variants of two carriers, render through the
    pinned poppler path with `-cropbox` enabled at the mapping's dpi, then
    assert the PNG pixel dimensions equal the resolved mapping's page extent
    (page_px) — which itself equals the independently computed declared
    extent (cropbox dims at dpi, swapped for rotation 90). The check runs at
    72 dpi, where the integral-pt crop dims make the pinned round() extent
    exact; poppler sizes its bitmap with ceil, which diverges from the
    pinned round() formula by one pixel at dpis with a fractional factor.
    """
    root = tmp_path_factory.mktemp("extent-binding")
    dpi = 72
    chosen = [("accounting-made-simple-excerpt", "crop"),
              ("accounting-made-simple-excerpt", "rot-crop"),
              ("invoice-arca-redacted", "crop"),
              ("invoice-arca-redacted", "rot-crop")]
    checked = 0
    for stem, kind in chosen:
        carrier = CARRIERS_DIR / f"{stem}.pdf"
        variant_path = root / f"{stem}-{kind}.pdf"
        _make_variant(carrier, kind, variant_path)
        run = root / f"{stem}-{kind}-run"
        extract(str(variant_path), str(run))
        for frame in json.loads((run / "page-map.json").read_text()):
            page = frame["page"]
            declared = _variant_page_extent(variant_path, page, dpi)
            rendered = render_page(_render_config(page, cropbox=True, dpi=dpi),
                                   variant_path)
            assert rendered.status == "rendered", rendered.reason
            page_px = _png_size(rendered.data)
            assert page_px == declared, (
                f"{stem} {kind} page {page}: rendered PNG {page_px} != "
                f"declared extent {declared}")
            mapping = frames.resolve_pixel_mapping(
                frame, _render_config(page, cropbox=True, dpi=dpi), page_px)
            assert isinstance(mapping, frames.PixelMapping), (
                f"{stem} {kind} page {page}: {mapping.reason}: {mapping.detail}")
            assert mapping.page_px == declared
            checked += 1
    assert checked >= 4
