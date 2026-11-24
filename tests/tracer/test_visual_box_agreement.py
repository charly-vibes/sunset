# Purpose: Independent box-agreement statistic tests (sunset-7b4.3, deferred
#   from improve-geometry-render-binding Non-goals; unblocked by
#   add-anchor-derived-identity quantized boxes + add-scale-complete-regions
#   word-level regions).
# Responsibilities: Pin the dsc03.visual.agreement contract: an agreement
#   statistic between two INDEPENDENT box sources on one carrier page — the
#   native word/line descriptor regions (manifest v3, quantized 1/1000pt
#   boxes with word-map source_box provenance) vs observation-derived boxes
#   (content-class-observations records). Verified here: (a) identical box
#   sets agree fully (fraction 1.0, no disagreements); (b) seeded defects —
#   shift, omit, duplicate — each DEGRADE the symmetric agreement fraction
#   with a typed attribution naming the failing region/observation;
#   (c) matching is one-to-one with a declared IoU threshold over quantized
#   integer boxes (exact cross-multiplied ordering, no float tie flips);
#   (d) the outcome vocabulary is exactly agree/differ/unknown/unavailable
#   (unchanged from the coverage oracle); (e) the unknown/unavailable matrix
#   is typed (no native regions, malformed boxes, invalid threshold, missing
#   or invalid observation records, page/frame mismatch, unresolved frame,
#   hypotheses not derived, render unavailable carrying its reason);
#   (f) provenance binding: a corrupted word-map quantized box is a typed
#   provenance-mismatch, while poisoned raw source_box floats never change
#   any outcome (boxes are compared as quantized operative boxes, never raw
#   source_box); (g) identical inputs give byte-identical outcomes across
#   processes; (h) aggregation passes only when every page agrees. A real
#   native run against a real observed page proves the loaders RUN
#   end-to-end (typed outcome, no accuracy/conformance claims).
# Rationale: improve-geometry-render-binding proposal Non-goals ("Independent
#   box agreement ... depend on add-anchor-derived-identity (quantized boxes)
#   and add-scale-complete-regions (word-level regions)"); PROPOSAL-SET.md
#   necessity cuts; document-visual-oracles outcome vocabulary (D5); O-A01
#   (hypothesis entries stay render-derived evidence, disclosed through the
#   record's evidence_class — correlated comparisons can never support
#   accuracy claims). Synthetic quantized boxes are hand-computed so every
#   fraction is exact; no seeds.
"""Independent box-agreement statistic tests (sunset-7b4.3)."""
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import agreement, coverage, content_classes, render
from digitization.native import extract as native_extract

REPO = Path(__file__).resolve().parents[2]
TESTS_DIR = Path(__file__).resolve().parent
PROFILES = TESTS_DIR / "profiles"
FIXTURES = TESTS_DIR / "fixtures" / "visual"
PRISTINE = FIXTURES / "bora-like.pdf"
GEOMETRY = json.loads((PROFILES / "geometry-page-pt.json").read_text())

# --- hand-computed quantized boxes (integer counts of 1/1000 pt) --------------
#
# Four disjoint word boxes on a synthetic page, each area 5e8 quanta^2.
W_A = [100000, 100000, 150000, 110000]
W_B = [200000, 100000, 250000, 110000]
W_C = [100000, 200000, 150000, 210000]
W_D = [200000, 200000, 250000, 210000]
BOXES = (W_A, W_B, W_C, W_D)


def _regions(boxes=BOXES):
    return [{"id": f"r{i}", "kind": "word", "page": 1, "box": list(b)}
            for i, b in enumerate(boxes)]


def _observations(boxes=BOXES):
    return [{"id": f"o{i}", "class": "graphic-hypothesis", "page": 1,
             "box": list(b)} for i, b in enumerate(boxes)]


def _outcome(regions, observations, **kwargs):
    kwargs.setdefault("carrier", "carrier-a")
    kwargs.setdefault("page", 1)
    return agreement.agreement_outcome(regions=list(regions),
                                       observations=list(observations), **kwargs)


# --- real native run (word/line descriptor regions, manifest v3) --------------

@pytest.fixture(scope="module")
def native_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("native")
    src = root / "carrier.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page(width=300, height=400)
    p1.insert_text((30, 50), "alpha beta", fontsize=12)
    p1.insert_text((30, 80), "gamma", fontsize=12)
    p2 = doc.new_page(width=300, height=400)
    p2.insert_text((30, 50), "delta", fontsize=12)
    doc.save(str(src))
    out = root / "run"
    result = native_extract(str(src), str(out))
    assert result["status"] == "text-complete", result
    read = lambda name: json.loads((out / name).read_text(encoding="utf-8"))
    return {"source": src, "manifest": read("manifest.json"),
            "descriptor": read("descriptor.json"), "word_map": read("word-map.json")}


# --- real observation record (committed fixture, real poppler render) --------

@pytest.fixture(scope="module")
def observed():
    return content_classes.observe_page(PRISTINE, GEOMETRY)


# --- (a) identical sources agree fully ----------------------------------------

def test_identical_sources_agree_fully():
    outcome = _outcome(_regions(), _observations())
    assert outcome.status == "agree"
    assert outcome.reason is None
    assert outcome.property == "box-agreement"
    assert outcome.page == 1
    assert outcome.carrier == "carrier-a"
    assert outcome.agreement == 1.0
    assert outcome.disagreements == ()
    assert outcome.min_iou == agreement.MIN_IOU
    assert outcome.degenerate_observations == 0
    assert len(outcome.regions) == 4
    assert all(entry["status"] == "agree" for entry in outcome.regions)
    assert outcome.regions[0]["matched"] == "o0"
    assert outcome.regions[0]["iou"] == 1.0


def test_outcome_vocabulary_is_unchanged():
    assert agreement.STATUSES == ("agree", "differ", "unknown", "unavailable")


# --- (b) seeded defects degrade agreement with typed attribution --------------

def test_shifted_region_differs_below_threshold_with_pair(tmp_path):
    boxes = list(BOXES)
    boxes[1] = [230000, 100000, 280000, 110000]  # W_B shifted +30000 quanta in x
    outcome = _outcome(_regions(boxes), _observations())
    assert outcome.status == "differ"
    # IoU(inter 2e8, union 8e8) = 0.25 < 0.5: region unmatched, pair retained.
    assert outcome.agreement == round(2 * 3 / (4 + 4), 6)
    assert outcome.regions[1] == {"id": "r1", "status": "differ",
                                  "reason": "below-threshold"}
    assert {"kind": "below-threshold", "region": "r1", "observation": "o1",
            "iou": 0.25} in outcome.disagreements
    # The shifted region also vacates its observation: both sides attributed.
    assert {"kind": "unmatched-observation", "observation": "o1"} \
        in outcome.disagreements
    assert len(outcome.disagreements) == 2


def test_fully_shifted_region_differs_without_overlap():
    boxes = list(BOXES)
    boxes[1] = [300000, 100000, 350000, 110000]  # no overlap with any observation
    outcome = _outcome(_regions(boxes), _observations())
    assert outcome.status == "differ"
    assert outcome.agreement == 0.75
    assert outcome.regions[1] == {"id": "r1", "status": "differ",
                                  "reason": "no-overlap"}
    assert {"kind": "no-overlap", "region": "r1"} in outcome.disagreements


def test_omitted_region_degrades_agreement_with_observation_attribution():
    regions = [r for r in _regions() if r["id"] != "r2"]  # omit W_C's region
    outcome = _outcome(regions, _observations())
    assert outcome.status == "differ"
    assert outcome.agreement == round(2 * 3 / (3 + 4), 6)  # 6/7
    assert {"kind": "unmatched-observation", "observation": "o2"} \
        in outcome.disagreements
    assert len(outcome.disagreements) == 1


def test_duplicated_region_degrades_with_duplicate_attribution():
    regions = _regions()
    regions.append({"id": "r0-dup", "kind": "word", "page": 1, "box": list(W_A)})
    outcome = _outcome(regions, _observations())
    assert outcome.status == "differ"
    assert outcome.agreement == round(2 * 4 / (5 + 4), 6)  # 8/9
    # First-input region wins the one-to-one match; the duplicate is typed.
    assert outcome.regions[0]["status"] == "agree"
    assert outcome.regions[4] == {"id": "r0-dup", "status": "differ",
                                  "reason": "duplicate-of:r0"}
    assert {"kind": "duplicate", "region": "r0-dup", "of": "r0"} \
        in outcome.disagreements


def test_duplicates_on_both_sides_agree_fully():
    boxes = (W_A, W_A, W_B, W_B)
    outcome = _outcome(_regions(boxes), _observations(boxes))
    assert outcome.status == "agree"
    assert outcome.agreement == 1.0
    assert outcome.disagreements == ()


# --- (c) declared one-to-one IoU threshold over quantized boxes ---------------

def test_threshold_boundary_is_inclusive_and_declared():
    a = [0, 0, 15000, 10000]
    b = [5000, 0, 20000, 10000]  # IoU = 1e8 / 2e8 = exactly 0.5
    regions = [{"id": "r0", "kind": "word", "page": 1, "box": a}]
    observations = [{"id": "o0", "class": "text", "page": 1, "box": b}]
    assert _outcome(regions, observations, min_iou=0.5).status == "agree"
    strict = _outcome(regions, observations, min_iou=0.500001)
    assert strict.status == "differ"
    assert strict.disagreements[0]["iou"] == 0.5
    assert strict.min_iou == 0.500001


# --- (d) typed unknown / unavailable matrix ------------------------------------

def test_empty_native_side_is_unknown_not_a_pass():
    outcome = _outcome([], _observations())
    assert outcome.status == "unknown"
    assert outcome.reason == "no-native-regions"
    assert outcome.agreement is None
    assert outcome.regions == ()


def test_page_must_be_a_positive_int():
    for bad in (0, -1, True, "1", 1.0):
        outcome = _outcome(_regions(), _observations(), page=bad)
        assert outcome.status == "unknown" and outcome.reason == "page-invalid"


def test_malformed_boxes_are_typed_unknown():
    for box in ([1, 2, 3], [100000.0, 0, 150000, 100000],
                [150000, 0, 100000, 100000], None):
        regions = [{"id": "r0", "kind": "word", "page": 1, "box": box}]
        outcome = _outcome(regions, _observations())
        assert outcome.status == "unknown"
        assert outcome.reason == "native-regions-invalid"
    observations = [{"id": "o0", "class": "text", "page": 1, "box": [0, 0, 0, 0]}]
    outcome = _outcome(_regions(), observations)
    assert outcome.status == "unknown"
    assert outcome.reason == "observation-boxes-invalid"


def test_invalid_threshold_is_typed_unknown():
    for bad in (0, -0.1, 1.5, True, "0.5", None):
        outcome = _outcome(_regions(), _observations(), min_iou=bad)
        assert outcome.status == "unknown"
        assert outcome.reason == "match-threshold-invalid"


def test_empty_observation_side_differs_without_silent_pass():
    outcome = _outcome(_regions(), [])
    assert outcome.status == "differ"
    assert outcome.agreement == 0.0
    assert len(outcome.regions) == 4
    assert all(entry["status"] == "differ" for entry in outcome.regions)
    assert len(outcome.disagreements) == 4


# --- (e) native loader: descriptor regions, manifest v3, provenance -----------

def test_native_regions_parse_real_descriptor_regions(native_run):
    loaded = agreement.native_regions(native_run["descriptor"], 1,
                                      manifest=native_run["manifest"])
    assert loaded.status == "ok" and loaded.reason is None
    assert loaded.degenerate == 0
    kinds = {}
    for item in loaded.items:
        assert isinstance(item["id"], str) and item["page"] == 1
        assert item["kind"] in ("word", "line")
        box = item["box"]
        assert (isinstance(box, list) and len(box) == 4
                and all(type(v) is int for v in box)
                and box[2] > box[0] and box[3] > box[1])
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    assert kinds == {"word": 3, "line": 2}
    # Parsed boxes match the descriptor's selector locators for the same ids.
    locators = {s["target"]: s["locator"] for s in native_run["descriptor"]["selectors"]
                if s["kind"] == "pdf-area"}
    for item in loaded.items:
        assert f"box=[{','.join(str(v) for v in item['box'])}]" \
            in locators[item["id"]]


def test_native_regions_filter_by_page(native_run):
    loaded = agreement.native_regions(native_run["descriptor"], 2,
                                      manifest=native_run["manifest"])
    assert loaded.status == "ok"
    assert len(loaded.items) == 2  # one word + its line on page 2
    assert all(item["page"] == 2 for item in loaded.items)


def test_native_regions_absent_page_is_unknown(native_run):
    loaded = agreement.native_regions(native_run["descriptor"], 5,
                                      manifest=native_run["manifest"])
    assert loaded.items == () and loaded.status == "unknown"
    assert loaded.reason == "no-native-regions"


def test_native_regions_refuse_non_v3_manifest(native_run):
    manifest = dict(native_run["manifest"], version="2")
    loaded = agreement.native_regions(native_run["descriptor"], 1, manifest=manifest)
    assert loaded.status == "unknown"
    assert loaded.reason == "manifest-version-unsupported"


def test_malformed_word_region_is_typed_invalid():
    descriptor = {"regions": [{"id": "x", "kind": "word", "view_id": "v-main"}]}
    loaded = agreement.native_regions(descriptor, 1)
    assert loaded.status == "unknown"
    assert loaded.reason == "native-regions-invalid"


def test_word_map_provenance_binds_quantized_boxes(native_run):
    loaded = agreement.native_regions(
        native_run["descriptor"], 1, manifest=native_run["manifest"],
        word_map=native_run["word_map"])
    assert loaded.status == "ok"
    words = json.loads(json.dumps(native_run["word_map"]))
    words[0]["box"] = [v + 1 for v in words[0]["box"]]
    corrupted = agreement.native_regions(
        native_run["descriptor"], 1, manifest=native_run["manifest"],
        word_map=words)
    assert corrupted.status == "unknown"
    assert corrupted.reason == "provenance-mismatch"


def test_raw_source_box_never_affects_any_outcome(native_run):
    plain = agreement.native_regions(native_run["descriptor"], 1,
                                     manifest=native_run["manifest"])
    words = json.loads(json.dumps(native_run["word_map"]))
    for word in words:
        word["source_box"] = [0.0, 0.0, 0.0, 0.0]  # poisoned raw floats
    poisoned = agreement.native_regions(
        native_run["descriptor"], 1, manifest=native_run["manifest"],
        word_map=words)
    assert poisoned.status == "ok"
    assert poisoned.items == plain.items  # operative quantized boxes only
    base = _outcome(plain.items, _observations())
    other = _outcome(poisoned.items, _observations())
    assert asdict(base) == asdict(other)


# --- (f) observation loader: content-class-observations records ---------------

def test_observation_boxes_parse_real_record(observed):
    loaded = agreement.observation_boxes(observed, page=1, frame="page-1",
                                         classes=("text", "vector", "raster"))
    assert loaded.status == "ok" and loaded.reason is None
    assert loaded.degenerate == 1  # the stroked hairline has zero area
    assert len(loaded.items) == 8  # 4 text spans + 3 fills + 1 raster
    assert loaded.items[0]["box"] == [72000, 696711, 189381, 711825]
    assert loaded.items[0]["class"] == "text"


def test_observation_boxes_load_hypotheses_when_requested(observed):
    loaded = agreement.observation_boxes(observed, page=1, frame="page-1",
                                         classes=("graphic-hypothesis",))
    assert loaded.status == "ok" and loaded.degenerate == 0
    assert len(loaded.items) == 11  # pinned morphology candidates
    assert [71000, 698000, 153000, 710000] in [b["box"] for b in loaded.items]


def test_observation_boxes_filter_classes(observed):
    loaded = agreement.observation_boxes(observed, page=1, frame="page-1",
                                         classes=("text",))
    assert loaded.status == "ok"
    assert len(loaded.items) == 4
    assert {b["class"] for b in loaded.items} == {"text"}


def _record(**overrides):
    record = {
        "kind": "content-class-observations", "version": 1,
        "status": "observed", "reason": None, "page": 1,
        "frame": {"name": "page-1", "status": "resolved", "reason": None},
        "render": {"status": "rendered", "reason": None, "config": {}},
        "evidence_class": "independent",
        "classes": {
            "text": {"role": "carrier-observation", "count": 1, "entries": [
                {"class": "text", "page": 1, "rect_pt": [10.0, 10.0, 20.0, 12.0]}]},
            "graphic-hypothesis": {"role": "hypothesis", "count": 1,
                                   "status": "derived", "method": None, "entries": [
                {"class": "graphic-hypothesis", "page": 1,
                 "rect_pt": [10.0, 20.0, 30.0, 30.0]}]},
        },
    }
    record.update(overrides)
    return record


def test_observation_boxes_success_on_hand_built_record():
    loaded = agreement.observation_boxes(_record(), page=1, frame="page-1",
                                         classes=("text", "graphic-hypothesis"))
    assert loaded.status == "ok"
    assert [b["box"] for b in loaded.items] == [
        [10000, 10000, 20000, 12000], [10000, 20000, 30000, 30000]]


def test_observation_boxes_typed_error_matrix():
    loaded = agreement.observation_boxes(None, page=1, frame="page-1",
                                         classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "observations-missing")
    loaded = agreement.observation_boxes({"kind": "other"}, page=1,
                                         frame="page-1", classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "observations-invalid")
    loaded = agreement.observation_boxes(_record(status="invalid-source"),
                                         page=1, frame="page-1", classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "observations-invalid")
    loaded = agreement.observation_boxes(_record(), page=2, frame="page-1",
                                         classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "page-mismatch")
    loaded = agreement.observation_boxes(_record(), page=1, frame="page-2",
                                         classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "frame-mismatch")
    loaded = agreement.observation_boxes(
        _record(frame={"name": "page-1", "status": "unknown",
                       "reason": "invalid_geometry_frame"}),
        page=1, frame="page-1", classes=("text",))
    assert (loaded.status, loaded.reason) == ("unknown", "frame-unresolved")
    loaded = agreement.observation_boxes(_record(), page=1, frame="page-1",
                                         classes=("notes",))
    assert (loaded.status, loaded.reason) == ("unknown", "observations-invalid")
    # An observed record that measured zero boxes is a measured EMPTY side
    # (the agreement degrades), never a missing record.
    loaded = agreement.observation_boxes(
        _record(classes={"text": {"role": "carrier-observation", "count": 0,
                                  "entries": []}}),
        page=1, frame="page-1", classes=("text",))
    assert loaded.status == "ok" and loaded.items == ()
    assert loaded.degenerate == 0


def test_hypothesis_gating_is_typed():
    classes = {"text": _record()["classes"]["text"]}
    loaded = agreement.observation_boxes(
        _record(classes=classes), page=1, frame="page-1",
        classes=("graphic-hypothesis",))
    assert (loaded.status, loaded.reason) == ("unknown", "hypotheses-not-derived")
    loaded = agreement.observation_boxes(
        _record(render={"status": "unavailable", "reason": "pdftoppm-missing",
                        "config": {}},
                classes={"graphic-hypothesis": {
                    "role": "hypothesis", "count": 0,
                    "status": "render-unavailable", "method": None,
                    "entries": []}}),
        page=1, frame="page-1", classes=("graphic-hypothesis",))
    assert loaded.status == "unavailable"
    assert loaded.reason == "pdftoppm-missing"


def test_degenerate_observation_rects_are_skipped_and_disclosed():
    record = _record()
    record["classes"]["text"]["entries"].append(
        {"class": "text", "page": 1, "rect_pt": [72.0, 600.0, 540.0, 600.0]})
    loaded = agreement.observation_boxes(record, page=1, frame="page-1",
                                         classes=("text",))
    assert loaded.status == "ok"
    assert len(loaded.items) == 1 and loaded.degenerate == 1


# --- (g) end-to-end on real native + observed artifacts -----------------------

def _text_carrier(path):
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((30, 50), "alpha beta gamma", fontsize=12)
    page.insert_text((30, 90), "delta epsilon", fontsize=12)
    doc.save(str(path))


def test_end_to_end_native_regions_vs_observed_hypotheses(tmp_path):
    src = tmp_path / "carrier.pdf"
    _text_carrier(src)
    run = tmp_path / "run"
    result = native_extract(str(src), str(run))
    assert result["status"] == "text-complete", result
    read = lambda name: json.loads((run / name).read_text(encoding="utf-8"))
    native = agreement.native_regions(read("descriptor.json"), 1,
                                      manifest=read("manifest.json"),
                                      word_map=read("word-map.json"))
    assert native.status == "ok"
    record = content_classes.observe_page(src, GEOMETRY)
    observed_boxes = agreement.observation_boxes(
        record, page=1, frame="page-1", classes=("graphic-hypothesis",))
    assert observed_boxes.status == "ok"
    outcome = agreement.agreement_outcome(
        carrier="carrier-t", page=1, regions=native.items,
        observations=observed_boxes.items,
        evidence_class=record["evidence_class"])
    # Typed machinery result only — no accuracy or conformance claim.
    assert outcome.status in ("agree", "differ")
    assert outcome.property == "box-agreement"
    assert outcome.evidence_class == "independent"
    assert outcome.agreement is not None
    assert 0.0 <= outcome.agreement <= 1.0
    assert len(outcome.regions) == len(native.items)
    assert render.supports_accuracy_claim(outcome.evidence_class)
    again = agreement.agreement_outcome(
        carrier="carrier-t", page=1, regions=native.items,
        observations=observed_boxes.items,
        evidence_class=record["evidence_class"])
    assert asdict(again) == asdict(outcome)


# --- (h) determinism across processes ------------------------------------------

def test_identical_inputs_identical_outcomes_across_processes(tmp_path):
    payload = tmp_path / "input.json"
    payload.write_text(json.dumps({"regions": _regions(),
                                   "observations": _observations()}))
    script = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from dataclasses import asdict\n"
        "from dsc03.visual import agreement\n"
        "i = json.load(open(sys.argv[1]))\n"
        "o = agreement.agreement_outcome(carrier='c', page=1,\n"
        "                                regions=i['regions'],\n"
        "                                observations=i['observations'])\n"
        "print(json.dumps(asdict(o), sort_keys=True))\n" % str(REPO)
    )
    runs = [subprocess.run([sys.executable, "-B", "-c", script, str(payload)],
                           capture_output=True, text=True, cwd=REPO)
            for _ in range(2)]
    for run in runs:
        assert run.returncode == 0, run.stderr
    local = agreement.agreement_outcome(carrier="c", page=1,
                                        regions=_regions(),
                                        observations=_observations())
    pinned = json.dumps(asdict(local), sort_keys=True)
    assert runs[0].stdout.strip() == pinned
    assert runs[1].stdout.strip() == pinned


# --- aggregation + evidence-class gate -----------------------------------------

def test_aggregate_blocks_unless_every_page_agrees():
    agree = _outcome(_regions(), _observations())
    differ = _outcome(_regions()[:3], _observations())
    assert agreement.aggregate([agree, agree]).status == "pass"
    blocked = agreement.aggregate([agree, differ])
    assert blocked.status == "blocked"
    assert any("carrier-a page 1: differ" in reason for reason in blocked.reasons)
    unknown = agreement.agreement_outcome(carrier="c", page=2, regions=[],
                                          observations=[])
    blocked = agreement.aggregate([agree, unknown])
    assert blocked.status == "blocked"
    assert any("unknown (no-native-regions)" in reason
               for reason in blocked.reasons)
    assert agreement.aggregate([]).status == "blocked"
    assert agreement.aggregate([]).reasons == ("no-page-outcomes",)


def test_correlated_evidence_never_supports_accuracy_claims():
    regions = _regions()
    observations = [{"id": "o0", "class": "text", "page": 1, "box": list(W_A)}]
    outcome = agreement.agreement_outcome(
        carrier="c", page=1, regions=regions, observations=observations,
        evidence_class=render.evidence_class("pymupdf", "pymupdf"))
    assert outcome.evidence_class == "correlated"
    assert agreement.supports_accuracy_claim(outcome) is False
    independent = agreement.agreement_outcome(
        carrier="c", page=1, regions=regions, observations=observations,
        evidence_class=render.evidence_class("pymupdf", "poppler"))
    assert agreement.supports_accuracy_claim(independent) is True


def test_outcomes_are_also_aggregatable_with_coverage_aggregate():
    # Same family contract: coverage.aggregate consumes agreement outcomes.
    agree = _outcome(_regions(), _observations())
    assert coverage.aggregate([agree]).status == "pass"
