# Purpose: sunset-xx7.4 Part B — independent second-reader agreement harness.
#   Recomputes, from the golden fixture INPUTS only, the canonical comparison
#   outputs via the shipped public API (dsc03.compare), and compares them
#   against the stored goldens.
# Responsibilities: load each golden bundle; rebuild ComparatorSpec and
#   ComparisonInputs strictly from the stored bundle; re-run scoped_compare +
#   export_counterexample; canonicalize (sorted keys, no timestamps) and diff
#   field-by-field; classify every disagreement explicitly with BOTH sides
#   recorded — never elect a winner; emit an AGENT-EXECUTED-labeled agreement
#   record (.org). Run: python3 -B -m dsc03.second_reader
# Rationale: the shipped tracer tests were agent-executed too; this module is
#   a second, independently written reader over the same public API. Agreement
#   here is machine-vs-stored-golden only. OWNER GATE ON AGREEMENT RESULTS
#   REMAINS OPEN — a human pass supersedes; this is NOT a claim of
#   human-equivalent independent agreement.
"""Independent second-reader agreement harness for the debugger goldens."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dsc03.compare import ComparatorSpec, ComparisonInput, export_counterexample, scoped_compare  # noqa: E402

GOLDENS = ROOT / "fixtures" / "debugger-goldens"
AGREEMENT_ORG = GOLDENS / "second-reader-agreement.org"

# Canonicalization declaration: both sides are serialized with sorted keys,
# fixed indent, no timestamps (the goldens contain none by construction).
def canonical(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=1) + "\n").encode("utf-8")


@dataclass
class GoldenReport:
    golden: str
    status: str  # agree | disagree | not_replayable
    discrepancies: list = field(default_factory=list)
    note: str = ""


def _diff(path: str, stored, recomputed, out: list) -> None:
    """Field-level diff; records both sides, elects no winner."""
    if type(stored) is not type(recomputed):
        out.append({"path": path, "stored": stored, "recomputed": recomputed,
                    "class": "type-mismatch"})
        return
    if isinstance(stored, dict):
        for key in sorted(set(stored) | set(recomputed)):
            if key not in stored or key not in recomputed:
                out.append({"path": f"{path}.{key}", "stored": stored.get(key),
                            "recomputed": recomputed.get(key), "class": "present-in-one-side"})
            else:
                _diff(f"{path}.{key}", stored[key], recomputed[key], out)
    elif isinstance(stored, list):
        if stored != recomputed:
            out.append({"path": path, "stored": stored, "recomputed": recomputed,
                        "class": "list-value"})
    elif stored != recomputed:
        out.append({"path": path, "stored": stored, "recomputed": recomputed,
                    "class": "scalar-value"})


def _inputs_from_bundle(bundle: dict) -> tuple:
    """Rebuild ComparisonInputs strictly from the stored bundle's inputs."""
    def one(side: dict) -> ComparisonInput:
        return ComparisonInput(side["endpoint_type"], side["payload"],
                               side.get("descriptor_sha256", ""),
                               side.get("source_sha256", ""))
    return one(bundle["inputs"]["left"]), one(bundle["inputs"]["right"])


def _spec_from_bundle(bundle: dict) -> ComparatorSpec:
    w = bundle["witness"]
    return ComparatorSpec(w["comparator"]["id"], w["comparator"]["version"],
                          tuple(w["endpoint_types"]), tuple(w["observable_scope"]))


def recompute_golden(path: Path) -> GoldenReport:
    stored = json.loads(path.read_text(encoding="utf-8"))
    name = path.name
    if not stored["witness"].get("replayable", True):
        # Golden withholds its own source payloads: recomputation from inputs
        # is impossible by design. Classified explicitly — never counted as
        # agreement or silent disagreement.
        return GoldenReport(name, "not_replayable",
                            note="inputs redacted in stored golden "
                                 "(redaction.omitted); recomputation skipped")

    left, right = _inputs_from_bundle(stored)
    spec = _spec_from_bundle(stored)
    outcome = scoped_compare(spec, left, right)
    recomputed = export_counterexample(outcome, spec, left, right)

    # Provenance is generator metadata, not recomputed output: excluded from
    # the comparison scope on both sides (declared canonicalization).
    stored_cmp = {k: v for k, v in stored.items() if k != "provenance"}
    diffs: list = []
    _diff("", stored_cmp, recomputed, diffs)
    if canonical(stored_cmp) == canonical(recomputed):
        return GoldenReport(name, "agree")
    return GoldenReport(name, "disagree", discrepancies=diffs)


def run_agreement() -> list:
    return [recompute_golden(p) for p in sorted(GOLDENS.glob("golden-*.json"))]


def write_agreement_org(reports: list, out_path: Path = AGREEMENT_ORG) -> None:
    agree = sum(r.status == "agree" for r in reports)
    disagree = sum(r.status == "disagree" for r in reports)
    not_replayable = sum(r.status == "not_replayable" for r in reports)
    lines = [
        "#+title: Second-reader agreement — sunset-xx7.4 Part B (AGENT-EXECUTED)",
        "",
        "* Provenance",
        "- Agent/model :: z-ai/glm-5.3-flash via pi (non-interactive)",
        "- Date :: 2026-10-15",
        "- Session :: subagent:sunset-xx7.4b:impl",
        "- Method :: public-API recompute (dsc03.compare scoped_compare +"
        " export_counterexample from stored golden INPUTS) vs stored goldens;",
        "  canonicalization = sorted keys, indent 1, no timestamps;",
        "  provenance section excluded from comparison scope (generator metadata).",
        "- Independence :: second reader written from the public API only,"
        " independent of tests/tracer/test_debugger_a11y.py and"
        " tests/tracer/test_compare.py (not read).",
        "",
        "* Results",
        f"- Agree :: {agree}",
        f"- Disagree :: {disagree}",
        f"- Not replayable (classified, excluded from agreement counts) :: {not_replayable}",
        "",
    ]
    for r in reports:
        lines.append(f"** {r.golden} — {r.status}")
        if r.note:
            lines.append(f"  - Note :: {r.note}")
        for d in r.discrepancies:
            lines.append(f"  - Discrepancy :: path={d['path']} class={d['class']}"
                         f" stored={json.dumps(d['stored'], sort_keys=True)}"
                         f" recomputed={json.dumps(d['recomputed'], sort_keys=True)}")
    lines += [
        "",
        "* Owner gate",
        "- OWNER GATE ON AGREEMENT RESULTS REMAINS OPEN — human pass supersedes.",
        "- This record is machine-vs-stored-golden agreement by an agent-executed"
        " second reader; it is NOT a claim of human-equivalent independent agreement.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    reports = run_agreement()
    write_agreement_org(reports)
    for r in reports:
        print(f"{r.golden}: {r.status}"
              + (f" ({len(r.discrepancies)} discrepancies)" if r.discrepancies else ""))
    return 1 if any(r.status == "disagree" for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
