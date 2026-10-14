# Purpose: Evidence lineage and transform replay tests (sunset-r68.7, tasks.md 1.3).
# Responsibilities: Build a source→corrected→normalized chain on the tracer fixture;
#   assert validator enforces exactly-one producer per transform-participating
#   content, transform inputs/outputs disjoint with outputs == content_ids,
#   derived-from edges exactly equal the input producers, acyclicity; broken
#   lineage yields invalid_transform_binding; replay walks the chain through a
#   supplied transform registry and reports unreplayable transforms instead of
#   guessing.
# Rationale: add-dsc-03 document-evidence "Replay material for derived observations"
#   (native → corrected → normalized scenario).
"""Evidence lineage + transform replay tests (sunset-r68.7)."""
import copy
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import evidence, profiles, validator

TRACER = Path(__file__).parent / "fixture_minimal.json"
REGISTRY = profiles.Registry(Path(__file__).parent)

CFG_NFC = "1" * 64  # stand-in config digest for the NFC transform


def chain():
    """Tracer fixture extended to e0(source, c0) → e1(NFC, c1) → e2(NFC, c2)."""
    d = validator.load(TRACER)
    d["contents"] += [
        # NFC on already-NFC source text is the identity transform; c1 and c2 are
        # distinct objects with equal value (distinctness is only required when
        # code-point sequences differ)
        {"id": "c1", "kind": "text", "value": "Hello page"},
        {"id": "c2", "kind": "text", "value": "Hello page"},
    ]
    d["evidence"] += [
        {
            "id": "e1", "origin": "inferred", "source_ref": "urn:example:correct",
            "content_ids": ["c1"], "selector_ids": [],
            "transform": {
                "id": "t-nfc", "version": "1", "config_sha256": CFG_NFC,
                "dependencies": ["unicode:nfc"], "inputs": ["c0"], "outputs": ["c1"],
            },
        },
        {
            "id": "e2", "origin": "inferred", "source_ref": "urn:example:normalize",
            "content_ids": ["c2"], "selector_ids": [],
            "transform": {
                "id": "t-nfc", "version": "1", "config_sha256": CFG_NFC,
                "dependencies": ["unicode:nfc"], "inputs": ["c1"], "outputs": ["c2"],
            },
        },
    ]
    d["relations"] += [
        {"id": "rel-df1", "kind": "derived-from", "from": "e1", "to": "e0"},
        {"id": "rel-df2", "kind": "derived-from", "from": "e2", "to": "e1"},
    ]
    return d


def resolved(d):
    out = {}
    for p in d["profiles"]:
        out[p["id"]] = profiles.resolve(p, REGISTRY)
    return out


def test_chain_validates():
    assert validator.validate(chain()) == []


def test_missing_derived_from_edge_is_invalid_transform_binding():
    d = chain()
    d["relations"] = [r for r in d["relations"] if r["id"] != "rel-df2"]
    assert "invalid_transform_binding" in validator.validate(d)


def test_input_without_producer_is_invalid_transform_binding():
    d = chain()
    d["evidence"][2]["transform"]["inputs"] = ["c0", "c2"]  # c2 has no producer yet
    assert "invalid_transform_binding" in validator.validate(d)


def test_declared_parent_that_is_not_an_input_producer_is_invalid():
    d = chain()
    d["relations"] = [r for r in d["relations"] if r["id"] != "rel-df2"]
    d["relations"].append({"id": "rel-df2", "kind": "derived-from", "from": "e2", "to": "e0"})
    assert "invalid_transform_binding" in validator.validate(d)


def test_duplicate_producer_is_invalid():
    d = chain()
    d["evidence"].append({
        "id": "e3", "origin": "source", "source_ref": "urn:example:dup",
        "content_ids": ["c0"], "selector_ids": [],
    })
    assert "invalid_transform_binding" in validator.validate(d)


def test_output_that_is_its_own_input_is_invalid():
    d = chain()
    d["evidence"][2]["transform"]["inputs"] = ["c2"]
    assert "invalid_transform_binding" in validator.validate(d)


def test_lineage_cycle_is_lineage_cycle():
    d = chain()
    # c3 produced by e4, e2 ← e4 and e4 ← e2 would need shared outputs; simplest
    # acyclic-violation: e2 derived-from e1 and e1 derived-from e2
    d["relations"].append({"id": "rel-df3", "kind": "derived-from", "from": "e1", "to": "e2"})
    assert "lineage_cycle" in validator.validate(d)


def test_replay_walks_the_chain():
    d = chain()
    res = resolved(d)
    fns = {CFG_NFC: lambda s: unicodedata.normalize("NFC", s)}
    status, detail = evidence.replay(d["evidence"][2], d, res, transform_fns=fns)
    assert status == "replayed"
    assert detail["chain"] == ["c2"]
    assert detail["observations"]["c2"] == "Hello page"


def test_replay_reports_missing_transform_as_unreplayable():
    d = chain()
    res = resolved(d)
    status, detail = evidence.replay(d["evidence"][2], d, res, transform_fns={})
    assert status == "unreplayable"


def test_source_link_replay_still_works():
    d = chain()
    status, detail = evidence.replay(d["evidence"][0], d, resolved(d), transform_fns={})
    assert status == "replayed"
    assert detail["observations"] == {"s0": "Hello"}
