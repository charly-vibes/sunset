# Purpose: Slice-1 tests for the read-only DSC descriptor inspection layer
#   (sunset-xx7.1, add-document-structural-debugger).
# Responsibilities: Assert loader round-trip byte-identity on a frozen 0.3
#   fixture (unchanged_bytes property per read_only invariant); assert the
#   inspection index resolves region / reading-order / evidence ids by O(1)-ish
#   id lookup; assert the typed diagnostics model emits all five categories
#   (pass, violated, disputed, unsupported, unexamined) with stable rule IDs and
#   smallest available witnesses; assert unexamined content is never reported as
#   pass (evidence_truth_boundary invariant).
# Rationale: document-debugger spec deltas; slice 1 excludes carriers,
#   comparators, goldens and a11y (slices 2-4). The loader/index never write.
"""Read-only inspection loader, index and typed diagnostics tests (sunset-xx7.1)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import inspect as dbg
from dsc03 import validator

TRACER = Path(__file__).parent / "fixture_minimal.json"

EXPECTED_CATEGORIES = {"pass", "violated", "disputed", "unsupported", "unexamined"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mutated() -> dict:
    """Valid 0.3 descriptor, fully supported, with a same-view precedes edge."""
    d = validator.load(TRACER)
    d["annotations"][0]["status"] = "supported"
    d["annotations"][0]["evidence"] = ["e0"]
    d["interpretations"][0]["status"] = "supported"
    d["interpretations"][0]["evidence"] = ["e0"]
    d["regions"].append({"id": "r-body2", "view_id": "v-log", "kind": "paragraph"})
    d["relations"].append(
        {
            "id": "rel-cont2",
            "kind": "contains",
            "from": "r-art",
            "to": "r-body2",
        }
    )
    d["relations"].append(
        {
            "id": "rel-pre",
            "kind": "precedes",
            "from": "r-art",
            "to": "r-body2",
            "interpretation_id": "i-order",
        }
    )
    assert validator.validate(d) == []
    return d


def mixed() -> dict:
    """Loadable descriptor exercising violated/disputed/unsupported/unexamined."""
    d = mutated()
    # disputed annotation (attributed claim)
    d["annotations"][0]["status"] = "disputed"
    # unsupported annotation + interpretation (asserted_without_evidence)
    d["annotations"].append(
        {
            "id": "a-uns",
            "target": "c0",
            "term": "ex:guess",
            "value": "unsupported guess",
            "origin": "manual",
            "status": "asserted_without_evidence",
            "evidence": [],
            "view_id": "v-log",
        }
    )
    d["interpretations"].append(
        {
            "id": "i-uns",
            "kind": "reading-order",
            "view_id": "v-log",
            "origin": "manual",
            "status": "asserted_without_evidence",
            "evidence": [],
        }
    )
    # structural violation: relation with a dangling endpoint
    d["relations"].append(
        {"id": "rel-bad", "kind": "contains", "from": "r-page", "to": "r-ghost"}
    )
    # coverage: one unexamined scope, one unsupported feature
    profiles_dir = Path(__file__).parent / "profiles"
    d["profiles"] += [
        {
            "id": "p-inv",
            "kind": "carrier-inventory",
            "uri": "profiles/inventory-pdf.json",
            "version": "1",
            "sha256": hashlib.sha256((profiles_dir / "inventory-pdf.json").read_bytes()).hexdigest(),
        },
        {
            "id": "p-man",
            "kind": "adapter-manifest",
            "uri": "profiles/manifest-pdf.json",
            "version": "1",
            "sha256": hashlib.sha256((profiles_dir / "manifest-pdf.json").read_bytes()).hexdigest(),
        },
    ]
    d["coverage"] = [
        {
            "inventory_id": "p-inv",
            "manifest_id": "p-man",
            "feature": "pdf:glyphs",
            "scope": "*",
            "status": "unexamined",
            "reason": "not inspected",
            "adapter_id": "demo-adapter",
            "adapter_version": "0.1",
            "config_sha256": "b" * 64,
        },
        {
            "inventory_id": "p-inv",
            "manifest_id": "p-man",
            "feature": "pdf:images",
            "scope": "*",
            "status": "unsupported",
            "reason": "no adapter",
            "adapter_id": "demo-adapter",
            "adapter_version": "0.1",
            "config_sha256": "b" * 64,
        },
    ]
    return d


def write_fixture(tmp_path: Path, d: dict) -> Path:
    """Write a descriptor plus its referenced source artifact to tmp_path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    d = copy.deepcopy(d)
    d["source"]["locator"] = "tracer-minimal.pdf"
    p = tmp_path / "descriptor.json"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (tmp_path / "tracer-minimal.pdf").write_bytes(b"%PDF-1.4 frozen bytes")
    return p


# -- (a) loader round-trip byte-identity (read_only / unchanged_bytes) ----------


def test_loader_roundtrip_byte_identity(tmp_path):
    p = write_fixture(tmp_path, mutated())
    before_descriptor = sha(p.read_bytes())
    before_source = sha((tmp_path / "tracer-minimal.pdf").read_bytes())

    result = dbg.inspect(p)

    assert sha(p.read_bytes()) == before_descriptor
    assert sha((tmp_path / "tracer-minimal.pdf").read_bytes()) == before_source
    assert result.unchanged_bytes is True
    assert result.descriptor_sha256 == before_descriptor
    assert result.source_sha256 == before_source
    # round-trip: the loaded descriptor equals the parsed input document
    assert result.index.descriptor == json.loads(p.read_text(encoding="utf-8"))


def test_loader_rejects_unparsable_descriptor(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    before = sha(p.read_bytes())
    with pytest.raises(dbg.DescriptorParseError):
        dbg.inspect(p)
    assert sha(p.read_bytes()) == before


# -- (b) inspection index resolves region / reading-order / evidence ids --------


def test_index_resolves_region_reading_order_and_evidence_ids(tmp_path):
    p = write_fixture(tmp_path, mutated())
    result = dbg.inspect(p)
    idx = result.index

    assert idx.region("r-body")["kind"] == "paragraph"
    assert idx.region("r-ghost") is None

    edges = idx.reading_order_edges("v-log")
    assert ("r-art", "r-body2", "i-order") in edges

    assert idx.evidence_for_content("c0") == ("e0",)
    assert idx.evidence["e0"]["origin"] == "source"


# -- (c) typed diagnostics: five categories, stable rule IDs, minimal witness ---


def test_typed_diagnostics_emits_all_five_categories(tmp_path):
    clean_result = dbg.inspect(write_fixture(tmp_path / "clean", mutated()))
    categories = {d.category for d in clean_result.diagnostics}
    assert categories <= EXPECTED_CATEGORIES
    passes = [d for d in clean_result.diagnostics if d.category == "pass"]
    assert len(passes) == 1
    assert passes[0].rule_id and passes[0].witness

    result = dbg.inspect(write_fixture(tmp_path / "mixed", mixed()))
    cats = {d.category for d in result.diagnostics}
    assert cats <= EXPECTED_CATEGORIES
    for needed in ("violated", "disputed", "unsupported", "unexamined"):
        assert needed in cats, f"missing category {needed}"
    for d in result.diagnostics:
        assert d.category in EXPECTED_CATEGORIES
        assert d.rule_id, f"{d} lacks stable rule id"
        assert d.witness, f"{d} lacks smallest available witness"
    violated = [d for d in result.diagnostics if d.category == "violated"]
    assert any(d.rule_id == "dsc03.dangling_reference" and d.witness == "rel-bad" for d in violated)
    disputed = [d for d in result.diagnostics if d.category == "disputed"]
    assert any(d.rule_id == "dbg.annotation.disputed" and d.witness == "a-note" for d in disputed)


# -- (d) unexamined content is never reported as pass ---------------------------


def test_unexamined_never_reported_as_pass(tmp_path):
    result = dbg.inspect(write_fixture(tmp_path, mixed()))
    cats = {d.category for d in result.diagnostics}
    assert "unexamined" in cats
    assert "pass" not in cats
