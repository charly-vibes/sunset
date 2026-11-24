# Purpose: Overcoverage-penalty and per-class-mask tests for the two visual
#   oracles (generalization of sunset-xzy.3/.4): (1) the region-alignment
#   oracle gains seeded-validated oversized-region detection — a region whose
#   rect area exceeds its contained simplified-ink area by more than the
#   pinned bound "explains ink but overcovers blank area" and must end
#   `differ` WITH the "region-oversized" attribution, never agree; (2) BOTH
#   oracles evaluate claims per content class (from the landed
#   dsc03/visual/content_classes.py observations): a region scoped to
#   "text"/"vector"/"raster" is measured against that class's observed
#   rect-union mask under the SAME recorded calibration bounds, so a
#   decorative raster band no longer reads as [satisfying] missing text —
#   the retained differ carries the "explained-by-<class>" attribution, while
#   genuinely missing ink stays a plain differ. Pinned invariants: outcome
#   vocabulary unchanged (agree/differ/unknown/unavailable), calibration
#   contract unchanged (same recorded entry shape, same bounds — no
#   recalibration), and claims without a "class" key evaluate exactly as
#   before (existing fixtures reproduce unchanged).
# Responsibilities: Build seed-free synthetic carriers with pymupdf (white
#   page + filled black rects / native text spans / an embedded black raster
#   band at hand-computed coordinates) so every measured fraction is
#   deterministic; drive dsc03/visual/coverage.py and dsc03/visual/masks.py
#   through the pinned render pipeline exactly as test_visual_coverage.py /
#   test_visual_masks.py do; demonstrate the oversize defect class with an
#   unmutated baseline control that agrees plus a seeded oversized claim that
#   differs with attribution (mutation-validation pattern of
#   test_visual_mutations.py, extended by one class AFTER seeded
#   demonstration); and pin the per-class unknown matrix (missing/invalid
#   observations) plus per-class aggregation under the unchanged aggregate
#   rule. This suite adds NO threshold-recalibration path: the oversize bound
#   is a pinned morphology parameter of the masks oracle, not a recorded
#   calibration entry.
# Rationale: spec "Mutation-validated sensitivity" (detection attributable to
#   the seeded mutation via baseline controls), "No silent resolution"
#   (attribution retained on every differ; unknown is an answer), "Calibrated
#   thresholds with per-page outcomes" (bounds reused verbatim), "Scoped
#   property claims". All numbers below are AGENT-EXECUTED measurements
#   through the pinned pipeline (pymupdf 1.28.2 decode, pdftoppm render,
#   fixed-threshold-128, ink-dilation-2px) — proxy metrics; a human pass
#   supersedes.
"""Overcoverage penalty + per-class content masks (visual oracles)."""
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import coverage, masks, render
from dsc03.visual.content_classes import observe_page

from conftest import make_carrier as _make_carrier, render_config as _render_config

TESTS_DIR = Path(__file__).resolve().parent
PROFILES = TESTS_DIR / "profiles"
REAL_CARRIER = TESTS_DIR.parents[1] / "fixtures" / "carriers" / "bank-statement-ca-excerpt.pdf"

PAGE_W, PAGE_H = 612, 792

# --- oversize fixture (hand-computed, seed-free) -------------------------------
#
# Pristine strip carrier (same geometry family as the sunset-xzy.5 mutation
# fixtures): ink strip over descriptor x 100..400, y 300..324 -> fitz
# Rect(100, 468, 400, 492); raw ink lands at raster px x 100..400, y 468..492.
# The oversized claim is a REGION defect on the pristine raster: descriptor
# x 20..592, y 20..540 (area 572*520 = 297,440 px^2) contains the whole strip
# (simplified ink ~8.8k px, agent-measured) yet overcovers ~97% blank area.
# Agent-measured under the pinned pipeline: fraction ~0.030 (inside the
# [0.01, 1.0] window below, so the PRIMARY test passes) with a region-area :
# contained-ink-area ratio ~34, far past the masks oracle's pinned
# OVERSIZE_MAX_AREA_RATIO = 20. The tight strip region (ratio 1.0) and the
# real bank-statement header band (agent-measured ratio ~13.3, the largest
# legitimate observed region) both stay under the bound.
STRIP_FITZ = pymupdf.Rect(100, 468, 400, 492)
REGION_STRIP = {"id": "ink-strip", "x": 100, "y": 300, "w": 300, "h": 24,
                "expected": "ink"}
REGION_BLANK_LOWER = {"id": "blank-lower", "x": 100, "y": 60, "w": 300, "h": 24,
                      "expected": "no-ink"}
REGION_GIANT = {"id": "giant-claim", "x": 20, "y": 20, "w": 572, "h": 520,
                "expected": "ink"}
REGION_GIANT_NO_INK = {"id": "giant-no-ink", "x": 20, "y": 20, "w": 572, "h": 520,
                       "expected": "no-ink"}
OVERSIZE_CARRIER = "oversize-strip"
OVERSIZE_BOUNDS = {"min": 0.01, "max": 1.0}

# --- per-class fixture (hand-computed, seed-free) -------------------------------
#
# 612x792 white page carrying (a) one native text line at fitz (72, 720)
# ("Texto visible", helv 11) and (b) an embedded 24x16 all-black raster
# band placed over descriptor x 300..500, y 400..440 (fitz Rect(300, 352,
# 500, 392), keep_proportion=False so the placement rect is inked exactly).
# Agent-measured observations through content_classes.observe_page: text
# span rect_px [72, 708, 133, 723], raster placement rect_px
# [300, 352, 500, 392]; the vector class is empty. A region claiming "ink"
# scoped to class "text" over the band differs per class (text mask empty)
# and the ink is attributed to the raster class — under the undifferentiated
# mask the band's ink alone would satisfy the claim.
BAND_FITZ = pymupdf.Rect(300, 352, 500, 392)  # descriptor x300..500, y400..440
BAND_REGION = {"id": "band-as-text", "x": 310, "y": 410, "w": 180, "h": 20,
               "expected": "ink"}
BAND_REGION_NO_INK = {"id": "band-no-ink-text", "x": 310, "y": 410, "w": 180,
                      "h": 20, "expected": "no-ink"}
BLANK_REGION = {"id": "blank-as-text", "x": 520, "y": 60, "w": 60, "h": 40,
                "expected": "ink"}
CLASS_CARRIER = "class-band"
# Coverage window with a positive floor (like every recorded window): the
# whole-page fraction of the class-band carrier measures ~0.02 under the
# pinned pipeline (text + band ink), so min=0.01 admits the page while a
# zero class measurement (text claimed over the band / blank paper) falls
# below the floor -> differ.
CLASS_COV_BOUNDS = {"min": 0.01, "max": 1.0}
CLASS_ALN_BOUNDS = {"min": 0.9, "max": 1.0}


def _calibration(property_name, carrier, page, bounds):
    """A calibration entry in the unchanged recorded contract shape."""
    return {"property": property_name, "carrier": carrier, "page": page,
            "min": bounds["min"], "max": bounds["max"]}


def _geometry(name="geometry-page-pt.json"):
    return json.loads((PROFILES / name).read_text())


def _strip_carrier(tmp_path, rects=(STRIP_FITZ,), name="oversize-strip.pdf"):
    return _make_carrier(tmp_path, name, rects, width=PAGE_W, height=PAGE_H)


def _masks_strip(tmp_path, regions, *, rects=(STRIP_FITZ,),
                 bounds=OVERSIZE_BOUNDS, name="oversize-strip.pdf"):
    """Render the strip carrier and evaluate the region-alignment oracle."""
    pdf = _strip_carrier(tmp_path, rects=rects, name=name)
    config = _render_config()
    rendered = render.render_page(config, pdf)
    assert isinstance(rendered, render.Rendered), rendered.reason
    return masks.masks_outcome(
        rendered, carrier=OVERSIZE_CARRIER, regions=list(regions),
        calibration=_calibration(masks.PROPERTY, OVERSIZE_CARRIER, config.page,
                                 bounds),
        geometry=_geometry(), frame_name="page-1",
    )


def _class_carrier(tmp_path, name="class-band.pdf"):
    """White page + native text line + embedded black raster band."""
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_text((72, 720), "Texto visible", fontname="helv", fontsize=11)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 24, 16), False)
    pix.clear_with(0)  # all-black band ink under the pinned threshold
    page.insert_image(BAND_FITZ, pixmap=pix, keep_proportion=False)
    path = tmp_path / name
    doc.save(str(path))
    return path


def _class_record(tmp_path):
    """The content-class observations record for the class-band carrier."""
    record = observe_page(_class_carrier(tmp_path), _geometry())
    assert record["status"] == "observed", record
    assert record["frame"]["status"] == "resolved", record
    return record


def _region_from_entry(entry, expected, cls=None):
    """Descriptor rect region built from an observed entry's canonical rect."""
    x0, y0, x1, y1 = entry["rect_pt"]
    region = {"id": f"{entry['class']}-observed", "x": x0, "y": y0,
              "w": x1 - x0, "h": y1 - y0, "expected": expected}
    if cls is not None:
        region["class"] = cls
    return region


def _coverage_class(tmp_path, regions, *, observations, bounds=CLASS_COV_BOUNDS):
    pdf = _class_carrier(tmp_path)
    config = _render_config()
    rendered = render.render_page(config, pdf)
    assert isinstance(rendered, render.Rendered), rendered.reason
    return coverage.coverage_outcome(
        rendered, carrier=CLASS_CARRIER, regions=list(regions),
        calibration=_calibration(coverage.PROPERTY, CLASS_CARRIER, config.page,
                                 bounds),
        geometry=_geometry(), frame_name="page-1", observations=observations,
    )


def _masks_class(tmp_path, regions, *, observations, bounds=CLASS_ALN_BOUNDS):
    pdf = _class_carrier(tmp_path)
    config = _render_config()
    rendered = render.render_page(config, pdf)
    assert isinstance(rendered, render.Rendered), rendered.reason
    return masks.masks_outcome(
        rendered, carrier=CLASS_CARRIER, regions=list(regions),
        calibration=_calibration(masks.PROPERTY, CLASS_CARRIER, config.page,
                                 bounds),
        geometry=_geometry(), frame_name="page-1", observations=observations,
    )


# === (1) oversize: seeded detection with baseline control ======================


def test_oversize_baseline_control_tight_claims_agree(tmp_path):
    """Unmutated baseline: the pristine strip under tight claims agrees."""
    outcome = _masks_strip(tmp_path, (REGION_STRIP, REGION_BLANK_LOWER))
    assert outcome.status == "agree", outcome
    assert dict(id="ink-strip", status="agree") in outcome.regions
    assert dict(id="blank-lower", status="agree") in outcome.regions
    assert outcome.property == "region-alignment"


def test_seeded_oversized_region_differs_with_attribution(tmp_path):
    """Seeded oversize: the giant claim explains the strip's ink (its
    fraction is inside the recorded window) yet overcovers ~97% blank area
    -> differ WITH the region-oversized attribution, never agree."""
    outcome = _masks_strip(tmp_path, (REGION_STRIP, REGION_GIANT))
    assert outcome.status == "differ", outcome
    assert {"id": "giant-claim", "status": "differ",
            "reason": "region-oversized"} in outcome.regions, outcome.regions
    assert dict(id="ink-strip", status="agree") in outcome.regions
    # The blocked aggregate lists the differ page (unchanged vocabulary).
    verdict = masks.aggregate([outcome])
    assert verdict.status == "blocked"
    assert any(OVERSIZE_CARRIER in r for r in verdict.reasons)


def test_oversize_spares_the_largest_legitimate_observed_region(tmp_path):
    """Legitimacy side of the pinned bound: the bank-statement header band
    (agent-measured region-area:ink-area ratio ~13.3, the sparsest region
    any recorded window admits) must keep agreeing — no threshold drift."""
    config = _render_config()
    rendered = render.render_page(config, REAL_CARRIER)
    assert isinstance(rendered, render.Rendered), rendered.reason
    outcome = masks.masks_outcome(
        rendered, carrier="bank-statement-ca-excerpt",
        regions=[{"id": "header-text", "x": 50, "y": 700, "w": 512, "h": 60,
                  "expected": "ink"}],
        calibration=_calibration(masks.PROPERTY, "bank-statement-ca-excerpt",
                                 config.page, {"min": 0.0, "max": 1.0}),
        geometry=_geometry(), frame_name="page-1",
    )
    assert outcome.status == "agree", outcome
    assert dict(id="header-text", status="agree") in outcome.regions


def test_no_ink_claims_are_never_oversized(tmp_path):
    """A giant no-ink claim over blank paper covers exactly what it claims:
    oversize is an ink-claim defect only."""
    outcome = _masks_strip(tmp_path, (REGION_GIANT_NO_INK,), rects=())
    assert outcome.status == "agree", outcome
    assert dict(id="giant-no-ink", status="agree") in outcome.regions
    assert all("reason" not in entry for entry in outcome.regions)


def test_primary_failure_keeps_plain_differ_without_oversize_reason(tmp_path):
    """Oversize attributes overcoverage on top of a PASSING primary test; a
    region failing its primary test (ink over blank paper) stays a plain
    differ — the penalty never invents a second reading."""
    outcome = _masks_strip(tmp_path, (REGION_GIANT,), rects=(),
                           bounds={"min": 0.05, "max": 1.0})
    assert outcome.status == "differ", outcome
    assert {"id": "giant-claim", "status": "differ"} in outcome.regions
    assert all("reason" not in entry for entry in outcome.regions)


def test_oversize_ratio_is_measured_on_the_claimed_surface(tmp_path):
    """Class-scoped claims are oversize-checked on the same surface their
    primary test uses (the class mask): a giant region claiming class
    'text' over the one small text line passes the permissive window but
    overcovers ~169x its contained text-ink area -> differ with the
    attribution."""
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    assert text_entry["rect_px"] == [72, 708, 133, 723]
    giant = {"id": "giant-as-text", "x": 20, "y": 20, "w": 572, "h": 520,
             "expected": "ink", "class": "text"}
    outcome = _masks_class(tmp_path, (giant,), observations=record,
                           bounds={"min": 0.0, "max": 1.0})
    assert outcome.status == "differ", outcome
    assert {"id": "giant-as-text", "status": "differ",
            "reason": "region-oversized", "class": "text"} in outcome.regions


# === (2) per-class masks (coverage oracle) =====================================


def test_coverage_per_class_text_region_agrees_from_observations(tmp_path):
    """A class-scoped ink claim is measured against the class's observed
    rect-union mask under the SAME recorded bounds; the region entry names
    the class; claims without a class key are untouched, and supplying
    observations changes nothing when no claim is class-scoped."""
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    scoped = _region_from_entry(text_entry, "ink", cls="text")
    plain = dict(scoped, id="plain-copy")
    plain.pop("class")
    outcome = _coverage_class(tmp_path, (scoped, plain), observations=record)
    assert outcome.status == "agree", outcome
    assert {"id": "text-observed", "status": "agree", "class": "text"} in (
        outcome.regions), outcome.regions
    assert dict(id="plain-copy", status="agree") in outcome.regions
    # Drift pin: with no class-scoped claim the outcome is byte-identical
    # with and without observations.
    without = _coverage_class(tmp_path, (plain,), observations=None)
    with_obs = _coverage_class(tmp_path, (plain,), observations=record)
    assert without == with_obs


def test_decorative_raster_band_no_longer_reads_as_missing_text(tmp_path):
    """The pinned per-class story: under the undifferentiated mask the
    band's ink alone satisfies a text-scoped claim (the masking defect);
    per class the claim differs and the ink is attributed to the raster
    class — while genuinely blank paper stays a PLAIN differ (missing)."""
    record = _class_record(tmp_path)
    raster_entries = record["classes"]["raster"]["entries"]
    assert raster_entries[0]["rect_px"] == [300, 352, 500, 392]
    # Undifferentiated reading (pinned baseline): band ink masks the claim.
    plain_over_band = {k: v for k, v in BAND_REGION.items() if k != "class"}
    plain = _coverage_class(tmp_path, (plain_over_band,), observations=record)
    assert plain.status == "agree", plain
    assert dict(id="band-as-text", status="agree") in plain.regions
    # Per-class reading: differ with the explaining-class attribution.
    scoped = dict(BAND_REGION, **{"class": "text"})
    outcome = _coverage_class(tmp_path, (scoped,), observations=record)
    assert outcome.status == "differ", outcome
    assert {"id": "band-as-text", "status": "differ",
            "reason": "explained-by-raster", "class": "text"} in (
        outcome.regions), outcome.regions
    # Genuinely blank paper: plain differ — no attribution is invented.
    blank = dict(BLANK_REGION, **{"class": "text"})
    missing = _coverage_class(tmp_path, (blank,), observations=record)
    assert missing.status == "differ", missing
    assert {"id": "blank-as-text", "status": "differ",
            "class": "text"} in missing.regions
    assert all("reason" not in entry for entry in missing.regions)


def test_no_ink_class_claim_is_class_scoped(tmp_path):
    """A no-ink claim scoped to 'text' measures TEXT blankness: the raster
    band does not contradict it; real text ink does (plain differ)."""
    record = _class_record(tmp_path)
    over_band = dict(BAND_REGION_NO_INK, **{"class": "text"})
    outcome = _coverage_class(tmp_path, (over_band,), observations=record)
    assert outcome.status == "agree", outcome
    assert {"id": "band-no-ink-text", "status": "agree",
            "class": "text"} in outcome.regions
    text_entry = record["classes"]["text"]["entries"][0]
    over_text = _region_from_entry(text_entry, "no-ink", cls="text")
    over_text["id"] = "text-is-ink"
    contradicted = _coverage_class(tmp_path, (over_text,), observations=record)
    assert contradicted.status == "differ", contradicted
    assert {"id": "text-is-ink", "status": "differ",
            "class": "text"} in contradicted.regions


# === (3) per-class masks (masks oracle) ========================================


def test_masks_per_class_band_claim_differs_with_explained_by(tmp_path):
    """Region-alignment per class: the text-scoped band claim differs with
    the explained-by attribution; the text-scoped observed-span claim
    agrees; the undifferentiated reading of the same band claim still
    agrees (plain claims untouched)."""
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    scoped_text = _region_from_entry(text_entry, "ink", cls="text")
    scoped_band = dict(BAND_REGION, **{"class": "text"})
    outcome = _masks_class(tmp_path, (scoped_text, scoped_band),
                           observations=record)
    assert outcome.status == "differ", outcome
    assert {"id": "text-observed", "status": "agree",
            "class": "text"} in outcome.regions, outcome.regions
    assert {"id": "band-as-text", "status": "differ",
            "reason": "explained-by-raster", "class": "text"} in (
        outcome.regions), outcome.regions
    plain_band = {k: v for k, v in BAND_REGION.items() if k != "class"}
    plain = _masks_class(tmp_path, (plain_band,), observations=record)
    assert plain.status == "agree", plain
    assert dict(id="band-as-text", status="agree") in plain.regions


# === (4) per-class unknown matrix and claim vocabulary =========================


def test_class_claims_without_usable_observations_are_unknown(tmp_path):
    """A class-scoped claim the oracle cannot evaluate per class is a typed
    unknown — never a silent fall back to the undifferentiated mask."""
    scoped = dict(BAND_REGION, **{"class": "text"})
    missing = _coverage_class(tmp_path, (scoped,), observations=None)
    assert missing.status == "unknown"
    assert missing.reason == "class-observations-missing"
    assert missing.regions == ()
    invalid = _coverage_class(tmp_path, (scoped,), observations={"kind": "nope"})
    assert invalid.status == "unknown"
    assert invalid.reason == "class-observations-invalid"
    wrong_frame = _coverage_class(tmp_path, (scoped,),
                                  observations={"kind": "nope", "status": "x"})
    assert wrong_frame.status == "unknown"
    # The masks oracle routes identically.
    m_missing = _masks_class(tmp_path, (scoped,), observations=None)
    assert m_missing.status == "unknown"
    assert m_missing.reason == "class-observations-missing"


def test_class_claim_outside_vocabulary_is_retained_differ(tmp_path):
    """A 'class' value outside the carrier-observation vocabulary is a
    claim-format violation: retained differ with the region id — never
    guessed, never dropped, and independent of any observations."""
    bogus = dict(BAND_REGION, **{"class": "decoration"})
    outcome = _coverage_class(tmp_path, (bogus,), observations=None)
    assert outcome.status == "differ", outcome
    assert {"id": "band-as-text", "status": "differ",
            "class": "decoration"} in outcome.regions
    with_record = _coverage_class(tmp_path, (bogus,),
                                  observations=_class_record(tmp_path))
    assert {"id": "band-as-text", "status": "differ",
            "class": "decoration"} in with_record.regions


# === (5) per-class aggregation under the unchanged rule ========================


def test_per_class_aggregation_pass_and_block(tmp_path):
    """Aggregation semantics are unchanged: per-class agree pages pass; one
    per-class differ page blocks with the attribution retained."""
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    agree_page = _coverage_class(tmp_path,
                                 (_region_from_entry(text_entry, "ink",
                                                     cls="text"),),
                                 observations=record)
    assert agree_page.status == "agree"
    assert coverage.aggregate([agree_page]).status == "pass"
    scoped_band = dict(BAND_REGION, **{"class": "text"})
    differ_page = _coverage_class(tmp_path, (scoped_band,),
                                  observations=record)
    assert differ_page.status == "differ"
    verdict = coverage.aggregate([agree_page, differ_page])
    assert verdict.status == "blocked"
    assert any(CLASS_CARRIER in reason and "differ" in reason
               for reason in verdict.reasons), verdict.reasons


def test_masks_per_class_aggregation_blocked(tmp_path):
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    agree_page = _masks_class(tmp_path,
                              (_region_from_entry(text_entry, "ink",
                                                  cls="text"),),
                              observations=record)
    assert agree_page.status == "agree"
    scoped_band = dict(BAND_REGION, **{"class": "text"})
    differ_page = _masks_class(tmp_path, (scoped_band,), observations=record)
    assert differ_page.status == "differ"
    verdict = masks.aggregate([agree_page, differ_page])
    assert verdict.status == "blocked"
    assert any(CLASS_CARRIER in reason for reason in verdict.reasons)


# === (6) unchanged outcome vocabulary ==========================================


def test_outcome_vocabulary_unchanged(tmp_path):
    """No silent outcome-vocabulary change: every status produced across
    this suite's scenarios stays inside agree/differ/unknown/unavailable,
    and both oracles keep their pinned PROPERTY values."""
    record = _class_record(tmp_path)
    text_entry = record["classes"]["text"]["entries"][0]
    statuses = set()
    statuses.add(_masks_strip(tmp_path, (REGION_GIANT,)).status)
    statuses.add(_coverage_class(tmp_path, (dict(BAND_REGION,
                                                 **{"class": "text"}),),
                                 observations=record).status)
    statuses.add(_masks_class(tmp_path,
                              (_region_from_entry(text_entry, "ink",
                                                  cls="text"),),
                              observations=record).status)
    statuses.add(_coverage_class(tmp_path, (dict(BAND_REGION,
                                                 **{"class": "text"}),),
                                 observations=None).status)
    statuses.add(_coverage_class(tmp_path, (), observations={"x": 1}).status)
    assert statuses <= {"agree", "differ", "unknown", "unavailable"}, statuses
    assert coverage.PROPERTY == "ink-coverage"
    assert masks.PROPERTY == "region-alignment"
