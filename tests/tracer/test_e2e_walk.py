# Purpose: End-to-end walking-skeleton test for the DSC 0.3 tracer bullet (sunset-r68.1.5).
# Responsibilities: Walk the full tracer path — parse descriptor, validate schema,
#   resolve every declared profile via pinned local resolution, replay the
#   evidence link — and assert each stage; assert the frozen 0.2 validator still
#   passes its 11 fixtures untouched.
# Rationale: sunset-r68.1 acceptance criterion: one automated test proves the 0.3
#   pipeline shape end-to-end (descriptor -> validate -> profile resolve -> evidence
#   replay). Deliberately excludes adapters, coverage inventories, benchmarks and
#   migration (sunset-r68 follow-ups).
"""Tracer e2e walk: descriptor -> validate -> profile resolve -> evidence replay."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import evidence, profiles, validator

REPO = Path(__file__).resolve().parents[2]
TRACER = Path(__file__).parent / "fixture_minimal.json"
REGISTRY = profiles.Registry(Path(__file__).parent)


def run_frozen():
    return subprocess.run(
        [sys.executable, str(REPO / "spec" / "document-model-specodelic-v3" / "validator.py"), "test"],
        capture_output=True, text=True, cwd=REPO,
    )


def test_tracer_walks_end_to_end():
    d = validator.load(TRACER)
    # stage 1: 0.3 schema validation
    assert validator.validate(d) == []
    # stage 2: pinned local profile resolution (no network, no latest fallback)
    resolved = {}
    for p in d["profiles"]:
        status, artifact = profiles.resolve(p, REGISTRY)
        assert status == "resolved", p["id"]
        resolved[p["id"]] = (status, artifact)
    # stage 3: evidence link replay reproduces the anchored observation
    for ev in d["evidence"]:
        status, detail = evidence.replay(ev, d, resolved)
        assert status == "replayed", ev["id"]
        assert detail["observations"] == {"s0": "Hello"}


def test_frozen_02_validator_still_passes_untouched():
    r = run_frozen()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS 11 descriptor fixtures" in r.stdout
