# Purpose: Tight-ink snapping of declared boxes against the pinned raster
#   (sunset-7b4.7; improve-geometry-render-binding Non-goals lift, review
#   finding EDGE-005).
# Responsibilities: Given a Rendered page and a declared box (descriptor pt,
#   y-up bottom-left origin), measure per-edge ink with the shared
#   _pixels comparison mask (raw, pre-simplification band: snapping measures
#   actual ink; the recorded dilation stays a comparison tolerance, not a
#   snap target) and snap each edge to the tight ink boundary when within
#   the declared tolerance; accept and record sub-tolerance overhang —
#   never refuse it (EDGE-005 BINDING CONSTRAINT); refuse a snap beyond
#   tolerance with a typed witness naming declared vs tight box and signed
#   per-edge deltas; refuse an edge with no contiguous ink in the tolerance
#   band instead of silently leaving it unsnapped; return the snapped box
#   quantized 1/1000 pt under the declared round-half-even rule (never
#   re-quantized differently — quantization is idempotent on the operative
#   box); deterministic across processes (pure function of rendered pixels,
#   declared box and tolerance).
# Rationale: the containment statistic must DECLARE a tolerance and never
#   refuse sub-point box overhangs (EDGE-005); snapping is the recorded
#   counterpart. The declared tolerance reuses the zoom.py convention
#   (DEFAULT_TOLERANCE_PT = 0.5 pt, the sub-point overhang bound under which
#   box geometry is still considered contained), so a snap within 0.5 pt is
#   exactly the overhang containment already accepts. MaskUnavailable from
#   the shared gate propagates (documented unknown — the caller converts it
#   like the other oracles); no silent fallback, no accuracy claim.
"""Tight-ink snapping: declared boxes to tight ink bounds within a declared tolerance."""
import math

from dsc03.substrate.space import quantize_scalar
from dsc03.visual._pixels import comparison_mask
from dsc03.zoom import DEFAULT_TOLERANCE_PT

# Declared snap tolerance: derived from the zoom.py containment convention
# (0.5 pt) — sub-tolerance box overhang is accepted there, so an ink
# boundary within 0.5 pt of a declared edge is the same sub-point slack
# snapping is allowed to absorb. Explicit constant, never inferred.
SNAP_TOLERANCE_PT = DEFAULT_TOLERANCE_PT


def _checked_tolerance(tolerance):
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) \
            or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("invalid declared snap tolerance")
    return float(tolerance)


def _checked_box(box):
    if not isinstance(box, dict):
        raise ValueError("declared box must be a dict")
    coords = (box.get("x"), box.get("y"), box.get("width"), box.get("height"))
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in coords):
        raise ValueError("declared box coordinates must be finite numbers")
    x, y, w, h = (float(v) for v in coords)
    if not (w > 0 and h > 0):
        raise ValueError("declared box must have positive extent")
    return x, y, w, h


def snap_box_to_ink(rendered, config, box, tolerance=SNAP_TOLERANCE_PT):
    """Snap a declared box to the tight ink bounds within `tolerance`.

    box: {"x", "y", "width", "height"} in descriptor pt (y-up bottom-left
    origin). Returns:
      {"status": "snapped", "box": <quantized 1/1000 pt ints>,
       "tolerance", "deltas": {"left","right","top","bottom"}} with signed
      tight-minus-declared per-edge deltas in pt, overhang recorded, never
      refused;
      {"status": "refused", "reason": "beyond-tolerance" |
       "no-contiguous-ink-edge", "witness": {"declared", "tight", "deltas",
       "tolerance", "edges"}} where "tight" is the measured tight box
      (quantized) or None when no edge found ink.

    Raises ValueError for a malformed box or tolerance; propagates
    MaskUnavailable from the shared pixel gate (documented unknown).
    """
    tolerance = _checked_tolerance(tolerance)
    x, y, w, h = _checked_box(box)
    x1, y1 = x + w, y + h
    width, height, raw, _simplified = comparison_mask(rendered, config)
    scale = config.dpi / 72.0  # pt -> px; raster y is top-down
    tpx = tolerance * scale
    # declared box in raster px: x maps directly, y flips
    px0, px1 = x * scale, x1 * scale
    py0, py1 = height - y1 * scale, height - y * scale  # top, bottom rows
    # perpendicular span each edge scans against (the box's other axis,
    # clamped to the raster)
    sy0, sy1 = max(0, int(math.floor(py0))), min(height, int(math.ceil(py1)))
    sx0, sx1 = max(0, int(math.floor(px0))), min(width, int(math.ceil(px1)))

    def ink_col(c):
        return any(raw[c + width * r] for r in range(sy0, sy1))

    def ink_row(r):
        return any(raw[c + width * r] for c in range(sx0, sx1))

    def tight_left():
        for c in range(max(0, int(math.floor(px0 - tpx))),
                       min(width, int(math.ceil(px0 + tpx)) + 1)):
            if ink_col(c):
                return c
        return None

    def tight_right():
        for c in range(min(width, int(math.ceil(px1 + tpx))) - 1,
                       max(0, int(math.floor(px1 - tpx))) - 1, -1):
            if ink_col(c):
                return c
        return None

    def tight_top():
        for r in range(max(0, int(math.floor(py0 - tpx))),
                       min(height, int(math.ceil(py0 + tpx)) + 1)):
            if ink_row(r):
                return r
        return None

    def tight_bottom():
        for r in range(min(height, int(math.ceil(py1 + tpx))) - 1,
                       max(0, int(math.floor(py1 - tpx))) - 1, -1):
            if ink_row(r):
                return r
        return None

    measured = {"left": tight_left(), "right": tight_right(),
                "top": tight_top(), "bottom": tight_bottom()}
    quantized_declared = {
        "x": quantize_scalar(x), "y": quantize_scalar(y),
        "width": quantize_scalar(w), "height": quantize_scalar(h)}
    missing = sorted(e for e, c in measured.items() if c is None)
    if missing:
        return {"status": "refused", "reason": "no-contiguous-ink-edge",
                "witness": {"declared": quantized_declared, "tight": None,
                            "deltas": None, "tolerance": tolerance,
                            "edges": missing}}
    deltas = {
        "left": measured["left"] / scale - x,
        "right": (measured["right"] + 1) / scale - x1,
        "top": height - (measured["top"] / scale) - y1,
        "bottom": height - ((measured["bottom"] + 1) / scale) - y,
    }
    quantized_tight = {
        "x": quantize_scalar(x + deltas["left"]),
        "y": quantize_scalar(y + deltas["bottom"]),
        "width": quantize_scalar(
            (x1 + deltas["right"]) - (x + deltas["left"])),
        "height": quantize_scalar(
            (y1 + deltas["top"]) - (y + deltas["bottom"])),
    }
    beyond = sorted(e for e, d in deltas.items() if abs(d) > tolerance)
    if beyond:
        return {"status": "refused", "reason": "beyond-tolerance",
                "witness": {"declared": quantized_declared,
                            "tight": quantized_tight, "deltas": deltas,
                            "tolerance": tolerance, "edges": beyond}}
    return {"status": "snapped", "box": quantized_tight,
            "tolerance": tolerance, "deltas": deltas}
