# Purpose: Geometry-mask alignment oracle — representation level C (sunset-xzy.4,
#   tasks.md 4.2).
# Responsibilities: Evaluate exactly ONE property ("region-alignment") for
#   pinned carrier pages: compare claimed descriptor region rects — mapped
#   ONLY through the declared frame — against the SIMPLIFIED source render
#   (the binarized ink mask dilated by the recorded like-with-like source
#   simplification, design D4), using the one recorded calibration entry for
#   the carrier+page. Never a naive mask-vs-pixels diff: rectangles
#   naturally cover whitespace between glyphs, so the comparison surface is
#   the simplified source, not raw pixels. Region claims may scope themselves
#   to ONE carrier-observation content class (text / vector / raster) via a
#   "class" key, measured against that class's observed rect-union mask from
#   a content_classes record under the SAME recorded bounds; and an "ink"
#   claim that passes its primary window yet overcovers blank area — its
#   rect area exceeding the contained ink area by more than the pinned
#   OVERSIZE_MAX_AREA_RATIO — ends differ WITH the "region-oversized"
#   attribution, so a giant rectangle cannot pass by overcovering. Report
#   typed per-page outcomes
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

- Per-class claims: a region may scope its claim to ONE carrier-observation
  content class — ``"class": "text" | "vector" | "raster"``
  (``coverage.CONTENT_CLASSES``, the observation classes of
  ``dsc03/visual/content_classes.py``). A class-scoped claim is measured
  against THAT class's observed rect-union mask — built by painting every
  usable record entry's ``rect_px`` — under the SAME recorded ``[min, max]``
  bounds (the calibration contract is unchanged; no recalibration). The
  record arrives as the optional ``observations`` argument and is consumed
  ONLY when at least one claim is class-scoped: claims without a ``class``
  key are measured against the undifferentiated simplified source exactly
  as before. A class-scoped claim that cannot be evaluated per class is a
  typed page ``unknown`` — ``class-observations-missing`` (no record
  passed) or ``class-observations-invalid`` (the record is not a usable
  ``content-class-observations`` "observed" record for THIS page, frame,
  dpi and raster extent) — never a silent fall back. A ``class`` value
  outside the vocabulary is a retained region ``differ``. When a
  class-scoped ``"ink"`` claim FAILS its primary test with the claimed
  class absent from the rect while ANOTHER carrier class's observed rects
  overlap it, the retained ``differ`` carries the attribution
  ``"explained-by-<class>"`` (deterministic CONTENT_CLASSES order): the
  ink present belongs to another content class — a decorative raster band
  no longer reads as missing text. Ink attributable to no carrier
  observation stays a plain ``differ``; attribution is never invented, and
  class-scoped claims never take the ``ink-outside-rect`` attribution
  (theirs is the class-scoped explanation above).

- Overcoverage penalty (pinned refinement, still ``differ``): when a region
  claiming ``"ink"`` PASSES its primary test but its rect area exceeds its
  contained comparison-surface ink area by more than the pinned
  ``OVERSIZE_MAX_AREA_RATIO`` (region-area : contained-ink-area), the
  verdict is ``differ`` with attribution ``"region-oversized"``: the region
  explains the ink but overcovers blank area — a giant rectangle cannot
  pass by overcovering. The ratio is measured on the SAME surface as the
  primary test (the simplified source; the class mask for class-scoped
  claims), and a contained-ink area of zero counts as infinite
  overcoverage. ``"no-ink"`` claims are never oversized (covering blank
  area is their claim), and a region failing its primary test keeps a
  plain ``differ`` — the penalty never invents a second reading. The bound
  is a pinned morphology parameter of THIS oracle (like
  content_classes' ``MIN_AREA_PX``), NOT a recorded calibration entry:
  recorded thresholds and the calibration contract are unchanged. Seeded
  validation (AGENT-EXECUTED measurements through the pinned pipeline —
  proxy metrics, a human pass supersedes): the sparsest region any
  recorded window legitimately admits measures a ratio of ~13.3
  (bank-statement-ca-excerpt header band, ~7.5% simplified ink); the
  smallest demonstrated oversized claim measures ~34; the pinned 20 sits
  between with margin on both sides.

- Ink-outside-rect attribution (pinned refinement, still ``differ``): when a
  region FAILS its primary test, its rect contains no RAW ink (pre-
  simplification), and the raw ink mask has ink within the recorded dilation
  N px (Chebyshev distance) OUTSIDE the rect boundary, the disagreement is
  attributed reason ``"ink-outside-rect"``: the claimed ink is misplaced
  adjacent to the rect, not missing (missing ink would be a plain ``differ``
  with no reason). The verdict REMAINS ``differ`` — the oracle never elects
  to move or grow the region to manufacture agreement; the reason exists so
  disagreements are attributable, satisfying "No silent resolution". The
  attribution window is exactly the recorded dilation N — the same tolerance
  the comparison itself uses; the only OTHER threshold in this module is the
  pinned overcoverage bound above, which is a module constant and touches no
  recorded calibration entry. A failing ``"no-ink"`` region always has ink
  inside its rect, so the attribution can never fire for it.

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
from dsc03.visual._pixels import (
    MaskUnavailable,
    comparison_mask,
    parse_dilation,
)
from dsc03.visual.coverage import (
    CONTENT_CLASSES,
    _any_ink,
    _class_ink_masks,
    _explained_by,
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

# The disagreement attributions this oracle may attach to a retained,
# region-attributed `differ` verdict (see the module docstring for the
# pinned rules; the ink-outside-rect window is the recorded dilation, the
# overcoverage bound is the pinned module constant below — neither is a
# recorded calibration entry).
INK_OUTSIDE_RECT = "ink-outside-rect"
OVERSIZE = "region-oversized"

# Pinned overcoverage bound (region-area : contained-comparison-surface-ink-
# area): an "ink" claim whose rect explains the ink yet overcovers blank
# area past this ratio ends `differ` with "region-oversized". Seeded-
# validated against the committed corpus — sparsest legitimate recorded
# region ~13.3 (bank header band), smallest demonstrated oversize ~34 — and
# deliberately NOT part of the recorded calibration contract.
OVERSIZE_MAX_AREA_RATIO = 20.0


@dataclass(frozen=True)
class AlignmentOutcome:
    """Typed per-page, per-property oracle outcome (design D5).

    ``regions`` retains one ``{"id": ..., "status": "agree"|"differ"}``
    entry per evaluated claim, in input order, plus an optional ``"reason"``
    (pinned: ``"ink-outside-rect"``, ``"region-oversized"`` or
    ``"explained-by-<class>"``) on disagreeing entries; class-scoped claims
    carry their ``"class"`` verbatim — disagreements are attributed to
    their source regions and never smoothed or elected away. For page-level
    ``unknown``/``unavailable`` outcomes no region verdicts exist, so
    ``regions`` is empty and ``reason`` explains why.
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
    return _any_ink(mask, width, (x0, y0, x1, y1))


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
    observations=None,
) -> AlignmentOutcome:
    """Evaluate geometry-mask (region) alignment on one pinned page.

    ``render_result`` is a ``render.Rendered`` or ``render.RenderUnavailable``
    for the page; ``regions`` the page's claimed region rects in descriptor
    points (``{"id", "x", "y", "w", "h", "expected"}``, optional ``"class"``);
    ``calibration`` the ONE recorded entry for this carrier+page (or None);
    ``geometry``/``frame_name`` name the declared frame the claims are mapped
    through; ``observations`` the page's content-class observations record
    (consumed only when some claim is class-scoped). See the module docstring
    for the pinned semantics (comparison surface is the simplified source;
    exact agree rules; ink-outside-rect attribution; overcoverage penalty;
    per-class claims).
    """
    config = render_result.config
    carrier = str(carrier)
    if isinstance(render_result, render.RenderUnavailable):
        return AlignmentOutcome(
            status="unavailable", page=config.page,
            evidence_class=config.evidence_class, carrier=carrier, regions=(),
            reason=render_result.reason,
        )

    try:
        width, height, raw, simplified = comparison_mask(render_result, config)
    except MaskUnavailable as unavailable:
        return _unknown(config, carrier, unavailable.reason)

    dilation = parse_dilation(config.source_simplification)

    mapping = frames.frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, frames.UnknownMapping):
        return _unknown(config, carrier, mapping.reason)

    bounds = _usable_region_calibration(calibration, carrier, config.page)
    if bounds is None:
        return _unknown(config, carrier, "uncalibrated")
    low, high = bounds

    # Per-class machinery is built only when some claim is actually scoped
    # to a carrier class; classless claims never consult (or require) it.
    class_scoped = any(
        isinstance(region, dict) and region.get("class") in CONTENT_CLASSES
        for region in regions
    )
    class_masks = None
    if class_scoped:
        class_masks, class_reason = _class_ink_masks(
            observations, config=config, frame_name=frame_name,
            width=width, height=height,
        )
        if class_masks is None:
            return _unknown(config, carrier, class_reason)

    evaluated = []
    all_regions_agree = True
    for region in regions:
        rid = region.get("id") if isinstance(region, dict) else None
        claimed_class = region.get("class") if isinstance(region, dict) else None
        entry = {"id": rid}
        if claimed_class is not None:
            # Retain the claim's class dimension verbatim — including an
            # out-of-vocabulary value (a retained disagreement below).
            entry["class"] = claimed_class
        rect = _pixel_rect(mapping, region)
        if rect is None:
            # Malformed or out-of-bounds claim: a retained disagreement, not
            # something to clip, fix or drop ("No silent resolution").
            entry["status"] = "differ"
        elif claimed_class is not None and claimed_class not in CONTENT_CLASSES:
            # Out-of-vocabulary class: contradicts the claim format, never
            # guessed into a measurable claim.
            entry["status"] = "differ"
        else:
            surface = class_masks[claimed_class] if claimed_class else simplified
            measured = _region_fraction(surface, width, rect)
            if region["expected"] == "ink":
                agree = low <= measured <= high
            else:  # "no-ink": nothing beyond the calibration floor
                agree = measured <= low
            if agree and region["expected"] == "ink":
                # Overcoverage penalty: the region explains the ink but its
                # rect overcovers blank area past the pinned ratio (zero
                # contained ink counts as infinite overcoverage). The ratio
                # is measured on the SAME surface as the primary test.
                area = (rect[2] - rect[0]) * (rect[3] - rect[1])
                contained_ink = round(measured * area)
                if contained_ink == 0 or area > OVERSIZE_MAX_AREA_RATIO * contained_ink:
                    agree = False
                    entry["reason"] = OVERSIZE
            entry["status"] = "agree" if agree else "differ"
            if not agree and region["expected"] == "ink":
                if claimed_class is not None:
                    if not _any_ink(surface, width, rect):
                        explained = _explained_by(rect, claimed_class,
                                                  class_masks, width)
                        if explained is not None:
                            # The ink present belongs to another content
                            # class — attributed, never read as missing.
                            entry["reason"] = explained
                elif _ink_outside_rect(raw, width, height, rect, dilation):
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
