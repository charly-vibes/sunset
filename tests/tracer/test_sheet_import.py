"""Contract tests for the attributed human-sheet import core (sunset-905.3).

Purpose: Pin dsc03.visual.sheet_import against the document-adapters
  "Attributed human region import" requirement using the real committed
  HITL corpus and real carrier fixtures — no synthetic sheets except where
  a refusal path must be induced deliberately.
Responsibilities: Assert the seven pinned behaviors — total accounting
  (regions + refusals == input structure count, zero silent drops),
  sheet-scoped local ids, typed source-digest-mismatch on a tampered
  carrier, retained blank type provenance, hand-computed bbox_px through
  the recorded page frame, typed invalid-box on degenerate geometry, and
  typed missing-frame — plus the typed frame-binding-refused path.
Rationale: the import is the accepted human geometry corpus's entry into
  DSC 0.3; every refusal reason and provenance flag here is contract, not
  implementation detail (shared API contract, 2026-11 milestone).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from dsc03.visual.sheet_import import (
    REFUSAL_REASONS,
    ImportRefusal,
    SheetImportResult,
    import_sheets,
)

REPO = Path(__file__).resolve().parents[2]
SHEETS = REPO / "hitl" / "sunset-905.3"
ALL_SHEETS = sorted(SHEETS.glob("*.observations.json"))
BANK_SHEET = SHEETS / "bank-statement-ca-excerpt-a.observations.json"
DIARIO_SHEET = SHEETS / "diario-de-poesia-excerpt.observations.json"

# Pinned in hitl/sunset-905.3/bundle/SHA256SUMS.txt; fixtures/carriers matches.
CARRIER_DIGESTS = {
    "agentic-patterns-excerpt": "3b2425e5faeb373b3e46984d194bb26d2a0b8fc10c9ba1a49bcfec730e273c66",
    "bank-statement-ca-excerpt": "18ce0c49df1ad61bdc638abb1b4cb9185987acda4c6333cc3fb5b10facdc29a2",
    "diario-de-poesia-excerpt": "42292cc690f4c10f88f8b9768eb491e7accb31704c897d47769ea54758093ad4",
}

# The shared API contract's exact region dict keys.
REGION_KEYS = {
    "sheet_id",
    "region_id",
    "reader",
    "page",
    "bbox_px",
    "bbox_relative",
    "viewport_w",
    "viewport_h",
    "carrier_sha256",
    "type",
    "type_provenance",
    "order_rank",
    "order_alternatives",
    "evidence",
}


def _mutated_sheet(tmp_path, mutate, name="mutated.observations.json"):
    """A copy of the real one-region bank sheet with a deliberate defect."""
    sheet = json.loads(BANK_SHEET.read_text())
    mutate(sheet)
    path = tmp_path / name
    path.write_text(json.dumps(sheet))
    return path


def test_total_accounting_preserves_or_refuses_every_input_region():
    """Regions + refusals == input structure count, per sheet and overall."""
    result = import_sheets(ALL_SHEETS, source_root=SHEETS)
    assert isinstance(result, SheetImportResult)
    expected = 0
    carrier_of = {}
    for path in ALL_SHEETS:
        raw = json.loads(path.read_text())
        expected += len(raw["structure"])
        carrier_of[path.name[: -len(".observations.json")]] = raw["carrier"]
    # Spec scenario "Preserve the accepted human geometry corpus": the six
    # owner-accepted sheets hold 203 regions, and all import clean.
    assert expected == 203
    assert len(result.regions) + len(result.refusals) == expected
    assert len(result.regions) == expected
    ids = [r["region_id"] for r in result.regions]
    assert len(set(ids)) == len(ids), "region ids must be unique within the corpus"
    assert len(result.sheets) == len(ALL_SHEETS)
    assert {s["sheet_id"] for s in result.sheets} == {
        p.name[: -len(".observations.json")] for p in ALL_SHEETS
    }
    for region in result.regions:
        assert set(region) == REGION_KEYS
        assert region["carrier_sha256"] == CARRIER_DIGESTS[carrier_of[region["sheet_id"]]]
    for refusal in result.refusals:
        assert isinstance(refusal, ImportRefusal)
        assert refusal.reason in REFUSAL_REASONS
    # Pinned provenance: sheet digests come from the bundle SHA256SUMS.
    for sheet in result.sheets:
        assert sheet["source_sha256"] == CARRIER_DIGESTS[sheet["carrier"]]
    # Derived order is retained WITH its provenance flag, never as judgment.
    bank = next(s for s in result.sheets if s["sheet_id"] == "bank-statement-ca-excerpt-a")
    assert bank["prefill_provenance"] == {"order_ranks": "derived_from_arrangement"}
    bank_region = next(r for r in result.regions if r["sheet_id"] == "bank-statement-ca-excerpt-a")
    assert bank_region["order_rank"] == "1"
    assert bank_region["order_alternatives"] == []
    # Sheets without prefill keep None ranks verbatim.
    diario = next(r for r in result.regions if r["sheet_id"] == "diario-de-poesia-excerpt")
    assert diario["order_rank"] is None


def test_local_region_ids_are_scoped_to_the_originating_sheet():
    """Same-carrier sheets from different readers keep distinct local ids."""
    a = import_sheets([BANK_SHEET], source_root=SHEETS)
    b = import_sheets([SHEETS / "bank-statement-ca-excerpt-b.observations.json"], source_root=SHEETS)
    assert [r["region_id"] for r in a.regions] == ["bank-statement-ca-excerpt-a:1"]
    assert [r["region_id"] for r in b.regions] == [
        "bank-statement-ca-excerpt-b:1",
        "bank-statement-ca-excerpt-b:2",
        "bank-statement-ca-excerpt-b:3",
    ]
    assert {r["region_id"] for r in a.regions}.isdisjoint(r["region_id"] for r in b.regions)
    assert all(r["sheet_id"] == "bank-statement-ca-excerpt-a" for r in a.regions)
    assert all(r["reader"] == "reader-a" for r in a.regions)
    assert all(r["reader"] == "reader-b" for r in b.regions)


def test_tampered_carrier_file_yields_typed_source_digest_mismatch(tmp_path):
    """A carrier that no longer digests to the sheet's pinned sha is refused."""
    (tmp_path / "bundle" / "carriers").mkdir(parents=True)
    shutil.copy(BANK_SHEET, tmp_path / BANK_SHEET.name)
    shutil.copy(SHEETS / "bundle" / "SHA256SUMS.txt", tmp_path / "bundle" / "SHA256SUMS.txt")
    carrier = tmp_path / "bundle" / "carriers" / "bank-statement-ca-excerpt.pdf"
    shutil.copyfile(REPO / "fixtures" / "carriers" / "bank-statement-ca-excerpt.pdf", carrier)

    # Sanity: the pristine temp layout imports clean through the same path.
    clean = import_sheets([tmp_path / BANK_SHEET.name], source_root=tmp_path)
    assert clean.refusals == []
    assert len(clean.regions) == 1

    carrier.write_bytes(carrier.read_bytes() + b"tampered-after-the-fact")
    result = import_sheets([tmp_path / BANK_SHEET.name], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1  # total accounting still holds
    refusal = result.refusals[0]
    assert refusal.reason == "source-digest-mismatch"
    assert refusal.region_key == "bank-statement-ca-excerpt-a:1"
    assert CARRIER_DIGESTS["bank-statement-ca-excerpt"] in refusal.detail
    assert (
        hashlib.sha256(carrier.read_bytes()).hexdigest() in refusal.detail
    ), "detail must name the actual digest that failed the pin"


def test_blank_type_is_retained_with_its_provenance(tmp_path):
    """An empty type is an accounted region flagged blank, never a drop."""
    result = import_sheets([BANK_SHEET], source_root=SHEETS)
    region = result.regions[0]
    assert region["type"] == ""
    assert region["type_provenance"] == "blank"

    # A machine-prefilled non-blank type stays machine-inferred.
    def machine_types(sheet):
        sheet["prefill_provenance"] = {"types": "derived_from_arrangement"}
        sheet["structure"][0]["type"] = "text"

    path = _mutated_sheet(tmp_path, machine_types, name="machine.observations.json")
    result = import_sheets([path], source_root=tmp_path)
    assert result.refusals == []
    assert result.regions[0]["type_provenance"] == "machine-inferred"

    # The committed diario sheet types are human entries (no prefill marker).
    diario = import_sheets([DIARIO_SHEET], source_root=SHEETS)
    assert diario.refusals == []
    assert all(r["type_provenance"] == "human" for r in diario.regions)
    assert {r["type"] for r in diario.regions} == {"text", "image", "heading", "title", "header", "footer"}


def test_bbox_px_matches_the_hand_computed_frame_transform():
    """bank page 1: full-bleed frame, CropBox 612x792pt, viewport 966x1250px.

    Hand computation through the declared frame: scale (966/612, 1250/792)
    px per pt, crop none, canonical y-flip by h0=1250 — the box top-left pt
    (x*612, (1-y)*792) maps to (x*966, y*1250), bottom-right likewise, so
    bbox_px is the fraction-times-viewport rectangle:
    """
    result = import_sheets([BANK_SHEET], source_root=SHEETS)
    region = result.regions[0]
    assert (region["viewport_w"], region["viewport_h"]) == (966, 1250)
    sheet_bbox = json.loads(BANK_SHEET.read_text())["structure"][0]["bbox"]
    assert region["bbox_relative"] == sheet_bbox, "original geometry retained as provenance"
    expected = {
        "x": sheet_bbox["x"] * 966,       # 0.0933 * 966  = 90.1278
        "y": sheet_bbox["y"] * 1250,      # 0.0698 * 1250 = 87.25
        "w": sheet_bbox["w"] * 966,       # 0.2888 * 966  = 278.9808
        "h": sheet_bbox["h"] * 1250,      # 0.0672 * 1250 = 84.0
    }
    assert region["bbox_px"] == pytest.approx(expected, rel=1e-12)
    assert region["bbox_px"]["x"] == pytest.approx(90.1278, rel=1e-12)
    assert region["bbox_px"]["y"] == pytest.approx(87.25, rel=1e-12)
    assert region["bbox_px"]["w"] == pytest.approx(278.9808, rel=1e-12)
    assert region["bbox_px"]["h"] == pytest.approx(84.0, rel=1e-12)


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda s: s["structure"][0]["bbox"].__setitem__("w", 0), "zero-area"),
        (lambda s: s["structure"][0]["bbox"].__setitem__("h", 0), "zero-area"),
        (lambda s: s["structure"][0]["bbox"].__setitem__("x", -0.1), "negative"),
        (lambda s: s["structure"][0]["bbox"].__setitem__("y", float("nan")), "finite"),
        (lambda s: s["structure"][0]["bbox"].__setitem__("w", 1.5), "viewport"),
    ],
)
def test_degenerate_box_yields_typed_invalid_box_refusal(tmp_path, mutate, fragment):
    path = _mutated_sheet(tmp_path, mutate)
    result = import_sheets([path], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.reason == "invalid-box"
    assert refusal.region_key == "mutated:1"
    assert fragment in refusal.detail


def test_missing_page_frame_yields_typed_missing_frame_refusal(tmp_path):
    path = _mutated_sheet(tmp_path, lambda s: s.__setitem__("page_frames", {}))
    result = import_sheets([path], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.reason == "missing-frame"
    assert refusal.region_key == "mutated:1"
    assert "page 1" in refusal.detail


def test_unresolvable_frame_binding_yields_typed_frame_binding_refusal(tmp_path):
    """A recorded frame frames.py cannot resolve (degenerate viewport extent)
    is refused typed, never bound by guessing a convention."""
    path = _mutated_sheet(tmp_path, lambda s: s["page_frames"]["1"].__setitem__("viewport_w", 0))
    result = import_sheets([path], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.reason == "frame-binding-refused"
    assert refusal.region_key == "mutated:1"
    assert "invalid_page_extent" in refusal.detail


def test_swapped_viewport_frame_is_refused_not_silently_mismapped(tmp_path):
    """A rotated/swapped viewport recording (aspect far off the CropBox
    aspect) cannot bind — the corpus's real frames deviate < 0.1%."""
    def swap(sheet):
        sheet["page_frames"]["1"]["viewport_w"] = 1250
        sheet["page_frames"]["1"]["viewport_h"] = 966

    path = _mutated_sheet(tmp_path, swap)
    result = import_sheets([path], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.reason == "frame-binding-refused"
    assert "page-extent-mismatch" in refusal.detail


def test_non_dict_structure_entry_is_refused_not_fatal(tmp_path):
    """One malformed row must not sink the sheet: typed refusal instead."""
    path = _mutated_sheet(tmp_path, lambda s: s["structure"].__setitem__(0, None))
    result = import_sheets([path], source_root=tmp_path)
    assert result.regions == []
    assert len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.reason == "invalid-box"
    assert refusal.region_key == "mutated:1"
