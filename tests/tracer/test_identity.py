# Purpose: Anchor-derived identity tests for DSC 0.3 identity profiles
#   (sunset-v0j, add-anchor-derived-identity tasks §2.1-§2.4).
# Responsibilities: Assert ids are derived identically by two independent
#   interpreter processes from one fixed anchor tuple (Requirement: Independent
#   derivation); collision refusal with a witness naming both tuples; position
#   independence; typed malformed-anchor refusals; pinned-registry resolution of
#   the identity profile kind; validator enforcement of the derivation under the
#   identity profile and byte-identical behavior without it.
# Rationale: add-anchor-derived-identity design Decisions 1-2 and the
#   document-identity delta scenarios — ids are functions of anchors, never of
#   position, producer-local counters or operand order.
"""Identity derivation, collision refusal and validator enforcement tests."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import identity, profiles, validator

ROOT = Path(__file__).resolve().parents[2]

ANCHOR = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "selector",
    "page:3/line:12/word:4",
    "p-identity",
    "1",
)

RUN_DERIVE = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[2])\n"
    "from dsc03.identity import derive_id\n"
    "print(derive_id(tuple(json.loads(sys.argv[1])))[1])\n"
)


def _derive_in_fresh_process():
    out = subprocess.run(
        [sys.executable, "-I", "-c", RUN_DERIVE, json.dumps(list(ANCHOR)), str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def test_two_independent_processes_derive_identical_ids():
    first = _derive_in_fresh_process()
    second = _derive_in_fresh_process()
    assert first == second
    assert re.fullmatch(r"a:[0-9a-f]{32}", first)


def test_position_and_wire_form_do_not_change_ids():
    # the id is a function of the anchor tuple only: container shape (tuple vs
    # JSON-wire list) and the anchor's position inside a containing array
    # cannot leak into the derivation
    direct = identity.derive_id(ANCHOR)[1]
    assert identity.derive_id(list(ANCHOR))[1] == direct
    embedded = json.loads(json.dumps([["before"], list(ANCHOR), ["after"]]))[1]
    assert identity.derive_id(tuple(embedded))[1] == direct


def test_forced_truncated_digest_collision_is_refused_with_both_tuples():
    trunc = lambda raw: hashlib.sha256(raw).digest()[:2]  # noqa: E731  16-bit ids collide readily
    # birthday scan: two different anchors whose truncated derivations agree
    first = second = None
    seen = {}
    for n in range(1000):
        candidate = (ANCHOR[0], "region", f"page:1/word:{n}", "p-identity", "1")
        rid = identity.derive_id(candidate, digest=trunc)[1]
        if rid in seen:
            first, second = seen[rid], candidate
            break
        seen[rid] = candidate
    assert first is not None and second is not None and first != second
    registry = identity.IdentityRegistry()
    status, rid = registry.register(first, digest=trunc)
    assert status == "admitted"
    status, witness = registry.register(second, digest=trunc)
    assert status == "collision"
    assert witness["id"] == rid
    assert witness["witness"] == [list(first), list(second)]
    # re-admitting the identical anchor is idempotent, not a collision
    assert registry.register(first, digest=trunc) == ("admitted", rid)


@pytest.mark.parametrize(
    ("anchor", "reason"),
    [
        ((ANCHOR[0], "region", "page:1", "p-identity"), "anchor_arity"),
        ((ANCHOR[0], "region", "page:1", "p-identity", "1", "extra"), "anchor_arity"),
        ("not-a-tuple", "anchor_arity"),
        (("AB" * 32, "region", "page:1", "p-identity", "1"), "anchor_source_digest"),  # uppercase
        (("zz", "region", "page:1", "p-identity", "1"), "anchor_source_digest"),
        ((ANCHOR[0], "", "page:1", "p-identity", "1"), "anchor_field"),
        ((ANCHOR[0], "region", "", "p-identity", "1"), "anchor_field"),
        ((ANCHOR[0], "region", "page:1", "", "1"), "anchor_field"),
        ((ANCHOR[0], "region", "page:1", "p-identity", ""), "anchor_field"),
        ((ANCHOR[0], None, "page:1", "p-identity", "1"), "anchor_field"),
        ((ANCHOR[0], "region", "page:1", "p-identity", 1), "anchor_field"),
    ],
)
def test_malformed_anchor_is_typed_refusal(anchor, reason):
    assert identity.derive_id(anchor) == ("invalid_anchor", reason)
    assert identity.IdentityRegistry().register(anchor) == ("invalid_anchor", reason)


IDENTITY_ARTIFACT = {
    "kind": "identity",
    "version": "1",
    "digest": {"algorithm": "sha256", "truncation_bits": 128, "prefix": "a:"},
}


def _identity_decl(tmp_path, uri, version, sha=None):
    return {
        "id": "p-identity",
        "kind": "identity",
        "uri": uri,
        "version": version,
        "sha256": sha or hashlib.sha256((tmp_path / uri).read_bytes()).hexdigest(),
    }


def test_identity_profile_resolves_through_pinned_registry(tmp_path):
    raw = json.dumps(IDENTITY_ARTIFACT, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (tmp_path / "identity-v1.json").write_bytes(raw)
    status, artifact = profiles.resolve(
        _identity_decl(tmp_path, "identity-v1.json", "1"), profiles.Registry(tmp_path)
    )
    assert status == "resolved"
    assert artifact["digest"]["truncation_bits"] == 128


def test_identity_pin_rejects_drift_and_wrong_digest_form(tmp_path):
    (tmp_path / "identity-v1.json").write_bytes(
        json.dumps(IDENTITY_ARTIFACT, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    newer = dict(IDENTITY_ARTIFACT, version="2")
    (tmp_path / "identity-v2.json").write_bytes(
        json.dumps(newer, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    bits64 = dict(IDENTITY_ARTIFACT, digest=dict(IDENTITY_ARTIFACT["digest"], truncation_bits=64))
    (tmp_path / "identity-bits64.json").write_bytes(
        json.dumps(bits64, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    registry = profiles.Registry(tmp_path)
    # the version-1 pin never resolves against newer registry bytes
    assert profiles.resolve(_identity_decl(tmp_path, "identity-v2.json", "1"), registry)[0] == "unsupported_profile"
    assert profiles.resolve(_identity_decl(tmp_path, "identity-v2.json", "2"), registry)[0] == "resolved"
    # an unimplemented digest form is unsupported, never approximated
    assert profiles.resolve(_identity_decl(tmp_path, "identity-bits64.json", "1"), registry)[0] == "unsupported_profile"
    # substituted bytes under the pinned uri are a digest mismatch
    assert profiles.resolve(_identity_decl(tmp_path, "identity-v1.json", "1", sha="0" * 64), registry)[0] == "profile_digest_mismatch"


# -- validator enforcement (add-anchor-derived-identity §2.4) -----------------------

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ID_PROFILE_ID = "p-id"


def _profile(pid, kind, uri):
    return {
        "id": pid,
        "kind": kind,
        "uri": uri,
        "version": "1",
        "sha256": hashlib.sha256(uri.encode("utf-8")).hexdigest(),
    }


def _anchored(rec_kind, locator, **fields):
    """A record whose id is the derivation of its anchor under (p-id, "1")."""
    if rec_kind != "selector":  # selectors carry their own source_sha256
        fields.pop("source_sha256", None)
    source = fields.get("source_sha256", SHA)
    rec = dict(fields)
    rec["anchor"] = {"record_kind": rec_kind, "locator_path": locator}
    rec["id"] = identity.derive_id((source, rec_kind, locator, ID_PROFILE_ID, "1"))[1]
    return rec


def identity_descriptor():
    content = _anchored("content", "raw:[0,5)", kind="text", value="Hello")
    selector = _anchored(
        "selector", "[0,5)",
        kind="text-range",
        profile_id="p-sel",
        source_sha256=SHA,
        target=content["id"],
    )
    selector["locator"] = "[0,5)"
    root = _anchored("region", "doc:root", view_id="v-log", kind="article")
    evidence = _anchored(
        "evidence", "urn:example:src",
        origin="source",
        source_ref="urn:example:src",
        content_ids=[content["id"]],
        selector_ids=[selector["id"]],
    )
    return {
        "version": "0.3",
        "id": "identity-tracer",
        "source": {"format": "application/pdf", "sha256": SHA, "locator": "fixtures/identity.pdf"},
        "views": [{"id": "v-log", "kind": "logical", "root": root["id"]}],
        "regions": [root],
        "contents": [content],
        "relations": [],
        "annotations": [],
        "evidence": [evidence],
        "vocabularies": [],
        "selectors": [selector],
        "interpretations": [],
        "coverage": [],
        "profiles": [_profile("p-sel", "selector", "profiles/selector-text-scalar.json"), _profile(ID_PROFILE_ID, "identity", "profiles/identity-v1.json")],
    }


def test_identity_descriptor_with_correct_derived_ids_is_valid():
    assert validator.validate(identity_descriptor()) == []


def test_wrong_derived_id_is_identity_mismatch():
    d = identity_descriptor()
    d["evidence"][0]["id"] = "a:" + "0" * 32  # evidence id is referenced nowhere else
    assert validator.validate(d) == ["identity_mismatch"]


def test_missing_anchor_is_identity_anchor_missing():
    d = identity_descriptor()
    del d["selectors"][0]["anchor"]
    assert validator.validate(d) == ["identity_anchor_missing"]


def test_malformed_anchor_wire_form_is_invalid_shape():
    d = identity_descriptor()
    d["contents"][0]["anchor"] = {"record_kind": "content"}  # locator_path missing
    assert validator.validate(d) == ["invalid_shape"]


def test_exact_text_exception_survives_the_anchor_field():
    # text content values stay exempt from the NFC walk under the identity profile
    d = identity_descriptor()
    d["contents"][0]["value"] = "a\u0301"  # non-NFC ("á" decomposed)
    assert validator.validate(d) == []


def test_same_descriptor_without_identity_profile_is_valid_unchanged():
    d = identity_descriptor()
    d["profiles"] = [p for p in d["profiles"] if p["kind"] != "identity"]
    assert validator.validate(d) == []
