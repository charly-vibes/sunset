# Purpose: Binarized ink-coverage oracle tests (sunset-xzy.3, tasks.md 4.1).
# Responsibilities: Pin the document-visual-oracles contract for the level-B
#   (D3) oracle: it evaluates exactly one property ("ink-coverage") over
#   pinned carrier pages, comparing claimed region coverage against the
#   pinned render's binarized ink after the recorded like-with-like source
#   simplification (D4, pinned: 8-connected ink dilation). Verified here:
#   (a) ink regions within recorded calibration bounds agree; (b) claims over
#   blank areas differ with the region id retained ("No silent resolution");
#   the dilation simplification measurably lifts verdicts ("ink-dilation-Npx"
#   vs "ink-dilation-0px"); (c) rotated rasters are judged through the
#   DECLARED frame's mapping — the same raster under a wrong declared frame
#   changes the verdict; (d) RenderUnavailable inputs yield typed
#   `unavailable` with the reason carried; (e) the unknown matrix — missing
#   frame, uncalibrated, binarization disabled, source simplification "none";
#   (f) aggregate passes ONLY when every page agrees (one blank/degraded page
#   blocks; spec "Faint scan"); (g) every outcome carries
#   property="ink-coverage" + the evidence class, SCOPED_CLAIM disclaims
#   text/reading-order/semantic/completeness claims, and correlated evidence
#   cannot support accuracy claims. A real pinned carrier proves the oracle
#   RUNS end-to-end (not unknown/unavailable) under recorded bounds.
# Rationale: spec "Scoped property claims", "Calibrated thresholds with
#   per-page outcomes", "No silent resolution", "Labeled evidence class",
#   "Pinned render configuration"; design D3/D4/D5. Synthetic carriers are
#   built seed-free with pymupdf (white page + filled black rectangles at
#   hand-computed coordinates) so every measured fraction is deterministic.
"""Binarized ink-coverage oracle tests (sunset-xzy.3)."""
import json
import shutil
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import coverage, frames, render
from dsc03.visual.render import Binarization, RenderConfig

TESTS_DIR = Path(__file__).resolve().parent
PROFILES = TESTS_DIR / "profiles"
REAL_CARRIER = TESTS_DIR.parents[1] / "fixtures" / "carriers" / "bank-statement-ca-excerpt.pdf"

# --- synthetic carrier geometry (hand-computed, seed-free) --------------------
#
# Carrier A: 612x792pt white page, black box over descriptor (bottom-left,
# y-up) rect x 100..400, y 300..600. pymupdf draws with a TOP-LEFT y-down
# origin, so the same box is drawn at fitz Rect(100, 192, 400, 492). At 72dpi
# 1pt = 1px and poppler renders user space directly: ink lands at raster
# px x 100..400, y (792-600)..(792-300) = 192..492. Page ink fraction after
# 2px dilation is ~0.19; recorded calibration bounds [0.1, 1.0] admit it.
PAGE_W, PAGE_H = 612, 792
BOX_FITZ = pymupdf.Rect(100, 192, 400, 492)
BOX_DESCRIPTOR = (100, 300, 400, 600)  # x0, y0, x1, y1 (bottom-left, y-up)
CALIB_A = {"min": 0.1, "max": 1.0}

# Region dicts (descriptor coords; x/y is the minimal corner, w/h extents).
REGION_INK_BOX = {"id": "ink-box", "x": 110, "y": 310, "w": 280, "h": 280, "expected": "ink"}
REGION_BLANK_CORNER = {"id": "blank-corner", "x": 450, "y": 50, "w": 100, "h": 100,
                       "expected": "no-ink"}
REGION_PHANTOM_INK = {"id": "phantom-ink", "x": 450, "y": 50, "w": 100, "h": 100,
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


def _rendered(tmp_path, config, rects, name="carrier.pdf", width=PAGE_W,
              height=PAGE_H, blank_pages_after=0, white_rects=()):
    pdf = _make_carrier(tmp_path, name, rects, width=width, height=height,
                        blank_pages_after=blank_pages_after, white_rects=white_rects)
    result = render.render_page(config, pdf)
    assert isinstance(result, render.Rendered), result.reason
    return result


def _calibration(carrier, page, bounds):
    return {"property": "ink-coverage", "carrier": carrier, "page": page,
            "min": bounds["min"], "max": bounds["max"]}


def _geometry_artifact(name="geometry-page-pt.json"):
    return json.loads((PROFILES / name).read_text())


_NO_CALIBRATION = object()  # sentinel: explicitly pass calibration=None


def _evaluate(tmp_path, *, config=None, carrier="carrier-a", regions=(REGION_INK_BOX,
              REGION_BLANK_CORNER), calibration=_NO_CALIBRATION, geometry=None,
              frame_name="page-1", rects=(BOX_FITZ,), width=PAGE_W, height=PAGE_H,
              name="carrier.pdf", white_rects=()):
    if config is None:
        config = _render_config()
    if calibration is _NO_CALIBRATION:
        calibration = _calibration(carrier, config.page, CALIB_A)
    rendered = _rendered(tmp_path, config, rects, name=name, width=width,
                         height=height, blank_pages_after=config.page - 1,
                         white_rects=white_rects)
    return coverage.coverage_outcome(
        rendered, carrier=carrier, regions=list(regions), calibration=calibration,
        geometry=geometry if geometry is not None else _geometry_artifact(),
        frame_name=frame_name,
    )


# --- (a) ink region within calibration bounds agrees ---------------------------


def test_ink_region_within_bounds_agrees(tmp_path):
    outcome = _evaluate(tmp_path)
    assert outcome.status == "agree"
    assert outcome.reason is None
    assert outcome.property == "ink-coverage"
    assert outcome.page == 1
    assert outcome.carrier == "carrier-a"
    assert outcome.evidence_class == "independent"
    assert dict(id="ink-box", status="agree") in outcome.regions
    assert dict(id="blank-corner", status="agree") in outcome.regions


# --- (b) claim over blank area differs, region id retained --------------------


def test_blank_area_claiming_ink_differs_with_region_retained(tmp_path):
    outcome = _evaluate(tmp_path, regions=(REGION_BLANK_CORNER, REGION_PHANTOM_INK))
    assert outcome.status == "differ"
    assert dict(id="phantom-ink", status="differ") in outcome.regions, (
        "the disagreeing region id must be retained, never smoothed away"
    )
    assert dict(id="blank-corner", status="agree") in outcome.regions
    assert outcome.property == "ink-coverage"


# --- D4: the recorded source simplification is applied as tolerance -----------


def test_dilation_simplification_lifts_verdict(tmp_path):
    # Near-all-ink carrier: black page minus a white hole at descriptor
    # (400..450, 400..450) -> fitz Rect(400, 342, 450, 392). Calibration
    # [0.8, 1.0] sits BETWEEN the undilated (0.75) and dilated (~0.84) ink
    # fraction of a region straddling the hole edge, so only a real dilation
    # of the ink mask can agree.
    rects = (pymupdf.Rect(10, 10, 602, 782),)
    hole = pymupdf.Rect(400, 342, 450, 392)
    straddle = {"id": "hole-edge-straddle", "x": 440, "y": 440, "w": 20, "h": 20,
                "expected": "ink"}
    interior = {"id": "hole-interior", "x": 405, "y": 405, "w": 40, "h": 40,
                "expected": "no-ink"}
    calib = _calibration("carrier-c", 1, {"min": 0.8, "max": 1.0})
    dilated = _evaluate(tmp_path, carrier="carrier-c", regions=(straddle, interior),
                        calibration=calib, rects=rects, name="carrier-c.pdf",
                        white_rects=(hole,))
    assert dilated.status == "agree", dilated
    assert dict(id="hole-edge-straddle", status="agree") in dilated.regions
    # The same carrier under "ink-dilation-0px" (pinned valid no-op) must NOT
    # agree for the straddling region: proof the simplification is parsed and
    # applied, not decorative.
    nodil_config = _render_config(simplification="ink-dilation-0px")
    nodil = _evaluate(tmp_path, config=nodil_config, carrier="carrier-c",
                      regions=(straddle,), calibration=calib, rects=rects,
                      name="carrier-c.pdf", white_rects=(hole,))
    assert nodil.status == "differ"
    assert dict(id="hole-edge-straddle", status="differ") in nodil.regions


# --- (c) rotated raster judged through the declared frame ----------------------


def test_rotated_raster_verdict_follows_declared_frame(tmp_path):
    # Landscape 792x612 raster carrying the 90-degree-clockwise view of a
    # 612x792 descriptor page: ink drawn at fitz Rect(350, 50, 750, 450),
    # exactly where the declared rot90 frame maps the descriptor box
    # (50, 350)-(450, 750) (rot90: descriptor (x, y) -> raster (y, x)).
    rects = (pymupdf.Rect(350, 50, 750, 450),)
    rot_box = (50, 350, 450, 750)
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
    # Verdict computed on the correctly mapped rect: ink block agrees, the
    # bottom-left corner is blank, page fraction ~0.33 is inside bounds.
    assert outcome.status == "agree", outcome
    assert dict(id="corner-blank", status="agree") in outcome.regions
    # Same raster under the WRONG declared frame (rot180) must change the
    # verdict: the corner region then lands on the ink block.
    wrong = _evaluate(tmp_path, carrier="carrier-rot", regions=regions,
                      calibration=_calibration("carrier-rot", 1, CALIB_A),
                      geometry=geometry, frame_name="page-1-rot180",
                      rects=rects, width=792, height=612, name="carrier-rot.pdf")
    assert wrong.status == "differ"
    assert dict(id="corner-blank", status="differ") in wrong.regions


# --- (d) typed unavailable from RenderUnavailable ------------------------------


def test_render_unavailable_yields_unavailable_with_reason_carried():
    config = _render_config(executable="/nonexistent/pdftoppm-nope")
    unavailable = render.render_page(config, REAL_CARRIER)
    assert isinstance(unavailable, render.RenderUnavailable)
    outcome = coverage.coverage_outcome(
        unavailable, carrier="carrier-a", regions=[REGION_INK_BOX],
        calibration=_calibration("carrier-a", 1, CALIB_A),
        geometry=_geometry_artifact(), frame_name="page-1",
    )
    assert outcome.status == "unavailable"
    assert outcome.reason == unavailable.reason
    assert outcome.property == "ink-coverage"
    assert outcome.evidence_class == config.evidence_class
    assert outcome.regions == ()


# --- (e) unknown matrix ---------------------------------------------------------


def test_missing_frame_yields_unknown(tmp_path):
    outcome = _evaluate(tmp_path, frame_name="no-such-frame")
    assert outcome.status == "unknown"
    assert outcome.reason == "invalid_geometry_frame"
    assert outcome.property == "ink-coverage"
    assert outcome.regions == ()


def test_missing_calibration_yields_unknown_uncalibrated(tmp_path):
    outcome = _evaluate(tmp_path, calibration=None)
    assert outcome.status == "unknown"
    assert outcome.reason == "uncalibrated"


def test_calibration_for_other_property_or_carrier_is_not_usable(tmp_path):
    other_property = dict(_calibration("carrier-a", 1, CALIB_A), property="glyph-density")
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


# --- (f) aggregate: pass ONLY when every page agrees ---------------------------


def test_aggregate_passes_when_all_pages_agree(tmp_path):
    page1 = _evaluate(tmp_path, carrier="carrier-a", regions=(REGION_INK_BOX,
                      REGION_BLANK_CORNER))
    # Page 2 of the same synthetic document is genuinely blank white; its
    # recorded calibration admits zero coverage and claims a blank region.
    blank_config = _render_config(page=2)
    blank_geometry = {
        "kind": "geometry", "version": "1", "subunit": "integers-are-points",
        "frames": [{
            "name": "page-2", "unit": "pt", "origin": "bottom-left",
            "axes": "x-right-y-up", "scale": [1, 1], "rotation": 0, "crop": None,
            "source_scope": "page:2",
        }],
    }
    blank_region = {"id": "blank-page", "x": 50, "y": 50, "w": 200, "h": 200,
                    "expected": "no-ink"}
    rendered = _rendered(tmp_path, blank_config, (), name="carrier-a.pdf",
                         blank_pages_after=1)
    page2 = coverage.coverage_outcome(
        rendered, carrier="carrier-a", regions=[blank_region],
        calibration=_calibration("carrier-a", 2, {"min": 0.0, "max": 0.1}),
        geometry=blank_geometry, frame_name="page-2",
    )
    assert page2.status == "agree", page2
    verdict = coverage.aggregate([page1, page2])
    assert verdict.status == "pass"
    assert verdict.reasons == ()


def test_faint_scan_unknown_page_blocks_aggregate(tmp_path):
    page1 = _evaluate(tmp_path, carrier="carrier-a", regions=(REGION_INK_BOX,))
    # Spec "Faint scan": a degraded page with no usable recorded calibration
    # stays `unknown` and the aggregate must not report pass.
    faint = _evaluate(tmp_path, carrier="faint-scan-carrier", calibration=None,
                      rects=(BOX_FITZ,), name="faint.pdf")
    assert faint.status == "unknown"
    assert faint.reason == "uncalibrated"
    verdict = coverage.aggregate([page1, faint])
    assert verdict.status == "blocked"
    assert verdict.reasons
    assert any("faint-scan-carrier" in reason and "uncalibrated" in reason
               for reason in verdict.reasons)


def test_blank_page_with_ink_calibraton_cannot_pass(tmp_path):
    # A blank page judged under page-1's ink-bearing bounds measures 0.0,
    # below the recorded floor -> differ -> aggregate blocked. One blank page
    # must never yield an aggregate pass.
    blank_config = _render_config(page=2)
    blank_geometry = {
        "kind": "geometry", "version": "1", "subunit": "integers-are-points",
        "frames": [{
            "name": "page-2", "unit": "pt", "origin": "bottom-left",
            "axes": "x-right-y-up", "scale": [1, 1], "rotation": 0, "crop": None,
            "source_scope": "page:2",
        }],
    }
    rendered = _rendered(tmp_path, blank_config, (), name="blank.pdf",
                         blank_pages_after=1)
    blank = coverage.coverage_outcome(
        rendered, carrier="carrier-a", regions=[],
        calibration=_calibration("carrier-a", 2, CALIB_A),
        geometry=blank_geometry, frame_name="page-2",
    )
    assert blank.status == "differ"
    page1 = _evaluate(tmp_path, carrier="carrier-a", regions=(REGION_INK_BOX,))
    verdict = coverage.aggregate([page1, blank])
    assert verdict.status == "blocked"


def test_aggregate_over_no_pages_is_blocked():
    verdict = coverage.aggregate([])
    assert verdict.status == "blocked"
    assert verdict.reasons


# --- (g) scoped claims, evidence class, correlated restriction -----------------


def test_scoped_claim_constant_and_docstring_disclaim_everything_else():
    assert coverage.PROPERTY == "ink-coverage"
    for phrase in ("text correctness", "reading order", "semantic grouping",
                   "visual completeness"):
        assert phrase in coverage.SCOPED_CLAIM
    assert "NOTHING" in coverage.SCOPED_CLAIM
    assert coverage.SCOPED_CLAIM in " ".join((coverage.__doc__ or "").split())


def test_correlated_evidence_cannot_support_accuracy_claim(tmp_path):
    config = _render_config(extractor="poppler-26.01", renderer="poppler-26.01")
    assert config.evidence_class == "correlated"
    outcome = _evaluate(tmp_path, config=config, carrier="carrier-a",
                        regions=(REGION_INK_BOX,))
    assert outcome.status == "agree"
    assert outcome.evidence_class == "correlated"
    assert coverage.supports_accuracy_claim(outcome) is False
    assert outcome.property == "ink-coverage"


# --- real pinned carrier: the oracle runs end-to-end ---------------------------


def test_real_pinned_carrier_runs_with_recorded_bounds(tmp_path):
    config = _render_config()
    rendered = render.render_page(config, REAL_CARRIER)
    assert isinstance(rendered, render.Rendered)
    calibration = _calibration("bank-statement-ca-excerpt", 1,
                               {"min": 0.0, "max": 1.0})
    outcome = coverage.coverage_outcome(
        rendered, carrier="bank-statement-ca-excerpt",
        regions=[{"id": "header-text", "x": 50, "y": 700, "w": 512, "h": 60,
                  "expected": "ink"}],
        calibration=calibration, geometry=_geometry_artifact(), frame_name="page-1",
    )
    assert outcome.status in ("agree", "differ")
    assert outcome.status == "agree"  # header band carries ink; bounds are [0, 1]
    assert outcome.property == "ink-coverage"
    assert outcome.evidence_class == "independent"
    assert outcome.page == 1
