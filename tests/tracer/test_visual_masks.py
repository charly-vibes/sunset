# Purpose: Geometry-mask alignment oracle tests (sunset-xzy.4, tasks.md 4.2).
# Responsibilities: Pin the document-visual-oracles contract for the level-C
#   (D3) oracle: it evaluates exactly one property ("region-alignment"),
#   comparing descriptor region masks (claimed rects mapped through the
#   DECLARED frame) against the SIMPLIFIED source render — binarized ink
#   dilated by the recorded "ink-dilation-<N>px" simplification (D4: never a
#   naive mask-vs-pixels diff; rectangles cover whitespace between glyphs).
#   Verified here: (a) an aligned ink region agrees; (b) ink sitting just
#   outside a failing rect is attributed reason "ink-outside-rect" with the
#   region id retained ("No silent resolution" — misplaced, not missing, but
#   never elected into agreement); (c) "no-ink" regions agree over blank
#   areas and differ over ink; (d) rotated rasters are judged through the
#   declared 90° frame — the same raster under a wrong (rot180) frame flips
#   the verdict, proving the declared frame drives the comparison; (e)
#   RenderUnavailable yields typed `unavailable` with the reason carried;
#   (f) the unknown matrix — missing frame, uncalibrated, binarization
#   disabled, source simplification "none"; (g) aggregate passes ONLY when
#   every page agrees (one unknown/degraded page blocks); (h) every outcome
#   carries property="region-alignment" + the evidence class, SCOPED_CLAIM
#   disclaims text/reading-order/semantic/completeness claims, and
#   correlated evidence cannot support accuracy claims. A real pinned
#   carrier proves the oracle RUNS end-to-end (not unknown/unavailable).
# Rationale: spec "No silent resolution" (scenario "Mask disagreement":
#   retained region ids, neither reading replaced), "Scoped property
#   claims", "Calibrated thresholds with per-page outcomes", "Labeled
#   evidence class"; design D3 (level C = geometry-only masks), D4 (like-
#   with-like: the recorded source simplification is the tolerance), D5.
#   Synthetic carriers are built seed-free with pymupdf (white page + filled
#   black rectangles at hand-computed coordinates) so every measured
#   fraction is deterministic. The rotated carrier uses the sunset-xzy.3
#   landscape-raster trick: a plain 792x612 page with ink drawn exactly
#   where the declared rot90 frame maps the descriptor box — no
#   pymupdf set_rotation (its drawing-coordinate meaning shifts).
"""Geometry-mask alignment oracle tests (sunset-xzy.4)."""
import json
import shutil
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import frames, masks, render
from dsc03.visual.render import Binarization, RenderConfig

TESTS_DIR = Path(__file__).resolve().parent
PROFILES = TESTS_DIR / "profiles"
REAL_CARRIER = TESTS_DIR.parents[1] / "fixtures" / "carriers" / "bank-statement-ca-excerpt.pdf"

# --- synthetic carrier geometry (hand-computed, seed-free) --------------------
#
# Carrier A: 612x792pt white page, black box over descriptor (bottom-left,
# y-up) rect x 100..400, y 300..600. pymupdf draws with a TOP-LEFT y-down
# origin, so the same box is drawn at fitz Rect(100, 192, 400, 492). At 72dpi
# 1pt = 1px and poppler renders user space directly: raw ink lands at raster
# px x 100..400, y 192..492 (integer-exact edges, no anti-aliasing spill).
PAGE_W, PAGE_H = 612, 792
BOX_FITZ = pymupdf.Rect(100, 192, 400, 492)
BOX_DESCRIPTOR = (100, 300, 400, 600)  # x0, y0, x1, y1 (bottom-left, y-up)
CALIB_A = {"min": 0.1, "max": 1.0}

# Region dicts (descriptor coords; x/y is the minimal corner, w/h extents).
REGION_INK_BOX = {"id": "ink-box", "x": 110, "y": 310, "w": 280, "h": 280, "expected": "ink"}
REGION_BLANK_CORNER = {"id": "blank-corner", "x": 450, "y": 50, "w": 100, "h": 100,
                       "expected": "no-ink"}
# A 2px-wide rect hugging the ink box's right edge (descriptor x 402..404):
# raw-empty interior, but raw ink sits within the recorded 2px dilation band
# outside its left boundary (the fill's 1pt stroke inks pixel col 400) —
# misplaced, not missing.
REGION_MISPLACED = {"id": "misplaced-ink", "x": 402, "y": 310, "w": 2, "h": 280,
                    "expected": "ink"}


def _poppler_executable():
    return shutil.which("pdftoppm") or "/usr/bin/pdftoppm"


def _render_config(*, page=1, dpi=72, enabled=True, threshold=128,
                   simplification="ink-dilation-2px", extractor="pymupdf",
                   renderer="poppler", executable=None):
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=executable or _poppler_executable(),
        renderer_version=render.detect_renderer_version(executable or _poppler_executable()),
        dpi=dpi,
        page=page,
        binarization=Binarization(enabled=enabled, method="fixed-threshold",
                                  threshold=threshold),
        source_simplification=simplification,
        extractor_lineage=extractor,
        renderer_lineage=renderer,
    )


def _make_carrier(tmp_path, name, rects, width=PAGE_W, height=PAGE_H,
                  blank_pages_after=0):
    """White page + filled black rects (fitz coords) -> saved PDF path."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    for rect in rects:
        page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))
    for _ in range(blank_pages_after):
        doc.new_page(width=width, height=height)
    path = tmp_path / name
    doc.save(str(path))
    return path


def _rendered(tmp_path, config, rects, name="carrier.pdf", width=PAGE_W,
              height=PAGE_H, blank_pages_after=0):
    pdf = _make_carrier(tmp_path, name, rects, width=width, height=height,
                        blank_pages_after=blank_pages_after)
    result = render.render_page(config, pdf)
    assert isinstance(result, render.Rendered), result.reason
    return result


def _calibration(carrier, page, bounds):
    return {"property": "region-alignment", "carrier": carrier, "page": page,
            "min": bounds["min"], "max": bounds["max"]}


def _geometry_artifact(name="geometry-page-pt.json"):
    return json.loads((PROFILES / name).read_text())


_NO_CALIBRATION = object()  # sentinel: explicitly pass calibration=None


def _evaluate(tmp_path, *, config=None, carrier="carrier-a",
              regions=(REGION_INK_BOX, REGION_BLANK_CORNER),
              calibration=_NO_CALIBRATION, geometry=None, frame_name="page-1",
              rects=(BOX_FITZ,), width=PAGE_W, height=PAGE_H, name="carrier.pdf"):
    if config is None:
        config = _render_config()
    if calibration is _NO_CALIBRATION:
        calibration = _calibration(carrier, config.page, CALIB_A)
    rendered = _rendered(tmp_path, config, rects, name=name, width=width,
                         height=height, blank_pages_after=config.page - 1)
    return masks.masks_outcome(
        rendered, carrier=carrier, regions=list(regions), calibration=calibration,
        geometry=geometry if geometry is not None else _geometry_artifact(),
        frame_name=frame_name,
    )


# --- (a) aligned ink region agrees ---------------------------------------------


def test_aligned_ink_region_agrees(tmp_path):
    outcome = _evaluate(tmp_path)
    assert outcome.status == "agree"
    assert outcome.reason is None
    assert outcome.property == "region-alignment"
    assert outcome.page == 1
    assert outcome.carrier == "carrier-a"
    assert outcome.evidence_class == "independent"
    assert dict(id="ink-box", status="agree") in outcome.regions
    assert dict(id="blank-corner", status="agree") in outcome.regions


# --- (b) ink just outside a failing rect: attributed, retained, never elected --


def test_ink_outside_rect_differs_with_region_and_reason_retained(tmp_path):
    # Carrier A's raw ink ends at raster col 400 (the fill's 1pt stroke
    # straddles the rect boundary). The misplaced rect (402..404) is raw-empty;
    # under the 2px dilation the neighbouring ink bleeds one of its two
    # columns (measured 0.5 < recorded min 0.9) so the primary test fails,
    # and the raw ring check attributes WHY: the claimed ink sits within the
    # dilation band just outside the rect. Verdict stays `differ` — the
    # oracle never moves the region to make it agree.
    config = _render_config(simplification="ink-dilation-2px")
    calib = _calibration("carrier-a", 1, {"min": 0.9, "max": 1.0})
    outcome = _evaluate(tmp_path, config=config, regions=(REGION_MISPLACED,),
                        calibration=calib)
    assert outcome.status == "differ"
    assert {"id": "misplaced-ink", "status": "differ",
            "reason": "ink-outside-rect"} in outcome.regions, outcome.regions
    # A genuinely empty neighbourhood must NOT earn the attribution: the same
    # rect shape over blank paper is plain `differ` (missing ink, full stop).
    blank = _evaluate(tmp_path, config=config, regions=(REGION_MISPLACED,),
                      calibration=calib, rects=(), name="blank.pdf")
    assert blank.status == "differ"
    assert dict(id="misplaced-ink", status="differ") in blank.regions
    assert all("reason" not in entry for entry in blank.regions)


# --- (c) no-ink regions: agree over blank, differ over ink ---------------------


def test_no_ink_region_over_blank_agrees_and_over_ink_differs(tmp_path):
    outcome = _evaluate(tmp_path, regions=(REGION_BLANK_CORNER,))
    assert outcome.status == "agree"
    assert dict(id="blank-corner", status="agree") in outcome.regions
    phantom = dict(REGION_BLANK_CORNER, id="phantom-no-ink", x=110, y=310,
                   w=280, h=280)
    over_ink = _evaluate(tmp_path, regions=(phantom,))
    assert over_ink.status == "differ"
    assert dict(id="phantom-no-ink", status="differ") in over_ink.regions


# --- (d) rotated raster judged through the DECLARED frame ----------------------


def test_rotated_raster_verdict_follows_declared_frame(tmp_path):
    # Landscape 792x612 raster carrying the 90-degree-clockwise view of a
    # 612x792 descriptor page: ink drawn at fitz Rect(350, 50, 750, 450),
    # exactly where the declared rot90 frame maps the descriptor box
    # (50, 350)-(450, 750) (rot90: descriptor (x, y) -> raster (y, x)).
    rects = (pymupdf.Rect(350, 50, 750, 450),)
    regions = (
        {"id": "ink-block", "x": 60, "y": 360, "w": 380, "h": 380, "expected": "ink"},
        {"id": "corner-blank", "x": 50, "y": 60, "w": 40, "h": 40, "expected": "no-ink"},
    )
    geometry = _geometry_artifact("geometry-rotated-page.json")
    outcome = _evaluate(tmp_path, carrier="carrier-rot", regions=regions,
                        calibration=_calibration("carrier-rot", 1, CALIB_A),
                        geometry=geometry, frame_name="page-1-rot90",
                        rects=rects, width=792, height=612, name="carrier-rot.pdf")
    # The frame in play is the declared rot90 one — hand-check its mapping.
    mapping = frames.frame_mapping(geometry, "page-1-rot90", _render_config(), (792, 612))
    assert isinstance(mapping, frames.PixelMapping)
    assert mapping.descriptor_to_pixel(60.0, 360.0) == (360.0, 60.0)
    assert outcome.status == "agree", outcome
    assert dict(id="corner-blank", status="agree") in outcome.regions
    # Same raster under the WRONG declared frame (rot180) must flip the
    # verdict: the corner region then lands on the ink block.
    wrong = _evaluate(tmp_path, carrier="carrier-rot", regions=regions,
                      calibration=_calibration("carrier-rot", 1, CALIB_A),
                      geometry=geometry, frame_name="page-1-rot180",
                      rects=rects, width=792, height=612, name="carrier-rot.pdf")
    assert wrong.status == "differ"
    assert dict(id="corner-blank", status="differ") in wrong.regions


# --- (e) typed unavailable from RenderUnavailable -------------------------------


def test_render_unavailable_yields_unavailable_with_reason_carried():
    config = _render_config(executable="/nonexistent/pdftoppm-nope")
    unavailable = render.render_page(config, REAL_CARRIER)
    assert isinstance(unavailable, render.RenderUnavailable)
    outcome = masks.masks_outcome(
        unavailable, carrier="carrier-a", regions=[REGION_INK_BOX],
        calibration=_calibration("carrier-a", 1, CALIB_A),
        geometry=_geometry_artifact(), frame_name="page-1",
    )
    assert outcome.status == "unavailable"
    assert outcome.reason == unavailable.reason
    assert outcome.property == "region-alignment"
    assert outcome.evidence_class == config.evidence_class
    assert outcome.regions == ()


# --- (f) unknown matrix ----------------------------------------------------------


def test_missing_frame_yields_unknown(tmp_path):
    outcome = _evaluate(tmp_path, frame_name="no-such-frame")
    assert outcome.status == "unknown"
    assert outcome.reason == "invalid_geometry_frame"
    assert outcome.property == "region-alignment"
    assert outcome.regions == ()


def test_missing_or_mismatched_calibration_yields_unknown_uncalibrated(tmp_path):
    outcome = _evaluate(tmp_path, calibration=None)
    assert outcome.status == "unknown"
    assert outcome.reason == "uncalibrated"
    other_property = dict(_calibration("carrier-a", 1, CALIB_A),
                          property="ink-coverage")
    outcome = _evaluate(tmp_path, calibration=other_property)
    assert outcome.status == "unknown"
    assert outcome.reason == "uncalibrated"
    other_carrier = _calibration("someone-else", 1, CALIB_A)
    outcome = _evaluate(tmp_path, calibration=other_carrier)
    assert outcome.status == "unknown"
    assert outcome.reason == "uncalibrated"


def test_binarization_disabled_yields_unknown(tmp_path):
    config = _render_config(enabled=False)
    outcome = _evaluate(tmp_path, config=config)
    assert outcome.status == "unknown"
    assert outcome.reason == "binarization-not-configured"


def test_source_simplification_none_yields_unknown(tmp_path):
    config = _render_config(simplification="none")
    outcome = _evaluate(tmp_path, config=config)
    assert outcome.status == "unknown"
    assert outcome.reason == "source-simplification-missing"


# --- (g) aggregate: pass ONLY when every page agrees ----------------------------


def test_aggregate_passes_only_when_all_pages_agree(tmp_path):
    page1 = _evaluate(tmp_path, carrier="carrier-a")
    # Page 2 of the same synthetic document is genuinely blank white; its
    # recorded calibration is all-no-ink and its claim is a blank region.
    blank_config = _render_config(page=2)
    blank_geometry = {
        "kind": "geometry", "version": "1", "subunit": "integers-are-points",
        "frames": [{
            "name": "page-2", "unit": "pt", "origin": "bottom-left",
            "axes": "x-right-y-up", "scale": [1, 1], "rotation": 0, "crop": None,
            "source_scope": "page:2",
        }],
    }
    rendered = _rendered(tmp_path, blank_config, (), name="carrier-a.pdf",
                         blank_pages_after=1)
    page2 = masks.masks_outcome(
        rendered, carrier="carrier-a",
        regions=[{"id": "blank-page", "x": 50, "y": 50, "w": 200, "h": 200,
                  "expected": "no-ink"}],
        calibration=_calibration("carrier-a", 2, {"min": 0.0, "max": 0.1}),
        geometry=blank_geometry, frame_name="page-2",
    )
    assert page2.status == "agree", page2
    verdict = masks.aggregate([page1, page2])
    assert verdict.status == "pass"
    assert verdict.reasons == ()
    # One uncalibrated (degraded) page blocks the aggregate — never passes.
    degraded = _evaluate(tmp_path, carrier="degraded-scan", calibration=None,
                         name="degraded.pdf")
    assert degraded.status == "unknown"
    verdict = masks.aggregate([page1, degraded])
    assert verdict.status == "blocked"
    assert any("degraded-scan" in reason and "uncalibrated" in reason
               for reason in verdict.reasons)


def test_aggregate_over_no_pages_is_blocked():
    verdict = masks.aggregate([])
    assert verdict.status == "blocked"
    assert verdict.reasons


# --- (h) scoped claims, evidence class, correlated restriction ------------------


def test_every_outcome_carries_property_and_evidence_class(tmp_path):
    agree = _evaluate(tmp_path)
    differ = _evaluate(tmp_path, regions=(REGION_MISPLACED,),
                       calibration=_calibration("carrier-a", 1, {"min": 0.9, "max": 1.0}))
    unknown = _evaluate(tmp_path, calibration=None)
    config = _render_config(executable="/nonexistent/pdftoppm-nope")
    unavailable = masks.masks_outcome(
        render.render_page(config, REAL_CARRIER), carrier="carrier-a",
        regions=[], calibration=None, geometry=_geometry_artifact(),
        frame_name="page-1",
    )
    for outcome in (agree, differ, unknown, unavailable):
        assert outcome.property == "region-alignment"
        assert outcome.evidence_class == "independent"
        assert outcome.page >= 1
        assert outcome.carrier == "carrier-a"
    assert agree.status == "agree"
    assert differ.status == "differ"
    assert unknown.status == "unknown" and unknown.reason == "uncalibrated"
    assert unavailable.status == "unavailable"


def test_scoped_claim_constant_and_docstring_disclaim_everything_else():
    assert masks.PROPERTY == "region-alignment"
    for phrase in ("text correctness", "reading order", "semantic grouping",
                   "visual completeness"):
        assert phrase in masks.SCOPED_CLAIM
    assert "NOTHING" in masks.SCOPED_CLAIM
    assert masks.SCOPED_CLAIM in " ".join((masks.__doc__ or "").split())
    assert "ink-outside-rect" in (masks.__doc__ or "")


def test_correlated_evidence_cannot_support_accuracy_claim(tmp_path):
    config = _render_config(extractor="poppler-26.01", renderer="poppler-26.01")
    assert config.evidence_class == "correlated"
    outcome = _evaluate(tmp_path, config=config)
    assert outcome.status == "agree"
    assert outcome.evidence_class == "correlated"
    assert masks.supports_accuracy_claim(outcome) is False
    assert outcome.property == "region-alignment"


# --- real pinned carrier: the oracle runs end-to-end ----------------------------


def test_real_pinned_carrier_runs_with_recorded_bounds(tmp_path):
    config = _render_config()
    rendered = render.render_page(config, REAL_CARRIER)
    assert isinstance(rendered, render.Rendered)
    calibration = _calibration("bank-statement-ca-excerpt", 1,
                               {"min": 0.0, "max": 1.0})
    outcome = masks.masks_outcome(
        rendered, carrier="bank-statement-ca-excerpt",
        regions=[{"id": "header-text", "x": 50, "y": 700, "w": 512, "h": 60,
                  "expected": "ink"}],
        calibration=calibration, geometry=_geometry_artifact(), frame_name="page-1",
    )
    assert outcome.status in ("agree", "differ")
    assert outcome.status == "agree"  # wide bounds [0, 1] admit any measurement
    assert outcome.property == "region-alignment"
    assert outcome.evidence_class == "independent"
    assert outcome.page == 1
