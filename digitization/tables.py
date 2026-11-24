# Purpose: Sunset-zea table-aware geometry — detect ruled-table structure on
#   one observed page, assign word observations to exactly one cell, and
#   expose the single-ownership check as a testable, replayable property.
# Responsibilities: Extract axis-aligned ruling-line candidates from
#   content-class vector carrier observations (sunset-9rg.1 landed
#   dsc03.visual.content_classes entries: canonical ``rect_pt``); assemble
#   tables from crossing rule sets (row/column lines, cell boxes); assign
#   native word-map observations (digitization.native word-map.json entries)
#   by box center — exactly one owning cell for
#   every in-bounds assignable word, borderline/edge words typed
#   ``unknown-borderline`` and never force-assigned, out-of-table words typed
#   ``outside``; verify single ownership as a typed property
#   (holds/violated/unsupported) and export counterexample bundles under the
#   dsc03.compare convention (deterministic bundle: rule id, sha256 input
#   hashes, exact scope, versions, expected/observed, replayable flag,
#   byte-deterministic serialization, load + replay, NotReplayable when
#   redacted). Header/semantic interpretation (header rows, column meaning)
#   stays out — hypothesis-class, not declared geometry.
# Rationale: the check is an internal-ownership-check (internal consistency
#   property of this detector's own assignment), never an independent
#   verification claim. Declared frames and units: the working frame is
#   canonical page pt, origin top-left, x-right, y-down — identical to the
#   digitization.native word-map ``box`` frame at rotation 0 (word boxes are
#   integer milli-points, rescaled through the declared QUANTUM_SCALE of the
#   sanctioned substrate quantization helper). Content-class vector entries
#   carry canonical ``rect_pt`` (origin bottom-left, y-up, per
#   dsc03.visual.content_classes._canonical_rect); extract_rules converts
#   them to the working frame when the page height is declared. Words are
#   keyed by their box CENTER; a word physically overlapping two cells still
#   owns the one cell containing its center. Detection consumes observed rule
#   geometry only; every threshold is a declared constant, nothing guessed.
"""Table-aware geometry: ruled tables, cell boxes, single-ownership words."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

# Sole sanctioned substrate import (add-anchor-derived-identity Decision 4,
# same scope as digitization.native): the declared quantum of word-box
# coordinates. Word-map boxes are integer milli-points (quantize_scalar).
from dsc03.substrate.space import QUANTUM_SCALE

__all__ = [
    "BORDERLINE_BAND_PT",
    "DETECTOR_ID",
    "DETECTOR_VERSION",
    "LINE_MERGE_TOLERANCE_PT",
    "MIN_RULES_PER_AXIS",
    "OWNERSHIP_OUTCOMES",
    "NotReplayable",
    "OBSERVABLE_SCOPE",
    "RULE_BORDERLINE_FORCED",
    "RULE_DOUBLE_OWNERSHIP",
    "RULE_LENGTH_MIN_PT",
    "RULE_MISPLACED",
    "RULE_SCOPE_UNSUPPORTED",
    "RULE_SINGLE_OWNERSHIP",
    "RULE_THICKNESS_MAX_PT",
    "RULE_UNASSIGNED",
    "STATUS_ASSIGNED",
    "STATUS_BORDERLINE",
    "STATUS_OUTSIDE",
    "TableInputError",
    "TableObservation",
    "TableSpec",
    "WORD_STATUSES",
    "assign_words",
    "check_single_ownership",
    "detect_tables",
    "export_counterexample",
    "extract_rules",
    "load_bundle",
    "replay",
    "serialize_bundle",
]

KIND = "table-geometry"
VERSION = 1
DETECTOR_ID = "digitization.tables"
DETECTOR_VERSION = "1.0.0"
# Observable scope of the ownership property (declared, never inferred).
OBSERVABLE_SCOPE = ("word-cell-ownership",)

# Declared geometry policy. A rule is a thin long axis-aligned vector rect:
# at most RULE_THICKNESS_MAX_PT across and at least RULE_LENGTH_MIN_PT along.
RULE_THICKNESS_MAX_PT = 2.0
RULE_LENGTH_MIN_PT = 8.0
# Parallel rules closer than this merge into one line (double borders).
LINE_MERGE_TOLERANCE_PT = 1.0
# A table needs at least this many rules per axis (a ruled grid has a frame).
MIN_RULES_PER_AXIS = 2
# Word centers within this distance of any ruling (row or column line) are
# borderline: typed unknown, never force-assigned.
BORDERLINE_BAND_PT = 1.0

STATUS_ASSIGNED = "assigned"
STATUS_OUTSIDE = "outside"
STATUS_BORDERLINE = "unknown-borderline"
WORD_STATUSES = (STATUS_ASSIGNED, STATUS_OUTSIDE, STATUS_BORDERLINE)

# Closed outcome vocabulary of the single-ownership property check.
OWNERSHIP_OUTCOMES = ("holds", "violated", "unsupported")

# Stable rule IDs (tbl.* namespace, dsc03.compare convention).
RULE_SINGLE_OWNERSHIP = "tbl.ownership.single"
RULE_DOUBLE_OWNERSHIP = "tbl.ownership.double"
RULE_UNASSIGNED = "tbl.ownership.unassigned"
RULE_BORDERLINE_FORCED = "tbl.ownership.borderline.forced"
RULE_MISPLACED = "tbl.ownership.misplaced"
RULE_SCOPE_UNSUPPORTED = "tbl.ownership.scope.unsupported"


class TableInputError(ValueError):
    """Structurally malformed input geometry: refused, never guessed."""


@dataclass(frozen=True)
class Rule:
    """One ruling-line candidate in canonical pt (top-left y-down)."""

    axis: str  # "horizontal" | "vertical"
    position: float  # the constant coordinate (y for horizontal, x for vertical)
    start: float
    end: float


@dataclass(frozen=True)
class Cell:
    """One grid cell: row/column indices (0 = top/left) and its rect."""

    row: int
    column: int
    rect: tuple  # (x0, y0, x1, y1) canonical pt


@dataclass(frozen=True)
class TableObservation:
    """One detected ruled table: outer rect, merged row/column lines, cells."""

    rect: tuple  # (x0, y0, x1, y1) canonical pt
    row_lines: tuple  # ascending y of row rules
    col_lines: tuple  # ascending x of column rules
    cells: tuple  # row-major tuple of Cell


@dataclass(frozen=True)
class WordPlacement:
    """One word observation's ownership outcome (exactly one entry per word)."""

    index: int
    text: str | None
    box: tuple  # canonical word box as consumed
    status: str  # exactly one of WORD_STATUSES
    table_index: int | None
    cell: tuple | None  # (row, column) when assigned
    center: tuple  # (cx, cy) of the word box


@dataclass(frozen=True)
class OwnershipCheck:
    """Typed outcome of the single-ownership property check."""

    outcome: str  # exactly one of OWNERSHIP_OUTCOMES
    rule_id: str
    witness: str | None = None
    message: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OWNERSHIP_OUTCOMES:
            raise ValueError(f"invalid ownership outcome: {self.outcome!r}")


@dataclass(frozen=True)
class TableSpec:
    """Declared detector scope for counterexample export (ComparatorSpec shape)."""

    detector_id: str
    version: str
    observable_scope: tuple


class NotReplayable(Exception):
    """The exported bundle withheld input geometry (replayable=false)."""


TABLE_SPEC = TableSpec(DETECTOR_ID, DETECTOR_VERSION, OBSERVABLE_SCOPE)


# -- rule extraction ---------------------------------------------------------------

def _entry_rect(entry):
    rect = entry.get("rect_pt")
    if not (isinstance(rect, (list, tuple)) and len(rect) == 4):
        raise TableInputError(f"content-class entry without 4-number rect_pt: {entry!r}")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               for v in rect):
        raise TableInputError(f"content-class entry with non-finite rect_pt: {rect!r}")
    return [float(v) for v in rect]


def extract_rules(source, page_height_pt=None):
    """Ruling-line candidates from content-class vector observations.

    `source` is a full content-class record (``record["classes"]["vector"]["entries"]``)
    or a bare entry list. With `page_height_pt` declared, entry ``rect_pt``
    is canonical content-class orientation (origin bottom-left, y-up) and is
    converted to the working frame (origin top-left, y-down); without it,
    entries are consumed in the working frame as given. A rule is a thin long
    axis-aligned rect; everything else (diagonal paths, thick bands,
    raster/text classes) is not table structure and yields no rule —
    extraction claims rules, never classes.
    """
    if isinstance(source, dict):
        entries = source.get("classes", {}).get("vector", {}).get("entries", [])
    else:
        entries = source
    rules = []
    for entry in entries:
        x0, y0, x1, y1 = _entry_rect(entry)
        if page_height_pt is not None:
            y0, y1 = page_height_pt - y1, page_height_pt - y0
        width, height = abs(x1 - x0), abs(y1 - y0)
        if height <= RULE_THICKNESS_MAX_PT and width >= RULE_LENGTH_MIN_PT and width > height:
            rules.append(Rule("horizontal", (y0 + y1) / 2.0, min(x0, x1), max(x0, x1)))
        elif width <= RULE_THICKNESS_MAX_PT and height >= RULE_LENGTH_MIN_PT and height > width:
            rules.append(Rule("vertical", (x0 + x1) / 2.0, min(y0, y1), max(y0, y1)))
    return rules


# -- table detection ---------------------------------------------------------------

class _UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _overlaps(a_start, a_end, b_start, b_end, tolerance):
    return max(a_start, b_start) - tolerance <= min(a_end, b_end) + tolerance


def _within(value, low, high, tolerance):
    return low - tolerance <= value <= high + tolerance


def _merge_positions(positions):
    """Cluster near-duplicate parallel rules into merged line coordinates."""
    merged = []
    cluster = [positions[0]]
    for position in positions[1:]:
        if position - cluster[-1] <= LINE_MERGE_TOLERANCE_PT:
            cluster.append(position)
        else:
            merged.append(round(sum(cluster) / len(cluster), 6))
            cluster = [position]
    merged.append(round(sum(cluster) / len(cluster), 6))
    return tuple(merged)


def detect_tables(rules):
    """Tables assembled from crossing rule sets (connected components).

    Two rules join one table when they cross (perpendicular pair) or overlap
    (parallel pair); a component qualifies when it holds at least
    MIN_RULES_PER_AXIS rules on each axis. Cells are the Cartesian product of
    consecutive merged lines. Tables are sorted by (y0, x0); deterministic.
    """
    count = len(rules)
    if count == 0:
        return ()
    components = _UnionFind(count)
    for i in range(count):
        for j in range(i + 1, count):
            first, second = rules[i], rules[j]
            if first.axis == second.axis:
                joined = _overlaps(first.start, first.end, second.start, second.end,
                                   LINE_MERGE_TOLERANCE_PT)
            else:
                horizontal, vertical = (first, second) if first.axis == "horizontal" else (second, first)
                joined = (_within(vertical.position, horizontal.start, horizontal.end,
                                  LINE_MERGE_TOLERANCE_PT)
                          and _within(horizontal.position, vertical.start, vertical.end,
                                      LINE_MERGE_TOLERANCE_PT))
            if joined:
                components.union(i, j)
    groups = {}
    for i, rule in enumerate(rules):
        groups.setdefault(components.find(i), []).append(rule)
    tables = []
    for members in groups.values():
        horizontal = sorted((m for m in members if m.axis == "horizontal"),
                            key=lambda rule: rule.position)
        vertical = sorted((m for m in members if m.axis == "vertical"),
                          key=lambda rule: rule.position)
        if (len(horizontal) < MIN_RULES_PER_AXIS or len(vertical) < MIN_RULES_PER_AXIS):
            continue
        row_lines = _merge_positions([rule.position for rule in horizontal])
        col_lines = _merge_positions([rule.position for rule in vertical])
        cells = tuple(Cell(row, column,
                           (col_lines[column], row_lines[row],
                            col_lines[column + 1], row_lines[row + 1]))
                      for row in range(len(row_lines) - 1)
                      for column in range(len(col_lines) - 1))
        tables.append(TableObservation(
            rect=(col_lines[0], row_lines[0], col_lines[-1], row_lines[-1]),
            row_lines=row_lines, col_lines=col_lines, cells=cells))
    return tuple(sorted(tables, key=lambda table: (table.rect[1], table.rect[0])))


# -- word assignment ---------------------------------------------------------------

def _word_box(word):
    """Word box in working-frame pt. Word-map entries carry integer
    milli-points (the declared QUANTUM_SCALE of quantize_scalar); the rescale
    happens here, once, at consumption."""
    box = word.get("box", word.get("rect_pt"))
    if not (isinstance(box, (list, tuple)) and len(box) == 4):
        raise TableInputError(f"word observation without 4-number box: {word!r}")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               for v in box):
        raise TableInputError(f"word observation with non-finite box: {box!r}")
    return tuple(float(v) / QUANTUM_SCALE for v in box)


def _containing_tables(center, tables):
    """Tables whose bounds contain the center (smallest area first: nested
    grids resolve to the innermost table deterministically)."""
    cx, cy = center
    inside = [table for table in tables
              if table.rect[0] <= cx <= table.rect[2] and table.rect[1] <= cy <= table.rect[3]]
    inside.sort(key=lambda table: ((table.rect[2] - table.rect[0]) * (table.rect[3] - table.rect[1]),
                                   table.rect[1], table.rect[0]))
    return inside


def _rule_distance(table, center):
    """Distance from the center to the nearest ruling line of the table."""
    cx, cy = center
    return min(min(abs(cy - y) for y in table.row_lines),
               min(abs(cx - x) for x in table.col_lines))


def _cell_at(table, center):
    """The unique cell whose row/column intervals contain the center (cells
    tile the table rect, so an interior center has exactly one cell)."""
    cx, cy = center
    row = column = None
    for index in range(len(table.row_lines) - 1):
        if table.row_lines[index] <= cy <= table.row_lines[index + 1]:
            row = index
            break
    for index in range(len(table.col_lines) - 1):
        if table.col_lines[index] <= cx <= table.col_lines[index + 1]:
            column = index
            break
    return None if row is None or column is None else (row, column)


def assign_words(words, tables):
    """Assign every word to at most one cell by its box center.

    Center inside table bounds farther than BORDERLINE_BAND_PT from every
    ruling -> assigned to the one cell containing it. Center within the band
    of any ruling -> typed ``unknown-borderline`` (never force-assigned).
    Center outside every table -> ``outside``. Returns one placement per
    word, in input order.
    """
    placements = []
    for index, word in enumerate(words):
        box = _word_box(word)
        center = ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)
        containing = _containing_tables(center, tables)
        if not containing:
            placements.append(WordPlacement(index, word.get("text"), box,
                                            STATUS_OUTSIDE, None, None, center))
            continue
        table = containing[0]
        table_index = tables.index(table)
        if _rule_distance(table, center) <= BORDERLINE_BAND_PT:
            placements.append(WordPlacement(index, word.get("text"), box,
                                            STATUS_BORDERLINE, table_index, None, center))
            continue
        placements.append(WordPlacement(index, word.get("text"), box,
                                        STATUS_ASSIGNED, table_index,
                                        _cell_at(table, center), center))
    return tuple(placements)


# -- single-ownership check --------------------------------------------------------

def _check_details(expected, observed):
    return {"expected": expected, "observed": observed}


def _unsupported(witness, message):
    return OwnershipCheck("unsupported", RULE_SCOPE_UNSUPPORTED, witness, message)


def check_single_ownership(words, tables, placements=None):
    """Verify the single-ownership property (internal-ownership-check).

    For every word: at most one placement; a word whose center is inside
    table bounds farther than BORDERLINE_BAND_PT from every ruling is
    assigned to exactly one cell whose rect strictly contains the center
    (zero double-ownership, zero unassigned); a word within the band is
    typed ``unknown-borderline`` and never force-assigned; words outside
    every table are unconstrained. Malformed inputs are ``unsupported`` —
    never a pass.
    """
    if not (isinstance(words, (list, tuple)) and isinstance(tables, (list, tuple))
            and (placements is None or isinstance(placements, (list, tuple)))):
        return _unsupported("inputs", "words, tables and placements must be sequences")
    if placements is None:
        try:
            placements = assign_words(words, tables)
        except TableInputError as error:
            return _unsupported("words", str(error))
    try:
        for word in words:
            _word_box(word)
    except TableInputError as error:
        return _unsupported("words", str(error))

    # double-listing scan: a word index may appear at most once
    seen = {}
    for placement in placements:
        seen.setdefault(placement.index, []).append(placement)
    for index in sorted(seen):
        entries = seen[index]
        if len(entries) > 1:
            return OwnershipCheck(
                "violated", RULE_DOUBLE_OWNERSHIP, f"word[{index}]",
                "word observation placed more than once",
                _check_details("each word owns at most one cell",
                               {"word": index,
                                "cells": [list(entry.cell) if entry.cell is not None
                                          else None for entry in entries]}))
    if len(placements) != len(words) or any(
            not 0 <= placement.index < len(words) for placement in placements):
        return _unsupported("placements", "placements must cover each word exactly once")

    assigned = borderline = outside = 0
    for index, word in enumerate(words):
        placement = seen[index][0]
        box = _word_box(word)
        center = ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)
        containing = _containing_tables(center, tables)
        if placement.status == STATUS_ASSIGNED and not containing:
            return OwnershipCheck(
                "violated", RULE_MISPLACED, f"word[{index}]",
                "word assigned while its center is outside every table",
                _check_details("assigned words lie inside their table",
                               {"word": index, "center": center, "status": placement.status}))
        if not containing:
            outside += 1
            continue
        table = containing[0]
        distance = _rule_distance(table, center)
        if distance <= BORDERLINE_BAND_PT:
            borderline += 1
            if placement.status != STATUS_BORDERLINE:
                rule_id = RULE_BORDERLINE_FORCED if placement.status == STATUS_ASSIGNED \
                    else RULE_UNASSIGNED
                return OwnershipCheck(
                    "violated", rule_id, f"word[{index}]",
                    "borderline word must be typed unknown-borderline, not "
                    + placement.status,
                    _check_details("borderline in-bounds words are typed "
                                   "unknown-borderline",
                                   {"word": index, "text": word.get("text"),
                                    "status": placement.status,
                                    "distance_to_ruling": distance}))
            continue
        if placement.status != STATUS_ASSIGNED or placement.cell is None:
            return OwnershipCheck(
                "violated", RULE_UNASSIGNED, f"word[{index}]",
                "assignable in-bounds word left unassigned",
                _check_details("every assignable in-bounds word owns exactly one cell",
                               {"word": index, "text": word.get("text"),
                                "status": placement.status, "center": center}))
        if not (0 <= placement.table_index < len(tables)):
            return OwnershipCheck(
                "violated", RULE_MISPLACED, f"word[{index}]",
                "assignment references an unknown table",
                _check_details("assignment table index in range",
                               {"word": index, "table_index": placement.table_index}))
        assigned += 1
        table = tables[placement.table_index]
        row, column = placement.cell
        if not (0 <= row < len(table.row_lines) - 1 and 0 <= column < len(table.col_lines) - 1):
            return OwnershipCheck(
                "violated", RULE_MISPLACED, f"word[{index}]",
                "assigned cell indices outside the table grid",
                _check_details("assigned cell within the table grid",
                               {"word": index, "cell": placement.cell}))
        x0, y0, x1, y1 = table.cells[row * (len(table.col_lines) - 1) + column].rect
        if not (x0 < center[0] < x1 and y0 < center[1] < y1):
            return OwnershipCheck(
                "violated", RULE_MISPLACED, f"word[{index}]",
                "assigned cell rect does not strictly contain the word center",
                _check_details("assigned cell strictly contains the word center",
                               {"word": index, "cell": placement.cell,
                                "center": center, "cell_rect": (x0, y0, x1, y1)}))
    return OwnershipCheck(
        "holds", RULE_SINGLE_OWNERSHIP, "words",
        "every in-bounds assignable word owns exactly one cell; "
        "borderline words typed unknown; no word placed twice",
        {"expected": "single ownership", "observed": {"words": len(words),
                                                      "assigned": assigned,
                                                      "borderline": borderline,
                                                      "outside": outside}})


# -- counterexample export (dsc03.compare convention) -------------------------------

def _jsonable(payload):
    if isinstance(payload, (list, tuple)):
        return [_jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _jsonable(value) for key, value in payload.items()}
    if hasattr(payload, "__dataclass_fields__"):
        return _jsonable(asdict(payload))
    return payload


def _sha(payload) -> str:
    return hashlib.sha256(json.dumps(_jsonable(payload), sort_keys=True)
                          .encode("utf-8")).hexdigest()


def export_counterexample(check: OwnershipCheck, spec: TableSpec, words, tables,
                          placements=None, *, redact: bool = False) -> dict:
    """Deterministic counterexample bundle: rule id, sha256 input hashes,
    exact scope, versions, expected/observed and replay limitations. Supplied
    `placements` (e.g. a forged assignment that demonstrates a violation)
    travel in the bundle inputs so replay reproduces the outcome; without
    them the check's own assignment is exported. With redact=True the input
    geometry is omitted and replayable=false is recorded instead of
    fabricating a reproducible source."""
    hashes = {"words": _sha(words), "tables": _sha(tables)}
    exported_placements = None
    if not redact:
        if placements is None:
            try:
                placements = assign_words(words, tables)
            except TableInputError:
                placements = None  # malformed words: replay re-derives unsupported
        if placements is not None:
            hashes["placements"] = _sha(placements)
            exported_placements = [_jsonable(asdict(placement))
                                   for placement in placements]
    witness = {
        "rule_id": check.rule_id,
        "outcome": check.outcome,
        "detector": {"id": spec.detector_id, "version": spec.version},
        "observable_scope": list(spec.observable_scope),
        "input_hashes": hashes,
        "expected": check.details.get("expected"),
        "observed": check.details.get("observed"),
        "message": check.message,
        "replayable": not redact,
    }
    if redact:
        witness["redaction"] = {
            "omitted": ["inputs.words", "inputs.tables"],
            "limitation": "input geometry withheld; rerun requires local access "
                          "to the original observations",
        }
        witness["replay_limitations"] = ["input geometry omitted (redacted)"]
        inputs = {"words": [], "tables": []}
    else:
        inputs = {"words": _jsonable(words), "tables": _jsonable(tables)}
        if exported_placements is not None:
            inputs["placements"] = exported_placements
    return {"witness": witness, "inputs": inputs}


def serialize_bundle(bundle: dict) -> bytes:
    """Byte-deterministic serialization: sorted keys, fixed indent, no timestamps."""
    return (json.dumps(bundle, indent=1, sort_keys=True) + "\n").encode("utf-8")


def load_bundle(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def replay(bundle: dict, words=None, tables=None, placements=None) -> OwnershipCheck:
    """Re-run the ownership check from an exported bundle. Supplied inputs
    replace bundle inputs when given (placements included, when the bundle
    exported them). Raises NotReplayable for a redacted bundle
    (replayable=false)."""
    witness = bundle["witness"]
    if not witness.get("replayable", True):
        raise NotReplayable(f"bundle for {witness['rule_id']} is not replayable: "
                            + "; ".join(witness.get("replay_limitations", ["redacted"])))
    inputs = bundle.get("inputs", {})
    words = inputs.get("words", []) if words is None else words
    tables = inputs.get("tables", []) if tables is None else tables
    if placements is None:
        placements = inputs.get("placements")
    rebuilt = []
    for table in tables:
        if isinstance(table, TableObservation):
            rebuilt.append(table)
            continue
        table = dict(table)
        table["cells"] = tuple(Cell(**cell) for cell in table.get("cells", []))
        rebuilt.append(TableObservation(**table))
    if placements is not None:
        placements = [placement if isinstance(placement, WordPlacement)
                      else WordPlacement(**placement) for placement in placements]
    return check_single_ownership(words, rebuilt, placements)
