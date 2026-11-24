# Purpose: Scale-free ink statistics (sunset-7b4.4; deferred Non-goal of the
#   improve-geometry-render-binding proposal, now unblocked).
# Responsibilities: Render ONE pinned carrier page at >= 2 distinct dpi
#   settings of one declared RenderConfig family, compute per-page ink
#   statistics that are INVARIANT to render scale — the binarized ink
#   fraction and normalized ink-distribution moments (centroid / spread,
#   coordinates divided by their own raster extent) over the RAW ink mask of
#   the shared _pixels gate — and compare every scale against the finest
#   declared scale within the DECLARED tolerance (TOLERANCE, an explicit
#   constant with a measured derivation, see TOLERANCE_DERIVATION). Report
#   typed outcomes: agree (all statistics within tolerance), differ (at least
#   one statistic exceeds the tolerance — RETAINED with every exceeded
#   statistic, both scales' values and the measured delta as attribution,
#   never smoothed), unknown (typed unavailability of the comparison itself),
#   unavailable (the pinned renderer could not render). Scale-dependence of
#   the measurement apparatus is surfaced, not smoothed: a scale whose
#   binarized ink mass sits within THRESHOLD_GUARD_BAND of the pinned
#   threshold beyond BAND_CONFOUND_LIMIT makes the comparison ABOUT the
#   threshold boundary rather than the carrier — typed unknown reason
#   "threshold-marginal-scale" with the confounded scales named and the
#   measured cross-scale delta carried. The px-radius source simplification
#   recorded in the config is deliberately NOT applied here: an ink-dilation
#   radius in pixels is scale-DEPENDENT by declaration (2px at 72dpi is 4x
#   2px at 300dpi in point space), so the statistics use the raw mask and
#   leave smoothing out of a scale-free measurement entirely. Statistics are
#   deterministic across processes: moments accumulate exact integer sums
#   (only one division and one sqrt per number) and the pinned renderer
#   reproduces byte-identical renders for identical configs.
# Rationale: document-visual-oracles "Pinned render configuration",
#   "Calibrated thresholds with per-page outcomes", "No silent resolution",
#   "Labeled evidence class"; design D3/D4/D5 (raw level-B ink mask, recorded
#   simplification applied only where like-with-like comparison is declared,
#   outcome vocabulary with typed unknown/unavailable); proposal Non-goals
#   scope anchor ("scale-free ink statistics ... deferred").
"""Scale-free ink statistics: cross-scale agreement of binarized ink."""
from __future__ import annotations

import math
from dataclasses import dataclass

from dsc03.visual import render
from dsc03.visual.render import RenderConfig
from dsc03.visual._pixels import MaskUnavailable, comparison_mask, decode_grayscale

PROPERTY = "scale-free-ink-stats"

# The declared cross-scale agreement tolerance, identical for every normalized
# statistic in STATISTICS. TOLERANCE_DERIVATION documents where the number
# comes from; every measured number below was agent-executed on the pinned
# poppler of this workstation (hard-edged vector rendering: fractional-edge
# probes produced only grays {0, 255}).
TOLERANCE = 0.002
TOLERANCE_DERIVATION = (
    "TOLERANCE = 0.002 for every statistic in STATISTICS. Statistics are "
    "normalized by their own scale's raster extent, so a uniform resolution "
    "change rescales coordinates exactly; the residual between-scale shift is "
    "raster quantization along ink edges (at most one coarse pixel per edge). "
    "Agent-executed measurement, canonical solid box on a letter page, "
    "72 <-> 300 dpi: fraction 4.97e-5, centroid-x 6.54e-5, centroid-y 1.52e-4, "
    "spread-x 1.81e-5, spread-y 1.40e-5 (max 1.52e-4). 0.002 declares ~13x "
    "headroom over that measured maximum and stays ~6.7x BELOW the smallest "
    "seeded defect this oracle must catch (24-rule hairline set, measured "
    "fraction delta 6.73e-3) and far below the canonical box fraction 0.187, "
    "so a missing ink region can never be absorbed by the tolerance. Declared "
    "blind spot: ONE 0.4pt hairline rule measures delta 1.20e-4 < TOLERANCE "
    "and agrees — a single sub-pixel rule is invisible to scale-free "
    "statistics by declaration; the seeded defect therefore seeds a rule set."
)

# Guard window around the pinned threshold, in gray levels: [t-32, t+32).
# Agent-executed: canonical carriers measure marginal_fraction 0.0 at 72 and
# 300 dpi (hard-edged rendering), while a 0.49-gray fill lands exactly on the
# threshold boundary (solid boundary-adjacent gray mass at 72/150/300 dpi)
# measuring ~0.187 of the page.
THRESHOLD_GUARD_BAND = 32
# A scale whose marginal pixel fraction exceeds this limit binarizes by the
# threshold boundary, not by carrier geometry: cross-scale statistics there
# measure the threshold, and the comparison is typed unknown
# ("threshold-marginal-scale") with the measured delta carried — never
# silently agreed, never misattributed as a carrier defect. Declared between
# the measured canonical 0.0 and the measured marginal-carrier ~0.187.
BAND_CONFOUND_LIMIT = 0.10
REASON_THRESHOLD_MARGINAL = "threshold-marginal-scale"

# The normalized statistics compared across scales; values are fractions of
# their own raster extent, so they are invariant under uniform rescaling.
STATISTICS = ("ink-fraction", "centroid-x", "centroid-y", "spread-x", "spread-y")

SCOPED_CLAIM = (
    "A passing scale-free ink statistics result establishes NOTHING about "
    "text correctness, reading order, semantic grouping, visual completeness, "
    "or which compared scale is the correct one; it covers only that the "
    "binarized ink fraction and normalized ink-distribution moments of the "
    "pinned carrier page agree across the DECLARED scales within the declared "
    "tolerance. Scale-dependence of the measurement apparatus is surfaced as "
    "a typed unknown with the measured delta — never smoothed away."
)


@dataclass(frozen=True)
class InkStats:
    """Scale-normalized ink statistics of one rendered page at one scale.

    Moments are undefined for a blank page (no ink): centroid/spread are None.
    ``marginal_fraction`` is the fraction of page pixels whose gray value lies
    inside the THRESHOLD_GUARD_BAND window around the binarization threshold —
    the declared measure of how much of the binarized decision rests on the
    threshold boundary at this scale.
    """

    dpi: int
    width: int
    height: int
    ink_px: int
    ink_fraction: float
    centroid_x: float | None
    centroid_y: float | None
    spread_x: float | None
    spread_y: float | None
    marginal_fraction: float


@dataclass(frozen=True)
class StatDelta:
    """Attribution of one exceeded (or undefined-side) statistic.

    ``delta`` is |coarse - fine| for numeric values, None when the statistic
    is defined at only one of the two scales (e.g. moments of a page that is
    blank at the coarse scale and carries a sub-tolerance ink speck at the
    fine scale) — an undefined comparison is a retained disagreement, never a
    silent pass.
    """

    statistic: str
    coarse_scale: int
    fine_scale: int
    coarse_value: float | None
    fine_value: float | None
    delta: float | None


@dataclass(frozen=True)
class ScaleStatsOutcome:
    """Typed cross-scale outcome for one carrier page (design D5 vocabulary).

    ``stats`` retains the per-scale InkStats in ascending dpi order whenever
    they could be computed. ``deltas`` retains EVERY exceeded statistic on a
    differ, in STATISTICS order per compared scale pair. ``measured_delta`` is
    the largest comparable numeric between-scale difference (0.0 for
    all-blank agreement) — always carried, including on unknown, so a
    scale-confounded comparison reports what was measured, not a verdict.
    """

    status: str
    property: str = PROPERTY
    page: int = 0
    evidence_class: str = ""
    carrier: str = ""
    scales: tuple = ()
    stats: tuple = ()
    deltas: tuple = ()
    reason: str | None = None
    measured_delta: float | None = None
    confounded_scales: tuple = ()


def _band_table(threshold: int) -> bytes:
    """Byte-translation table flagging gray values inside the guard window."""
    low = threshold - THRESHOLD_GUARD_BAND
    high = threshold + THRESHOLD_GUARD_BAND
    return bytes(1 if low <= value < high else 0 for value in range(256))


def ink_statistics(render_result, config: RenderConfig) -> InkStats:
    """Scale-normalized ink statistics of one rendered page.

    Runs the oracles' shared pixel gate (comparison_mask) for the declared
    binarization/simplification vocabulary and computes statistics over the
    RAW ink mask — MaskUnavailable propagates with its shared reason for the
    caller's typed routing. The gate's dilated mask is deliberately ignored:
    see module header (px-radius simplification is scale-dependent by
    declaration).
    """
    width, height, raw, _simplified = comparison_mask(render_result, config)
    ink_px = 0
    sum_x = sum_y = sum_x2 = sum_y2 = 0
    for y in range(height):
        base = y * width
        row = bytes(raw[base:base + width])
        x = row.find(1)
        while x != -1:
            sum_x += x
            sum_y += y
            sum_x2 += x * x
            sum_y2 += y * y
            ink_px += 1
            x = row.find(1, x + 1)
    if ink_px:
        mean_x = sum_x / ink_px
        mean_y = sum_y / ink_px
        var_x = sum_x2 / ink_px - mean_x * mean_x
        var_y = sum_y2 / ink_px - mean_y * mean_y
        centroid_x = mean_x / width
        centroid_y = mean_y / height
        spread_x = math.sqrt(var_x if var_x > 0.0 else 0.0) / width
        spread_y = math.sqrt(var_y if var_y > 0.0 else 0.0) / height
    else:
        centroid_x = centroid_y = spread_x = spread_y = None
    # The shared gate returns only binarized masks, so the guard-band count
    # re-decodes the same pinned bytes for the pre-binarization gray values.
    _w, _h, gray = decode_grayscale(render_result.data)
    band = gray.translate(_band_table(config.binarization.threshold)).count(1)
    return InkStats(
        dpi=config.dpi,
        width=width,
        height=height,
        ink_px=ink_px,
        ink_fraction=ink_px / (width * height),
        centroid_x=centroid_x,
        centroid_y=centroid_y,
        spread_x=spread_x,
        spread_y=spread_y,
        marginal_fraction=band / len(gray),
    )


def _stat_values(stats: InkStats):
    return (
        ("ink-fraction", stats.ink_fraction),
        ("centroid-x", stats.centroid_x),
        ("centroid-y", stats.centroid_y),
        ("spread-x", stats.spread_x),
        ("spread-y", stats.spread_y),
    )


def _family_checked(configs):
    """Validate one declared scale family; return configs ordered by dpi.

    A family is >= 2 RenderConfigs at DISTINCT dpi sharing every pinned field
    except dpi (page, binarization, simplification, crop-box binding,
    renderer identity and declared lineages). Anything else contradicts the
    module contract and raises ValueError — a cross-scale claim about
    mis-declared configurations would be a silently wrong comparison.
    """
    configs = tuple(configs)
    if len(configs) < 2:
        raise ValueError(
            "scale-free ink statistics need >= 2 declared scales, got "
            f"{len(configs)}"
        )
    for config in configs:
        if not isinstance(config, RenderConfig):
            raise ValueError(f"not a RenderConfig: {config!r}")
    first = configs[0]
    pinned = (
        first.page, first.binarization, first.source_simplification,
        first.render_cropbox, first.renderer_name, first.renderer_executable,
        first.renderer_lineage, first.extractor_lineage,
    )
    for config in configs[1:]:
        other = (
            config.page, config.binarization, config.source_simplification,
            config.render_cropbox, config.renderer_name,
            config.renderer_executable, config.renderer_lineage,
            config.extractor_lineage,
        )
        if other != pinned:
            raise ValueError(
                "scale family must differ in dpi only: "
                f"{other} != {pinned}"
            )
    scales = [config.dpi for config in configs]
    if len(set(scales)) != len(scales):
        raise ValueError(f"duplicate dpi in scale family: {sorted(scales)}")
    return tuple(sorted(configs, key=lambda config: config.dpi))


def evaluate(configs, pdf_path, carrier: str = "") -> ScaleStatsOutcome:
    """Compare one carrier page's ink statistics across >= 2 declared scales.

    ``configs`` is one declared RenderConfig family (see _family_checked);
    every scale is compared against the FINEST declared scale. Typed outcome
    precedence: unavailable (a pinned renderer could not render, reason
    carried verbatim) > unknown (shared pixel gate or threshold-marginal
    scale) > differ (exceeded statistics retained with attribution) > agree.
    """
    ordered = _family_checked(configs)
    scales = tuple(config.dpi for config in ordered)
    page = ordered[0].page

    def outcome(**overrides):
        fields = dict(
            status="agree", page=page, evidence_class=ordered[0].evidence_class,
            carrier=carrier, scales=scales,
        )
        fields.update(overrides)
        return ScaleStatsOutcome(**fields)

    rendered = [render.render_page(config, pdf_path) for config in ordered]
    for result in rendered:
        if isinstance(result, render.RenderUnavailable):
            return outcome(status="unavailable", reason=result.reason)
    stats = []
    for result, config in zip(rendered, ordered):
        try:
            stats.append(ink_statistics(result, config))
        except MaskUnavailable as unavailable:
            return outcome(status="unknown", reason=unavailable.reason)
    confounded = tuple(
        stats_iter.dpi for stats_iter in stats
        if stats_iter.marginal_fraction > BAND_CONFOUND_LIMIT
    )
    reference = stats[-1]
    deltas = []
    comparable = []
    for scale_stats in stats[:-1]:
        for name, coarse in _stat_values(scale_stats):
            fine = getattr(reference, name.replace("-", "_"))
            if coarse is None and fine is None:
                continue
            if coarse is None or fine is None:
                deltas.append(StatDelta(name, scale_stats.dpi, reference.dpi,
                                        coarse, fine, None))
                continue
            delta = abs(coarse - fine)
            comparable.append(delta)
            if delta > TOLERANCE:
                deltas.append(StatDelta(name, scale_stats.dpi, reference.dpi,
                                        coarse, fine, delta))
    measured_delta = max(comparable) if comparable else 0.0
    if confounded:
        return outcome(
            status="unknown", reason=REASON_THRESHOLD_MARGINAL, stats=tuple(stats),
            measured_delta=measured_delta, confounded_scales=confounded,
        )
    if deltas:
        return outcome(
            status="differ", stats=tuple(stats), deltas=tuple(deltas),
            measured_delta=measured_delta,
        )
    return outcome(status="agree", stats=tuple(stats), measured_delta=measured_delta)
