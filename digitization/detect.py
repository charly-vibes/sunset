# Purpose: Propose region geometry from rendered page pixels with no OCR run.
# Responsibilities: Decode the rendered page PNG, mark ink on a coarse grid,
#   merge ink into reading-order region proposals emitted as recorded-config
#   detections (id / kind / bbox in nonnegative integer y-down page points).
# Rationale: sunset-rmx.15 regional route (tasks 2.4, design step 1): OCR is
#   never a prerequisite for initial regions — this deterministic layout tool
#   proposes geometry from pixels alone, and the crop-OCR adapter recognizes
#   text per proposal later. Proposals are geometry only: kind stays
#   'ink-block' because classification (text/graphic) is refinement machinery,
#   not detection. Boxes are grid-resolution and deliberately conservative
#   (ceil outward on conversion) so crops never clip proposed ink.
"""Deterministic image-based region proposals (no OCR prerequisite)."""
import pymupdf

INK_LEVEL = 128   # grayscale at or below this counts as ink
CELL_PX = 8       # coarse analysis grid, pixels
GAP_CELLS = 2     # ink-free cells bridged when merging bands/columns


def _decode(png_bytes):
    with pymupdf.open(stream=png_bytes, filetype='png') as document:
        return document[0].get_pixmap(alpha=False)


def _row_ink(pix):
    """Boolean per-pixel-row list: True when the row contains any ink."""
    width, n, samples = pix.width, pix.n, pix.samples
    stride = width * n
    return [any(samples[offset + channel] <= INK_LEVEL
                for offset in range(base, base + stride, n)
                for channel in range(n))
            for base in range(0, len(samples), stride)]


def _column_ink(pix, first_row, last_row):
    """Boolean per-pixel-column list over the given pixel row range."""
    width, n, samples = pix.width, pix.n, pix.samples
    stride = width * n
    columns = [False] * width
    for row in range(first_row, last_row + 1):
        base = row * stride
        for column in range(width):
            offset = base + column * n
            if any(samples[offset + channel] <= INK_LEVEL
                   for channel in range(n)):
                columns[column] = True
    return columns


def _segments(flags, gap):
    """Merge True runs allowing up to `gap` False cells between them."""
    segments, start, hole = [], None, 0
    for index, flag in enumerate(flags):
        if flag:
            if start is None:
                start = index
            hole = 0
        elif start is not None:
            hole += 1
            if hole > gap:
                segments.append((start, index - hole))
                start = None
    if start is not None:
        segments.append((start, len(flags) - 1))
    return segments


def _cell_flags(pixel_flags):
    """Reduce per-pixel flags to per-cell flags (any ink in the cell)."""
    return [any(pixel_flags[base:base + CELL_PX])
            for base in range(0, len(pixel_flags), CELL_PX)]


def _pt_box(x0_px, y0_px, x1_px, y1_px, meta):
    """Convert a pixel box to nonnegative integer page points (y-down)."""
    scale = 72.0 / meta['dpi']
    x = max(0, int(x0_px * scale))
    y = max(0, int(y0_px * scale))
    # ceil outward so the proposal never clips ink at its edges
    x1 = min(int(meta['width_pt']), max(x + 1, -(-int(x1_px * scale) // 1)))
    y1 = min(int(meta['height_pt']), max(y + 1, -(-int(y1_px * scale) // 1)))
    return [x, y, x1 - x, y1 - y]


def detect_regions(png_bytes, meta):
    """Propose ink regions for a rendered page as recorded-config detections.

    Returns a list of {'id', 'kind', 'bbox': [x, y, width, height]} dicts in
    reading order (top-to-bottom, then left-to-right). bboxes are nonnegative
    integer page points (y-down), nonzero width/height, inside the page frame.
    """
    pix = _decode(png_bytes)
    band_cells = _segments(_cell_flags(_row_ink(pix)), GAP_CELLS)
    height_px, width_px = pix.height, pix.width
    proposals = []
    for band_first, band_last in band_cells:
        first_row = min(height_px - 1, band_first * CELL_PX)
        last_row = min(height_px - 1, (band_last + 1) * CELL_PX - 1)
        column_cells = _segments(
            _cell_flags(_column_ink(pix, first_row, last_row)), GAP_CELLS)
        for col_first, col_last in column_cells:
            x0_px = col_first * CELL_PX
            y0_px = band_first * CELL_PX
            x1_px = min(width_px, (col_last + 1) * CELL_PX)
            y1_px = min(height_px, (band_last + 1) * CELL_PX)
            proposals.append(_pt_box(x0_px, y0_px, x1_px, y1_px, meta))
    proposals.sort(key=lambda box: (box[1], box[0]))
    return [{'id': f'det-{number}', 'kind': 'ink-block', 'bbox': box}
            for number, box in enumerate(proposals, 1)]
