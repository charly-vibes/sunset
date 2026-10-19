# Purpose: Slice-3 tests for dsc03.compare — scoped comparators, composition
#   probes, counterexample export and the debugger-goldens fixtures.
# Responsibilities: Assert that (a) all five comparison outcomes are emitted
#   and loss/unresolved/unexamined never convert to equivalent/pass,
#   (b) identity/associativity probes pass on declared-compatible mappings and
#   fail with a minimal witness on broken ones, (c) title/filename-only edition
#   matching is refused, (d) each negative fixture fails with its exact
#   expected diagnostic code plus a minimal witness, (e) counterexample
#   export→reload→re-compare is byte-deterministic including the redacted
#   replayable=false path, (f) an unsupported comparator is classified
#   unsupported with no equivalence claim, and (g) the committed goldens are
#   deterministic, carrier-provenanced and honor redaction state.
# Rationale: document-debugger-comparison delta constraints scoped_comparison,
#   typed_outcome, composition_checks, no_edition_guess, counterexample_replay
#   and loss_visibility (independent_agreement is slice 4, not tested here).
"""Scoped comparators, counterexample export and goldens (sunset-xx7.3)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dsc03 import compare
from dsc03.compare import (
    OUTCOMES,
    ComparatorSpec,
    ComparisonInput,
    diagnose_fixture,
    edition_match,
    export_counterexample,
    probe_associativity,
    probe_identity,
    scoped_compare,
    serialize_bundle,
    load_bundle,
    replay,
)
GOLDENS = Path(__file__).resolve().parents[2] / "fixtures" / "debugger-goldens"
CARRIER = Path(__file__).resolve().parents[2] / "fixtures" / "carriers" / "accounting-made-simple-excerpt.pdf"


def _spec(scope=("flattened_text", "sign_column_positions")):
    return ComparatorSpec(
        comparator_id="dbg.text-flatten",
        version="1.0.0",
        input_types=("descriptor", "descriptor"),
        observable_scope=tuple(scope),
    )


def _inp(payload, endpoint_type="descriptor"):
    return ComparisonInput(
        endpoint_type=endpoint_type,
        payload=payload,
        descriptor_sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        source_sha256="deadbeef",
    )


FLAT = "ACME CORP 2026-01-31 DEBIT -12.00 CREDIT 34.00"

# (a) five outcomes + loss-visibility non-conversion -----------------------------
def test_typed_outcomes_and_loss_never_converts_to_equivalent():
    same = (ComparisonInput("descriptor", {"flattened_text": FLAT, "sign_column_positions": {"page:1": 3}}),
            ComparisonInput("descriptor", {"flattened_text": FLAT, "sign_column_positions": {"page:1": 3}}))
    assert scoped_compare(_spec(), *same).outcome == "equivalent"

    textdiff = (same[0], ComparisonInput("descriptor", {"flattened_text": FLAT + " X", "sign_column_positions": {"page:1": 3}}))
    assert scoped_compare(_spec(), *textdiff).outcome == "different"

    signloss = (same[0], ComparisonInput("descriptor", {"flattened_text": FLAT, "sign_column_positions": {"page:1": 5}}))
    out = scoped_compare(_spec(), *signloss)
    assert out.outcome == "different"  # never equivalent: cannot certify sign preservation
    assert out.rule_id == compare.RULE_SIGN_LOSS
    assert out.details["loss"] == "sign preservation not certified"

    # unexamined scope key can never be equivalent (loss_visibility)
    out = scoped_compare(_spec(("flattened_text", "unexamined_coverage")), *same)
    assert out.outcome == "unexamined"
    assert out.rule_id == compare.RULE_UNEXAMINED

    # disputed surfaces through the typed outcome space too
    d = diagnose_fixture("sign-loss")
    assert d.rule_id == compare.RULE_SIGN_LOSS
    assert all(o in OUTCOMES for o in ("equivalent", "different", "disputed", "unsupported", "unexamined"))


# (b) identity + associativity probes -------------------------------------------
def _t(name, fn, observables=("flattened_text",), compose=None):
    return compare.Transformation(transform_id=name, version="1.0.0",
                                  declared_observables=tuple(observables), fn=fn,
                                  compose=compose)


IDENT = _t("identity", lambda d: d)
LOWER = _t("lowercase", lambda d: {**d, "flattened_text": d["flattened_text"].lower()})
STRIP = _t("strip", lambda d: {**d, "flattened_text": d["flattened_text"].strip()})
BROKEN_IDENT = _t("bad-identity", lambda d: {**d, "flattened_text": d["flattened_text"] + "!"})

SAMPLE = {"flattened_text": "Hello World", "sign_column_positions": {"page:1": 3}}


def test_identity_and_associativity_probes_pass_and_fail_with_witness():
    assert probe_identity(IDENT, SAMPLE) is None
    assert probe_associativity(LOWER, STRIP, IDENT, SAMPLE) is None

    bad = probe_identity(BROKEN_IDENT, SAMPLE)
    assert bad is not None and bad["rule"] == compare.RULE_IDENTITY
    assert bad["observable"] == "flattened_text"
    assert bad["expected"] == SAMPLE["flattened_text"]
    assert bad["observed"] == SAMPLE["flattened_text"] + "!"
    # minimal witness: smallest input that breaks it
    assert "!" in bad["observed"]

    # declared composition bug: t2 claims to fuse with t1 by dropping itself
    NONASSOC_A = _t("pad", lambda d: {**d, "flattened_text": d["flattened_text"] + " "})
    NONASSOC_B = _t("rstrip", lambda d: {**d, "flattened_text": d["flattened_text"].rstrip()},
                    compose=lambda prev: prev)  # declared fusion drops t2's own effect
    wit = probe_associativity(NONASSOC_A, NONASSOC_B, LOWER, SAMPLE)
    assert wit is not None and wit["rule"] == compare.RULE_ASSOCIATIVITY
    assert wit["expected"] != wit["observed"]
    assert wit["observable"] == "flattened_text"


# (c) no_edition_guess ------------------------------------------------------------
def test_title_only_edition_match_is_refused():
    a = {"title": "Accounting Made Simple", "filename": "ams.pdf"}
    b = {"title": "Accounting Made Simple", "filename": "ams-2nd-edition.pdf"}
    out = edition_match(a, b)
    assert out.outcome != "equivalent"
    assert out.rule_id == compare.RULE_NO_EDITION_GUESS
    # even identical titles+filenames without declared edition evidence are refused
    out = edition_match({**a, "filename": "ams.pdf"}, {**a, "filename": "ams.pdf"})
    assert out.outcome != "equivalent"
    assert out.rule_id == compare.RULE_NO_EDITION_GUESS
    # explicit matching edition + matching source hash is required for equivalence
    out = edition_match({**a, "edition": "2", "source_sha256": "aa"}, {**a, "edition": "2", "source_sha256": "aa"})
    assert out.outcome == "equivalent"


# (d) negative fixtures: exact expected diagnostic code + minimal witness ---------
@pytest.mark.parametrize(
    "fixture,rule_id",
    [
        ("wrong-reading-order", compare.RULE_WRONG_ORDER),
        ("containment-cycle", compare.RULE_CONTAINMENT_CYCLE),
        ("dangling-target", compare.RULE_DANGLING_TARGET),
        ("selector-ambiguity", compare.RULE_SELECTOR_AMBIGUITY),
        ("edition-mismatch", compare.RULE_NO_EDITION_GUESS),
        ("sign-loss", compare.RULE_SIGN_LOSS),
    ],
)
def test_negative_fixture_exact_code_and_minimal_witness(fixture, rule_id):
    d = diagnose_fixture(fixture)
    assert d.rule_id == rule_id
    assert d.witness, f"{fixture} must carry a minimal witness"
    assert d.category in ("violated", "disputed", "unsupported")


# (e) counterexample export -> reload -> re-compare byte determinism --------------
def test_counterexample_export_replay_byte_determinism_and_redaction():
    left = _inp({"flattened_text": FLAT, "sign_column_positions": {"page:1": 3}})
    right = _inp({"flattened_text": FLAT, "sign_column_positions": {"page:1": 5}})
    out = scoped_compare(_spec(), left, right)
    bundle = export_counterexample(out, _spec(), left, right)
    b1 = serialize_bundle(bundle)
    b2 = serialize_bundle(load_bundle(b1))
    assert b1 == b2  # byte-deterministic, no timestamps

    rec = json.loads(b1)
    assert rec["witness"]["rule_id"] == compare.RULE_SIGN_LOSS
    assert rec["witness"]["input_hashes"]["left"] == left.descriptor_sha256
    assert rec["witness"]["replayable"] is True
    # replay reproduces the same typed outcome
    out2 = replay(load_bundle(b1), left, right)
    assert out2.outcome == out.outcome and out2.rule_id == out.rule_id

    # redacted path: source bytes omitted, replayable=false, no fabricated source
    rb = export_counterexample(out, _spec(), left, right, redact=True)
    rr = json.loads(serialize_bundle(rb))
    assert rr["witness"]["replayable"] is False
    assert rr["witness"]["redaction"]["omitted"] == ["left.payload", "right.payload"]
    assert "payload" not in rr["inputs"]["left"]
    with pytest.raises(compare.NotReplayable):
        replay(load_bundle(serialize_bundle(rb)), left, right)


# (f) unsupported comparator ------------------------------------------------------
def test_unsupported_comparator_classified_unsupported_no_equivalence_claim():
    identical = (ComparisonInput("descriptor", {"flattened_text": FLAT}), ComparisonInput("descriptor", {"flattened_text": FLAT}))
    out = scoped_compare(None, *identical)
    assert out.outcome == "unsupported"
    assert out.rule_id == compare.RULE_SCOPE_UNSUPPORTED
    # incompatible endpoint types are also rejected, never guessed equivalent
    out = scoped_compare(_spec(), ComparisonInput("layout", {"flattened_text": FLAT}), identical[1])
    assert out.outcome == "unsupported"
    assert out.rule_id == compare.RULE_SCOPE_UNSUPPORTED


# (g) committed goldens -----------------------------------------------------------
def test_goldens_deterministic_carrier_provenance_and_redaction():
    names = sorted(p.name for p in GOLDENS.glob("golden-*.json"))
    assert names, "goldens must be committed"
    for p in GOLDENS.glob("golden-*.json"):
        raw = p.read_bytes()
        rec = json.loads(raw)
        assert json.dumps(rec, sort_keys=True, indent=1) + "\n" == raw.decode()
        assert "timestamp" not in raw.decode()
    # carrier golden is built from a real committed carrier via dsc03.adapters
    carrier_rec = json.loads((GOLDENS / "golden-01-carrier-text-compare.json").read_bytes())
    assert carrier_rec["provenance"]["carrier"] == "accounting-made-simple-excerpt.pdf"
    assert carrier_rec["provenance"]["source_sha256"] == hashlib.sha256(CARRIER.read_bytes()).hexdigest()
    assert carrier_rec["witness"]["replayable"] is True
    # redaction golden marks non-replayability
    red = json.loads((GOLDENS / "golden-03-private-redaction.json").read_bytes())
    assert red["witness"]["replayable"] is False
