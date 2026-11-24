# Purpose: Label-id -> identity-profile migration tests (sunset-c6i,
#   add-anchor-derived-identity tasks.md 5.1).
# Responsibilities: Assert dsc03.migrate.migrate_to_identity turns a valid
#   label-id descriptor into an identity-profile descriptor that the 0.3
#   validator accepts; record ids equal derive_id over each record's
#   DECLARED-data anchor (selector locators, evidence source_ref, a unique
#   targeting selector's locator — selectors keep their own source_sha256);
#   every reference to a renamed record is rebound; the relabel table maps
#   EVERY migrated old id and is emitted as one relabel-table evidence record
#   per design Decision 5; content values and record counts are unchanged;
#   records whose anchor cannot be derived from declared data (and anchor-tuple
#   duplicates) are reported in report["unanchored"] and never invented;
#   migration is deterministic (two runs, identical canonical bytes).
# Rationale: add-anchor-derived-identity design.md Decision 5 ("migrate emits
#   relabel-table evidence mapping old->new ids") and the delta requirement
#   "Explicit relabeling" (every content value unchanged, table maps every old
#   id); migrate.py's loss-accounting style — nothing invented.
"""Label-id → identity-profile migration tests (sunset-c6i)."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import identity, migrate, validator

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
# text-range selectors carry their own source digest, distinct from the
# descriptor's — the derivation must use the selector's own field
SHA_SEL = hashlib.sha256(b"migration-selector-source").hexdigest()
PROF_ID = migrate.IDENTITY_PROFILE_ID
PROF_VERSION = migrate.IDENTITY_PROFILE_VERSION


def _label_descriptor():
    """A valid label-id 0.3 descriptor; every record is anchorable from
    declared data (each region/content is pinned by exactly one selector)."""
    return {
        "version": "0.3",
        "id": "migration-tracer",
        "source": {"format": "application/pdf", "sha256": SHA,
                   "locator": "fixtures/migration.pdf"},
        "views": [
            {"id": "v-phys", "kind": "physical", "root": "pg1"},
            {"id": "v-log", "kind": "logical", "root": "r-doc"},
        ],
        "regions": [
            {"id": "pg1", "view_id": "v-phys", "kind": "page"},
            {"id": "r-doc", "view_id": "v-log", "kind": "article"},
        ],
        "contents": [{"id": "c-poem", "kind": "text", "value": "Rose"}],
        "relations": [
            {"id": "rel-realizes", "kind": "realizes", "from": "pg1", "to": "r-doc"},
            {"id": "rel-hc", "kind": "has-content", "from": "r-doc", "to": "c-poem"},
        ],
        "annotations": [{
            "id": "a-head", "target": "c-poem", "term": "ex:note",
            "value": "marginal heading", "origin": "manual",
            "status": "asserted_without_evidence", "evidence": [],
            "view_id": "v-log",
        }],
        "evidence": [{
            "id": "e-src", "origin": "source",
            "source_ref": "urn:example:migration:page1",
            "content_ids": ["c-poem"], "selector_ids": ["s-poem"],
        }],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [
            {"id": "s-page1", "kind": "pdf-area", "profile_id": "p-sel",
             "source_sha256": SHA, "target": "pg1", "locator": "page:1"},
            {"id": "s-doc", "kind": "pdf-object", "profile_id": "p-sel",
             "source_sha256": SHA, "target": "r-doc", "locator": "object:12"},
            {"id": "s-poem", "kind": "text-range", "profile_id": "p-sel",
             "source_sha256": SHA_SEL, "target": "c-poem", "locator": "[40,44)"},
        ],
        "interpretations": [],
        "coverage": [],
        "profiles": [{
            "id": "p-sel", "kind": "selector",
            "uri": "profiles/selector-text-scalar.json", "version": "1",
            "sha256": hashlib.sha256(b"profiles/selector-text-scalar.json").hexdigest(),
        }],
    }


def _label_with_unanchorable_records():
    """The anchored fixture plus: a region no selector targets, a content
    pinned by two text-range selectors (ambiguous), and two selectors sharing
    one locator (their anchor tuples collide)."""
    d = _label_descriptor()
    d["regions"].append({"id": "pg2", "view_id": "v-phys", "kind": "page"})
    d["relations"].append({"id": "rel-c2", "kind": "contains", "from": "pg1", "to": "pg2"})
    d["contents"].append({"id": "c-two", "kind": "text", "value": "Twin"})
    d["selectors"].append({"id": "s-t1", "kind": "text-range", "profile_id": "p-sel",
                           "source_sha256": SHA_SEL, "target": "c-two", "locator": "[70,74)"})
    d["selectors"].append({"id": "s-t2", "kind": "text-range", "profile_id": "p-sel",
                           "source_sha256": SHA_SEL, "target": "c-two", "locator": "[70,74)"})
    return d


def _derived(source_sha, rec_kind, locator):
    return identity.derive_id((source_sha, rec_kind, locator, PROF_ID, PROF_VERSION))[1]


def _relabel_pairs(d):
    """The [old, new] pairs carried by the relabel-table evidence record."""
    table = next(e for e in d["evidence"]
                 if e.get("anchor", {}).get("locator_path") == migrate.RELABEL_LOCATOR)
    prefix = f"sha256:{d['source']['sha256']}#relabel-table="
    assert table["source_ref"].startswith(prefix), table["source_ref"]
    return json.loads(table["source_ref"][len(prefix):])


def test_migrated_descriptor_declares_identity_profile_and_validates():
    label = _label_descriptor()
    assert validator.validate(label) == []  # fixture soundness
    d, report = migrate.migrate_to_identity(label)
    identity_profiles = [p for p in d["profiles"] if p["kind"] == "identity"]
    assert len(identity_profiles) == 1
    assert identity_profiles[0]["id"] == PROF_ID
    assert identity_profiles[0]["version"] == PROF_VERSION
    assert validator.validate(d) == [], validator.validate(d)
    assert report["unanchored"] == []


def test_ids_are_anchor_derivations_from_declared_data():
    d, _ = migrate.migrate_to_identity(_label_descriptor())
    by_kind = {"regions": "region", "contents": "content",
               "selectors": "selector", "evidence": "evidence"}
    anchors = {}  # (record_kind, locator_path) -> record; region pg1 and
    # selector s-page1 share the locator "page:1", so the kind disambiguates
    for section, rec_kind in by_kind.items():
        for rec in d[section]:
            assert rec["anchor"]["record_kind"] == rec_kind
            source = rec["source_sha256"] if rec_kind == "selector" else SHA
            assert rec["id"] == _derived(source, rec_kind,
                                         rec["anchor"]["locator_path"]), rec
            anchors[(rec_kind, rec["anchor"]["locator_path"])] = rec
    assert anchors[("region", "page:1")]  # pg1, pinned by s-page1's locator
    assert anchors[("region", "object:12")]  # r-doc, pinned by s-doc's locator
    # the text content takes its text-range selector's locator as a raw interval
    assert anchors[("content", "raw:[40,44)")]
    # selectors: own locator and OWN source digest, not the descriptor's
    assert anchors[("selector", "[40,44)")]
    # evidence: its declared source_ref
    assert anchors[("evidence", "urn:example:migration:page1")]
    # no old id survives on any migrated record
    for old in ("pg1", "r-doc", "c-poem", "s-page1", "s-doc", "s-poem", "e-src"):
        assert all(rec["id"] != old for section in by_kind for rec in d[section])


def test_content_values_and_record_counts_are_unchanged():
    label = _label_descriptor()
    d, report = migrate.migrate_to_identity(label)
    assert [c["value"] for c in d["contents"]] == ["Rose"]
    assert [len(d[k]) for k in ("regions", "contents", "relations", "selectors")] == [2, 1, 2, 3]
    assert report["relabel_evidence"]
    assert len(d["evidence"]) == 2  # e-src renamed + the new relabel-table record


def test_relabel_table_maps_every_old_id():
    label = _label_descriptor()
    old_ids = ["pg1", "r-doc", "c-poem", "s-page1", "s-doc", "s-poem", "e-src"]
    d, report = migrate.migrate_to_identity(label)
    pairs = _relabel_pairs(d)
    assert [old for old, _ in pairs] == sorted(old_ids)  # EVERY old id, sorted
    new_by_old = dict(pairs)
    assert report["relabel"] == pairs
    # the table's new ids are exactly the migrated records' ids
    migrated = {rec["id"] for rec in
                (d["regions"] + d["contents"] + d["selectors"]
                 + [e for e in d["evidence"]
                    if e.get("anchor", {}).get("locator_path") != migrate.RELABEL_LOCATOR])}
    assert set(new_by_old.values()) == migrated
    # the relabel record itself is a derived identity anchored at the table path
    table = next(e for e in d["evidence"] if e["id"] == report["relabel_evidence"])
    assert table["anchor"] == {"record_kind": "evidence",
                               "locator_path": migrate.RELABEL_LOCATOR}
    assert table["origin"] == "manual"
    assert table["id"] == _derived(SHA, "evidence", migrate.RELABEL_LOCATOR)


def test_every_reference_is_rebound_no_old_id_survives_outside_the_table():
    d, _ = migrate.migrate_to_identity(_label_descriptor())
    old_ids = {"pg1", "r-doc", "c-poem", "s-page1", "s-doc", "s-poem", "e-src"}
    table = next(e for e in d["evidence"]
                 if e.get("anchor", {}).get("locator_path") == migrate.RELABEL_LOCATOR)
    evidence = [dict(e, source_ref="") if e is table else e for e in d["evidence"]]
    blob = json.dumps(dict(d, evidence=evidence))
    for old in old_ids:
        assert old not in blob, old  # only the table's source_ref may name old ids
    assert d["views"][0]["root"] == _derived(SHA, "region", "page:1")
    assert d["views"][1]["root"] == _derived(SHA, "region", "object:12")
    relation_ends = {(r["kind"], r["from"], r["to"]) for r in d["relations"]}
    assert (_derived(SHA, "region", "page:1"), _derived(SHA, "region", "object:12")) in {
        (a, b) for k, a, b in relation_ends if k == "realizes"}
    assert d["annotations"][0]["target"] == _derived(SHA, "content", "raw:[40,44)")
    assert d["annotations"][0]["value"] == "marginal heading"  # claims untouched
    assert d["evidence"][0]["selector_ids"] == [_derived(SHA_SEL, "selector", "[40,44)")]


def test_unanchorable_and_duplicate_anchor_records_are_reported_not_invented():
    label = _label_with_unanchorable_records()
    assert validator.validate(label) == []  # valid label-id input
    d, report = migrate.migrate_to_identity(label)
    unanchored = {entry["id"]: entry["reason"] for entry in report["unanchored"]}
    assert set(unanchored) == {"pg2", "c-two", "s-t1", "s-t2"}
    assert "pg2" in unanchored and "no selector targets" in unanchored["pg2"]
    assert "pinned by 2 selectors" in unanchored["c-two"]
    assert "duplicates" in unanchored["s-t1"] and "duplicates" in unanchored["s-t2"]
    # never invented: the reported records keep their label ids and gain no anchor
    by_id = {rec["id"]: rec for section in
             ("regions", "contents", "selectors", "evidence") for rec in d[section]}
    for old in ("pg2", "c-two", "s-t1", "s-t2"):
        assert by_id[old]["id"] == old
        assert "anchor" not in by_id[old]
    # the table maps exactly the migrated old ids — not the reported ones
    assert {old for old, _ in _relabel_pairs(d)} == {
        "pg1", "r-doc", "c-poem", "s-page1", "s-doc", "s-poem", "e-src"}
    # and the honest outcome is typed: incomplete migration does not validate
    assert validator.validate(d) == ["identity_anchor_missing"]


def test_migration_is_deterministic():
    a, _ = migrate.migrate_to_identity(_label_descriptor())
    b, _ = migrate.migrate_to_identity(_label_descriptor())
    assert validator.canonical(a) == validator.canonical(b)
