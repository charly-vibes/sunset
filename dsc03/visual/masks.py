# Purpose: Geometry-mask alignment oracle — representation level C (sunset-xzy.4,
#   tasks.md 4.2).
# Responsibilities: Evaluate exactly ONE property ("region-alignment") for
#   pinned carrier pages: compare claimed descriptor region rects — mapped
#   ONLY through the declared frame — against the SIMPLIFIED source render
#   (the binarized ink mask dilated by the recorded like-with-like source
#   simplification, design D4), using the one recorded calibration entry for
#   the carrier+page. Never a naive mask-vs-pixels diff: rectangles
#   naturally cover whitespace between glyphs, so the comparison surface is
#   the simplified source, not raw pixels. Report typed per-page outcomes
#   (agree/differ/unknown/unavailable) with per-region verdicts — every
#   disagreement retained and region-attributed (including the pinned
#   "ink-outside-rect" attribution: ink sitting within the dilation band
#   just outside an empty rect is misplaced, not missing) — never electing a
#   winner, never smoothing, never mutating inputs. Decode and measure only.
# Rationale: document-visual-oracles "No silent resolution" (scenario "Mask
#   disagreement": retained region ids, neither reading replaced), "Scoped
#   property claims", "Calibrated thresholds with per-page outcomes",
#   "Labeled evidence class"; design D3 (level C = geometry-only masks), D4
#   (like-with-like comparison), D5 (outcome vocabulary with typed
#   `unavailable`). Decoding rendered bytes is NOT a lineage-bearing step:
#   the evidence label comes solely from the config's declared extractor/
#   renderer lineages.
"""Geometry-mask alignment oracle (representation level C, design D3).

Pinned semantics (every verdict below is derived from recorded configuration
alone — no defaults, no fallbacks):

- Property: this oracle evaluates exactly one property, "region-alignment"
  (``PROPERTY``). Every outcome carries it as a field.

- SCOPED CLAIM: A passing region-alignment result establishes NOTHING about
  text correctness, reading order, semantic grouping or visual completeness;
  it covers only the alignment of claimed descriptor region masks against
  the simplified source render under recorded calibration for the pinned
  carrier page.

- No naive mask-vs-pixels (D4): claimed rects cover whitespace between
  glyphs, so the comparison surface is the SIMPLIFIED source: rendered PNG
  pixels are decoded to grayscale, reduced to ink (pixel INK iff gray value
  strictly below the recorded ``Binarization.threshold``), then dilated by
  the recorded ``source_simplification`` — pinned format
  ``ink-dilation-<N>px``, 8-connected (Chebyshev) dilation, same parser
  semantics as the level-B coverage oracle. ``ink-dilation-0px`` is a valid
  no-op. ``"none"`` — or any unparseable string — means no comparable
  simplification is recorded: outcome ``unknown`` (reason
  ``source-simplification-missing``). If ``binarization.enabled`` is false —
  or the recorded method is not the pinned ``fixed-threshold``, or no
  threshold is recorded — the outcome is ``unknown`` (reason
  ``binarization-not-configured``). Undecodable render bytes yield
  ``unknown`` (reason ``render-decode-failed``).

- Frames: region rects arrive in canonical descriptor points (origin
  bottom-left, y-up; ``x``/``y`` is the minimal corner, ``w``/``h`` the
  extents) and are mapped ONLY through the declared geometry frame
  (``frames.frame_mapping``). An ``UnknownMapping`` makes the outcome
  ``unknown`` with that mapping's reason — never a guessed conversion.

- Calibration: one recorded entry per carrier+page, of the same shape as the
  coverage oracle's: ``{"property": "region-alignment", "carrier": ...,
  "page": ..., "min": float, "max": float}`` with ``min <= max``. A missing
  entry, an entry for another property/carrier/page, or a malformed entry
  (non-numeric or inverted bounds) leaves the page ``unknown`` (reason
  ``uncalibrated``). EXACT region rule pinned here: let ``measured`` be the
  simplified-source ink fraction inside the mapped integer pixel rect.
  A region claiming ``"ink"`` AGREES iff ``min <= measured <= max``.
  A region claiming ``"no-ink"`` AGREES iff ``measured <= min`` — the
  calibration floor is the complement bound, and since ``min <= max`` a
  no-ink measurement is then trivially ``<= max`` too. Anything else is
  ``differ``. (These mirror the level-B oracle's pinned per-region
  semantics.)

- Ink-outside-rect attribution (pinned refinement, still ``differ``): when a
  region FAILS its primary test, its rect contains no RAW ink (pre-
  simplification), and the raw ink mask has ink within the recorded dilation
  N px (Chebyshev distance) OUTSIDE the rect boundary, the disagreement is
  attributed reason ``"ink-outside-rect"``: the claimed ink is misplaced
  adjacent to the rect, not absent (missing ink would be a plain ``differ``
  with no reason). The verdict REMAINS ``differ`` — the oracle never elects
  to move or grow the region to manufacture agreement; the reason exists so
  disagreements are attributable, satisfying "No silent resolution". The
  attribution window is exactly the recorded dilation N — the same tolerance
  the comparison itself uses — and no other threshold exists in this module.
  A failing ``"no-ink"`` region always has ink inside its rect, so the
  attribution can never fire for it.

- Region hygiene: malformed rects or rects mapping partly/wholly outside the
  raster, or claims outside the declared vocabulary ``{"ink", "no-ink"}``,
  are ``differ`` and RETAINED with their id — never clipped, fixed or
  dropped. The page agrees iff every region agrees (region-scoped property:
  there is deliberately NO whole-page fraction requirement); a page with
  usable calibration and no region claims agrees vacuously — the oracle
  measures only what is claimed.

- Typed unavailability: a ``RenderUnavailable`` input yields ``unavailable``
  with the render's reason carried. Neither it nor any ``unknown`` ever
  collapses to a pass, a fail, or a silent skip (design D5).

- Aggregation: ``aggregate`` returns ``pass`` ONLY if every page outcome is
  ``agree`` (which requires recorded, usable calibration); any
  ``unknown``/``unavailable``/``differ`` page — or an empty outcome set —
  yields ``blocked`` with the blocking reasons listed. One blank/degraded
  page must never yield an aggregate pass.
"""
from __future__ import annotations

from dataclasses import dataclass

from dsc03.visual import coverage, frames, render
from dsc03.visual.coverage import (
    _decode_grayscale,
    _dilate,
    _ink_table,
    _parse_dilation,
    _pixel_rect,
    _region_fraction,
)

PROPERTY = "region-alignment"

SCOPED_CLAIM = (
    "A passing region-alignment result establishes NOTHING about text "
    "correctness, reading order, semantic grouping or visual completeness; "
    "it covers only the alignment of claimed descriptor region masks "
    "against the simplified source render under recorded calibration for "
    "the pinned carrier page."
)

# The disagreement attribution this oracle may attach to a retained,
# region-attributed `differ` verdict (see the module docstring for the
# pinned rule; its single threshold is the recorded dilation).
INK_OUTSIDE_RECT = "ink-outside-rect"


@dataclass(frozen=True)
class AlignmentOutcome:
    """Typed per-page, per-property oracle outcome (design D5).

    ``regions`` retains one ``{"id": ..., "status": "agree"|"differ"}``
    entry per evaluated claim, in input order, plus an optional ``"reason"``
    (pinned: ``"ink-outside-rect"``) on disagreeing entries — disagreements
    are attributed to their source regions and never smoothed or elected
    away. For page-level ``unknown``/``unavailable`` outcomes no region
    verdicts exist, so ``regions`` is empty and ``reason`` explains why.
    """

    status: str
    property: str = PROPERTY
    page: int = 0
    evidence_class: str = ""
    carrier: str = ""
    regions: tuple = ()
    reason: str | None = None


# The typed aggregate is shared semantics with the level-B oracle: `pass`
# only when every page outcome agrees, else `blocked` + reasons. Delegated,
# not duplicated.
AggregateOutcome = coverage.AggregateOutcome


def supports_accuracy_claim(outcome) -> bool:
    """Whether an oracle outcome MAY support an accuracy claim.

    Reuses render.py semantics at the oracle level: ``correlated`` evidence
    (render and extraction sharing an implementation lineage) demonstrates
    sensitivity only and can never support an accuracy claim.
    """
    return render.supports_accuracy_claim(outcome.evidence_class)


def _unknown(config, carrier, reason, page=None):
    return AlignmentOutcome(
        status="unknown", page=config.page if page is None else page,
        evidence_class=config.evidence_class, carrier=carrier, regions=(),
        reason=reason,
    )


def _usable_region_calibration(calibration, carrier: str, page: int):
    """Validate the recorded entry for THIS carrier+page; (min, max) or None.

    Same entry shape and validation as the level-B oracle, but bound to THIS
    module's property ("region-alignment") — an ink-coverage entry is not a
    region-alignment calibration.
    """
    if not isinstance(calibration, dict):
        return None
    if calibration.get("property") != PROPERTY:
        return None
    if calibration.get("carrier") != carrier:
        return None
    recorded_page = calibration.get("page")
    if not isinstance(recorded_page, int) or isinstance(recorded_page, bool):
        return None
    if recorded_page != page:
        return None
    low = calibration.get("min")
    high = calibration.get("max")
    if not (
        isinstance(low, (int, float)) and not isinstance(low, bool)
        and isinstance(high, (int, float)) and not isinstance(high, bool)
        and low <= high
    ):
        return None
    return float(low), float(high)


def _has_ink(mask, width: int, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Whether the packed 0/1 mask has any ink in the half-open pixel rect."""
    for y in range(y0, y1):
        if mask[y * width + x0:y * width + x1].count(1):
            return True
    return False


def _ink_outside_rect(raw, width: int, height: int, rect, dilation: int) -> bool:
    """Pinned attribution test: empty rect with ink in its dilation ring.

    True iff the RAW (pre-simplification) mask has no ink inside the mapped
    rect AND has ink within ``dilation`` px (Chebyshev) outside the rect
    boundary — the claimed ink is misplaced adjacent to the rect, not
    missing. ``rect`` comes from ``_pixel_rect`` and is already clamped
    in-bounds; the ring is clamped to the raster here.
    """
    x0, y0, x1, y1 = rect
    if _has_ink(raw, width, x0, y0, x1, y1):
        return False  # the rect itself is not empty: attribution doesn't apply
    rx0, ry0 = max(0, x0 - dilation), max(0, y0 - dilation)
    rx1, ry1 = min(width, x1 + dilation), min(height, y1 + dilation)
    return (
        _has_ink(raw, width, rx0, ry0, x0, ry1)     # left band
        or _has_ink(raw, width, x1, ry0, rx1, ry1)  # right band
        or _has_ink(raw, width, x0, ry0, x1, y0)    # band above (pixel y-down)
        or _has_ink(raw, width, x0, y1, x1, ry1)    # band below
    )


def masks_outcome(
    render_result,
    *,
    carrier: str,
    regions,
    calibration,
    geometry,
    frame_name,
) -> AlignmentOutcome:
    """Evaluate geometry-mask (region) alignment on one pinned page.

    ``render_result`` is a ``render.Rendered`` or ``render.RenderUnavailable``
    for the page; ``regions`` the page's claimed region rects in descriptor
    points (``{"id", "x", "y", "w", "h", "expected"}``); ``calibration`` the
    ONE recorded entry for this carrier+page (or None); ``geometry``/
    ``frame_name`` name the declared frame the claims are mapped through.
    See the module docstring for the pinned semantics (comparison surface is
    the simplified source; exact agree rules; ink-outside-rect attribution).
    """
    config = render_result.config
    carrier = str(carrier)
    if isinstance(render_result, render.RenderUnavailable):
        return AlignmentOutcome(
            status="unavailable", page=config.page,
            evidence_class=config.evidence_class, carrier=carrier, regions=(),
            reason=render_result.reason,
        )

    binarization = config.binarization
    if (
        not binarization.enabled
        or binarization.method != "fixed-threshold"
        or not isinstance(binarization.threshold, int)
        or isinstance(binarization.threshold, bool)
    ):
        return _unknown(config, carrier, "binarization-not-configured")

    try:
        width, height, gray = _decode_grayscale(render_result.data)
    except Exception:
        return _unknown(config, carrier, "render-decode-failed")

    dilation = _parse_dilation(config.source_simplification)
    if dilation is None:
        return _unknown(config, carrier, "source-simplification-missing")

    raw = bytearray(gray.translate(_ink_table(binarization.threshold)))
    simplified = _dilate(bytearray(raw), width, height, dilation)

    mapping = frames.frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, frames.UnknownMapping):
        return _unknown(config, carrier, mapping.reason)

    bounds = _usable_region_calibration(calibration, carrier, config.page)
    if bounds is None:
        return _unknown(config, carrier, "uncalibrated")
    low, high = bounds

    evaluated = []
    all_regions_agree = True
    for region in regions:
        rid = region.get("id") if isinstance(region, dict) else None
        rect = _pixel_rect(mapping, region)
        if rect is None:
            # Malformed or out-of-bounds claim: a retained disagreement, not
            # something to clip, fix or drop ("No silent resolution").
            entry = {"id": rid, "status": "differ"}
        else:
            measured = _region_fraction(simplified, width, rect)
            if region["expected"] == "ink":
                agree = low <= measured <= high
            else:  # "no-ink": nothing beyond the calibration floor
                agree = measured <= low
            entry = {"id": rid, "status": "agree" if agree else "differ"}
            if not agree and region["expected"] == "ink" and _ink_outside_rect(
                raw, width, height, rect, dilation
            ):
                entry["reason"] = INK_OUTSIDE_RECT
        evaluated.append(entry)
        all_regions_agree = all_regions_agree and entry["status"] == "agree"

    # Region-scoped property: the page agrees iff every region agrees. No
    # whole-page fraction requirement exists for region alignment.
    status = "agree" if all_regions_agree else "differ"
    return AlignmentOutcome(
        status=status, page=config.page, evidence_class=config.evidence_class,
        carrier=carrier, regions=tuple(evaluated), reason=None,
    )


def aggregate(outcomes) -> AggregateOutcome:
    """Aggregate page outcomes: ``pass`` ONLY if every page agrees.

    Delegates to the shared aggregate rule: any ``unknown``,
    ``unavailable`` or ``differ`` page blocks, with its blocking reason
    listed; an empty outcome set is blocked too (an aggregate over nothing
    must never claim a pass). An ``agree`` page outcome is only reachable
    with usable recorded calibration, so one blank/degraded/uncalibrated
    page can never hide inside a pass.
    """
    return coverage.aggregate(outcomes)
