# Purpose: Binarized ink-coverage oracle — representation level B (sunset-xzy.3,
#   tasks.md 4.1).
# Responsibilities: Evaluate exactly ONE property ("ink-coverage") for pinned
#   carrier pages: binarize the pinned render's pixels through the recorded
#   binarization config, apply the recorded like-with-like source
#   simplification (design D4, pinned here as 8-connected ink dilation parsed
#   from "ink-dilation-<N>px"), map claimed region rects from descriptor
#   points through the declared frame, and compare measured ink fractions
#   against the one recorded calibration entry for the carrier+page. Region
#   claims may scope themselves to ONE carrier-observation content class (text /
#   vector / raster) via a "class" key: class-scoped claims are measured
#   against that class's observed rect-union mask built from a
#   content_classes record passed as `observations`, under the SAME recorded
#   bounds — so a decorative raster band no longer reads as [satisfying]
#   missing text. Claims without a "class" key are measured against the
#   undifferentiated simplified ink exactly as before. Report
#   typed per-page/per-property outcomes (agree/differ/unknown/unavailable)
#   with the evidence class, retain every region-attributed disagreement,
#   and aggregate page outcomes so one blank/degraded page never yields a
#   pass. Decode and measure only — never modify inputs, never elect a
#   winner, never smooth differences, never guess a coordinate convention.
# Rationale: document-visual-oracles "Scoped property claims", "Calibrated
#   thresholds with per-page outcomes", "No silent resolution", "Labeled
#   evidence class", "Pinned render configuration"; design D3 (level B is
#   the binarized ink mask), D4 (like-with-like comparison: the oracle
#   applies the source simplification RECORDED in the render config as its
#   tolerance), D5 (outcome vocabulary with typed unavailable). Decoding the
#   rendered bytes is NOT a lineage-bearing step: the evidence label comes
#   solely from the config's declared extractor/renderer lineages.
"""Binarized ink-coverage oracle (representation level B, design D3).

Pinned semantics (every verdict below is derived from recorded configuration
alone — no defaults, no fallbacks):

- Property: this oracle evaluates exactly one property, "ink-coverage"
  (``PROPERTY``). Every outcome carries it as a field.

- SCOPED CLAIM: A passing ink-coverage result establishes NOTHING about text
  correctness, reading order, semantic grouping or visual completeness; it
  covers only binarized ink coverage of claimed regions against recorded
  calibration bounds for the pinned carrier page.

- Binarization: rendered PNG pixels are decoded (pymupdf Pixmap) and reduced
  to grayscale; a pixel is INK iff its gray value is strictly below the
  recorded ``Binarization.threshold`` (dark ink on light paper). If
  ``binarization.enabled`` is false — or the recorded method is not the
  pinned ``fixed-threshold``, or no threshold is recorded — the outcome is
  ``unknown`` (reason ``binarization-not-configured``).

- Source simplification (D4, like-with-like): the string recorded in
  ``RenderConfig.source_simplification`` is applied to the ink mask as the
  oracle's tolerance. Pinned format: ``ink-dilation-<N>px`` dilates the ink
  mask by N pixels with an 8-connected structuring element (square /
  Chebyshev ball; ``DILATION_CONNECTIVITY = 8``). ``ink-dilation-0px`` is a
  valid no-op. ``"none"`` — or any string this oracle cannot parse — means
  no comparable simplification is recorded: outcome ``unknown`` (reason
  ``source-simplification-missing``).

- Frames: region rects arrive in canonical descriptor points (origin
  bottom-left, y-up; ``x``/``y`` is the minimal corner, ``w``/``h`` the
  extents) and are mapped ONLY through the declared geometry frame
  (``frames.frame_mapping``). An ``UnknownMapping`` makes the outcome
  ``unknown`` with that mapping's reason — never a guessed conversion.

- Calibration: one recorded entry per carrier+page,
  ``{"property": "ink-coverage", "carrier": ..., "page": ...,
  "min": float, "max": float}``. A missing entry, an entry for another
  property/carrier/page, or a malformed entry (non-numeric or inverted
  bounds) leaves the page ``unknown`` (reason ``uncalibrated``).

- Per-class claims: a region may scope its claim to ONE carrier-observation
  content class — ``"class": "text" | "vector" | "raster"``
  (``CONTENT_CLASSES``, the observation classes of
  ``dsc03/visual/content_classes.py``). A class-scoped claim is measured
  against THAT class's observed rect-union mask — built by painting every
  usable record entry's ``rect_px`` — under the SAME recorded ``[min, max]``
  bounds (the calibration contract is unchanged; no recalibration). The
  record arrives as the optional ``observations`` argument and is consumed
  ONLY when at least one claim is class-scoped: claims without a ``class``
  key are measured against the undifferentiated simplified ink exactly as
  before. A class-scoped claim that cannot be evaluated per class is a
  typed page ``unknown`` — ``class-observations-missing`` (no record
  passed) or ``class-observations-invalid`` (the record is not a usable
  ``content-class-observations`` "observed" record for THIS page, frame,
  dpi and raster extent) — never a silent fall back to the undifferentiated
  mask. A ``class`` value outside ``CONTENT_CLASSES`` contradicts the claim
  format and is a retained region ``differ`` (like any out-of-vocabulary
  claim). When a class-scoped ``"ink"`` claim FAILS its primary test with
  the claimed class absent from the rect while ANOTHER carrier class's
  observed rects overlap it, the retained ``differ`` carries the attribution
  ``"explained-by-<class>"`` (deterministic ``CONTENT_CLASSES`` order): the
  ink present belongs to another content class — a decorative raster band no
  longer reads as missing text. Ink attributable to no carrier observation
  stays a plain ``differ``; attribution is never invented.

- Verdicts: a region claiming "ink" agrees iff its measured ink fraction
  (after simplification, inside the mapped integer pixel rect) lies within
  ``[min, max]``; a region claiming "no-ink" agrees iff its fraction is at
  most ``min`` (no ink beyond the calibration floor). Regions mapping partly
  or wholly outside the raster, or claims outside the declared vocabulary,
  are ``differ`` and RETAINED with their id ("No silent resolution"). The
  page agrees iff every region agrees AND the whole-page ink fraction is
  within ``[min, max]``.

- Typed unavailability: a ``RenderUnavailable`` input yields ``unavailable``
  with the render's reason carried; undecodable render bytes yield
  ``unknown`` (reason ``render-decode-failed``). Neither ever collapses to a
  pass, a fail, or a silent skip (design D5).

- Aggregation: ``aggregate`` returns ``pass`` ONLY if every page outcome is
  ``agree``; any ``unknown``/``unavailable``/``differ`` page — or an empty
  outcome set — yields ``blocked`` with the blocking reasons listed. One
  blank/degraded page must never yield an aggregate pass.
"""
from __future__ import annotations

from dataclasses import dataclass

from dsc03.visual import frames
from dsc03.visual import render
from dsc03.visual._pixels import MaskUnavailable, comparison_mask

PROPERTY = "ink-coverage"

SCOPED_CLAIM = (
    "A passing ink-coverage result establishes NOTHING about text correctness, "
    "reading order, semantic grouping or visual completeness; it covers only "
    "binarized ink coverage of claimed regions against recorded calibration "
    "bounds for the pinned carrier page."
)

# Pinned structuring element for ink dilation (design D4 tolerance):
# 8-connected = square (Chebyshev) ball, separable into two 1-D passes.
DILATION_CONNECTIVITY = 8

# The declared region-claim vocabulary; anything else contradicts the claim
# format and is retained as a disagreement, never guessed.
EXPECTED_VALUES = frozenset({"ink", "no-ink"})

# Carrier-observation content classes a region claim may be scoped to (the
# observation classes of dsc03/visual/content_classes.py; the pixel-derived
# "graphic-hypothesis" class is deliberately NOT claimable: hypotheses are
# never DSC observations, O-A01).
CONTENT_CLASSES = ("text", "vector", "raster")
CLASS_OBSERVATIONS_KIND = "content-class-observations"
CLASS_OBSERVATIONS_MISSING = "class-observations-missing"
CLASS_OBSERVATIONS_INVALID = "class-observations-invalid"

@dataclass(frozen=True)
class CoverageOutcome:
    """Typed per-page, per-property oracle outcome (design D5).

    ``regions`` retains one ``{"id": ..., "status": "agree"|"differ"}`` entry
    per evaluated claim, in input order — disagreements are attributed to
    their source regions and never smoothed. Class-scoped claims carry their
    ``"class"`` verbatim, and a failing class-scoped ink claim whose ink is
    explained by another carrier class carries ``"reason":
    "explained-by-<class>"``. For page-level ``unknown``/``unavailable``
    outcomes no region verdicts exist, so ``regions`` is empty and
    ``reason`` explains why.
    """

    status: str
    property: str = PROPERTY
    page: int = 0
    evidence_class: str = ""
    carrier: str = ""
    regions: tuple = ()
    reason: str | None = None


@dataclass(frozen=True)
class AggregateOutcome:
    """Typed aggregate over page outcomes: ``pass`` or ``blocked`` + reasons."""

    status: str
    reasons: tuple = ()


def supports_accuracy_claim(outcome) -> bool:
    """Whether an oracle outcome MAY support an accuracy claim.

    Reuses render.py semantics at the oracle level: ``correlated`` evidence
    (render and extraction sharing an implementation lineage) demonstrates
    sensitivity only and can never support an accuracy claim.
    """
    return render.supports_accuracy_claim(outcome.evidence_class)


def _unknown(config, carrier, reason, page=None):
    return CoverageOutcome(
        status="unknown", page=config.page if page is None else page,
        evidence_class=config.evidence_class, carrier=carrier, regions=(),
        reason=reason,
    )


def _usable_calibration(calibration, carrier: str, page: int):
    """Validate the recorded entry for THIS carrier+page; (min, max) or None."""
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


def _pixel_rect(mapping, region):
    """Map a region's descriptor rect to integer raster bounds, or None.

    Returns (x0, y0, x1, y1) with pixels half-open [x0, x1) x [y0, y1), or
    None when the region is malformed or maps (partly) outside the raster —
    an out-of-bounds claim is a disagreement, not something to clip.
    """
    if not isinstance(region, dict):
        return None
    rid = region.get("id")
    coords = (region.get("x"), region.get("y"), region.get("w"), region.get("h"))
    if rid is None or not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in coords
    ):
        return None
    x, y, w, h = coords
    if not (w > 0 and h > 0) or region.get("expected") not in EXPECTED_VALUES:
        return None
    p0 = mapping.descriptor_to_pixel(x, y)
    p1 = mapping.descriptor_to_pixel(x + w, y + h)
    x0 = int(round(min(p0[0], p1[0])))
    x1 = int(round(max(p0[0], p1[0])))
    y0 = int(round(min(p0[1], p1[1])))
    y1 = int(round(max(p0[1], p1[1])))
    if x0 < 0 or y0 < 0 or x1 > mapping.page_px[0] or y1 > mapping.page_px[1]:
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _region_fraction(mask, width: int, rect) -> float:
    x0, y0, x1, y1 = rect
    ink = 0
    for y in range(y0, y1):
        base = y * width
        ink += mask[base + x0:base + x1].count(1)
    return ink / ((x1 - x0) * (y1 - y0))


def _any_ink(mask, width: int, rect) -> bool:
    """Whether the packed 0/1 mask has any ink in the half-open pixel rect."""
    x0, y0, x1, y1 = rect
    for y in range(y0, y1):
        if mask[y * width + x0:y * width + x1].count(1):
            return True
    return False


def _paint_class_rect(mask, rect, width: int, height: int) -> None:
    """Paint one observed entry's raster rect into a class mask.

    Degenerate rects (hairline strokes report zero-height ``rect_px``) are
    painted as a one-pixel line — an observed entry is never silently
    dropped. Bounds were validated by ``_class_ink_masks``.
    """
    x0, y0, x1, y1 = rect
    if x1 <= x0:
        x1 = x0 + 1
    if y1 <= y0:
        y1 = y0 + 1
    ones = b"\x01" * (x1 - x0)
    for y in range(y0, min(y1, height)):
        base = y * width
        mask[base + x0:base + min(x1, width)] = ones


def _class_ink_masks(observations, *, config, frame_name, width, height):
    """Validate the content-class observations and build per-class masks.

    Returns ``(masks, None)`` — one packed 0/1 rect-union mask per class in
    ``CONTENT_CLASSES`` painted from the record's carrier-observation
    ``rect_px`` entries — or ``(None, reason)`` with the typed unknown
    reason when no record was passed
    (``class-observations-missing``) or the record is not a usable
    observed record for THIS page, frame, dpi and raster extent
    (``class-observations-invalid``). Nothing is guessed: an unusable
    record never degrades into partial per-class masks.
    """
    if observations is None:
        return None, CLASS_OBSERVATIONS_MISSING
    usable = (
        isinstance(observations, dict)
        and observations.get("kind") == CLASS_OBSERVATIONS_KIND
        and observations.get("status") == "observed"
        and observations.get("page") == config.page
    )
    frame = observations.get("frame") if usable else None
    usable = usable and isinstance(frame, dict) \
        and frame.get("name") == frame_name and frame.get("status") == "resolved"
    render_record = observations.get("render") if usable else None
    render_config = render_record.get("config") if usable and isinstance(
        render_record, dict) else None
    usable = usable and isinstance(render_config, dict) \
        and render_config.get("dpi") == config.dpi
    classes = observations.get("classes") if usable else None
    usable = usable and isinstance(classes, dict)
    if not usable:
        return None, CLASS_OBSERVATIONS_INVALID
    masks = {}
    for name in CONTENT_CLASSES:
        section = classes.get(name)
        entries = section.get("entries") if isinstance(section, dict) else None
        if not isinstance(entries, list):
            return None, CLASS_OBSERVATIONS_INVALID
        mask = bytearray(width * height)
        for entry in entries:
            rect = entry.get("rect_px") if isinstance(entry, dict) else None
            if not (
                isinstance(rect, list) and len(rect) == 4
                and all(isinstance(v, int) and not isinstance(v, bool)
                        for v in rect)
                and 0 <= rect[0] <= rect[2] <= width
                and 0 <= rect[1] <= rect[3] <= height
            ):
                # An entry outside this raster (or malformed) means the
                # record does not describe THIS render: never painted
                # partially, never clipped silently.
                return None, CLASS_OBSERVATIONS_INVALID
            _paint_class_rect(mask, rect, width, height)
        masks[name] = mask
    return masks, None


def _explained_by(rect, claimed_class, class_masks, width: int):
    """Attribution for a failing class-scoped claim: which OTHER carrier
    class's observed rects overlap the rect, in CONTENT_CLASSES order, or
    None when no carrier observation explains the ink (never invented)."""
    for name in CONTENT_CLASSES:
        if name == claimed_class:
            continue
        if _any_ink(class_masks[name], width, rect):
            return f"explained-by-{name}"
    return None


def coverage_outcome(
    render_result,
    *,
    carrier: str,
    regions,
    calibration,
    geometry,
    frame_name,
    observations=None,
) -> CoverageOutcome:
    """Evaluate binarized ink coverage of claimed regions on one pinned page.

    ``render_result`` is a ``render.Rendered`` or ``render.RenderUnavailable``
    for the page; ``regions`` the page's claimed region rects in descriptor
    points; ``calibration`` the ONE recorded entry for this carrier+page (or
    None); ``geometry``/``frame_name`` name the declared frame the claims are
    mapped through; ``observations`` the page's content-class observations
    record (consumed only when some claim is class-scoped — see the module
    docstring). See the module docstring for the pinned semantics.
    """
    config = render_result.config
    carrier = str(carrier)
    if isinstance(render_result, render.RenderUnavailable):
        return CoverageOutcome(
            status="unavailable", page=config.page,
            evidence_class=config.evidence_class, carrier=carrier, regions=(),
            reason=render_result.reason,
        )

    try:
        width, height, _raw, mask = comparison_mask(render_result, config)
    except MaskUnavailable as unavailable:
        return _unknown(config, carrier, unavailable.reason)

    mapping = frames.frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, frames.UnknownMapping):
        return _unknown(config, carrier, mapping.reason)

    bounds = _usable_calibration(calibration, carrier, config.page)
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
            status = "differ"
        elif claimed_class is not None and claimed_class not in CONTENT_CLASSES:
            # Out-of-vocabulary class: contradicts the claim format, never
            # guessed into a measurable claim.
            status = "differ"
        else:
            surface = class_masks[claimed_class] if claimed_class else mask
            measured = _region_fraction(surface, width, rect)
            if region["expected"] == "ink":
                status = "agree" if low <= measured <= high else "differ"
            else:  # "no-ink": no ink beyond the calibration floor
                status = "agree" if measured <= low else "differ"
            if status == "differ" and claimed_class is not None \
                    and region["expected"] == "ink" \
                    and not _any_ink(surface, width, rect):
                explained = _explained_by(rect, claimed_class, class_masks,
                                          width)
                if explained is not None:
                    # The ink present belongs to another content class —
                    # attributed, never silently read as missing.
                    entry["reason"] = explained
        entry["status"] = status
        evaluated.append(entry)
        all_regions_agree = all_regions_agree and status == "agree"

    page_fraction = mask.count(1) / (width * height)
    page_ok = low <= page_fraction <= high
    status = "agree" if (all_regions_agree and page_ok) else "differ"
    return CoverageOutcome(
        status=status, page=config.page, evidence_class=config.evidence_class,
        carrier=carrier, regions=tuple(evaluated), reason=None,
    )


def aggregate(outcomes) -> AggregateOutcome:
    """Aggregate page outcomes: ``pass`` ONLY if every page agrees.

    Any ``unknown``, ``unavailable`` or ``differ`` page blocks, with its
    blocking reason listed; an empty outcome set is blocked too (an aggregate
    over nothing must never claim a pass).
    """
    outcomes = list(outcomes)
    if not outcomes:
        return AggregateOutcome(status="blocked", reasons=("no-page-outcomes",))
    reasons = []
    for outcome in outcomes:
        if outcome.status == "agree":
            continue
        detail = f"{outcome.carrier} page {outcome.page}: {outcome.status}"
        if outcome.reason:
            detail += f" ({outcome.reason})"
        reasons.append(detail)
    if reasons:
        return AggregateOutcome(status="blocked", reasons=tuple(reasons))
    return AggregateOutcome(status="pass", reasons=())
