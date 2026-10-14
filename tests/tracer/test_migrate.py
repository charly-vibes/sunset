# Purpose: Migration tests — 0.2 descriptors to reported 0.3 per-view trees
#   (sunset-r68.9, tasks.md 4.1 + 4.2).
# Responsibilities: dsc03.migrate.migrate converts every valid frozen 0.2 fixture
#   into a 0.3 descriptor that the 0.3 validator accepts; legacy cross-view
#   containment becomes per-view trees; conflicting/unsupported order assertions
#   are reported, not guessed; original source digests and ids are preserved where
#   unambiguous; legacy geometry without profile bindings, legacy extracted
#   evidence without replay material, and ambiguous/unbound annotation bindings
#   are reported as unrecoverable/unexamined rather than invented; NFC-only 0.2
#   text is reported as unrecoverable to original code points.
# Rationale: add-dsc-03 design.md "Compatibility and migration".
"""0.2 → 0.3 migration tests (sunset-r68.9)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import migrate, validator

FIXTURES = Path(__file__).resolve().parents[2] / "spec" / "document-model-specodelic-v3" / "fixtures" / "valid"


def load_02(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def migrate_fixture(name):
    d02 = load_02(name)
    d03, report = migrate.migrate(d02)
    return d02, d03, report


def test_every_valid_02_fixture_migrates_to_valid_03():
    for name in sorted(p.name for p in FIXTURES.glob("*.json")):
        _, d03, _ = migrate_fixture(name)
        assert d03["version"] == "0.3"
        assert validator.validate(d03) == [], (name, validator.validate(d03))


def test_ids_and_source_digest_are_preserved():
    d02, d03, _ = migrate_fixture("mixed-pdf.json")
    assert d03["id"] == d02["id"]
    assert d03["source"] == d02["source"]
    legacy_region_ids = {r["id"] for r in d02["regions"]}
    migrated_region_ids = {r["id"] for r in d03["regions"]}
    assert legacy_region_ids == migrated_region_ids


def test_cross_view_containment_is_split_into_per_view_trees():
    _, d03, report = migrate_fixture("mixed-pdf.json")
    # mixed-pdf: logical root contains physical p1/p2 — the cross edges go away
    contains = [(r["from"], r["to"]) for r in d03["relations"] if r["kind"] == "contains"]
    view_of = {r["id"]: r["view_id"] for r in d03["regions"]}
    for a, b in contains:
        assert view_of[a] == view_of[b]
    dropped = [d for d in report["dropped"] if d["what"] == "contains-edge"]
    assert dropped, "cross-view contains edges must be reported"


def test_every_view_has_exactly_one_root_and_regions_have_parents():
    for name in sorted(p.name for p in FIXTURES.glob("*.json")):
        _, d03, _ = migrate_fixture(name)
        assert validator.validate(d03) == []


def test_unsupported_order_assertions_are_reported_not_invented():
    _, d03, report = migrate_fixture("mixed-pdf.json")
    # p1 and p2 land in different physical views; the legacy precedes edge
    # cannot be kept without guessing — it is reported, not silently kept
    view_of = {r["id"]: r["view_id"] for r in d03["regions"]}
    for r in d03["relations"]:
        if r["kind"] == "precedes":
            assert view_of[r["from"]] == view_of[r["to"]]
    assert any(d["what"] == "precedes-edge" for d in report["dropped"] + report["unsupported"])


def test_legacy_geometry_without_profile_is_reported_unexamined():
    _, d03, report = migrate_fixture("mixed-pdf.json")
    assert all("geometry" not in r for r in d03["regions"])
    assert any("geometry" in str(x) for x in report["unexamined"])


def test_legacy_extracted_evidence_without_replay_is_reported_unrecoverable():
    _, d03, report = migrate_fixture("mixed-pdf.json")
    ev_origins = {e["id"]: e["origin"] for e in d03["evidence"]}
    assert "ev-ocr" not in ev_origins  # extracted evidence had no replay material
    assert any("ev-ocr" in str(x) for x in report["unrecoverable"])


def test_nfc_only_text_is_reported_unrecoverable_to_original_code_points():
    _, d03, report = migrate_fixture("two-regions.json")
    assert any("code points" in str(x) for x in report["unrecoverable"])


def test_annotations_keep_status_and_gain_view_binding():
    d02, d03, _ = migrate_fixture("mixed-pdf.json")
    ann02 = {a["id"]: a for a in d02["annotations"]}
    ann03 = {a["id"]: a for a in d03["annotations"]}
    for aid, a in ann03.items():
        assert "view_id" in a and a["view_id"]
        assert a["status"] == ann02[aid]["status"]  # schema validity never promotes
        assert a["term"] == ann02[aid]["term"]
