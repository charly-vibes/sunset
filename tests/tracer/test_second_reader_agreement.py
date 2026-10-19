"""Second-reader agreement tests — sunset-xx7.4 Part B (AGENT-EXECUTED).

Independently written from the public dsc03.compare API; the shipped tracer
tests (test_debugger_a11y.py, test_compare.py) were NOT read.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDENS = ROOT / "fixtures" / "debugger-goldens"

from dsc03.second_reader import AGREEMENT_ORG, canonical, run_agreement  # noqa: E402


def test_second_reader_canonical_outputs_match_goldens():
    """(a) Replayable goldens: recomputed witness+inputs byte-identical to the
    stored golden after declared canonicalization (sorted keys, no timestamps,
    provenance excluded as generator metadata)."""
    reports = {r.golden: r for r in run_agreement()}
    replayable = [p for p in sorted(GOLDENS.glob("golden-*.json"))
                  if json.loads(p.read_text())["witness"].get("replayable", True)]
    assert replayable, "expected at least one replayable golden"
    for p in replayable:
        assert reports[p.name].status == "agree", (
            f"{p.name}: {reports[p.name].discrepancies}")


def test_every_disagreement_is_classified_no_silent_winner():
    """(b) Any non-agree golden is explicitly classified; discrepancies always
    carry BOTH stored and recomputed values — the record elects no winner."""
    for r in run_agreement():
        assert r.status in {"agree", "disagree", "not_replayable"}
        if r.status == "disagree":
            assert r.discrepancies, "disagreement without classified fields"
            for d in r.discrepancies:
                assert "stored" in d and "recomputed" in d and "class" in d
        if r.status == "not_replayable":
            assert r.note, "non-replayable golden must be explained, not skipped silently"


def test_canonicalization_is_deterministic_and_lossless_shape():
    assert canonical({"b": 1, "a": 2}) == b'{\n "a": 2,\n "b": 1\n}\n'
    stored = json.loads((GOLDENS / "golden-02-wrong-order-counterexample.json").read_text())
    assert canonical(stored).endswith(b"\n") and b"timestamp" not in canonical(stored)


def test_agreement_record_written_and_labeled():
    """(c) The agreement record exists, is agent-executed-labeled, and records
    the owner ruling (agreement gate PASSED and CLOSED, 2026-10-19)."""
    text = AGREEMENT_ORG.read_text(encoding="utf-8")
    assert "AGENT-EXECUTED" in text
    assert "z-ai/glm-5.3-flash" in text
    assert "subagent:sunset-xx7.4b:impl" in text
    assert "OWNER RULING 2026-10-19: gate PASSED and CLOSED" in text
