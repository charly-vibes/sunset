# Purpose: Calibration-record suite (sunset-xzy.6, tasks.md 5.2).
# Responsibilities: Assert the committed calibration record
#   fixtures/visual/calibration.json against re-run reality: (a) it carries all
#   six design-D6 record fields; (b) re-running BOTH shipped oracles
#   (dsc03/visual/coverage.py "ink-coverage", dsc03/visual/masks.py
#   "region-alignment") with the recorded calibration over the recorded
#   carriers reproduces every recorded per-page outcome; (c) the aggregate rule
#   holds — aggregate() NEVER reports pass while any page outcome is
#   unknown/unavailable or the property is uncalibrated, asserted with the REAL
#   committed faint page (visual-strip-faint.pdf), not just synthetic stubs;
#   (d) detection runs live on pages OUTSIDE the threshold-derivation set with
#   the derivation/detection split (and its single recorded raster overlap)
#   declared explicitly (ALIGN-001); (e) unknown cases are surfaced in the
#   record and in the aggregate, never masked corpus-wide.
# Responsibilities (continued): This suite adds NO oracle semantics — the
#   oracles are consumed as shipped, never edited here. Thresholds and timings
#   are AGENT-EXECUTED (measured through the pinned render pipeline); a human
#   pass supersedes.
# Rationale: spec "Calibrated thresholds with per-page outcomes" (thresholds
#   from recorded calibration over varied pinned carriers; per-page AND
#   per-property outcomes; no aggregate pass while any page is
#   unknown/unavailable or its property uncalibrated; scenario "Faint scan"),
#   "Mutation-validated sensitivity" (detection set), "No silent resolution",
#   "Scoped property claims"; design D6 (six record fields), D4
#   (simplification-is-the-tolerance: ink-dilation-2px is part of the recorded
#   render configuration). The faint page is pinned to the honest
#   uncalibrated-mechanism path: its gray-200 ink is invisible under the
#   pinned fixed-threshold-128 binarization, so no usable window exists — the
#   record carries no entry for it and the typed "uncalibrated" reason yields
#   unknown; no outcome is faked.
"""Calibration record suite (sunset-xzy.6, tasks.md 5.2).

The record is authority AND claim: this suite re-runs both shipped visual
oracles over the recorded carriers with the recorded calibration and asserts
the recorded per-page outcomes reproduce exactly (status AND typed reason),
including the real faint page whose outcome is ``unknown`` via the
``uncalibrated`` mechanism. The aggregate rule is asserted both ways: the
calibrated varieties alone aggregate to ``pass`` (positive control — the rule
is not vacuously blocking), and adding the real faint page (or any
unknown/unavailable/differ outcome) blocks it with the blocking page listed.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import coverage, masks, render
from dsc03.visual.render import Binarization, RenderConfig

ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "fixtures" / "visual" / "calibration.json"
PROFILES = Path(__file__).resolve().parent / "profiles"
MUTATION_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "visual"

# Committed calibration record (sunset-xzy.6). Its absence is the RED state
# of this slice: the suite must fail until the record exists.
RECORD = json.loads(RECORD_PATH.read_text())

SIX_FIELDS = ("property", "defect_classes_exerciced", "carriers",
              "per_page_outcomes", "thresholds", "render_configuration")
# Exact oracle-consumed entry shape (_usable_calibration /
# _usable_region_calibration): nothing more is consumed, nothing less works.
ORACLE_ENTRY_KEYS = {"property", "carrier", "page", "min", "max"}
PROPERTIES = ("ink-coverage", "region-alignment")
# The five spec/design page varieties the thresholds must be derived over.
FIVE_VARIETIES = {"native text", "image-only scan", "mixed", "rotated", "faint"}
# xzy.5-pinned class->oracle claim mapping (test_visual_mutations.py).
CLAIMED_CLASSES = {
    "ink-coverage": {"omission", "duplication"},
    "region-alignment": {"shift", "wrong-frame"},
}
FAINT_CARRIER = "visual-strip-faint"

_GEOMETRY_CACHE = {}


def _poppler_executable():
    return shutil.which("pdftoppm") or "/usr/bin/pdftoppm"


def _render_config():
    """The pinned render configuration (identical to the sibling suites)."""
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=_poppler_executable(),
        renderer_version=render.detect_renderer_version(_poppler_executable()),
        dpi=72,
        page=1,
        binarization=Binarization(enabled=True, method="fixed-threshold",
                                  threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


def _geometry(artifact):
    """Load a named geometry artifact declared by the record."""
    if artifact not in _GEOMETRY_CACHE:
        if artifact == "geometry-page-pt":
            path = PROFILES / "geometry-page-pt.json"
        elif artifact == "geometry-rotated-strip":
            path = MUTATION_FIXTURES / "geometry-rotated-strip.json"
        else:
            raise AssertionError(f"unknown geometry artifact: {artifact}")
        _GEOMETRY_CACHE[artifact] = json.loads(path.read_text())
    return _GEOMETRY_CACHE[artifact]


def _carrier(cid):
    matches = [c for c in RECORD["carriers"] if c["id"] == cid]
    assert len(matches) == 1, f"carrier {cid!r} not uniquely recorded"
    return matches[0]


def _threshold_for(property_name, carrier):
    """The recorded oracle-consumable entry for property+carrier, or None."""
    entries = [t for t in RECORD["thresholds"]
               if t["property"] == property_name and t["carrier"] == carrier]
    assert len(entries) <= 1, f"multiple {property_name} entries for {carrier}"
    return entries[0] if entries else None


def _runs(run=None, status=None):
    selected = RECORD["per_page_outcomes"]
    if run is not None:
        selected = [r for r in selected if r["run"] == run]
    if status is not None:
        selected = [r for r in selected if r["status"] == status]
    return selected


def _run_outcome(recorded_run):
    """Re-run ONE recorded oracle run through the shipped oracle as-is."""
    config = _render_config()
    assert config.page == recorded_run["page"]
    rendered = render.render_page(config, ROOT / recorded_run["file"])
    assert isinstance(rendered, render.Rendered), getattr(rendered, "reason", rendered)
    carrier = _carrier(recorded_run["carrier"])
    calibration = _threshold_for(recorded_run["property"], recorded_run["carrier"])
    if recorded_run["property"] == coverage.PROPERTY:
        return coverage.coverage_outcome(
            rendered, carrier=recorded_run["carrier"],
            regions=[dict(r) for r in carrier["regions"]],
            calibration=calibration, geometry=_geometry(recorded_run["geometry"]),
            frame_name=recorded_run["frame"])
    return masks.masks_outcome(
        rendered, carrier=recorded_run["carrier"],
        regions=[dict(r) for r in carrier["regions"]],
        calibration=calibration, geometry=_geometry(recorded_run["geometry"]),
        frame_name=recorded_run["frame"])


def _assert_region_attribution(outcome, recorded_run):
    """Recorded per-region expectations reproduce in the re-run outcome."""
    got = {(e["id"], e["status"]) for e in outcome.regions}
    for rid in recorded_run.get("expected_differ_regions", []):
        assert (rid, "differ") in got, (rid, outcome.regions)
    for rid in recorded_run.get("expected_agree_regions", []):
        assert (rid, "agree") in got, (rid, outcome.regions)


# --- (a) the record carries all six design-D6 fields ---------------------------


def test_record_carries_all_six_d6_fields():
    for field in SIX_FIELDS:
        assert field in RECORD, f"missing D6 field: {field}"
    # Documented mapping: the record covers BOTH shipped oracle properties;
    # each thresholds entry carries its own oracle-consumed "property" key.
    assert isinstance(RECORD["property"], list)
    assert set(RECORD["property"]) == set(PROPERTIES)

    classes = RECORD["defect_classes_exerciced"]
    assert set(classes) == set(PROPERTIES)
    for prop, claimed in CLAIMED_CLASSES.items():
        assert set(classes[prop]) == claimed, prop

    varieties = {c["variety"] for c in RECORD["carriers"]}
    assert FIVE_VARIETIES <= varieties, varieties
    for carrier in RECORD["carriers"]:
        assert (ROOT / carrier["file"]).is_file(), carrier["file"]
        assert carrier["source_simplification"].startswith("ink-dilation-")
        expected = [r["expected"] for r in carrier["regions"]]
        assert "ink" in expected and "no-ink" in expected, carrier["id"]

    assert RECORD["per_page_outcomes"], "no per-page outcomes recorded"
    for run in RECORD["per_page_outcomes"]:
        for key in ("carrier", "file", "page", "property", "run", "geometry",
                    "frame", "status"):
            assert key in run, (key, run)
        assert run["property"] in PROPERTIES
        assert run["run"] in ("derivation", "detection")
        assert run["status"] in ("agree", "differ", "unknown", "unavailable")

    assert RECORD["thresholds"], "no thresholds recorded"
    for entry in RECORD["thresholds"]:
        assert set(entry) == ORACLE_ENTRY_KEYS, entry
        assert entry["property"] in PROPERTIES
        assert isinstance(entry["page"], int) and not isinstance(entry["page"], bool)
        assert isinstance(entry["min"], (int, float))
        assert isinstance(entry["max"], (int, float))
        assert entry["min"] <= entry["max"], entry

    for key in ("renderer_name", "renderer_version", "dpi", "page",
                "binarization", "source_simplification", "extractor_lineage",
                "renderer_lineage", "evidence_class",
                "per_carrier_simplification"):
        assert key in RECORD["render_configuration"], key


def test_render_configuration_matches_the_pinned_runtime_config():
    config = _render_config()
    recorded = RECORD["render_configuration"]
    live = config.to_dict()
    live.pop("renderer_executable")  # resolved via shutil.which at run time
    for key, value in live.items():
        assert recorded[key] == value, (key, recorded[key], value)
    assert recorded["evidence_class"] == config.evidence_class
    # D4: the simplification is part of the recorded render configuration and
    # is recorded per carrier entry — every carrier pinned to the same one.
    for carrier in RECORD["carriers"]:
        recorded_dilation = RECORD["render_configuration"][
            "per_carrier_simplification"][carrier["id"]]
        assert recorded_dilation == config.source_simplification
        assert carrier["source_simplification"] == config.source_simplification


# --- (b) re-running BOTH oracles reproduces every recorded outcome -------------


def test_rerun_reproduces_every_recorded_per_page_outcome():
    reproduced = 0
    for run in RECORD["per_page_outcomes"]:
        outcome = _run_outcome(run)
        assert outcome.status == run["status"], (run, outcome)
        assert outcome.reason == run["reason"], (run, outcome)
        assert outcome.property == run["property"], (run, outcome)
        assert outcome.page == run["page"], (run, outcome)
        assert outcome.carrier == run["carrier"], (run, outcome)
        if run["status"] == "differ":
            _assert_region_attribution(outcome, run)
        reproduced += 1
    derivation = _runs(run="derivation")
    detection = _runs(run="detection")
    assert len(derivation) + len(detection) == reproduced
    # Both oracles are exercised per the recorded property split.
    for prop in PROPERTIES:
        assert any(r["property"] == prop for r in derivation)
        assert any(r["property"] == prop for r in derivation
                   if r["status"] == "agree")


# --- (c) the aggregate rule, with the REAL faint page --------------------------


def test_aggregate_never_passes_while_any_page_is_unknown_unavailable_or_uncalibrated():
    agree_runs = [r for r in _runs(run="derivation") if r["status"] == "agree"]
    assert len(agree_runs) >= 8  # four calibrated varieties x two properties
    agree_outcomes = [_run_outcome(r) for r in agree_runs]
    assert all(o.status == "agree" for o in agree_outcomes)
    # Positive control: calibrated pages alone DO aggregate to pass — the rule
    # below is not vacuously blocking.
    assert coverage.aggregate(agree_outcomes).status == "pass"

    # The REAL faint page: its recorded runs are unknown via "uncalibrated"
    # (no usable calibration exists for it — see the record's faint_mechanism).
    faint_runs = [r for r in _runs()
                  if r["carrier"] == FAINT_CARRIER and r["status"] == "unknown"]
    assert len(faint_runs) == len(PROPERTIES)
    faint_outcomes = [_run_outcome(r) for r in faint_runs]
    for outcome in faint_outcomes:
        assert outcome.status == "unknown"
        assert outcome.reason == "uncalibrated"
        assert outcome.regions == ()

    blocked = coverage.aggregate(agree_outcomes + faint_outcomes)
    assert blocked.status == "blocked"
    assert any(FAINT_CARRIER in reason and "uncalibrated" in reason
               for reason in blocked.reasons), blocked.reasons

    # The full recorded corpus (detection differ runs included) never passes.
    everything = [_run_outcome(r) for r in RECORD["per_page_outcomes"]]
    assert coverage.aggregate(everything).status == "blocked"

    # An aggregate over nothing must never claim a pass either.
    empty = coverage.aggregate([])
    assert empty.status == "blocked"
    assert "no-page-outcomes" in empty.reasons

    # Typed unavailable collapses to neither pass nor fail (synthetic stub is
    # sufficient here; the real-page case above is the faint page).
    stub_agree = coverage.CoverageOutcome(
        status="agree", page=1, evidence_class="independent",
        carrier="stub-carrier", regions=(), reason=None)
    stub_unavailable = coverage.CoverageOutcome(
        status="unavailable", page=1, evidence_class="independent",
        carrier="stub-carrier", regions=(), reason="renderer-missing")
    stub_blocked = coverage.aggregate([stub_agree, stub_unavailable])
    assert stub_blocked.status == "blocked"
    assert any("unavailable" in reason for reason in stub_blocked.reasons)


# --- (d) detection on pages OUTSIDE the threshold-derivation set ---------------


def test_detection_pages_are_outside_the_derivation_set_with_recorded_overlap():
    split = RECORD["derivation_vs_detection"]
    derivation = set(split["derivation_files"])
    detection = set(split["detection_files"])
    overlap = set(split["overlap_files"])
    # The split is declared honestly: overlap == actual intersection.
    assert overlap == derivation & detection, (overlap, derivation & detection)
    detection_only = detection - derivation
    assert detection_only == {
        "tests/tracer/fixtures/visual/visual-strip-shift.pdf",
        "tests/tracer/fixtures/visual/visual-strip-omission.pdf",
        "tests/tracer/fixtures/visual/visual-strip-duplication.pdf",
    }
    # Every detection run's file lives outside the derivation set, except the
    # declared raster overlap (rot90 raster: derived under the TRUE frame,
    # detected under the seeded-wrong frame).
    for run in _runs(run="detection"):
        assert run["file"] in detection
        if run["file"] not in overlap:
            assert run["file"] not in derivation
        # Detection happens against a CALIBRATED property+carrier: thresholds
        # exist and are provenanced from derivation files only — no property
        # is marked calibrated from a detection run (ALIGN-001).
        entry = _threshold_for(run["property"], run["carrier"])
        assert entry is not None, run
        provenance = [p for p in RECORD["threshold_provenance"]
                      if p["property"] == entry["property"]
                      and p["carrier"] == entry["carrier"]]
        assert len(provenance) == 1, provenance
        assert provenance[0]["derivation_file"] in derivation
        assert provenance[0]["derivation_file"] not in detection_only


def test_every_detection_run_reproduces_differ_with_region_attribution():
    detection_runs = _runs(run="detection")
    assert len(detection_runs) == len(CLAIMED_CLASSES), detection_runs
    for run in detection_runs:
        assert run["status"] == "differ" and run["reason"] is None
        outcome = _run_outcome(run)
        assert outcome.status == "differ", (run, outcome)
        assert outcome.reason is None
        _assert_region_attribution(outcome, run)


# --- (e) unknown surfaced in the record, never masked --------------------------


def test_faint_page_unknown_is_surfaced_by_the_record_and_the_aggregate():
    faint = _carrier(FAINT_CARRIER)
    assert faint["variety"] == "faint"
    assert faint["file"] == "tests/tracer/fixtures/visual/visual-strip-faint.pdf"
    assert (ROOT / faint["file"]).is_file()
    # The honest mechanism is pinned in the record: gray-200 ink, invisible
    # under the pinned threshold-128 binarization, measured identically zero.
    measured = faint["measured_under_pinned_render"]
    assert measured["page_fraction_dilated"] == 0.0
    assert measured["strip_gray_level"] == 200
    assert "uncalibrated" in RECORD["faint_mechanism"]

    # Uncalibrated BY RECORD: no threshold entry exists for the faint carrier
    # for either property — nothing was weakened to ease passing.
    for prop in PROPERTIES:
        assert _threshold_for(prop, FAINT_CARRIER) is None

    # Both properties' faint outcomes are recorded as unknown/uncalibrated
    # (surfaced per page AND per property, not folded into an aggregate).
    faint_runs = [r for r in _runs(run="derivation")
                  if r["carrier"] == FAINT_CARRIER]
    assert {r["property"] for r in faint_runs} == set(PROPERTIES)
    for run in faint_runs:
        assert run["status"] == "unknown" and run["reason"] == "uncalibrated"
        outcome = _run_outcome(run)
        assert outcome.status == "unknown"
        assert outcome.reason == "uncalibrated"

    # And the corpus-wide aggregate cannot mask it: blocked, faint listed.
    derivation_outcomes = [_run_outcome(r) for r in _runs(run="derivation")]
    blocked = coverage.aggregate(derivation_outcomes)
    assert blocked.status == "blocked"
    assert sum(FAINT_CARRIER in reason for reason in blocked.reasons) == 2
