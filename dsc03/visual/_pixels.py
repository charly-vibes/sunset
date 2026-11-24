# Purpose: Shared pixel-morphology primitives for the dsc03 raster visual
#   oracles (rule-of-5 review EXCL-001: coverage, masks and content_classes
#   each duplicated the decode/binarize/dilate machinery with private
#   cross-module imports).
# Responsibilities: Decode a pinned PNG render to grayscale samples; build
#   byte-translation ink tables (strictly below threshold = ink); parse the
#   pinned ink-dilation source-simplification format; 8-connected dilation
#   of a packed 0/1 mask (two separable 1-D passes); and comparison_mask —
#   the shared decode→binarize→dilate gate — raising MaskUnavailable with
#   the shared unknown vocabulary ('binarization-not-configured',
#   'render-decode-failed', 'source-simplification-missing') so each oracle
#   converts it to its own typed unknown outcome.
# Rationale: one statement of the render→mask pipeline; oracle modules keep
#   their own outcome types and unknown routing ("unknown is an answer").
"""Shared pixel morphology: decode, ink tables, dilation, comparison gate."""
import re

import pymupdf

_DILATION_RE = re.compile(r"^ink-dilation-(\d+)px$")
_INK_TABLES = {}


def decode_grayscale(data: bytes):
    """Decode rendered PNG bytes to (width, height, gray_samples).

    Pure decoding — not a lineage-bearing step. Raises on undecodable bytes.
    """
    pix = pymupdf.Pixmap(data)
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    gray = pymupdf.Pixmap(pymupdf.csGRAY, pix)
    return gray.width, gray.height, bytes(gray.samples)


def ink_table(threshold: int) -> bytes:
    """Byte-translation table: gray value strictly below threshold is ink."""
    table = _INK_TABLES.get(threshold)
    if table is None:
        table = bytes(1 if value < threshold else 0 for value in range(256))
        _INK_TABLES[threshold] = table
    return table


def parse_dilation(simplification: str):
    """Parse the pinned simplification format; None if none is comparable."""
    if not isinstance(simplification, str):
        return None
    match = _DILATION_RE.fullmatch(simplification)
    if match is None:
        return None
    return int(match.group(1))


def dilate(mask: bytearray, width: int, height: int, radius: int) -> bytearray:
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


class MaskUnavailable(Exception):
    """The shared pixel gate cannot produce a comparison mask.

    ``reason`` is from the shared unknown vocabulary and must surface in the
    caller's typed outcome — never swallowed, never silently skipped.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def comparison_mask(render_result, config):
    """Decode → binarize → dilate: the oracles' shared comparison surface.

    Returns ``(width, height, raw, simplified)`` — raw is the binarized ink
    mask, simplified its declared dilation (the comparison surface). Raises
    MaskUnavailable; callers convert it to their own typed unknown outcome
    with ``unavailable.reason``.
    """
    binarization = config.binarization
    if (
        not binarization.enabled
        or binarization.method != "fixed-threshold"
        or not isinstance(binarization.threshold, int)
        or isinstance(binarization.threshold, bool)
    ):
        raise MaskUnavailable("binarization-not-configured")
    try:
        width, height, gray = decode_grayscale(render_result.data)
    except Exception:
        raise MaskUnavailable("render-decode-failed")
    dilation = parse_dilation(config.source_simplification)
    if dilation is None:
        raise MaskUnavailable("source-simplification-missing")
    raw = bytearray(gray.translate(ink_table(binarization.threshold)))
    simplified = dilate(bytearray(raw), width, height, dilation)
    return width, height, raw, simplified
