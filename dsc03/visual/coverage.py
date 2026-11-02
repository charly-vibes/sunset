# Purpose: Binarized ink-coverage oracle — representation level B (sunset-xzy.3,
#   tasks.md 4.1).
# Responsibilities: Evaluate exactly ONE property ("ink-coverage") for pinned
#   carrier pages: binarize the pinned render's pixels through the recorded
#   binarization config, apply the recorded like-with-like source
#   simplification (design D4, pinned here as 8-connected ink dilation parsed
#   from "ink-dilation-<N>px"), map claimed region rects from descriptor
#   points through the declared frame, and compare measured ink fractions
#   against the one recorded calibration entry for the carrier+page. Report
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

import re
from dataclasses import dataclass

import pymupdf

from dsc03.visual import frames
from dsc03.visual import render

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

_DILATION_RE = re.compile(r"^ink-dilation-(\d+)px$")

# The declared region-claim vocabulary; anything else contradicts the claim
# format and is retained as a disagreement, never guessed.
EXPECTED_VALUES = frozenset({"ink", "no-ink"})

@dataclass(frozen=True)
class CoverageOutcome:
    """Typed per-page, per-property oracle outcome (design D5).

    ``regions`` retains one ``{"id": ..., "status": "agree"|"differ"}`` entry
    per evaluated claim, in input order — disagreements are attributed to
    their source regions and never smoothed. For page-level
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


def _decode_grayscale(data: bytes):
    """Decode rendered PNG bytes to (width, height, gray_samples).

    Pure decoding — not a lineage-bearing step. Raises on undecodable bytes.
    """
    pix = pymupdf.Pixmap(data)
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    gray = pymupdf.Pixmap(pymupdf.csGRAY, pix)
    return gray.width, gray.height, bytes(gray.samples)


_INK_TABLES = {}


def _ink_table(threshold: int) -> bytes:
    """Byte-translation table: gray value strictly below threshold is ink."""
    table = _INK_TABLES.get(threshold)
    if table is None:
        table = bytes(1 if value < threshold else 0 for value in range(256))
        _INK_TABLES[threshold] = table
    return table


def _parse_dilation(simplification: str):
    """Parse the pinned simplification format; None if none is comparable."""
    if not isinstance(simplification, str):
        return None
    match = _DILATION_RE.fullmatch(simplification)
    if match is None:
        return None
    return int(match.group(1))


def _dilate(mask: bytearray, width: int, height: int, radius: int) -> bytearray:
    """8-connected dilation of a packed 0/1 mask (two separable 1-D passes)."""
    if radius <= 0:
        return mask
    one = b"\x01"
    # horizontal pass, row-wise
    out = bytearray(width * height)
    for y in range(height):
        base = y * width
        row = bytes(mask[base:base + width])
        x = row.find(one)
        while x != -1:
            x0 = max(0, x - radius)
            x1 = min(width, x + radius + 1)
            out[base + x0:base + x1] = b"\x01" * (x1 - x0)
            x = row.find(one, x + 1)
    # vertical pass, column-wise (step-slice gather/scatter stays in C)
    for x in range(width):
        col = bytes(out[x::width])
        if col.count(1) == 0:
            continue
        column = bytearray(height)
        y = col.find(one)
        while y != -1:
            y0 = max(0, y - radius)
            y1 = min(height, y + radius + 1)
            column[y0:y1] = b"\x01" * (y1 - y0)
            y = col.find(one, y + 1)
        out[x::width] = column
    return out


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


def coverage_outcome(
    render_result,
    *,
    carrier: str,
    regions,
    calibration,
    geometry,
    frame_name,
) -> CoverageOutcome:
    """Evaluate binarized ink coverage of claimed regions on one pinned page.

    ``render_result`` is a ``render.Rendered`` or ``render.RenderUnavailable``
    for the page; ``regions`` the page's claimed region rects in descriptor
    points; ``calibration`` the ONE recorded entry for this carrier+page (or
    None); ``geometry``/``frame_name`` name the declared frame the claims are
    mapped through. See the module docstring for the pinned semantics.
    """
    config = render_result.config
    carrier = str(carrier)
    if isinstance(render_result, render.RenderUnavailable):
        return CoverageOutcome(
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

    mask = bytearray(gray.translate(_ink_table(binarization.threshold)))
    mask = _dilate(mask, width, height, dilation)

    mapping = frames.frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, frames.UnknownMapping):
        return _unknown(config, carrier, mapping.reason)

    bounds = _usable_calibration(calibration, carrier, config.page)
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
            status = "differ"
        else:
            measured = _region_fraction(mask, width, rect)
            if region["expected"] == "ink":
                status = "agree" if low <= measured <= high else "differ"
            else:  # "no-ink": no ink beyond the calibration floor
                status = "agree" if measured <= low else "differ"
        evaluated.append({"id": rid, "status": status})
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
