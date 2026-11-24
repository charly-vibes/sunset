# Purpose: Canonical set-order tests for DSC 0.3 identity-profile descriptors
#   (add-anchor-derived-identity tasks §3.1-§3.3).
# Responsibilities: Assert that permuting the set-like sections of a valid
#   identity-profile descriptor leaves both canonical readers' bytes unchanged
#   (Requirement: Permutation invariance), and that parsing each reader's
#   canonical bytes and re-serializing is a fixpoint even for a permuted input.
#   Descriptors without an identity profile keep today's order-preserving bytes.
# Rationale: design Decision 3 — under the identity profile, sequence meaning
#   lives only in precedes relations, so set-like sections serialize in
#   ascending id order (coverage by its uniqueness triple).
"""Canonical order under the identity profile: permutation invariance, roundtrip stability."""
import hashlib
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import canonical, identity, validator

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PROFILE_ID = "p-id"
PROFILE_VERSION = "1"

SET_LIKE = (
    "regions", "contents", "selectors", "evidence", "annotations",
    "coverage", "interpretations", "profiles",
)


def _profile(pid, kind):
    return {
        "id": pid,
        "kind": kind,
        "uri": f"profiles/{pid}.json",
        "version": "1",
        "sha256": hashlib.sha256(f"profiles/{pid}.json".encode("utf-8")).hexdigest(),
    }


def _anchored(rec_kind, locator, **fields):
    source = fields.get("source_sha256", SHA)
    if rec_kind != "selector":  # selectors carry their own source_sha256
        fields.pop("source_sha256", None)
    rec = dict(fields)
    rec["anchor"] = {"record_kind": rec_kind, "locator_path": locator}
    rec["id"] = identity.derive_id((source, rec_kind, locator, PROFILE_ID, PROFILE_VERSION))[1]
    return rec


def identity_descriptor():
    root = _anchored("region", "doc:root", view_id="v-log", kind="article")
    child = _anchored("region", "doc:child", view_id="v-log", kind="paragraph")
    content_a = _anchored("content", "raw:[0,5)", kind="text", value="Hello")
    content_b = _anchored("content", "raw:[6,11)", kind="text", value="World")
    selector_a = _anchored(
        "selector", "[0,5)", kind="text-range", profile_id="p-sel",
        source_sha256=SHA, target=content_a["id"],
    )
    selector_a["locator"] = "[0,5)"
    selector_b = _anchored(
        "selector", "[6,11)", kind="text-range", profile_id="p-sel",
        source_sha256=SHA, target=content_b["id"],
    )
    selector_b["locator"] = "[6,11)"
    evidence_a = _anchored(
        "evidence", "urn:example:src#1", origin="source", source_ref="urn:example:src#1",
        content_ids=[content_a["id"]], selector_ids=[selector_a["id"]],
    )
    evidence_b = _anchored(
        "evidence", "urn:example:src#2", origin="source", source_ref="urn:example:src#2",
        content_ids=[content_b["id"]], selector_ids=[selector_b["id"]],
    )
    return {
        "version": "0.3",
        "id": "set-order-tracer",
        "source": {"format": "application/pdf", "sha256": SHA, "locator": "fixtures/set-order.pdf"},
        "views": [{"id": "v-log", "kind": "logical", "root": root["id"]}],
        "regions": [root, child],
        "contents": [content_a, content_b],
        "relations": [
            {"id": "rel-contains", "kind": "contains", "from": root["id"], "to": child["id"]},
            {"id": "rel-hc-1", "kind": "has-content", "from": root["id"], "to": content_a["id"]},
            {"id": "rel-hc-2", "kind": "has-content", "from": root["id"], "to": content_b["id"]},
        ],
        "annotations": [
            {
                "id": "an-1", "target": content_a["id"], "term": "ex:note", "value": "first",
                "origin": "source", "status": "supported", "evidence": [evidence_a["id"]],
                "view_id": "v-log",
            },
            {
                "id": "an-2", "target": content_b["id"], "term": "ex:note", "value": "second",
                "origin": "source", "status": "supported", "evidence": [evidence_b["id"]],
                "view_id": "v-log",
            },
        ],
        "evidence": [evidence_a, evidence_b],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "views_kind": None,  # placeholder removed below
        "selectors": [selector_a, selector_b],
        "interpretations": [
            {
                "id": "it-1", "kind": "reading-order", "view_id": "v-log",
                "origin": "source", "status": "asserted_without_evidence", "evidence": [],
            },
            {
                "id": "it-2", "kind": "reading-order", "view_id": "v-log",
                "origin": "source", "status": "asserted_without_evidence", "evidence": [],
            },
        ],
        "coverage": [
            {
                "inventory_id": "p-inv", "manifest_id": "p-man", "feature": "text",
                "scope": "page:2", "status": "preserved", "reason": "",
                "adapter_id": "adp", "adapter_version": "1", "config_sha256": "unavailable",
            },
            {
                "inventory_id": "p-inv", "manifest_id": "p-man", "feature": "text",
                "scope": "page:1", "status": "preserved", "reason": "",
                "adapter_id": "adp", "adapter_version": "1", "config_sha256": "unavailable",
            },
            {
                "inventory_id": "p-inv", "manifest_id": "p-man", "feature": "text",
                "scope": "document", "status": "preserved", "reason": "",
                "adapter_id": "adp", "adapter_version": "1", "config_sha256": "unavailable",
            },
        ],
        "profiles": [
            _profile("p-man", "adapter-manifest"),
            _profile("p-sel", "selector"),
            _profile(PROFILE_ID, "identity"),
            _profile("p-inv", "carrier-inventory"),
        ],
    }


def _test_descriptor():
    d = identity_descriptor()
    del d["views_kind"]
    return d


def _permutations(descriptor, count=6):
    rng = random.Random(700)
    perms = []
    for _ in range(count):
        p = json.loads(json.dumps(descriptor))
        for section in SET_LIKE:
            rng.shuffle(p[section])
        perms.append(p)
    return perms


def test_fixture_is_valid_and_bytes_agree():
    d = _test_descriptor()
    assert validator.validate(d) == []
    assert canonical.agree(d)


def test_permutation_invariance_under_identity_profile():
    d = _test_descriptor()
    base_a = canonical.reader_a(d)
    base_b = canonical.reader_b(d)
    for permuted in _permutations(d):
        assert canonical.reader_a(permuted) == base_a
        assert canonical.reader_b(permuted) == base_b


def test_sorted_order_is_ascending_id_and_coverage_triple():
    d = _test_descriptor()
    ordered = json.loads(canonical.reader_a(d).decode("utf-8"))
    for section in ("regions", "contents", "selectors", "evidence", "annotations", "interpretations", "profiles"):
        ids = [r["id"] for r in ordered[section]]
        assert ids == sorted(ids)
    triples = [(c["inventory_id"], c["feature"], c["scope"]) for c in ordered["coverage"]]
    assert triples == sorted(triples)


def test_relations_keep_array_order_under_identity_profile():
    d = _test_descriptor()
    permuted = _permutations(d)[0]
    permuted["relations"].reverse()
    ordered = json.loads(canonical.reader_a(permuted).decode("utf-8"))
    assert [r["id"] for r in ordered["relations"]] == ["rel-hc-2", "rel-hc-1", "rel-contains"]


@pytest.mark.parametrize("reader", [canonical.reader_a, canonical.reader_b], ids=["reader_a", "reader_b"])
def test_roundtrip_fixpoint_including_permuted_input(reader):
    d = _test_descriptor()
    check = canonical.roundtrip_stable(reader)
    assert check(d)
    for permuted in _permutations(d, count=2):
        assert check(permuted)


def test_without_identity_profile_order_is_preserved():
    d = _test_descriptor()
    d["profiles"] = [p for p in d["profiles"] if p["kind"] != "identity"]
    assert validator.validate(d) == []
    permuted = _permutations(d, count=1)[0]
    assert canonical.reader_a(permuted) != canonical.reader_a(d)
    assert canonical.reader_b(permuted) != canonical.reader_b(d)
    # and the today-behavior contract: bytes reproduce the input array order
    ordered = json.loads(canonical.reader_b(d).decode("utf-8"))
    assert [r["id"] for r in ordered["regions"]] == [r["id"] for r in d["regions"]]
    assert [r["id"] for r in ordered["contents"]] == [r["id"] for r in d["contents"]]
