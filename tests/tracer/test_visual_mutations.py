# Purpose: Mutation-validation suite for the two visual oracles (sunset-xzy.5,
#   tasks.md 5.1): demonstrate, on committed seeded-mutation fixtures, that each
#   oracle detects exactly the defect classes it claims (spec
#   "Mutation-validated sensitivity"), with every demonstration ending `differ`
#   and region-attributed, every mutation test carrying an unmutated baseline
#   control that `agree`s on the pristine fixture (detection attributable to the
#   mutation, never to baseline miscalibration), and every unclaimed class
#   pinned to the spec "Undemonstrated class" consequence: the property stays
#   `uncalibrated` and cannot gate — missing calibration ⇒ `unknown`, and
#   `aggregate()` never reports `pass` while an outcome is
#   `unknown`/`uncalibrated`.
# Responsibilities: Load the committed fixtures under
#   tests/tracer/fixtures/visual/ (see that directory's README.org for
#   per-file provenance: seed-free hand-computed geometry, built with pymupdf
#   1.28.2, committed as bytes); render them through the pinned RenderConfig
#   exactly as test_visual_render.py/test_visual_masks.py do; evaluate the
#   coverage and masks oracles; and pin the class→oracle claim mapping below.
#   This suite adds NO oracle semantics: dsc03/visual/coverage.py and
#   dsc03/visual/masks.py are consumed as shipped, never edited here.
# Rationale: spec "Mutation-validated sensitivity" (scenarios "Seeded shift
#   detected": 12 px shift ⇒ alignment outcome `differ`, property eligible for
#   calibration; "Undemonstrated class": claimed-but-undemonstrated ⇒
#   `uncalibrated`, cannot gate), "Calibrated thresholds with per-page
#   outcomes" (aggregate never passes with unknown/uncalibrated pages), "No
#   silent resolution" (differ is retained and region-attributed — never
#   smoothed, elected or softened), "Scoped property claims".
"""Mutation-validation fixtures suite (sunset-xzy.5, tasks.md 5.1).

PINNED class→oracle claim mapping (derived from the oracles' documented
semantics — dsc03/visual/coverage.py and dsc03/visual/masks.py module
docstrings — not from experiment):

- region-alignment (masks oracle) CLAIMS:
  * shift — its comparison surface is claimed rects (mapped ONLY through the
    declared frame) against the simplified source render: ink displaced 12 px
    relative to the claimed rect is exactly an alignment disagreement, and the
    pinned "ink-outside-rect" attribution exists precisely to mark misplaced
    (not missing) ink. Spec scenario "Seeded shift detected" runs THE
    ALIGNMENT ORACLE on a 12 px-shifted fixture and expects `differ`.
  * wrong frame — its verdicts are derived exclusively from the declared
    geometry frame; a deliberately wrong declared frame (rot180 where rot90
    is true) misplaces every mapped rect ⇒ `differ`, region-attributed.
- region-alignment does NOT claim: omission, duplication — those are
  ink-QUANTITY defects; the scoped claim covers rect-vs-source ALIGNMENT
  only. Per spec "Undemonstrated class", region-alignment's calibration for
  those classes is never demonstrated: the no-gate path is pinned in
  test_undemonstrated_class_uncalibrated_cannot_gate_alignment (missing
  calibration ⇒ `unknown`; `aggregate()` never reports `pass` while an
  outcome is `unknown`/`uncalibrated`).

- ink-coverage (coverage oracle) CLAIMS:
  * omission — it measures binarized ink fractions (per claimed region AND
    whole page) against the recorded [min, max] bounds: expected ink absent
    drives the claimed region's fraction below the recorded floor ⇒ `differ`,
    region-attributed.
  * duplication — ink copied elsewhere on the page appears where a region
    claims none (or lifts fractions past the recorded ceiling): the
    no-ink claim's fraction exceeds the calibration floor ⇒ `differ`,
    region-attributed.
- ink-coverage does NOT claim: shift, wrong frame — those are position/
  declaration defects; ink-coverage measures HOW MUCH ink is present, not
  WHERE it sits, so a 12 px displacement leaves region and page fractions
  inside realistic recorded bounds. Its calibration for those classes is
  never demonstrated: the no-gate path is pinned in
  test_undemonstrated_class_uncalibrated_cannot_gate_coverage.

Each claimed class is demonstrated by a committed seeded fixture whose
mutated run ends `differ` WITH region attribution, paired with an unmutated
baseline control (the pristine fixture under identical claims/calibration)
that `agree`s — detection is attributable to the mutation alone.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import coverage, masks, render
from dsc03.visual.render import Binarization, RenderConfig

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visual"

# --- pinned fixture geometry (hand-computed, seed-free; see fixtures README) --

# Portrait family ("visual-strip"): 612x792 pt page, ink strip over descriptor
# (bottom-left, y-up) rect x 100..400, y 300..324 (300x24 pt). pymupdf draws
# top-left y-down, so the fill-only rect is fitz Rect(100, 468, 400, 492); at
# 72 dpi 1 pt = 1 px and poppler renders user space directly, so raw ink lands
# at raster px x 100..400, y 468..492 (integer-exact, no anti-aliasing spill).
PAGE_W, PAGE_H = 612, 792
REGION_INK_STRIP = {"id": "ink-strip", "x": 100, "y": 300, "w": 300, "h": 24,
                    "expected": "ink"}
REGION_BLANK_LOWER = {"id": "blank-lower", "x": 100, "y": 60, "w": 300, "h": 24,
                      "expected": "no-ink"}

# Rotated family ("visual-strip-rot"): landscape 792x612 raster carrying the
# 90-degree-clockwise view of the same descriptor page (sunset-xzy.3/.4
# landscape trick: ink drawn exactly where the declared rot90 frame maps the
# descriptor box — descriptor (x, y) -> raster (y, x) — never set_rotation).
# The ink strip maps to raster x 300..324, y 100..400 (fitz Rect(300, 100,
# 324, 400)).
ROT_REGIONS = (REGION_INK_STRIP, REGION_BLANK_LOWER)

# --- recorded calibration (shape pinned by _usable_calibration /
# _usable_region_calibration: property, carrier, page, min <= max) ------------

# Region-alignment window: a claimed rect must sit on >=95% simplified ink.
# Pristine rects exactly cover their fill (fraction 1.0); the seeded 12 px
# shift leaves ~0.56 even after the 2 px dilation — detected with margin.
ALN_BOUNDS = {"min": 0.95, "max": 1.0}
# Ink-coverage window: whole page must hold >=1% ink (pristine ~1.8%), claimed
# ink regions up to 100% (pristine strip region = 1.0); omission drops the
# region (and page) to 0, duplication lifts the no-ink region to ~1.0.
COV_BOUNDS = {"min": 0.01, "max": 1.0}


def _calibration(property_name, carrier, bounds):
    return {"property": property_name, "carrier": carrier, "page": 1,
            "min": bounds["min"], "max": bounds["max"]}


def _poppler_executable():
    return shutil.which("pdftoppm") or "/usr/bin/pdftoppm"


def _render_config():
    """The pinned render configuration (identical to the shipped oracle tests)."""
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=_poppler_executable(),
        renderer_version=render.detect_renderer_version(_poppler_executable()),
        dpi=72,
        page=1,
        binarization=Binarization(enabled=True, method="fixed-threshold",
                                  threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


def _rendered(fixture_name):
    """Render a committed fixture through the pinned config (typed failure)."""
    path = FIXTURES_DIR / fixture_name
    assert path.is_file(), f"missing committed mutation fixture: {path}"
    result = render.render_page(_render_config(), path)
    assert isinstance(result, render.Rendered), getattr(result, "reason", result)
    return result


def _rotated_geometry():
    """The committed rotated-frame artifact: true rot90 + seeded-wrong rot180."""
    path = FIXTURES_DIR / "geometry-rotated-strip.json"
    assert path.is_file(), f"missing committed frame fixture: {path}"
    return json.loads(path.read_text())


# --- shift: claimed by the alignment oracle (spec "Seeded shift detected") ----


def test_shift_baseline_control_agrees(tmp_path):
    rendered = _rendered("visual-strip.pdf")
    outcome = masks.masks_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("region-alignment", "visual-strip", ALN_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "agree", outcome
    assert dict(id="ink-strip", status="agree") in outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions
    assert outcome.property == "region-alignment"


def test_seeded_shift_12px_detected_by_alignment_oracle(tmp_path):
    # Seeded mutation: the ink strip is drawn 12 px shifted (+x, +y) on the
    # committed carrier; the region claims are UNCHANGED. >=12 px per the spec
    # scenario. The alignment oracle must end `differ` and attribute it to the
    # displaced region id ("No silent resolution") — never `unknown`, never a
    # softened aggregate.
    rendered = _rendered("visual-strip-shift.pdf")
    outcome = masks.masks_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("region-alignment", "visual-strip", ALN_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "differ", outcome
    assert dict(id="ink-strip", status="differ") in outcome.regions, outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions
    assert outcome.property == "region-alignment"


# --- wrong frame: claimed by the alignment oracle ------------------------------


def test_wrong_frame_baseline_control_true_rot90_frame_agrees(tmp_path):
    rendered = _rendered("visual-strip-rot90.pdf")
    outcome = masks.masks_outcome(
        rendered, carrier="visual-strip-rot", regions=list(ROT_REGIONS),
        calibration=_calibration("region-alignment", "visual-strip-rot", ALN_BOUNDS),
        geometry=_rotated_geometry(), frame_name="page-1-rot90",
    )
    assert outcome.status == "agree", outcome
    assert dict(id="ink-strip", status="agree") in outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions


def test_seeded_wrong_frame_rot180_declared_detected(tmp_path):
    # Seeded mutation: the SAME committed raster evaluated under the seeded
    # WRONG declared frame (rot180 where rot90 is true). Every mapped rect is
    # misplaced ⇒ `differ`, region-attributed — the declared frame drives the
    # comparison, and a wrong declaration is detectable, not guessed away.
    rendered = _rendered("visual-strip-rot90.pdf")
    outcome = masks.masks_outcome(
        rendered, carrier="visual-strip-rot", regions=list(ROT_REGIONS),
        calibration=_calibration("region-alignment", "visual-strip-rot", ALN_BOUNDS),
        geometry=_rotated_geometry(), frame_name="page-1-rot180",
    )
    assert outcome.status == "differ", outcome
    assert dict(id="ink-strip", status="differ") in outcome.regions, outcome.regions
    assert outcome.property == "region-alignment"


# --- omission: claimed by the coverage oracle ----------------------------------


def test_omission_baseline_control_agrees(tmp_path):
    rendered = _rendered("visual-strip.pdf")
    outcome = coverage.coverage_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "agree", outcome
    assert dict(id="ink-strip", status="agree") in outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions
    assert outcome.property == "ink-coverage"


def test_seeded_omission_detected_by_coverage_oracle(tmp_path):
    # Seeded mutation: the ink block is removed from the committed carrier.
    # The claimed-ink region's measured fraction drops to 0, below the
    # recorded floor ⇒ `differ`, region-attributed.
    rendered = _rendered("visual-strip-omission.pdf")
    outcome = coverage.coverage_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "differ", outcome
    assert dict(id="ink-strip", status="differ") in outcome.regions, outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions
    assert outcome.property == "ink-coverage"


# --- duplication: claimed by the coverage oracle -------------------------------


def test_duplication_baseline_control_agrees(tmp_path):
    rendered = _rendered("visual-strip.pdf")
    outcome = coverage.coverage_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "agree", outcome
    assert dict(id="blank-lower", status="agree") in outcome.regions


def test_seeded_duplication_detected_by_coverage_oracle(tmp_path):
    # Seeded mutation: the same 300x24 ink block is copied elsewhere on the
    # page — exactly over the region claiming "no-ink". The original region
    # still agrees (detection attributable to the COPY), the no-ink region's
    # fraction is lifted to ~1.0, past the calibration floor ⇒ `differ`,
    # region-attributed.
    rendered = _rendered("visual-strip-duplication.pdf")
    outcome = coverage.coverage_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert outcome.status == "differ", outcome
    assert dict(id="ink-strip", status="agree") in outcome.regions, outcome.regions
    assert dict(id="blank-lower", status="differ") in outcome.regions, outcome.regions
    assert outcome.property == "ink-coverage"


# --- "Undemonstrated class": uncalibrated ⇒ unknown, never gates ---------------


def test_undemonstrated_class_uncalibrated_cannot_gate_coverage(tmp_path):
    # Without a recorded calibration entry the coverage outcome is `unknown`
    # (reason "uncalibrated") — and `aggregate()` NEVER reports `pass` while
    # any outcome is `unknown`/`uncalibrated` (spec "Calibrated thresholds
    # with per-page outcomes" + "Undemonstrated class").
    rendered = _rendered("visual-strip.pdf")
    unknown = coverage.coverage_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=None,
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert unknown.status == "unknown", unknown
    assert unknown.reason == "uncalibrated"
    assert unknown.regions == ()
    assert unknown.property == "ink-coverage"
    agree = coverage.coverage_outcome(
        _rendered("visual-strip.pdf"), carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert agree.status == "agree"
    for outcome_set in ([agree, unknown], [unknown], []):
        verdict = coverage.aggregate(outcome_set)
        assert verdict.status != "pass", (outcome_set, verdict)
        assert verdict.status == "blocked"
        assert verdict.reasons


def test_undemonstrated_class_uncalibrated_cannot_gate_alignment(tmp_path):
    # Same no-gate pin for the alignment oracle: missing calibration ⇒
    # `unknown` ("uncalibrated"); aggregates over any unknown/uncalibrated
    # outcome never pass.
    rendered = _rendered("visual-strip.pdf")
    unknown = masks.masks_outcome(
        rendered, carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=None,
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert unknown.status == "unknown", unknown
    assert unknown.reason == "uncalibrated"
    assert unknown.regions == ()
    assert unknown.property == "region-alignment"
    agree = masks.masks_outcome(
        _rendered("visual-strip.pdf"), carrier="visual-strip",
        regions=[REGION_INK_STRIP, REGION_BLANK_LOWER],
        calibration=_calibration("region-alignment", "visual-strip", ALN_BOUNDS),
        geometry=json.loads(
            (Path(__file__).parent / "profiles" / "geometry-page-pt.json")
            .read_text()),
        frame_name="page-1",
    )
    assert agree.status == "agree"
    for outcome_set in ([agree, unknown], [unknown], []):
        verdict = masks.aggregate(outcome_set)
        assert verdict.status != "pass", (outcome_set, verdict)
        assert verdict.status == "blocked"
        assert verdict.reasons
