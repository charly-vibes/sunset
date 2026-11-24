# Purpose: Variant-matrix RED baseline (sunset-7b4.1, tasks.md 1.1, change
#   improve-geometry-render-binding).
# Responsibilities: Generate rotation (0/90/180/270) and cropbox variants of
#   every PDF carrier in fixtures/carriers/ deterministically at runtime into
#   pytest tmp (never committed), run the in-process native extraction on each
#   variant, collect every native page-map frame, and pin the HEAD baseline:
#   resolve_pixel_mapping refuses EVERY frame with the typed unknown
#   `unresolvable_source_scope`, because native page-map records carry
#   source_frame/target_frame/source_to_page/source_origin/source_dimensions
#   but not the declared fields resolve_pixel_mapping requires
#   (source_scope, origin, axes, scale, rotation, crop). The resolution test
#   is strict-xfail so a future xpass (sunset-7b4 §2 tasks 2.1-2.3 removing
#   the marker) fails loudly; the recorded-table test stays green at HEAD and
#   documents the baseline numerically.
# Rationale: design decision 4 ("variant matrix as RED tests first"): a frame
#   that fails to resolve for any variant is the RED state this change's
#   implementation must turn green. Variants are seed-free pymupdf saves of
#   the committed carriers, so the matrix is deterministic.
"""Variant-matrix RED baseline: native frames vs resolve_pixel_mapping."""
import json
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from digitization.native import extract
from dsc03.visual import frames
from dsc03.visual.render import RenderConfig

CARRIERS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
CARRIER_PATHS = sorted(CARRIERS_DIR.glob("*.pdf"))

VARIANTS = ("rot0", "rot90", "rot180", "rot270", "crop")
RENDER_DPI = 150
CROP_INSET_PT = 30.0

# Measured HEAD baseline (agent-executed 2026-11-24, beads sunset-7b4.1):
# carrier stem -> variant -> number of native page-map frames collected.
# Every one of the 200 frames resolved to unknown/unresolvable_source_scope.
RECORDED_MATRIX = {
    "accounting-made-simple-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6},
    "agentic-patterns-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6},
    "bank-statement-ca-excerpt": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1},
    "bank-transfer-redacted": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1},
    "budgeting-basics-excerpt": {"rot0": 3, "rot90": 3, "rot180": 3, "rot270": 3, "crop": 3},
    "cta-cte-propietario-redacted": {"rot0": 2, "rot90": 2, "rot180": 2, "rot270": 2, "crop": 2},
    "diario-de-poesia-excerpt": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6},
    "estado-deuda-abl-redacted": {"rot0": 1, "rot90": 1, "rot180": 1, "rot270": 1, "crop": 1},
    "invoice-arca-redacted": {"rot0": 3, "rot90": 3, "rot180": 3, "rot270": 3, "crop": 3},
    "lab-result-redacted": {"rot0": 6, "rot90": 6, "rot180": 6, "rot270": 6, "crop": 6},
    # Page 1 aligner-fails on every resumen variant (text-with-gaps).
    "resumen-periodical-excerpt": {"rot0": 5, "rot90": 5, "rot180": 5, "rot270": 5, "crop": 5},
}
RECORDED_TOTAL = 200


def _make_variant(carrier: Path, kind: str, path: Path):
    """Deterministically derive one variant PDF from a committed carrier."""
    with pymupdf.open(carrier) as doc:
        for page in doc:
            if kind.startswith("rot"):
                page.set_rotation(int(kind[3:]))
            elif kind == "crop":
                box = page.mediabox
                page.set_cropbox(pymupdf.Rect(
                    box.x0 + CROP_INSET_PT, box.y0 + CROP_INSET_PT,
                    box.x1 - CROP_INSET_PT, box.y1 - CROP_INSET_PT))
            else:
                raise ValueError(kind)
        doc.save(path)


def _render_config(page: int) -> RenderConfig:
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable="pdftoppm",
        renderer_version="26.01.0",
        dpi=RENDER_DPI,
        page=page,
        extractor_lineage="pymupdf-1.28.2",
        renderer_lineage="poppler-26.01.0",
    )


def _build_matrix(tmp_factory):
    """Run native extraction on every carrier x variant; resolve every frame.

    Returns rows of (carrier_stem, variant, page, mapping_outcome) where the
    outcome is a ("unknown", reason) tuple or ("resolved", None).
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
                mapping = frames.resolve_pixel_mapping(
                    frame, _render_config(frame["page"]), (612, 792))
                if isinstance(mapping, frames.UnknownMapping):
                    outcome = ("unknown", mapping.reason)
                else:
                    outcome = ("resolved", None)
                rows.append((carrier.stem, kind, frame["page"], outcome))
    return rows


@pytest.fixture(scope="session")
def matrix_rows(tmp_path_factory):
    return _build_matrix(tmp_path_factory)


@pytest.mark.xfail(strict=True, reason=(
    "unresolvable_source_scope at HEAD; marker removed by sunset-7b4 §2 "
    "implementation (tasks 2.1-2.3)"))
def test_every_native_frame_resolves(matrix_rows):
    """Resolve EVERY native page-map frame of every carrier x variant."""
    assert matrix_rows, "variant matrix produced no frames"
    unresolved = [row for row in matrix_rows if row[3] != ("resolved", None)]
    assert not unresolved, (
        f"{len(unresolved)}/{len(matrix_rows)} frames unresolved: "
        f"{unresolved[:5]}")


def test_head_baseline_all_frames_unknown_unresolvable_source_scope(
        matrix_rows):
    """Recorded HEAD baseline: every outcome is unknown/unresolvable_source_scope.

    Documents the RED baseline numerically (agent-executed 2026-11-24,
    beads sunset-7b4.1, change improve-geometry-render-binding); supersedes
    the chat-recorded baseline. Green at HEAD; when sunset-7b4 §2 lands this
    test is updated together with removing the strict xfail above.
    """
    assert matrix_rows, "variant matrix produced no frames"
    wrong = [row for row in matrix_rows
             if row[3] != ("unknown", "unresolvable_source_scope")]
    assert not wrong, f"unexpected outcomes at HEAD: {wrong[:5]}"

    counted = {}
    for stem, kind, _page, _outcome in matrix_rows:
        counted.setdefault(stem, {}).setdefault(kind, 0)
        counted[stem][kind] += 1
    assert counted == RECORDED_MATRIX, (
        f"variant matrix shape changed since the recorded baseline: "
        f"got {counted}")
    assert len(matrix_rows) == RECORDED_TOTAL
