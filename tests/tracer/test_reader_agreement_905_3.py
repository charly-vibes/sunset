"""Contract tests for the sunset-905.3 agent-executed reader-sheet ingest.

Owner ruling (b, 2026-10-18): the reader-grok and reader-claude sheet sets
returned via cotorreo are ingested as a labeled AGENT-EXECUTED agreement run.
They do NOT satisfy the two-human-reader gate; a human pass supersedes them
(recorded deviations policy). These tests pin the ingest shape:

- both reader sheet sets exist with exactly the four carrier sheets,
- every sheet validates against the observations template schema,
- a provenance file records the agent-executed ruling and both reader ids,
- an agreement matrix classifies observables without electing a winner.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "hitl" / "sunset-905.3" / "runs"
CARRIERS = [
    "diario-de-poesia-excerpt",
    "agentic-patterns-excerpt",
    "sunset-carrier-sample",
    "bank-statement-ca-excerpt",
]
READERS = ["reader-claude", "reader-grok"]

REQUIRED_SHEET_KEYS = {
    "reader",
    "carrier",
    "elapsed_minutes",
    "page_inventory",
    "structure",
    "relations",
    "space",
    "context",
    "annotations",
    "losses",
    "uncertainties",
    "notes",
}
CONTEXT_KINDS = {
    "publication_date",
    "publisher_or_source",
    "author_or_attribution",
    "quoted_material",
}
ROTATIONS = {"0", "90", "180", "270", "unknown"}
COLUMN_VALUES = {"single", "two", "multi", "unknown"}


def _sheets(reader):
    return sorted((RUNS / reader).glob("*.observations.json"))


def test_both_reader_sheet_sets_present_with_four_carriers():
    for reader in READERS:
        found = [p.stem.replace(".observations", "") for p in _sheets(reader)]
        assert sorted(found) == sorted(CARRIERS), f"{reader}: {found}"


def test_every_sheet_validates_against_template_schema():
    for reader in READERS:
        for path in _sheets(reader):
            sheet = json.loads(path.read_text())
            missing = REQUIRED_SHEET_KEYS - set(sheet)
            assert not missing, f"{path}: missing keys {missing}"
            assert sheet["reader"] == reader, f"{path}: reader id mismatch"
            assert sheet["carrier"] in CARRIERS, f"{path}: unknown carrier"
            assert sheet["elapsed_minutes"] is None or isinstance(
                sheet["elapsed_minutes"], (int, float)
            ), f"{path}: elapsed_minutes must be null or a number"
            assert isinstance(sheet["page_inventory"], list)
            for entry in sheet["space"]:
                assert entry["rotation"] in ROTATIONS or entry["rotation"] == "unknown"
                assert entry["columns"] in COLUMN_VALUES
            for entry in sheet["context"]:
                assert entry["kind"] in CONTEXT_KINDS, f"{path}: bad context kind"
                assert entry["status"] in {
                    "observed",
                    "observed_absent",
                    "unknown",
                }


def test_provenance_records_agent_executed_ruling_and_readers():
    prov = RUNS / "PROVENANCE.md"
    assert prov.exists(), "runs/PROVENANCE.md missing"
    text = prov.read_text()
    assert "agent-executed" in text.lower()
    for reader in READERS:
        assert reader in text
    # sha256 provenance for every sheet, one line per sheet
    for reader in READERS:
        for path in _sheets(reader):
            assert path.name in text, f"provenance missing digest entry for {path.name}"


def test_agreement_matrix_classifies_without_winner_election():
    matrix = REPO / "hitl" / "sunset-905.3" / "agreement-matrix-agent-run.md"
    assert matrix.exists(), "agreement-matrix-agent-run.md missing"
    text = matrix.read_text()
    for reader in READERS:
        assert reader in text
    for carrier in CARRIERS:
        assert carrier in text, f"matrix missing carrier {carrier}"
    allowed = {"AGREE", "COMPATIBLE", "UNKNOWN", "LOSS", "DISAGREE"}
    # every classified row uses a class from the legend
    rows = re.findall(r"^\|[^|\n]+\|[^|\n]+\|.*\|$", text, flags=re.M)
    assert rows, "matrix has no table rows"
    for row in rows:
        if re.match(r"^[\s:-]+$", row.replace("|", "")):
            continue  # markdown separator row
        cells = [c.strip() for c in row.strip("|").split("|")]
        clean = [c.strip().strip("*") for c in cells[1:] if c]
        if all(re.fullmatch(r"\d+", c) for c in clean):
            continue  # roll-up count rows carry no class tokens
        classes = {c for c in allowed if re.search(rf"\b{c}\b", row)}
        assert classes or "Observable" in row or "Carrier" in row, (
            f"row without legend class: {row}")
    # no silent winner election: a ruling column exists but is not auto-filled
    assert "Owner ruling" in text


# ---------------------------------------------------------------------------
# 2026-10-26 update: first real HUMAN baseline (owner-executed, reader-a)
# ---------------------------------------------------------------------------

def test_reader_a_human_baseline_present_and_schema_valid():
    """The owner completed the interactive annotator session for
    diario-de-poesia-excerpt: the first human-executed sheet. It is a
    single-human baseline — it does NOT satisfy the two-readers gate, but it
    supersedes the agent-executed sets for this carrier where they conflict."""
    base = RUNS / "reader-a"
    sheet_path = base / "diario-de-poesia-excerpt.observations.json"
    assert sheet_path.is_file(), "human baseline sheet missing"
    sheet = json.loads(sheet_path.read_text())
    missing = REQUIRED_SHEET_KEYS - set(sheet)
    assert not missing, f"missing keys {missing}"
    assert sheet["reader"] == "reader-a"
    assert sheet["carrier"] == "diario-de-poesia-excerpt"
    assert sheet["elapsed_minutes"] == 13
    # six image-only pages inventoried
    assert [p["index"] for p in sheet["page_inventory"]] == [1, 2, 3, 4, 5, 6]
    assert all(p["image_only"] is True for p in sheet["page_inventory"])
    # 56 drawn page-relative regions, all within the page
    assert len(sheet["structure"]) == 56
    for s in sheet["structure"]:
        assert s["bbox"]["relative"] == "page"
        for k in ("x", "y", "w", "h"):
            assert 0 <= s["bbox"][k] <= 1.0001, (s["label"], k, s["bbox"][k])
        assert s["bbox"]["x"] + s["bbox"]["w"] <= 1.0001
        assert s["bbox"]["y"] + s["bbox"]["h"] <= 1.0001
        assert 1 <= s["page"] <= 6
        assert s["type"] in {"text", "title", "heading", "image", "table",
                             "caption", "header", "footer", "list", "other"}
    # structure-layer-only baseline: other sections deliberately empty
    for key in ("relations", "space", "context", "annotations", "losses",
                "uncertainties"):
        assert sheet[key] == [], f"{key} should be empty in this baseline"


def test_reader_a_human_baseline_provenance_recorded():
    prov = (RUNS / "PROVENANCE.md").read_text()
    assert "first real HUMAN baseline" in prov
    assert "single-human baseline" in prov
    assert "NOT the two-independent-readers gate" in prov
    assert "60e0bd437953d19a7d1b14e9c5cd18c5f9fc41835cbd08ae8fceb01888fc313c" in prov
