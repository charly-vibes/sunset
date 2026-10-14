# Purpose: Evidence link replay tests for the tracer path (sunset-r68.1.4).
# Responsibilities: Replay the tracer's one evidence link — resolve its bound
#   content and selector ids, resolve the selector's pinned profile from the local
#   registry, and reproduce the anchored observation by applying the declared
#   text-range grammar (unicode-scalar-values, half-open) to the exact target
#   value without normalization; assert typed failures for dangling bindings and
#   malformed ranges.
# Rationale: add-dsc-03 document-evidence "Evidence link resolution" and
#   "Typed profile-defined source selectors" requirements. Byte-unit profiles,
#   transforms and multi-stage lineage are later tickets (sunset-r68.2+).
"""Evidence link replay tests (sunset-r68.1.4)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import evidence, profiles

TRACER = Path(__file__).parent / "fixture_minimal.json"
REGISTRY = profiles.Registry(Path(__file__).parent)


def resolved_tracer():
    from dsc03 import validator
    d = validator.load(TRACER)
    resolved = {}
    for p in d["profiles"]:
        status, artifact = profiles.resolve(p, REGISTRY)
        resolved[p["id"]] = (status, artifact)
    return d, resolved


def test_tracer_evidence_link_resolves_and_replays():
    d, resolved = resolved_tracer()
    e0 = d["evidence"][0]
    status, detail = evidence.replay(e0, d, resolved)
    assert status == "replayed"
    # the text-range anchor [0,5) on "Hello page" reproduces "Hello"
    assert detail["observations"] == {"s0": "Hello"}
    assert detail["content_ids"] == ["c0"]


def test_dangling_selector_binding_fails_typed():
    d, resolved = resolved_tracer()
    d["evidence"][0]["selector_ids"] = ["s-missing"]
    from dsc03 import validator
    assert "dangling_reference" in validator.validate(d)


def test_out_of_bounds_range_is_invalid_selector():
    d, resolved = resolved_tracer()
    d["selectors"][0]["locator"] = "[0,99)"
    status, detail = evidence.replay(d["evidence"][0], d, resolved)
    assert status == "invalid_selector"


def test_reversed_range_is_invalid_selector():
    d, resolved = resolved_tracer()
    d["selectors"][0]["locator"] = "[5,1)"
    status, detail = evidence.replay(d["evidence"][0], d, resolved)
    assert status == "invalid_selector"


def test_unresolved_profile_is_unsupported_at_replay():
    d, resolved = resolved_tracer()
    resolved["p-sel"] = ("unsupported_profile", None)
    status, detail = evidence.replay(d["evidence"][0], d, resolved)
    assert status == "unsupported_profile"
