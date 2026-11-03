# Purpose: Integration suite — visual-oracle results as a SEPARATE evidence
#   class in demo/evaluation reports (sunset-xzy.7, tasks.md 6.1).
# Responsibilities: Assert that dsc03/visual/reports.py record() adds a
#   distinct `visual_oracles` section (per property/page outcome status,
#   reasons, evidence-class label, aggregate status + blocker reasons, explicit
#   non-substitution note) to a report dict while leaving every pre-existing
#   section unchanged and never mutating its input; that honest
#   unknown/uncalibrated statuses pass through verbatim (never upgraded,
#   dropped, or masked by the aggregate — SCOPE-002); and that the section is
#   INERT with respect to conformance labels: dsc03.conformance.classify
#   output is identical with and without visual-oracle data, including a
#   demonstration suite with passing visual oracles but no independent readers
#   (label stays "incomplete", readers still listed missing), and no oracle
#   outcome (agree/blocked/unknown) can toggle real_carrier_conformance,
#   workflow_benefit, or any claim string.
# Rationale: spec "Distinct evidence class in demonstrations" (visual results
#   recorded separately from reader agreement, extractor comparison and
#   reviewed anchor mapping, never substituting for any of them), scenario
#   "Oracles cannot complete a suite", "Labeled evidence class" (correlated
#   demonstrates sensitivity, never accuracy), "No silent resolution",
#   "Scoped property claims", "No false claims". PLUMBING slice: no oracle
#   semantics change, no threshold change, no label change — classify() itself
#   is consumed as shipped, never edited here. Outcomes are built from the REAL
#   typed classes (dsc03/visual/coverage.py CoverageOutcome,
#   dsc03/visual/masks.py AlignmentOutcome) reusing the committed calibration
#   record's shape (fixtures/visual/calibration.json), including its real
#   faint-page uncalibrated → unknown entries. AGENT-EXECUTED: nothing here
#   produces human evidence; a human pass supersedes.
"""Visual-oracle report integration tests (sunset-xzy.7, tasks.md 6.1)."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import conformance
from dsc03.visual import coverage, masks, reports
from dsc03.visual.render import evidence_class as render_evidence_class

REPO = Path(__file__).resolve().parents[2]
RECORD = json.loads((REPO / "fixtures" / "visual" / "calibration.json").read_text())
PINNED_CLASS = RECORD["render_configuration"]["evidence_class"]

# The real typed outcome class per recorded property.
OUTCOME_CLS = {
    "ink-coverage": coverage.CoverageOutcome,
    "region-alignment": masks.AlignmentOutcome,
}


def _entries(carrier=None, statuses=None, run=None):
    """Select recorded per-page outcomes from the committed calibration record."""
    picked = []
    for entry in RECORD["per_page_outcomes"]:
        if carrier is not None and entry["carrier"] != carrier:
            continue
        if statuses is not None and entry["status"] not in statuses:
            continue
        if run is not None and entry.get("run") != run:
            continue
        picked.append(entry)
    return picked


def _regions(entry):
    """Region verdicts in the documented outcome shape (agree|differ, in order)."""
    regions = [{"id": rid, "status": "agree"}
               for rid in entry.get("expected_agree_regions", [])]
    regions += [{"id": rid, "status": "differ"}
                for rid in entry.get("expected_differ_regions", [])]
    return tuple(regions)


def _outcome(entry):
    """Build the real typed outcome for a recorded per-page entry."""
    return OUTCOME_CLS[entry["property"]](
        status=entry["status"], property=entry["property"], page=entry["page"],
        evidence_class=PINNED_CLASS, carrier=entry["carrier"],
        regions=_regions(entry), reason=entry["reason"],
    )


def passing_outcomes():
    """Both properties agree on the recorded calibrated derivation carrier."""
    return [_outcome(e) for e in _entries("visual-strip", run="derivation")]


def faint_outcomes():
    """The REAL uncalibrated faint page: unknown via the typed 'uncalibrated' reason."""
    return [_outcome(e) for e in _entries("visual-strip-faint")]


def blocked_outcomes():
    """A detection differ page blocks the aggregate (recorded omission run)."""
    return [_outcome(e) for e in _entries(statuses={"differ"})]


def sample_report():
    """A report dict with the four report.assess sections, honestly minimal."""
    return {
        "schema": {"status": "valid", "reasons": []},
        "profiles": {"status": "resolved", "unresolved": []},
        "coverage": {"status": "pass", "reasons": [], "summaries": {},
                     "source_coverage": "total"},
        "interpretation": {"by_annotation": {}, "counts": {}},
    }


# --- (a) distinct section; pre-existing sections byte-for-byte unchanged -----


def test_record_adds_distinct_visual_oracles_section_without_touching_existing():
    report = sample_report()
    snapshot = copy.deepcopy(report)
    outcomes = passing_outcomes()

    recorded = reports.record(report, outcomes)

    # The section exists and is the ONLY addition.
    assert "visual_oracles" in recorded
    assert sorted(recorded) == sorted(snapshot) + ["visual_oracles"]

    section = recorded["visual_oracles"]
    entries = section["outcomes"]
    assert len(entries) == len(outcomes)
    for entry, outcome in zip(entries, outcomes):
        assert entry["property"] == outcome.property
        assert entry["carrier"] == outcome.carrier
        assert entry["page"] == outcome.page
        assert entry["status"] == outcome.status == "agree"
        assert entry["reason"] == outcome.reason is None
        assert entry["evidence_class"] == outcome.evidence_class == PINNED_CLASS
        assert [r["id"] for r in entry["regions"]] == ["ink-strip", "blank-lower"]
        assert all(r["status"] == "agree" for r in entry["regions"])
    # All agree over a calibrated corpus: the real aggregate rule passes it.
    assert section["aggregate"]["status"] == "pass"
    assert section["aggregate"]["reasons"] == []
    # The section label is the pinned render evidence class (poppler vs pymupdf).
    assert section["evidence_class"] == PINNED_CLASS
    assert PINNED_CLASS in ("correlated", "independent")
    # The explicit non-substitution note names every conformance input this
    # section does NOT provide.
    note = section["non_substitution"]
    for absent in ("real_carriers", "independent_readers", "extractor_comparison",
                   "anchor_mapping_reviewed"):
        assert absent in note

    # Every pre-existing section is unchanged, and the input was not mutated.
    for key, value in snapshot.items():
        assert recorded[key] == value, key
    assert report == snapshot
    assert "visual_oracles" not in report

    # The evidence-class label passes through per entry via the render rule —
    # a correlated outcome is recorded as correlated, never relabeled.
    correlated = coverage.CoverageOutcome(
        status="agree", property="ink-coverage", page=1,
        evidence_class=render_evidence_class("pymupdf", "pymupdf"),
        carrier="visual-strip", regions=(), reason=None)
    assert render_evidence_class("pymupdf", "pymupdf") == "correlated"
    mixed = reports.record(sample_report(), list(passing_outcomes())[:1] + [correlated])
    labels = {e["evidence_class"] for e in mixed["visual_oracles"]["outcomes"]}
    assert labels == {"independent", "correlated"}
    assert mixed["visual_oracles"]["evidence_class"] == "mixed"


# --- (b) honest statuses verbatim (SCOPE-002) --------------------------------


def test_unknown_uncalibrated_recorded_verbatim_and_blocks_aggregate():
    outcomes = faint_outcomes()
    assert outcomes, "the record must document the faint page"
    for outcome in outcomes:
        assert outcome.status == "unknown"
        assert outcome.reason == "uncalibrated"
        assert outcome.carrier == "visual-strip-faint"

    recorded = reports.record(sample_report(), outcomes)
    section = recorded["visual_oracles"]
    entries = section["outcomes"]
    assert len(entries) == len(outcomes)
    for entry in entries:
        # Verbatim: never upgraded, never dropped, never masked.
        assert entry["status"] == "unknown"
        assert entry["reason"] == "uncalibrated"
    assert section["aggregate"]["status"] == "blocked"
    assert any("uncalibrated" in reason for reason in section["aggregate"]["reasons"])
    assert section["aggregate"]["status"] != "pass"


def test_empty_outcome_set_is_recorded_blocked_never_pass():
    recorded = reports.record(sample_report(), [])
    assert recorded["visual_oracles"]["aggregate"]["status"] == "blocked"
    assert recorded["visual_oracles"]["aggregate"]["reasons"] == ["no-page-outcomes"]


# --- (c) label inertness — the spec scenario ---------------------------------


def _suite(one_reader=True):
    """A 0.3 contract demonstration suite, one reader short of conformance."""
    suite = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "migration": True, "adversarial_corpus": True,
        "real_carriers": True, "extractor_comparison": True,
        "anchor_mapping_reviewed": True,
        "independent_readers": 1 if one_reader else 0,
    }
    return suite


def test_classify_identical_with_and_without_visual_oracle_key():
    base = _suite()
    without = conformance.classify(dict(base))
    with_visual = conformance.classify(reports.record(dict(base), passing_outcomes()))
    assert with_visual == without
    assert with_visual["status"] == "incomplete"
    assert "two independent readers" in with_visual["missing"]
    assert with_visual["real_carrier_conformance"] is False


def test_passing_oracles_with_no_independent_readers_stay_incomplete():
    base = _suite(one_reader=False)
    suite = reports.record(dict(base), passing_outcomes())
    result = conformance.classify(suite)
    assert result["status"] == "incomplete"
    assert "two independent readers" in result["missing"]
    assert result["real_carrier_conformance"] is False
    assert result == conformance.classify(dict(base))


# --- (d) no substitution, whatever the oracle outcomes -----------------------


def test_labels_identical_across_agree_blocked_unknown_outcomes():
    base = _suite()
    reference = conformance.classify(dict(base))
    scenarios = {
        "agree": passing_outcomes(),
        "blocked": blocked_outcomes(),
        "unknown": faint_outcomes(),
    }
    for name, outcomes in scenarios.items():
        suite = reports.record(dict(base), outcomes)
        result = conformance.classify(suite)
        assert result == reference, name
        assert result["real_carrier_conformance"] is False
        assert result["workflow_benefit"] == "unproven"


def test_visual_data_cannot_toggle_complete_suite_labels_either_way():
    complete = _suite()
    complete.update({
        "independent_readers": 2, "first_consumer_demo": True,
        "native_output_baseline": True,
        "demo_result": {"functional_gates_passed": True, "review_time_delta": 0},
    })
    reference = conformance.classify(dict(complete))
    assert reference["status"] == "complete"
    assert reference["real_carrier_conformance"] is True

    # Adding visual-oracle data changes nothing; removing it again changes
    # nothing back — the section is inert on labels in BOTH directions.
    with_visual = conformance.classify(
        reports.record(dict(complete), passing_outcomes()))
    assert with_visual == reference
    blocked = conformance.classify(
        reports.record(dict(complete), faint_outcomes()))
    assert blocked == reference
    assert with_visual["workflow_benefit"] == reference["workflow_benefit"]
    assert with_visual["claims"] == reference["claims"]
