"""Contract tests for sunset-zea table-aware geometry (single-ownership
word assignment) in digitization.tables.

digitization.tables detects ruled-table structure on one page from
content-class observations (sunset-9rg.1 landed dsc03.visual.content_classes:
vector carrier entries with canonical ``rect_pt``), derives row/column lines
and cell boxes, and assigns word observations to exactly one cell:

- every word whose box center lies inside table bounds and farther than the
  declared borderline band from every ruling is assigned to exactly one cell
  (zero double-ownership, zero unassigned),
- borderline/edge words (center on or within the band of any ruling) are
  typed ``unknown-borderline`` — never force-assigned,
- words outside every table are typed ``outside``,
- the single-ownership check is exposed as a replayable property with the
  dsc03.compare counterexample export convention (deterministic bundle:
  rule id, sha256 input hashes, exact scope, versions, expected/observed,
  byte-deterministic serialization, load + replay, NotReplayable when
  redacted).

Declared frames and units: the module's working frame is canonical page pt,
origin top-left, x-right, y-down — identical to the digitization.native
word-map ``box`` frame at rotation 0, whose values are integer milli-points
(rescaled through the declared QUANTUM_SCALE of
dsc03.substrate.space.quantize_scalar). Content-class vector entries carry
canonical ``rect_pt`` (origin bottom-left, y-up, per content_classes'
_canonical_rect); the test feeds authentic rect_pt and the module converts
them via its declared page_height_pt parameter.

Fixture provenance (committed bytes, never rebuilt by tests):
fixtures/visual/table-page.pdf — pymupdf 1.28.2-built page (8 hairline
stroked rules forming a 3x3 grid at hand-declared coordinates, 9 single-token
cell words auto-centered in their cells, 1 seeded borderline word "straddle"
whose quantized word-box center lands exactly on interior row rule
y=150-from-top). All results below are internal-ownership-check results
(internal consistency property, NOT independent verification).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import pymupdf

from dsc03.substrate.space import QUANTUM_SCALE, quantize_scalar

from digitization.tables import (
    BORDERLINE_BAND_PT,
    DETECTOR_ID,
    DETECTOR_VERSION,
    OWNERSHIP_OUTCOMES,
    NotReplayable,
    RULE_BORDERLINE_FORCED,
    RULE_DOUBLE_OWNERSHIP,
    RULE_MISPLACED,
    RULE_SCOPE_UNSUPPORTED,
    RULE_SINGLE_OWNERSHIP,
    RULE_UNASSIGNED,
    STATUS_ASSIGNED,
    STATUS_BORDERLINE,
    STATUS_OUTSIDE,
    TableSpec,
    assign_words,
    check_single_ownership,
    detect_tables,
    export_counterexample,
    extract_rules,
    load_bundle,
    replay,
    serialize_bundle,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "fixtures" / "visual" / "table-page.pdf"
PAGE_HEIGHT = 792.0

# Hand-declared table geometry in the module's working frame (page pt,
# top-left y-down — the fixture page is drawn at exactly these coordinates).
ROW_LINES = (100.0, 150.0, 200.0, 250.0)
COL_LINES = (100.0, 200.0, 300.0, 400.0)
TABLE_RECT = (COL_LINES[0], ROW_LINES[0], COL_LINES[-1], ROW_LINES[-1])
RULE_PDF_RECTS = [  # pinned get_drawings rects (PDF space, top-left y-down)
    (100.0, 100.0, 400.0, 100.0), (100.0, 150.0, 400.0, 150.0),
    (100.0, 200.0, 400.0, 200.0), (100.0, 250.0, 400.0, 250.0),
    (100.0, 100.0, 100.0, 250.0), (200.0, 100.0, 200.0, 250.0),
    (300.0, 100.0, 300.0, 250.0), (400.0, 100.0, 400.0, 250.0),
]

# Pinned raw word boxes from the committed fixture (PDF space; measured once
# at build time with pymupdf 1.28.2, re-extracted and compared exactly here).
RAW_BOXES = {
    "alpha": (137.77000427246094, 118.1300048828125, 162.22999572753906, 131.87001037597656),
    "bravo": (237.4949951171875, 118.1300048828125, 262.5050048828125, 131.87001037597656),
    "charlie": (335.2750244140625, 118.1300048828125, 364.7250061035156, 131.87001037597656),
    "delta": (139.16000366210938, 168.1300048828125, 160.83999633789062, 181.87001037597656),
    "echo": (239.16000366210938, 168.1300048828125, 260.8399963378906, 181.87001037597656),
    "foxtrot": (336.1050109863281, 168.1300048828125, 363.8949890136719, 181.87001037597656),
    "golf": (141.94000244140625, 218.1300048828125, 158.05999755859375, 231.87001037597656),
    "hotel": (239.16000366210938, 218.1300048828125, 260.8399963378906, 231.87001037597656),
    "india": (339.44000244140625, 218.1300048828125, 360.55999755859375, 231.87001037597656),
    "straddle": (132.21499633789062, 143.1300048828125, 167.7849884033203, 156.87001037597656),
}
# Declared order of word observations fed to the module (reading order).
WORD_ORDER = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
              "golf", "hotel", "india", "straddle"]
EXPECTED_CELLS = {
    "alpha": (0, 0), "bravo": (0, 1), "charlie": (0, 2),
    "delta": (1, 0), "echo": (1, 1), "foxtrot": (1, 2),
    "golf": (2, 0), "hotel": (2, 1), "india": (2, 2),
}
BORDERLINE_WORD = "straddle"


def _canonical(bbox):
    """PDF-space bbox -> authentic content-class rect_pt (bottom-left y-up,
    exactly content_classes._canonical_rect: [x0, H - y1, x1, H - y0])."""
    x0, y0, x1, y1 = bbox
    return [x0, PAGE_HEIGHT - y1, x1, PAGE_HEIGHT - y0]


def _vector_entries(rects):
    """Content-class-shaped vector entries (class/page/frame/rect_pt/draw_type)."""
    return [{"class": "vector", "page": 1, "source_sha256": "fixture",
             "frame": "page-1", "rect_pt": list(rect),
             "draw_type": "stroke", "items": 1}
            for rect in rects]


def _word_entry(text, box):
    """Native word-map-shaped entry (digitization.native word-map.json):
    ``box`` as produced at rotation 0 — quantized integer milli-points in
    page space (top-left y-down), no flip."""
    return {"source_sha256": "fixture", "page": 1, "frame": "page-1-pt",
            "text": text, "source_box": list(box), "box":
            [quantize_scalar(value) for value in box]}


def _fixture_words():
    return [_word_entry(text, RAW_BOXES[text]) for text in WORD_ORDER]


def _fixture_record():
    """Content-class-shaped record for the committed fixture page with
    authentic canonical rect_pt (bottom-left y-up, per content_classes'
    _canonical_rect over pymupdf drawing rects)."""
    doc = pymupdf.open(str(FIXTURE))
    page = doc[0]
    rects = [tuple(item["rect"]) for item in page.get_drawings()]
    entries = _vector_entries([_canonical(rect) for rect in rects])
    return {"classes": {"vector": {"role": "carrier-observation",
                                   "entries": entries}}}


def _fixture_tables():
    return detect_tables(extract_rules(_fixture_record(), page_height_pt=PAGE_HEIGHT))


def _synthetic_table(x0=100.0, y0=100.0, x1=300.0, y1=200.0, rows=2, cols=2):
    """A synthetic ruled grid: rule entries only, no PDF needed."""
    row_step, col_step = (y1 - y0) / rows, (x1 - x0) / cols
    rects = [(x0, y0 + i * row_step, x1, y0 + i * row_step) for i in range(rows + 1)]
    rects += [(x0 + j * col_step, y0, x0 + j * col_step, y1) for j in range(cols + 1)]
    return detect_tables(extract_rules(_vector_entries(rects)))


def _word(x0, y0, x1, y1, text="w"):
    return _word_entry(text, (x0, y0, x1, y1))


# -- table/cell detection ----------------------------------------------------------

def test_fixture_table_structure_detected():
    tables = _fixture_tables()
    assert len(tables) == 1
    table = tables[0]
    assert table.rect == TABLE_RECT
    assert table.row_lines == ROW_LINES
    assert table.col_lines == COL_LINES


def test_fixture_cells_are_the_declared_grid():
    cells = _fixture_tables()[0].cells
    assert len(cells) == 9
    for cell in cells:
        row, column = cell.row, cell.column
        assert cell.rect == (COL_LINES[column], ROW_LINES[row],
                             COL_LINES[column + 1], ROW_LINES[row + 1])
    assert sorted((c.row, c.column) for c in cells) == [
        (r, c) for r in range(3) for c in range(3)]


def test_fixture_integrity_rules_and_words_pinned():
    """Committed bytes still carry the declared rulings and pinned words
    (fixture tamper guard + extractor pin)."""
    doc = pymupdf.open(str(FIXTURE))
    page = doc[0]
    rects = [tuple(item["rect"]) for item in page.get_drawings()]
    assert rects == RULE_PDF_RECTS
    extracted = {w[4]: tuple(w[:4]) for w in page.get_text("words")}
    assert extracted == RAW_BOXES


# -- single ownership on the fixture ----------------------------------------------

def test_fixture_single_ownership_green_with_borderline_unknown():
    tables = _fixture_tables()
    placements = assign_words(_fixture_words(), tables)
    by_text = {p.text: p for p in placements}
    assert len(placements) == len(WORD_ORDER)
    for text, expected in EXPECTED_CELLS.items():
        placement = by_text[text]
        assert placement.status == STATUS_ASSIGNED, text
        assert placement.cell == expected, text
        assert placement.table_index == 0
    borderline = by_text[BORDERLINE_WORD]
    assert borderline.status == STATUS_BORDERLINE
    assert borderline.cell is None
    check = check_single_ownership(_fixture_words(), tables)
    assert check.outcome == "holds"
    assert check.rule_id == RULE_SINGLE_OWNERSHIP
    observed = check.details["observed"]
    assert observed["assigned"] == 9 and observed["borderline"] == 1


def test_borderline_word_center_lands_on_the_interior_rule():
    box = _word_entry(BORDERLINE_WORD, RAW_BOXES[BORDERLINE_WORD])["box"]
    center_y = (box[1] + box[3]) / 2.0 / QUANTUM_SCALE
    assert center_y == 150.0  # quantized milli-point center: exactly the rule
    assert abs(center_y - ROW_LINES[1]) <= BORDERLINE_BAND_PT


def test_borderline_word_is_in_no_cell_and_forcing_is_a_violation():
    tables = _fixture_tables()
    words = _fixture_words()
    placements = assign_words(words, tables)
    forced = [p if p.text != BORDERLINE_WORD
              else type(p)(index=p.index, text=p.text, box=p.box,
                           status=STATUS_ASSIGNED, table_index=0,
                           cell=(1, 0), center=p.center)
              for p in placements]
    check = check_single_ownership(words, tables, forced)
    assert check.outcome == "violated"
    assert check.rule_id == RULE_BORDERLINE_FORCED
    assert check.witness is not None and BORDERLINE_WORD in json.dumps(check.details)


# -- declared borderline/edge typing ----------------------------------------------

def test_center_exactly_on_interior_ruling_typed_unknown():
    tables = _synthetic_table()
    word = _word(190.0, 130.0, 210.0, 160.0)  # center exactly on x=200 rule
    placement = assign_words([word], tables)[0]
    assert placement.status == STATUS_BORDERLINE
    assert placement.cell is None


def test_center_on_outer_edge_typed_unknown():
    tables = _synthetic_table()
    word = _word(140.0, 95.0, 160.0, 105.0)  # center exactly on outer y=100
    placement = assign_words([word], tables)[0]
    assert placement.status == STATUS_BORDERLINE


def test_band_boundary_exactly_at_band_is_unknown_beyond_is_assigned():
    tables = _synthetic_table()
    at_band = _word(96.0, 120.0, 106.0, 140.0)      # center x=101 -> |101-100| = 1.0
    beyond = _word(96.5, 120.0, 107.5, 140.0)       # center x=102 -> 2.0 from rule
    assert assign_words([at_band], tables)[0].status == STATUS_BORDERLINE
    assigned = assign_words([beyond], tables)[0]
    assert assigned.status == STATUS_ASSIGNED
    assert assigned.cell == (0, 0)


def test_word_outside_every_table_typed_outside():
    tables = _synthetic_table()
    word = _word(400.0, 400.0, 420.0, 420.0)
    placement = assign_words([word], tables)[0]
    assert placement.status == STATUS_OUTSIDE
    assert placement.cell is None
    assert check_single_ownership([word], tables).outcome == "holds"


# -- detection scope ---------------------------------------------------------------

def test_two_disjoint_tables_detected_and_words_assigned_to_each():
    rects = ([100.0, 100.0, 200.0, 100.0], [100.0, 200.0, 200.0, 200.0],
             [100.0, 100.0, 100.0, 200.0], [200.0, 100.0, 200.0, 200.0],
             [400.0, 400.0, 500.0, 400.0], [400.0, 450.0, 500.0, 450.0],
             [400.0, 400.0, 400.0, 450.0], [500.0, 400.0, 500.0, 450.0])
    tables = detect_tables(extract_rules(_vector_entries(rects)))
    assert [t.rect for t in tables] == [(100.0, 100.0, 200.0, 200.0),
                                        (400.0, 400.0, 500.0, 450.0)]
    placements = assign_words([_word(130.0, 130.0, 150.0, 150.0, "left"),
                               _word(430.0, 410.0, 450.0, 430.0, "right")], tables)
    assert [p.cell for p in placements] == [(0, 0), (0, 0)]
    assert [p.table_index for p in placements] == [0, 1]
    assert check_single_ownership(
        [_word(130.0, 130.0, 150.0, 150.0, "left"),
         _word(430.0, 410.0, 450.0, 430.0, "right")], tables).outcome == "holds"


def test_parallel_rules_only_detect_no_table():
    rules = extract_rules(_vector_entries([(100.0, 100.0, 300.0, 100.0),
                                           (100.0, 200.0, 300.0, 200.0)]))
    assert detect_tables(rules) == ()


# -- ownership check violation coverage (forged placements) -----------------------

def _first_cell_word():
    # center (150, 175): strictly inside cell (1,0) of the default grid,
    # 25 pt from every ruling — comfortably beyond the borderline band.
    return _word(130.0, 165.0, 170.0, 185.0, "interior")


def test_double_ownership_violation():
    tables = _synthetic_table()
    words = [_first_cell_word()]
    placement = assign_words(words, tables)[0]
    assert placement.cell == (1, 0)
    doubled = [placement, placement]
    check = check_single_ownership(words, tables, doubled)
    assert check.outcome == "violated"
    assert check.rule_id == RULE_DOUBLE_OWNERSHIP
    assert check.details["observed"]["cells"] == [[1, 0], [1, 0]]


def test_unassigned_interior_word_violation():
    tables = _synthetic_table()
    words = [_first_cell_word()]
    placement = assign_words(words, tables)[0]
    mistyped = [type(placement)(**{**placement.__dict__, "status": STATUS_OUTSIDE,
                                   "cell": None, "table_index": None})]
    check = check_single_ownership(words, tables, mistyped)
    assert check.outcome == "violated"
    assert check.rule_id == RULE_UNASSIGNED


def test_misplaced_assignment_violation():
    tables = _synthetic_table()
    words = [_first_cell_word()]
    placement = assign_words(words, tables)[0]
    wrong_cell = (0, 1) if placement.cell == (1, 0) else (1, 0)
    misplaced = [type(placement)(**{**placement.__dict__, "cell": wrong_cell})]
    check = check_single_ownership(words, tables, misplaced)
    assert check.outcome == "violated"
    assert check.rule_id == RULE_MISPLACED


def test_malformed_word_box_is_unsupported():
    tables = _synthetic_table()
    check = check_single_ownership([{"text": "bad", "box": [1.0, 2.0]}], tables)
    assert check.outcome == "unsupported"
    assert check.rule_id == RULE_SCOPE_UNSUPPORTED


# -- counterexample export convention (per dsc03/compare.py) ----------------------

def test_outcome_vocabulary_is_closed():
    assert OWNERSHIP_OUTCOMES == ("holds", "violated", "unsupported")


def test_counterexample_export_replay_holds_byte_deterministic():
    spec = TableSpec(DETECTOR_ID, DETECTOR_VERSION, ("word-cell-ownership",))
    words, tables = _fixture_words(), _fixture_tables()
    check = check_single_ownership(words, tables)
    bundle = export_counterexample(check, spec, words, tables)
    witness = bundle["witness"]
    assert witness["rule_id"] == RULE_SINGLE_OWNERSHIP
    assert witness["detector"] == {"id": DETECTOR_ID, "version": DETECTOR_VERSION}
    assert witness["observable_scope"] == ["word-cell-ownership"]
    assert witness["replayable"] is True
    assert set(witness["input_hashes"]) == {"words", "tables", "placements"}
    assert all(len(h) == 64 for h in witness["input_hashes"].values())
    first, second = serialize_bundle(bundle), serialize_bundle(bundle)
    assert first == second
    replayed = replay(load_bundle(first), words, tables)
    assert replayed.outcome == "holds"
    assert replayed.rule_id == RULE_SINGLE_OWNERSHIP
    from_bundle = replay(load_bundle(first))
    assert from_bundle.outcome == "holds"


def test_counterexample_export_replay_violation():
    spec = TableSpec(DETECTOR_ID, DETECTOR_VERSION, ("word-cell-ownership",))
    tables = _synthetic_table()
    words = [_first_cell_word()]
    placement = assign_words(words, tables)[0]
    check = check_single_ownership(words, tables, [placement, placement])
    bundle = export_counterexample(check, spec, words, tables, [placement, placement])
    assert bundle["witness"]["outcome"] == "violated"
    assert bundle["witness"]["expected"] is not None
    assert bundle["witness"]["observed"] is not None
    replayed = replay(load_bundle(serialize_bundle(bundle)), words, tables)
    assert replayed.outcome == "violated"
    assert replayed.rule_id == RULE_DOUBLE_OWNERSHIP


def test_redacted_bundle_is_not_replayable():
    spec = TableSpec(DETECTOR_ID, DETECTOR_VERSION, ("word-cell-ownership",))
    words, tables = _fixture_words(), _fixture_tables()
    check = check_single_ownership(words, tables)
    bundle = export_counterexample(check, spec, words, tables, redact=True)
    assert bundle["witness"]["replayable"] is False
    assert bundle["witness"]["redaction"]["omitted"] == ["inputs.words", "inputs.tables"]
    assert bundle["inputs"] == {"words": [], "tables": []}
    with pytest.raises(NotReplayable):
        replay(load_bundle(serialize_bundle(bundle)))


# -- package hygiene ---------------------------------------------------------------

def test_module_imports_without_pymupdf():
    code = ("import digitization.tables, sys; "
            "assert not [m for m in sys.modules if m == 'pymupdf' or m.startswith('pymupdf.')], "
            "'digitization.tables must not import pymupdf'")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=str(REPO))
