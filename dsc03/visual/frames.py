# Purpose: Declared frame mapping — pixel↔descriptor coordinate resolution
#   (sunset-xzy.2, tasks.md 3.2).
# Responsibilities: Resolve pixel coordinates to descriptor geometry ONLY
#   through a declared geometry profile frame acquired via
#   profiles.resolve_frame; derive the mapping exclusively from the declared
#   fields (unit → pixel scale, origin/axes → canonical flips, declared
#   scale, declared rotation, declared crop offset, source_scope → page
#   binding) and return a typed outcome — PixelMapping (forward/inverse
#   transforms) or UnknownMapping (reason) — for missing, incompatible,
#   ambiguous or non-resolvable frames. Never a guessed coordinate
#   convention, never an identity fallback, and never comparison verdicts
#   (`agree`/`differ` belong to oracle tasks 4.x).
# Rationale: document-visual-oracles "Declared frame mapping" (scenarios
#   "Rotated page", "Missing frame"); document-adapters "Declared coordinate
#   frames". Declared conventions, pinned here so tests can hand-compute
#   expected pixels: (1) descriptor space is canonical PDF user space —
#   origin bottom-left, x-right, y-up, unit pt; pixel space is the rendered
#   raster — origin top-left, x-right, y-down. (2) `rotation` is the number
#   of degrees CLOCKWISE by which the rendered raster is rotated relative to
#   the descriptor page (PDF /Rotate convention); for 90/270 the raster
#   rectangle dimensions are the swapped page dimensions, derived from the
#   supplied raster extent — never assumed. (3) `crop`, when non-null, is
#   {"x", "y"} in frame units (pt), ADDED to descriptor coordinates in
#   descriptor orientation before unit conversion (it positions the
#   descriptor's local origin relative to the page origin); the transform is
#   exactly invertible. (4) The pinned pixel tolerance (PINNED_PIXEL_TOLERANCE_PX)
#   bounds round-trip recovery error: mapping(point) → pixel → mapping⁻¹(pixel)
#   must recover the original descriptor point within it.
"""Declared frame mapping: pixel↔descriptor coordinate resolution."""
from __future__ import annotations

import re
from dataclasses import dataclass

from dsc03 import profiles

# Frame unit → points per inch. Only declared, implemented units may map;
# anything else is `unknown` — px is a pixel unit and is NOT assumed.
SUPPORTED_UNITS = {"pt": 72.0}

# Canonical descriptor space: origin/axes must declare exactly this pair.
CANONICAL_ORIGIN = "bottom-left"
CANONICAL_AXES = "x-right-y-up"

# Declared rotations of the raster rectangle (clockwise degrees).
SUPPORTED_ROTATIONS = {0, 90, 180, 270}

# Pinned pixel tolerance: round-trip recovery error bound, in pixels.
# 1e-6 px is far below any rendered-pixel granularity yet comfortably above
# float64 rounding for page-sized coordinates.
PINNED_PIXEL_TOLERANCE_PX = 1e-6

# The complete outcome vocabulary of this module. Comparison verdicts
# (agree/differ) are NOT outcomes here — they belong to oracle tasks 4.x.
OUTCOME_STATUSES = frozenset({"resolved", "unknown"})

_SOURCE_SCOPE_RE = re.compile(r"^page:(\d+)$")


@dataclass(frozen=True)
class PixelMapping:
    """A resolved descriptor↔pixel mapping derived from one declared frame.

    Exposes exactly the two declared transforms; every field traces back to
    the frame record, the render configuration, or the supplied raster extent.
    """

    frame_name: object
    dpi: int
    page_px: tuple
    unit: str
    scale: tuple
    rotation: int
    crop: tuple | None
    status: str = "resolved"

    def _forward_axes(self):
        """Unrotated page pixel extent (W0, H0) derived from the raster."""
        w, h = self.page_px
        if self.rotation in (90, 270):
            return h, w
        return w, h

    def descriptor_to_pixel(self, x_pt, y_pt):
        """Map a descriptor point (pt, bottom-left, y-up) to raster pixels."""
        w0, h0 = self._forward_axes()
        points_per_unit = SUPPORTED_UNITS[self.unit]
        sx, sy = self.scale
        cx, cy = self.crop if self.crop is not None else (0.0, 0.0)
        # declared crop offset, then unit scale × declared scale
        ux = (x_pt + cx) * self.dpi / points_per_unit * sx
        uy = (y_pt + cy) * self.dpi / points_per_unit * sy
        # canonical bottom-left y-up → pixel top-left y-down (unrotated page)
        vx, vy = ux, h0 - uy
        # declared clockwise rotation of the raster rectangle
        if self.rotation == 90:
            return h0 - vy, vx
        if self.rotation == 180:
            return w0 - vx, h0 - vy
        if self.rotation == 270:
            return vy, w0 - vx
        return vx, vy

    def pixel_to_descriptor(self, px, py):
        """Map a raster pixel back to a descriptor point (pt, y-up)."""
        w0, h0 = self._forward_axes()
        # inverse of the declared clockwise rotation
        if self.rotation == 90:
            vx, vy = py, h0 - px
        elif self.rotation == 180:
            vx, vy = w0 - px, h0 - py
        elif self.rotation == 270:
            vx, vy = w0 - py, px
        else:
            vx, vy = px, py
        # inverse y-flip, then divide out declared scale × unit scale
        points_per_unit = SUPPORTED_UNITS[self.unit]
        sx, sy = self.scale
        cx, cy = self.crop if self.crop is not None else (0.0, 0.0)
        ux = vx / (self.dpi / points_per_unit * sx)
        uy = (h0 - vy) / (self.dpi / points_per_unit * sy)
        return ux - cx, uy - cy


@dataclass(frozen=True)
class UnknownMapping:
    """Typed unknown outcome: no mapping could be declared without guessing.

    Deliberately exposes NO transforms — an unresolvable frame must never
    silently behave like any coordinate convention.
    """

    reason: str
    detail: str
    status: str = "unknown"


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def resolve_pixel_mapping(frame, render_config, page_px):
    """Resolve one declared frame record against a pinned render config.

    `page_px` is the rendered raster extent (width, height) in pixels at
    `render_config.dpi` — supplied by the caller from the render, never
    assumed. Returns PixelMapping or UnknownMapping; every unknown carries a
    reason from the declared-field vocabulary.
    """
    if not isinstance(frame, dict):
        return UnknownMapping("invalid_geometry_frame", "frame record is not a mapping")
    dpi = getattr(render_config, "dpi", None)
    page = getattr(render_config, "page", None)
    if not _is_int(dpi) or dpi <= 0 or not _is_int(page) or page < 1:
        return UnknownMapping("invalid_render_config", "dpi and page must be positive integers")
    if not (
        isinstance(page_px, (tuple, list))
        and len(page_px) == 2
        and all(_is_int(v) and v > 0 for v in page_px)
    ):
        return UnknownMapping("invalid_page_extent", "page_px must be two positive integers")

    # source_scope binding: declared page must match the rendered page.
    scope = frame.get("source_scope")
    if not isinstance(scope, str):
        return UnknownMapping("unresolvable_source_scope", "source_scope missing or not a string")
    m = _SOURCE_SCOPE_RE.fullmatch(scope)
    if m is None:
        return UnknownMapping("unresolvable_source_scope", f"unparseable source_scope: {scope!r}")
    if int(m.group(1)) != page:
        return UnknownMapping(
            "unresolvable_source_scope",
            f"frame binds {scope}, render config declares page {page}",
        )

    # unit: only declared, implemented units map; never assume px.
    unit = frame.get("unit")
    if unit not in SUPPORTED_UNITS:
        return UnknownMapping("unsupported_unit", f"unit {unit!r} has no declared conversion")

    # origin/axes: only the canonical descriptor space is implemented.
    if frame.get("origin") != CANONICAL_ORIGIN or frame.get("axes") != CANONICAL_AXES:
        return UnknownMapping(
            "unsupported_axes",
            f"origin/axes {frame.get('origin')!r}/{frame.get('axes')!r} not canonical",
        )

    # declared scale: two positive finite factors (zero/invalid cannot invert).
    scale = frame.get("scale")
    if not (
        isinstance(scale, (tuple, list))
        and len(scale) == 2
        and all(_is_number(v) and v > 0 for v in scale)
    ):
        return UnknownMapping("malformed_frame", "scale must be two positive numbers")

    # declared rotation: exact supported values only — never guessed to 0.
    rotation = frame.get("rotation")
    if not _is_int(rotation) or rotation not in SUPPORTED_ROTATIONS:
        return UnknownMapping(
            "unsupported_rotation", f"rotation {rotation!r} not in {sorted(SUPPORTED_ROTATIONS)}"
        )

    # declared crop: null, or {"x","y"} numbers in frame units (pt).
    crop = frame.get("crop")
    if crop is not None:
        if not (
            isinstance(crop, dict)
            and _is_number(crop.get("x"))
            and _is_number(crop.get("y"))
        ):
            return UnknownMapping("malformed_frame", "crop must be null or {'x','y'} numbers")
        crop = (crop["x"], crop["y"])

    return PixelMapping(
        frame_name=frame.get("name"),
        dpi=dpi,
        page_px=(page_px[0], page_px[1]),
        unit=unit,
        scale=(scale[0], scale[1]),
        rotation=rotation,
        crop=crop,
    )


def frame_mapping(artifact, frame_name, render_config, page_px):
    """Acquire a named frame via profiles.resolve_frame and map it.

    A frame name that does not resolve (missing frame, non-geometry artifact)
    yields UnknownMapping(reason="invalid_geometry_frame") — never an
    identity mapping fallback.
    """
    status, frame = profiles.resolve_frame(artifact, frame_name)
    if status != "resolved":
        return UnknownMapping(
            "invalid_geometry_frame",
            f"frame {frame_name!r} did not resolve (profiles status: {status})",
        )
    return resolve_pixel_mapping(frame, render_config, page_px)
