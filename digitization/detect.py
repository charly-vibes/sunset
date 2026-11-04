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
#   (ceil outward on conversion) so crops never clip proposed ink. Full-width
#   rules (masthead bars, separators) cut bands so they cannot bridge column
#   gaps. KNOWN LIMITATION (recorded 2026-11-03, Diario p.2 scan): vertical
#   fold/crease shadows pollute true gutters with hundreds of ink rows, so
#   projection cannot split multi-column bodies there — distinguishing text
#   ink from crease/stain ink is content-class territory (sunset-pkj), not a
#   threshold tweak.
#   (ceil outward on conversion) so crops never clip proposed ink.
"""Deterministic image-based region proposals (no OCR prerequisite)."""
import pymupdf

INK_LEVEL = 128   # grayscale at or below this counts as ink
CELL_PX = 8       # coarse analysis grid, pixels
GAP_CELLS = 2     # ink-free cells bridged when merging columns
MIN_COLUMN_PX = 24  # presence runs narrower than this are scan dirt
                    # (fold/shadow creases), not columns
COLUMN_NOISE_FRACTION = 0.04  # pixel columns with ink in fewer than this
                              # share of the band's rows are gutter dirt
                              # (measured: Diario gutters <= 0.03, text
                              # columns >= 0.07), not text columns
RULE_FRACTION = 0.5   # row ink share at or above this, with a small max
                      # gap, is a full-width separator rule
RULE_MAX_GAP = 0.12   # rules are contiguous: longest ink-free run <= this
                      # share of the width (wide two-column text rows have a
                      # big central gutter and must not count as rules)


def _decode(png_bytes):
    """Decode the rendered PNG at its native pixels.

    The direct Pixmap decode is load-bearing: routing the PNG through an
    image-PDF page honors the PNG's pHYs dpi metadata and re-renders at
    72dpi (observed 2280x3147 -> 821x1133), which erases light-scan text
    into antialiasing gray and desynchronizes the px->pt conversion from
    the declared render dpi.
    """
    import io
    pix = pymupdf.Pixmap(io.BytesIO(png_bytes))
    if pix.alpha:  # drop any alpha channel: ink checks use raw channels
        pix = pymupdf.Pixmap(pix, 0)
    return pix


def _row_ink(pix):
    """Boolean per-pixel-row list: True when the row contains any ink."""
    return [any(v <= INK_LEVEL for v in row) for row in _row_values(pix)]


def _row_values(pix):
    """Per-row iterables of the minimum channel value per pixel."""
    width, n, samples = pix.width, pix.n, pix.samples
    stride = width * n
    for base in range(0, len(samples), stride):
        yield (min(samples[off:off + n]) for off in range(base, base + stride, n))


def _rule_rows(pix):
    """Boolean per-pixel-row list: True for full-width separator rules.

    A rule is a mostly-ink row whose ink is contiguous (longest ink-free
    run well under the width). Rows of wide multi-column text can reach
    high ink fractions but keep a large central gutter, so the max-gap
    test keeps them out; rules span column gaps and would bridge them.
    """
    flags = []
    for row in _row_values(pix):
        ink = [v <= INK_LEVEL for v in row]
        fraction = sum(ink) / pix.width
        longest_gap, run = 0, 0
        for is_ink in ink:
            run = 0 if is_ink else run + 1
            longest_gap = max(longest_gap, run)
        flags.append(fraction >= RULE_FRACTION
                     and longest_gap <= RULE_MAX_GAP * pix.width)
    return flags


def _ink_bands(pix):
    """(first_row, last_row) ink bands, cut hard at rule rows.

    Rules are separators: a band never contains one, and blank runs longer
    than GAP_CELLS cells also close a band.
    """
    ink, rules = _row_ink(pix), _rule_rows(pix)
    tolerance = GAP_CELLS * CELL_PX
    bands, state = [], {'start': None, 'blank': 0}

    def close(end_row):
        if state['start'] is not None:
            bands.append((state['start'], end_row))
        state['start'], state['blank'] = None, 0

    for y in range(pix.height):
        if rules[y]:
            close(y - 1)
        elif ink[y]:
            if state['start'] is None:
                state['start'] = y
            state['blank'] = 0
        elif state['start'] is not None:
            state['blank'] += 1
            if state['blank'] > tolerance:
                close(y - state['blank'])
    close(pix.height - 1 - state['blank'])
    return bands


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


def _column_counts(pix, first_row, last_row):
    """Ink row count per pixel column over the given row range."""
    width, n, samples = pix.width, pix.n, pix.samples
    stride = width * n
    counts = [0] * width
    for row in range(first_row, last_row + 1):
        base = row * stride
        for c in range(width):
            if min(samples[base + c * n: base + c * n + n]) <= INK_LEVEL:
                counts[c] += 1
    return counts


def _column_cells(pix, first_row, last_row):
    """Column presence cells after noise-floor and thin-crease rejection.

    Scan gutters carry low-level dirt (fold shadows, speckle) in almost
    every pixel column, so any-row presence merges across them; the noise
    floor requires ink in a real share of the band's rows. Solid thin
    creases that clear the floor are removed by the thin-run drop.
    """
    rows = last_row - first_row + 1
    floor = max(3, int(rows * COLUMN_NOISE_FRACTION))
    present = [count >= floor for count in _column_counts(pix, first_row, last_row)]
    return _drop_thin_runs(_cell_flags(present), max(1, MIN_COLUMN_PX // CELL_PX))


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


def _thin_runs(cells, min_cells):
    """(start, end) runs of present cells shorter than min_cells."""
    runs, start = [], None
    for i, present in enumerate(list(cells) + [False]):
        if present and start is None:
            start = i
        elif not present and start is not None:
            runs.append((start, i))
            start = None
    return [(a, b) for a, b in runs if b - a < min_cells]


def _drop_thin_runs(cells, min_cells):
    """Presence cells with runs shorter than min_cells are scan dirt.

    Fold/shadow creases are thin vertical structures (1-4px) with plenty of
    ink rows; real columns are wide (hundreds of px). Dropping thin presence
    runs keeps creases from extending or bridging regions across gutters.
    """
    cleaned = list(cells)
    for a, b in _thin_runs(cells, min_cells):
        for j in range(a, b):
            cleaned[j] = False
    return cleaned


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
    height_px, width_px = pix.height, pix.width
    proposals = []
    for first_row, last_row in _ink_bands(pix):
        column_cells = _segments(_column_cells(pix, first_row, last_row), GAP_CELLS)
        for col_first, col_last in column_cells:
            x0_px = col_first * CELL_PX
            y0_px = first_row
            x1_px = min(width_px, (col_last + 1) * CELL_PX)
            y1_px = min(height_px, last_row + 1)
            proposals.append(_pt_box(x0_px, y0_px, x1_px, y1_px, meta))
    proposals.sort(key=lambda box: (box[1], box[0]))
    return [{'id': f'det-{number}', 'kind': 'ink-block', 'bbox': box}
            for number, box in enumerate(proposals, 1)]
