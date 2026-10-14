# Purpose: Adversarial corpus + two-reader canonical-byte agreement + pinned
#   anchor-matched extractor comparison (sunset-r68.12, tasks.md 5.1 + 5.2).
# Responsibilities: dsc03.corpus builds the adversarial corpus required by
#   document-conformance (columns, page continuation, shared pages, OCR/native,
#   poetry, EPUB links, conflicting interpretations, coordinate transforms,
#   roundtrip, omission, replay, exact Unicode text) and gates it; dsc03.canonical
#   provides two independently implemented descriptor readers that MUST emit
#   identical canonical bytes for the same snapshot (ids, array order and exact
#   — including non-NFC — text preserved); dsc03.projection compares extractor
#   outputs through a pinned projection that matches observations by resolved
#   source anchors or an explicit reviewed mapping — never by snapshot-local ids
#   or label similarity — and reports per-observable matches/FP/FN/unresolved
#   with competing interpretations retained.
# Rationale: add-dsc-03 document-conformance "Adversarial corpus", "Ambiguity can
#   pass", "Reader independence". MACHINERY-ONLY: the corpus descriptors and
#   extractor outputs are machine-built; the anchor mapping is UNREVIEWED until
#   the HITL pass (r68.12 review), so no real-carrier conformance is claimed.
"""Adversarial corpus, canonical readers, pinned projection (sunset-r68.12)."""
import copy
import hashlib
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import canonical, conformance, corpus, evidence, projection, validator

REPO = Path(__file__).resolve().parents[2]

REQUIRED_CASES = {
    "columns", "page-continuation", "shared-pages", "ocr-native", "poetry",
    "epub-links", "conflicting-interpretations", "coordinate-transforms",
    "roundtrip", "omission", "replay", "exact-unicode",
}


# -- adversarial corpus (5.1) -----------------------------------------------------
def _built():
    with tempfile.TemporaryDirectory() as out:
        return corpus.build(Path(out))


def test_corpus_covers_all_required_adversarial_cases():
    cases = _built()
    gate = corpus.gate(cases)
    assert gate["status"] == "complete"
    assert gate["missing"] == []
    assert REQUIRED_CASES <= set(cases)


def test_corpus_case_missing_makes_gate_incomplete():
    cases = _built()
    del cases["columns"]
    gate = corpus.gate(cases)
    assert gate["status"] == "incomplete"
    assert gate["missing"] == ["columns"]


def test_corpus_descriptors_are_schema_valid():
    for name, case in _built().items():
        assert validator.validate(case["descriptor"]) == [], name


# -- two independent readers (5.2) ---------------------------------------------------
def test_two_readers_emit_identical_canonical_bytes():
    for name, case in _built().items():
        d = case["descriptor"]
        assert canonical.reader_a(d) == canonical.reader_b(d), name


def test_canonical_bytes_roundtrip_stable():
    for name, case in _built().items():
        d = case["descriptor"]
        raw = canonical.reader_a(d)
        again = canonical.reader_b(_loads(raw))
        assert again == raw, name


def _loads(raw):
    import json

    return json.loads(raw.decode("utf-8"))


def test_exact_non_nfc_text_survives_both_readers_unchanged():
    cases = _built()
    value = next(
        c["value"] for c in cases["exact-unicode"]["descriptor"]["contents"]
        if c["kind"] == "text"
    )
    assert unicodedata.normalize("NFC", value) != value  # genuinely non-NFC
    for reader in (canonical.reader_a, canonical.reader_b):
        assert reader(cases["exact-unicode"]["descriptor"]).decode("utf-8").count(value) >= 1


def test_readers_disagree_if_code_paths_diverge_is_detectable():
    # mutation check: a descriptor with reordered arrays must yield different
    # bytes (readers preserve array order; a change is visible, not normalized)
    cases = _built()
    d = copy.deepcopy(cases["columns"]["descriptor"])
    raw = canonical.reader_a(d)
    d["contents"] = list(reversed(d["contents"]))
    assert canonical.reader_a(d) != raw


# -- pinned anchor-matched extractor comparison (5.2) --------------------------------
def _extractor(extractor_id, version, observations):
    return {
        "extractor_id": extractor_id,
        "extractor_version": version,
        "observations": observations,
    }


def _obs(local_id, observable, anchors, values, alternatives=()):
    return {
        "id": local_id,
        "observable": observable,
        "anchors": anchors,
        "values": values,
        "alternatives": list(alternatives),
    }


PIN = {
    "projection_id": "sunset-common-projection",
    "version": "1",
    "projection_sha256": "a" * 64,
    "source_sha256": "b" * 64,
}


def test_anchor_match_across_different_local_ids():
    a = _extractor("alpha", "1", [_obs("a7", "page-text", ["sha256:#page:1"], ["Hello"])])
    b = _extractor("beta", "9", [_obs("b2", "page-text", ["sha256:#page:1"], ["Hello"])])
    report = projection.compare(a, b, PIN, {"required": ["page-text"], "forbidden": []})
    assert report["status"] == "complete"
    assert report["matches"] == 1
    assert report["pass"] is True


def test_label_similarity_never_matches_without_anchor():
    # same text, DIFFERENT anchors: must stay unresolved, never paired by text
    a = _extractor("alpha", "1", [_obs("a1", "page-text", ["sha256:#page:1"], ["Hello"])])
    b = _extractor("beta", "9", [_obs("b1", "page-text", ["sha256:#page:2"], ["Hello"])])
    report = projection.compare(a, b, PIN, {"required": ["page-text"], "forbidden": []})
    assert report["matches"] == 0
    assert report["unresolved"] == ["page-text"]
    assert report["pass"] is False


def test_false_positives_and_negatives_are_reported():
    a = _extractor("alpha", "1", [
        _obs("a1", "page-text", ["sha256:#page:1"], ["Hello"]),
        _obs("a2", "footnote", ["sha256:#page:1#fn"], ["extra"]),
    ])
    b = _extractor("beta", "9", [_obs("b1", "page-text", ["sha256:#page:1"], ["Hello"])])
    report = projection.compare(a, b, PIN, {"required": ["page-text"], "forbidden": []})
    assert report["false_positives"] == ["footnote"]
    assert report["false_negatives"] == []
    assert report["pass"] is True  # required observable matched; extra FP reported


def test_competing_interpretations_are_retained_and_can_pass():
    # opposing reading orders allowed by the reference oracle: both kept with
    # attribution, comparison may pass; discarding one would fail
    a = _extractor("alpha", "1", [
        _obs("a1", "reading-order", ["sha256:#doc"], ["A,B"], alternatives=[]),
    ])
    b = _extractor("beta", "9", [
        _obs("b1", "reading-order", ["sha256:#doc"], ["B,A"], alternatives=[]),
    ])
    oracle = {
        "required": ["reading-order"],
        "allowed_unresolved": ["reading-order"],  # oracle allows both orders
        "forbidden": [],
    }
    report = projection.compare(a, b, PIN, oracle)
    assert report["status"] == "complete"
    assert report["unresolved"] == ["reading-order"]
    # one retained set for the divergent observable, holding BOTH attributed
    # values (competing orders preserved with attribution, no winner picked)
    alt = report["retained_alternatives"]
    assert len(alt) == 1 and len(alt[0]["values"]) == 2
    assert {v["value"][0] for v in alt[0]["values"]} == {"A,B", "B,A"}
    assert report["pass"] is True


def test_discarding_an_expected_alternative_fails():
    a = _extractor("alpha", "1", [
        _obs("a1", "reading-order", ["sha256:#doc"], ["A,B"], alternatives=[]),
    ])
    b = _extractor("beta", "9", [])  # beta dropped the competing order entirely
    oracle = {
        "required": ["reading-order"],
        "allowed_unresolved": ["reading-order"],
        "forbidden": [],
    }
    report = projection.compare(a, b, PIN, oracle)
    assert report["pass"] is False
    assert report["false_negatives"] == ["reading-order"]


def test_missing_pin_or_oracle_is_incomplete():
    a = _extractor("alpha", "1", [_obs("a1", "x", ["anc"], ["v"])])
    b = _extractor("beta", "9", [_obs("b1", "x", ["anc"], ["v"])])
    assert projection.compare(a, b, None, {"required": []})["status"] == "incomplete"
    assert projection.compare(a, b, PIN, None)["status"] == "incomplete"


def test_machinery_pass_still_cannot_claim_real_carrier_conformance():
    # the corpus, two readers and a comparator all exist — but the anchor
    # mapping is UNREVIEWED (scripted machinery only), so real-carrier
    # conformance must remain incomplete
    r = conformance.classify({
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2, "extractor_comparison": True,
        "anchor_mapping_reviewed": False,
    })
    assert r["status"] == "incomplete"
    assert "reviewed anchor mapping" in r["missing"]
    assert r["real_carrier_conformance"] is False


def test_reviewed_mapping_completes_the_label():
    r = conformance.classify({
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2, "extractor_comparison": True,
        "anchor_mapping_reviewed": True,
    })
    assert r["status"] == "complete"
    assert r["real_carrier_conformance"] is True


# -- replay case integrates the evidence transform machinery --------------------------
def test_replay_case_replays_clean():
    case = _built()["replay"]
    sha = case["descriptor"]["source"]["sha256"]
    assert hashlib.sha256(sha.encode()).hexdigest()  # sanity: sha is set
    status, _ = evidence.replay(
        next(e for e in case["descriptor"]["evidence"] if "transform" in e),
        case["descriptor"],
        {},
        case["transform_fns"],
    )
    assert status == "replayed"
