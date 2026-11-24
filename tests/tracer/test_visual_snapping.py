# Purpose: Tight-ink snapping tests (sunset-7b4.7, review finding EDGE-005).
# Responsibilities: Pin the snap contract for declared boxes against the
#   pinned raster: per edge, ink is measured via the shared _pixels ink mask
#   and the edge snaps to the tight ink boundary when within the DECLARED
#   tolerance (explicit constant with the zoom.py 0.5 pt derivation);
#   sub-tolerance overhang is accepted and recorded — never refused
#   (EDGE-005 BINDING CONSTRAINT); a snap beyond tolerance is refused with a
#   typed witness carrying the declared vs tight box; an edge with no
#   contiguous ink within the band does not silently snap (typed refusal);
#   snapped operative boxes stay quantized 1/1000 pt under the declared
#   round-half-even rule (idempotent — never re-quantized differently); the
#   result is deterministic across processes. Synthetic carriers are built
#   seed-free with pymupdf fill-only rects so ink lands exactly on integer
#   pixel boundaries at 72 dpi (no stroke spill) — every expected number is
#   hand-computed.
# Rationale: improve-geometry-render-binding proposal Non-goals lift
#   (sunset-7b4.7) + EDGE-005: the containment statistic must DECLARE a
#   tolerance and never refuse sub-point box overhangs; snapping is the
#   recorded, deterministic counterpart. All numbers below are
#   agent-executed measurements of pinned carriers, not accuracy claims.
"""Tight-ink snapping tests (sunset-7b4.7, EDGE-005)."""
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dsc03.substrate.space import quantize_scalar
from dsc03.visual import render, snap

from conftest import render_config

# --- synthetic carrier geometry (hand-computed, seed-free) --------------------
#
# 612x792pt white page; fill-only black rect at fitz Rect(200, 392, 300, 492).
# pymupdf draws with a TOP-LEFT y-down origin, so the descriptor (y-up,
# bottom-left) ink rect is x 200..300, y 300..400 pt. Fill-only (no stroke).
# Agent-executed measurement of the pinned render at 72 dpi: poppler inks
# the boundary pixels inclusively — cols 200..300, rows 392..492 — so the
# tight half-open pixel extent maps to the tight descriptor box
# (200, 299, 101, 101) (one boundary pixel of slack on the max sides).
PAGE_W, PAGE_H = 612, 792
FITZ_RECT = pymupdf.Rect(200, 392, 300, 492)
TIGHT = (200, 299, 101, 101)  # x, y, w, h descriptor pt (measured)


def _carrier(tmp_path, rects, name="snap-carrier.pdf"):
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    for rect in rects:
        page.draw_rect(rect, fill=(0, 0, 0))  # fill-only: no stroke spill
    path = tmp_path / name
    doc.save(str(path))
    return path


def _rendered(tmp_path, rects=(FITZ_RECT,), name="snap-carrier.pdf"):
    config = render_config(dpi=72, simplification="ink-dilation-2px")
    pdf = _carrier(tmp_path, list(rects), name=name)
    result = render.render_page(config, pdf)
    assert isinstance(result, render.Rendered), result.reason
    png = tmp_path / (name + ".png")
    png.write_bytes(result.data)
    return config, png, result


# --- loose box snaps tight, per-edge deltas recorded ---------------------------


def test_loose_box_snaps_tight_with_recorded_deltas(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    # a box drawn loosely around text snaps tight: declared box 3 pt slack
    # on every side of the nominal ink rect, with the tolerance DECLARED
    # large enough to admit that slack (the default 0.5 pt would refuse it —
    # see the beyond-tolerance test)
    box = {"x": 197.0, "y": 297.0, "width": 106.0, "height": 106.0}
    outcome = snap.snap_box_to_ink(rendered, config, box, tolerance=3.0)
    assert outcome["status"] == "snapped"
    assert outcome["tolerance"] == 3.0
    tx, ty, tw, th = TIGHT
    assert outcome["box"] == {"x": tx * 1000, "y": ty * 1000,
                              "width": tw * 1000, "height": th * 1000}
    # signed tight-minus-declared, pt (agent-executed pinned values)
    assert outcome["deltas"] == {"left": 3.0, "right": -2.0,
                                 "top": -3.0, "bottom": 2.0}


def test_exact_box_snaps_with_zero_deltas(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    tx, ty, tw, th = TIGHT
    box = {"x": float(tx), "y": float(ty), "width": float(tw),
           "height": float(th)}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    assert outcome["status"] == "snapped"
    assert outcome["deltas"] == {"left": 0.0, "right": 0.0,
                                 "top": 0.0, "bottom": 0.0}
    assert outcome["box"] == {"x": tx * 1000, "y": ty * 1000,
                              "width": tw * 1000, "height": th * 1000}


# --- sub-point overhang accepted and recorded, never refused (EDGE-005) -------


def test_sub_point_overhang_accepted_not_refused(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    # declared box overhangs the tight ink by 0.3 pt on every edge (< 0.5 pt)
    tx, ty, tw, th = TIGHT
    box = {"x": tx - 0.3, "y": ty - 0.3, "width": tw + 0.6,
           "height": th + 0.6}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    assert outcome["status"] == "snapped"  # accepted, never refused
    assert outcome["deltas"] == pytest.approx(
        {"left": 0.3, "right": -0.3, "top": -0.3, "bottom": 0.3})
    assert outcome["box"] == {"x": tx * 1000, "y": ty * 1000,
                              "width": tw * 1000, "height": th * 1000}


# --- beyond-tolerance snap refused with typed witness --------------------------


def test_beyond_tolerance_refusal_carries_witness(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    # pinned declared box (203, 302)-(301, 398): left edge sits 1 pt inside
    # the ink band, top +1, bottom -2 (all beyond 0.5 pt); the right edge
    # lands exactly on the tight boundary (within tolerance). The witness
    # tight box is the PER-EDGE band measurement, not the global ink bbox.
    box = {"x": 203.0, "y": 302.0, "width": 98.0, "height": 96.0}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    assert outcome["status"] == "refused"
    assert outcome["reason"] == "beyond-tolerance"
    witness = outcome["witness"]
    assert witness["declared"] == {"x": 203000, "y": 302000,
                                   "width": 98000, "height": 96000}
    assert witness["tight"] == {"x": 202000, "y": 301000,
                                "width": 99000, "height": 98000}
    assert witness["deltas"] == {"left": -1.0, "right": 0.0,
                                 "top": 1.0, "bottom": -1.0}
    assert sorted(witness["edges"]) == ["bottom", "left", "top"]
    assert witness["tolerance"] == snap.SNAP_TOLERANCE_PT


# --- no contiguous ink edge does not silently snap ------------------------------


def test_blank_page_edge_does_not_silently_snap(tmp_path):
    config, png, rendered = _rendered(tmp_path, rects=[])
    box = {"x": 100.0, "y": 100.0, "width": 50.0, "height": 50.0}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    assert outcome["status"] == "refused"
    assert outcome["reason"] == "no-contiguous-ink-edge"
    assert outcome["witness"]["tight"] is None


def test_blank_corner_of_inked_page_does_not_silently_snap(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    box = {"x": 450.0, "y": 50.0, "width": 100.0, "height": 100.0}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    assert outcome["status"] == "refused"
    assert outcome["reason"] == "no-contiguous-ink-edge"


# --- quantized 1/1000 pt operative boxes preserved ------------------------------


def test_snapped_box_is_quantized_idempotently(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    box = {"x": TIGHT[0] - 0.3, "y": TIGHT[1] - 0.3,
           "width": TIGHT[2] + 0.6, "height": TIGHT[3] + 0.6}
    outcome = snap.snap_box_to_ink(rendered, config, box)
    tight = outcome["box"]
    assert all(isinstance(v, int) and not isinstance(v, bool)
               for v in tight.values())
    # re-quantizing the stored integer quanta is the identity: the operative
    # box is never re-quantized differently (round-half-even, 1/1000 pt)
    again = {k: quantize_scalar(v / 1000) for k, v in tight.items()}
    assert again == tight


# --- declared tolerance constant, zoom.py convention ----------------------------


def test_declared_tolerance_constant_matches_zoom_convention():
    from dsc03 import zoom  # read-only reference for the convention
    assert snap.SNAP_TOLERANCE_PT == zoom.DEFAULT_TOLERANCE_PT == 0.5


def test_invalid_tolerance_refused(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    box = {"x": 200.0, "y": 300.0, "width": 100.0, "height": 100.0}
    for bad in (-0.1, float("nan"), "0.5"):
        try:
            snap.snap_box_to_ink(rendered, config, box, tolerance=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"tolerance {bad!r} must raise ValueError")


# --- determinism across processes ------------------------------------------------


_SNAP_SNIPPET = """
import json, sys
sys.path.insert(0, {repo!r})
sys.path.insert(0, {tests!r})
from dsc03.visual import render, snap
from conftest import render_config
config = render_config(dpi=72, simplification="ink-dilation-2px")
data = open(sys.argv[1], "rb").read()
rendered = render.Rendered(config=config, data=data)
box = json.loads(sys.argv[2])
print(json.dumps(snap.snap_box_to_ink(rendered, config, box), sort_keys=True))
"""


def test_deterministic_across_processes(tmp_path):
    config, png, rendered = _rendered(tmp_path)
    box = {"x": 197.0, "y": 297.0, "width": 106.0, "height": 106.0}
    local = snap.snap_box_to_ink(rendered, config, box)
    snippet = _SNAP_SNIPPET.format(
        repo=str(Path(__file__).resolve().parents[2]),
        tests=str(Path(__file__).resolve().parent),
    )
    outputs = set()
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, "-c", snippet, str(png), json.dumps(box)],
            capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr
        outputs.add(proc.stdout)
    assert len(outputs) == 1
    assert json.loads(outputs.pop()) == local
