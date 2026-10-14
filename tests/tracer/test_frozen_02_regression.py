# Purpose: Regression proving the frozen 0.2 validator rejects 0.3 descriptors (sunset-r68.3).
# Responsibilities: Run spec/document-model-specodelic-v3/validator.py against a valid
#   0.3 descriptor and assert invalid + 0.2 outcome vocabulary; assert its fixture
#   suite still passes untouched.
# Rationale: add-dsc-03 document-core "Version dispatch" scenario — the 0.2 validator
#   is never upgraded in place; tasks.md item 1.2.
"""Frozen 0.2 validator regression (sunset-r68.3): rejects 0.3, stays untouched."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "spec" / "document-model-specodelic-v3" / "validator.py"
TRACER = Path(__file__).parent / "fixture_minimal.json"


def run_frozen(*args):
    return subprocess.run(
        [sys.executable, str(FROZEN), *args],
        capture_output=True, text=True, cwd=REPO,
    )


def test_frozen_fixture_suite_still_passes():
    r = run_frozen("test")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS 11 descriptor fixtures" in r.stdout


def test_frozen_rejects_valid_03_descriptor():
    r = run_frozen(str(TRACER))
    assert r.returncode == 1, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["status"] == "invalid"
    # 0.2 outcome vocabulary: shape error for the five new arrays / version
    assert "invalid_shape" in out["reasons"]
