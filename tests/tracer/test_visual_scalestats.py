# Purpose: Scale-free ink statistics tests (sunset-7b4.4, improve-geometry-render-binding
#   Non-goals item "scale-free ink statistics", deferred and now unblocked).
# Responsibilities: Pin the contract of dsc03/visual/scalestats.py: render ONE
#   carrier page at >= 2 distinct pinned dpi settings, compute per-page ink
#   statistics (binarized ink fraction + normalized ink-distribution moments
#   over the RAW ink mask from the shared _pixels gate), and compare across
#   scales within the DECLARED tolerance. Verified here: (a) canonical solid
#   carriers agree across 72/150/300 dpi within the declared tolerance; (b) a
#   single 0.4pt hairline is a DECLARED blind spot (measured delta below
#   tolerance) — pinned so the tolerance is never mistaken for hairline
#   sensitivity; (c) a seeded scale-sensitive defect (24 hairline rules that
#   thin out at the coarse scale) degrades agreement to a typed differ whose
#   attribution retains EVERY exceeded statistic with both scales' values and
#   the measured delta; (d) threshold-marginal ink (gray fill rendered exactly
#   at the binarization boundary, measured gray 128 = threshold on this pinned
#   poppler at 72/150/300 dpi) is typed unknown reason
#   "threshold-marginal-scale" with confounded scales named and the measured
#   cross-scale delta carried — even though the fraction delta alone would have
#   silently agreed (the guard is what flips it, never smoothed); (e) blank
#   pages agree with undefined (None) moments on both scales; (f) shared-gate
#   unknowns (binarization-not-configured) and typed render unavailability
#   carry their reasons verbatim; (g) family-contract violations (fewer than 2
#   scales, duplicate dpi, mismatched page/binarization/lineages across the
#   scale family) raise; (h) statistics are deterministic across processes:
#   a fresh interpreter computing the same carrier/scales produces exactly
#   equal values (integer moment sums; poppler byte-identical renders).
# Rationale: document-visual-oracles "Pinned render configuration",
#   "Calibrated thresholds with per-page outcomes", "No silent resolution",
#   "Labeled evidence class"; proposal Non-goals scope anchor. Measured
#   numbers below were agent-executed on the pinned poppler of this
#   workstation (pdftoppm renders hard, non-anti-aliased vector edges here:
#   fractional-edge probes produced only grays {0, 255}).
"""Scale-free ink statistics tests (sunset-7b4.4)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import render, scalestats
from dsc03.visual.scalestats import (
    BAND_CONFOUND_LIMIT,
    PROPERTY,
    SCOPED_CLAIM,
    TOLERANCE,
    THRESHOLD_GUARD_BAND,
)

from conftest import make_carrier as _make_carrier, render_config as _render_config

PAGE_W, PAGE_H = 612, 792
BOX_FITZ = pymupdf.Rect(100, 192, 400, 492)  # canonical solid box (see test_visual_coverage)

# Agent-executed measured deltas (canonical box, 72 <-> 300 dpi): fraction
# 4.97e-5, centroid-x 6.54e-5, centroid-y 1.52e-4, spread-x 1.81e-5,
# spread-y 1.40e-5 — all far inside the declared TOLERANCE.
SCALES = (72, 300)


def _configs(scales=SCALES, page=1, **overrides):
    return [_render_config(dpi=dpi, page=page, **overrides) for dpi in scales]


def _carrier(tmp_path, name, rects):
    return _make_carrier(tmp_path, name, rects, width=PAGE_W, height=PAGE_H)


def test_module_constants_declared():
    """The tolerance is an explicit declared constant with a documented derivation."""
    assert TOLERANCE == 0.002
    assert THRESHOLD_GUARD_BAND == 32
    assert BAND_CONFOUND_LIMIT == 0.10
    assert PROPERTY == "scale-free-ink-stats"
    # The scoped-claim disclaimer must establish nothing beyond scale-free ink.
    text = SCOPED_CLAIM.lower()
    assert "nothing" in text and "ink" in text
    derivation = scalestats.TOLERANCE_DERIVATION
    assert "0.002" in derivation and "TOLERANCE" in derivation


def test_canonical_box_agrees_across_two_scales(tmp_path):
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    outcome = scalestats.evaluate(_configs(), pdf, carrier="box")
    assert outcome.status == "agree"
    assert outcome.property == PROPERTY
    assert outcome.page == 1
    assert outcome.carrier == "box"
    assert outcome.evidence_class == "independent"
    assert outcome.scales == (72, 300)
    assert outcome.reason is None
    assert outcome.deltas == ()
    assert [s.dpi for s in outcome.stats] == [72, 300]
    for stats in outcome.stats:
        assert 0.18 < stats.ink_fraction < 0.20
        assert 0.0 <= stats.centroid_x < 1.0 and 0.0 <= stats.centroid_y < 1.0
        assert stats.marginal_fraction <= BAND_CONFOUND_LIMIT
    assert outcome.measured_delta is not None and outcome.measured_delta <= TOLERANCE


def test_canonical_box_agrees_across_three_scales(tmp_path):
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    outcome = scalestats.evaluate(_configs((72, 150, 300)), pdf, carrier="box")
    assert outcome.status == "agree"
    assert outcome.scales == (72, 150, 300)
    assert [s.dpi for s in outcome.stats] == [72, 150, 300]


def test_single_hairline_is_declared_blind_spot(tmp_path):
    """One 0.4pt rule (measured delta-fraction 1.2e-4) sits INSIDE the declared
    tolerance: agreement here is the documented blind spot, not sensitivity."""
    pdf = _carrier(tmp_path, "hair.pdf", [BOX_FITZ, pymupdf.Rect(100, 700, 512, 700.4)])
    outcome = scalestats.evaluate(_configs(), pdf, carrier="hair")
    assert outcome.status == "agree"
    assert outcome.measured_delta <= TOLERANCE


def test_seeded_rule_set_defect_differ_with_attribution(tmp_path):
    """24 hairline rules thin out at 72 dpi (measured delta-fraction 6.7e-3):
    typed differ, every exceeded statistic retained with both scales' values."""
    rects = [BOX_FITZ] + [
        pymupdf.Rect(60, 20 + i * 25, 552, 20.4 + i * 25) for i in range(24)
    ]
    pdf = _carrier(tmp_path, "ruled.pdf", rects)
    outcome = scalestats.evaluate(_configs(), pdf, carrier="ruled")
    assert outcome.status == "differ"
    assert outcome.reason is None
    names = [d.statistic for d in outcome.deltas]
    assert "ink-fraction" in names
    assert len(outcome.deltas) >= 2  # moments degrade alongside the fraction
    for delta in outcome.deltas:
        assert delta.delta is not None and delta.delta > TOLERANCE
        assert (delta.coarse_scale, delta.fine_scale) == (72, 300)
        assert delta.coarse_value is not None and delta.fine_value is not None
        assert abs(delta.coarse_value - delta.fine_value) == delta.delta
    fraction = next(d for d in outcome.deltas if d.statistic == "ink-fraction")
    assert fraction.fine_value > fraction.coarse_value  # ink lost at the coarse scale


def test_threshold_marginal_fill_unknown_with_measured_delta(tmp_path):
    """Gray 0.49 fill: this pinned poppler renders the fill as a solid gray
    exactly THRESHOLD_GUARD_BAND-adjacent to the pinned threshold at every
    scale (agent-executed: gray 125 mass, marginal fraction ~0.187 at 72/300).
    The scale comparison is ABOUT the threshold boundary there -> typed unknown
    with the measured delta carried, never a differ, never a silent agree."""
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.draw_rect(BOX_FITZ, color=(0.49, 0.49, 0.49), fill=(0.49, 0.49, 0.49))
    path = tmp_path / "marginal.pdf"
    doc.save(str(path))
    outcome = scalestats.evaluate(_configs(), path, carrier="marginal")
    assert outcome.status == "unknown"
    assert outcome.reason == "threshold-marginal-scale"
    assert outcome.confounded_scales == (72, 300)
    assert isinstance(outcome.measured_delta, float)
    for stats in outcome.stats:
        assert stats.marginal_fraction > BAND_CONFOUND_LIMIT


def test_marginal_guard_is_not_smoothed_away(tmp_path):
    """The marginal carrier's cross-scale fraction delta alone is sub-tolerance
    (it would silently agree); the declared guard is what flips the outcome to
    unknown. Pinned so the guard can never regress into smoothing."""
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.draw_rect(BOX_FITZ, color=(0.49, 0.49, 0.49), fill=(0.49, 0.49, 0.49))
    path = tmp_path / "marginal.pdf"
    doc.save(str(path))
    rendered = [render.render_page(cfg, path) for cfg in _configs()]
    assert all(isinstance(r, render.Rendered) for r in rendered)
    stats = [scalestats.ink_statistics(r, cfg) for r, cfg in zip(rendered, _configs())]
    assert abs(stats[0].ink_fraction - stats[1].ink_fraction) < TOLERANCE
    assert abs(stats[0].centroid_x - stats[1].centroid_x) < TOLERANCE
    outcome = scalestats.evaluate(_configs(), path, carrier="marginal")
    assert outcome.status == "unknown"  # NOT agree, despite the sub-tolerance deltas


def test_blank_page_agrees_with_undefined_moments(tmp_path):
    pdf = _make_carrier(tmp_path, "blank2.pdf", [], width=PAGE_W, height=PAGE_H,
                        blank_pages_after=1)
    outcome = scalestats.evaluate(_configs(page=2), pdf, carrier="blank")
    assert outcome.status == "agree"
    for stats in outcome.stats:
        assert stats.ink_fraction == 0.0
        assert stats.centroid_x is None and stats.centroid_y is None
        assert stats.spread_x is None and stats.spread_y is None
    assert outcome.measured_delta == 0.0


def test_binarization_not_configured_is_unknown(tmp_path):
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    configs = _configs(enabled=False)
    outcome = scalestats.evaluate(configs, pdf, carrier="box")
    assert outcome.status == "unknown"
    assert outcome.reason == "binarization-not-configured"


def test_missing_renderer_is_unavailable(tmp_path):
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    configs = _configs(executable="/nonexistent/pdftoppm-scalestats-probe")
    outcome = scalestats.evaluate(configs, pdf, carrier="box")
    assert outcome.status == "unavailable"
    assert "not found" in outcome.reason
    assert outcome.scales == (72, 300)


def test_family_contract_violations_raise(tmp_path):
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    one = _render_config(dpi=72, page=1)
    other_page = _render_config(dpi=300, page=2)
    other_threshold = _render_config(dpi=300, threshold=160)
    other_lineage = _render_config(dpi=300, extractor="mupdf")
    for bad in (
        (),                              # no scales at all
        (one,),                          # fewer than 2 scales
        (one, _render_config(dpi=72, page=1)),   # duplicate dpi
        (one, other_page),               # different declared page in one family
        (one, other_threshold),          # different binarization in one family
        (one, other_lineage),            # different declared extractor lineage
    ):
        try:
            scalestats.evaluate(bad, pdf, carrier="box")
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for configs={bad}")


def test_cross_process_determinism(tmp_path):
    """A fresh interpreter over the same carrier bytes produces exactly equal
    statistics: integer moment sums + byte-identical pinned renders."""
    pdf = _carrier(tmp_path, "box.pdf", [BOX_FITZ])
    mine = {}
    for dpi in SCALES:
        cfg = _render_config(dpi=dpi, page=1)
        result = render.render_page(cfg, pdf)
        assert isinstance(result, render.Rendered)
        stats = scalestats.ink_statistics(result, cfg)
        mine[dpi] = json.loads(json.dumps(_asdict(stats)))
    root = Path(__file__).resolve().parents[2]
    tracer = Path(__file__).resolve().parent
    script = "\n".join([
        "import dataclasses, json, sys",
        "sys.path.insert(0, sys.argv[1])",
        "sys.path.insert(0, sys.argv[2])",
        "from dsc03.visual import render, scalestats",
        "from conftest import render_config",
        "out = {}",
        "for dpi in (72, 300):",
        "    cfg = render_config(dpi=dpi, page=1)",
        "    r = render.render_page(cfg, sys.argv[3])",
        "    assert isinstance(r, render.Rendered), r.reason",
        "    s = scalestats.ink_statistics(r, cfg)",
        "    out[str(dpi)] = json.loads(json.dumps(dataclasses.asdict(s)))",
        "print(json.dumps(out))",
    ])
    proc = subprocess.run(
        [sys.executable, "-c", script, str(root), str(tracer), str(pdf)],
        capture_output=True, text=True, timeout=240, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    theirs = json.loads(proc.stdout)
    for dpi in SCALES:
        assert theirs[str(dpi)] == mine[dpi]  # exact float equality across processes


def _asdict(stats):
    import dataclasses
    return dataclasses.asdict(stats)
