# Purpose: Negative/positive core-delta fixtures beyond the tracer slice (sunset-r68.2).
# Responsibilities: Red→green coverage of the remaining document-core scenarios:
#   exact non-NFC text values allowed while metadata strings require NFC,
#   canonical bytes distinguish decomposed/composed snapshots, cross-view
#   containment rejected, wrong-view roots rejected, scoped reading order
#   (opposing hypotheses valid, cycles and duplicate edges rejected), unbound
#   claims rejected, cross-collection id collisions and wrong reference types
#   rejected.
# Rationale: add-dsc-03 document-core delta scenarios (tasks.md item 1.1 beyond
#   the tracer) — malformed-field handling already covered by test_tracer_validate.
"""Negative core fixtures (sunset-r68.2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import validator

TRACER = Path(__file__).parent / "fixture_minimal.json"

DECOMPOSED = "é"  # U+0065 U+0301, not NFC
I_PHYS = {
    "id": "i-phys-order",
    "kind": "reading-order",
    "view_id": "v-phys",
    "origin": "manual",
    "status": "asserted_without_evidence",
    "evidence": [],
}


def load():
    return validator.load(TRACER)


def test_text_value_may_be_non_nfc():
    d = load()
    d["contents"][0]["value"] = DECOMPOSED
    assert validator.validate(d) == []


def test_metadata_strings_require_nfc():
    d = load()
    d["annotations"][0]["value"] = DECOMPOSED
    assert validator.validate(d) == ["not_nfc"]


def test_canonical_bytes_distinguish_unicode_snapshots():
    decomposed = load()
    decomposed["contents"][0]["value"] = DECOMPOSED
    composed = load()
    composed["contents"][0]["value"] = "é"  # U+00E9
    assert validator.validate(decomposed) == []
    assert validator.validate(composed) == []
    assert validator.canonical(decomposed) != validator.canonical(composed)
    # each survives parse/reserialize unchanged
    for d in (decomposed, composed):
        again = validator.loads(validator.canonical(d).decode("utf-8"))
        assert validator.canonical(again) == validator.canonical(d)


def test_cross_view_containment_is_invalid():
    d = load()
    d["relations"].append({"id": "rel-x", "kind": "contains", "from": "r-page", "to": "r-art"})
    assert "relation_type" in validator.validate(d)


def test_root_belonging_to_another_view_is_invalid():
    d = load()
    d["views"][0]["root"] = "r-art"
    assert "containment_roots" in validator.validate(d)


def test_opposing_hypotheses_are_both_valid():
    d = load()
    d["interpretations"].append(I_PHYS)
    d["interpretations"].append({**I_PHYS, "id": "i-phys-order2"})
    d["relations"] += [
        {"id": "rel-p1", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order"},
        {"id": "rel-p2", "kind": "precedes", "from": "r-body", "to": "r-page", "interpretation_id": "i-phys-order2"},
    ]
    assert validator.validate(d) == []


def test_cycle_within_one_hypothesis_is_order_cycle():
    d = load()
    d["interpretations"].append(I_PHYS)
    d["relations"] += [
        {"id": "rel-p1", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order"},
        {"id": "rel-p2", "kind": "precedes", "from": "r-body", "to": "r-page", "interpretation_id": "i-phys-order"},
    ]
    assert validator.validate(d) == ["order_cycle"]


def test_duplicate_edge_in_same_interpretation():
    d = load()
    d["interpretations"].append(I_PHYS)
    d["relations"] += [
        {"id": "rel-p1", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order"},
        {"id": "rel-p2", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order"},
    ]
    assert validator.validate(d) == ["duplicate_edge"]


def test_same_edge_in_two_interpretations_is_valid():
    d = load()
    d["interpretations"].append(I_PHYS)
    d["interpretations"].append({**I_PHYS, "id": "i-phys-order2"})
    d["relations"] += [
        {"id": "rel-p1", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order"},
        {"id": "rel-p2", "kind": "precedes", "from": "r-page", "to": "r-body", "interpretation_id": "i-phys-order2"},
    ]
    assert validator.validate(d) == []


def test_unbound_claim_is_invalid():
    d = load()
    del d["relations"][2]  # drop the logical view's has-content binding for c0
    assert "dangling_reference" in validator.validate(d)


def test_id_collision_across_collections():
    d = load()
    d["selectors"][0]["id"] = "r-page"
    assert "duplicate_id" in validator.validate(d)


def test_selector_profile_id_naming_a_content_is_dangling():
    d = load()
    d["selectors"][0]["profile_id"] = "c0"
    assert validator.validate(d) == ["dangling_reference"]
