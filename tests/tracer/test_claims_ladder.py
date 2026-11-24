# Purpose: RED-first tests for sunset-1x7 claims ladder (add-claim-verification-ladder):
#   anchored extractive claims, refusals with stable reason codes, the
#   normalization registry, status order + meet aggregation, conflict
#   retention, idempotent resubmission, confidence outside the digest.
# Responsibilities: Exercise dsc03.claims only; all numbers/behaviors
#   agent-executed against synthetic descriptors; no accuracy claims.
"""Claims ladder tests: anchoring, normalization, statuses, retention."""
import pytest

from dsc03.substrate.context import issue_fixture
from dsc03.claims import (
    Refusal,
    STATUS_ORDER,
    add_claim,
    claim_id,
    meet_status,
    mark_conflicts,
    submit_claim,
)


def descriptor():
    """issue_fixture plus an amount-bearing content, all synthetic."""
    desc = issue_fixture()
    desc["contents"].append(
        {"id": "c-total", "kind": "text", "value": "1.234,56"})
    desc["relations"].append(
        {"id": "rel-hc3", "kind": "has-content", "from": "r-issue",
         "to": "c-total"})
    return desc


# -- 2.1 dangling anchor ------------------------------------------------------

def test_unresolved_anchor_refused():
    with pytest.raises(Refusal) as exc:
        submit_claim(descriptor(), {
            "type": "field:total", "anchors": ["r-nope"],
            "value": "1.234,56", "origin": "model", "extractive": True,
        })
    assert exc.value.reason_code == "claim.anchor.unresolved"


# -- 2.2 extractive value vs anchored text ------------------------------------

def test_extractive_mismatch_refused():
    with pytest.raises(Refusal) as exc:
        submit_claim(descriptor(), {
            "type": "field:total", "anchors": ["r-issue"],
            "value": "1.234,57", "origin": "model", "extractive": True,
        })
    assert exc.value.reason_code == "claim.value.mismatch"


def test_extractive_match_admitted_unverified():
    claim = submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-issue"],
        "value": "1.234,56", "origin": "model", "extractive": True,
    })
    assert claim["value"] == "1234.56"  # canonical AR decimal
    assert claim["status"] == "unverified"


def test_missing_normalization_admitted_unverified_with_reason():
    claim = submit_claim(descriptor(), {
        "type": "field:unregistered-kind", "anchors": ["r-issue"],
        "value": "1.234,56", "origin": "model", "extractive": True,
    })
    assert claim["status"] == "unverified"
    assert any(r["code"] == "claim.normalization.unregistered"
               for r in claim["reasons"])


def test_registered_type_unparseable_span_refused_typed():
    # field:date IS registered but the anchored span is prose: this must be
    # a typed refusal — not `claim.normalization.unregistered` with the raw
    # span stored as canonical (which discarded the model value and made a
    # same-origin corrected resubmission collide on id)
    with pytest.raises(Refusal) as exc:
        submit_claim(issue_fixture(), {
            "type": "field:date", "anchors": ["c-quote"],
            "value": "29/07/2026", "origin": "model", "extractive": True,
        })
    assert exc.value.reason_code == "claim.value.unparseable"


# -- 2.3 id derivation + idempotent resubmission ------------------------------

def test_claim_id_digest_of_identity_fields():
    a = claim_id("field:total", ["r-a", "r-b"], "1234.56", "model")
    b = claim_id("field:total", ["r-b", "r-a"], "1234.56", "model")
    c = claim_id("field:total", ["r-a", "r-b"], "1234.57", "model")
    assert a == b and a != c


def test_resubmission_is_idempotent():
    d = descriptor()
    claim = submit_claim(d, {
        "type": "field:total", "anchors": ["r-issue"],
        "value": "1.234,56", "origin": "model", "extractive": True,
    })
    claims = []
    claims = add_claim(claims, claim)
    claims = add_claim(claims, claim)
    assert len(claims) == 1


# -- 2.5 generative claims capped at unverified -------------------------------

def test_generative_capped_at_unverified():
    claim = submit_claim(descriptor(), {
        "type": "summary:theme", "anchors": ["r-poem"],
        "value": "melancholy sea voyage", "origin": "model",
        "extractive": False,
        "confidence": 0.99,
    })
    assert claim["value_origin"] == "model"
    assert claim["status"] == "unverified"
    assert claim["confidence"] == 0.99
    assert "confidence" not in claim["digest_input"]


# -- 3.1 status order and meet -------------------------------------------------

def test_status_order():
    assert STATUS_ORDER == ("verified", "agreed", "unverified", "conflicted")


def test_meet_of_verified_and_unverified_is_unverified():
    v = {"id": "a", "status": "verified", "origin": "model"}
    u = {"id": "b", "status": "unverified", "origin": "model"}
    assert meet_status([v] * 9 + [u]) == "unverified"


def test_rejected_excluded_from_meet():
    v = {"id": "a", "status": "verified", "origin": "model"}
    r = {"id": "b", "status": "rejected", "origin": "human"}
    assert meet_status([v, r]) == "verified"


# -- 3.2 conflict retention ----------------------------------------------------

def test_conflicting_claims_both_retained_conflicted():
    d = descriptor()
    c1 = submit_claim(d, {"type": "field:total", "anchors": ["r-issue"],
                          "value": "1.234,56", "origin": "model-a",
                          "extractive": True})
    # a second value must come from a different descriptor text; synthesize
    c2 = dict(c1, id=claim_id("field:total", ["r-issue"], "9999.00",
                              "model-b"),
              value="9999.00", origin="model-b")
    claims = add_claim(add_claim([], c1), c2)
    claims = mark_conflicts(claims)
    values = sorted(c["value"] for c in claims if c["type"] == "field:total")
    assert values == ["1234.56", "9999.00"]
    origins = {c["origin"] for c in claims if c["status"] == "conflicted"}
    assert origins == {"model-a", "model-b"}
    assert meet_status(claims) == "conflicted"


# -- 3.3 confidence outside the semantic digest --------------------------------

def test_confidence_change_changes_nothing_semantic():
    d = descriptor()
    base = {"type": "field:total", "anchors": ["r-issue"],
            "value": "1.234,56", "origin": "model", "extractive": True}
    c1 = submit_claim(d, dict(base, confidence=0.9))
    c2 = submit_claim(d, dict(base, confidence=0.1))
    assert c1["id"] == c2["id"]
    assert c1["status"] == c2["status"] == "unverified"
    assert c1["digest_input"] == c2["digest_input"]
    assert c1["confidence"] != c2["confidence"]


# -- 5.1 human decisions are claims --------------------------------------------

def test_human_correction_is_new_claim_model_claim_remains():
    d = descriptor()
    model = submit_claim(d, {"type": "field:total", "anchors": ["r-issue"],
                             "value": "1.234,56", "origin": "model",
                             "extractive": True})
    human = submit_claim(d, {"type": "field:total", "anchors": ["r-issue"],
                             "value": "1.234,56", "origin": "human",
                             "extractive": True, "reviewer": "rev-7"})
    claims = add_claim(add_claim([], model), human)
    assert len(claims) == 2
    assert {c["origin"] for c in claims} == {"model", "human"}
    assert model in claims


def test_human_decision_is_part_of_digest_identity():
    # accept and reject of the SAME value must not collide into one claim id:
    # the decision (accept | reject | edit) enters digest_input and the id
    d = descriptor()
    base = {"type": "field:total", "anchors": ["r-issue"],
            "value": "1.234,56", "origin": "human", "extractive": True}
    accept = submit_claim(d, dict(base, decision="accept"))
    accept_again = submit_claim(d, dict(base, decision="accept"))
    reject = submit_claim(d, dict(base, decision="reject"))
    assert accept["id"] == accept_again["id"]   # repeat decision idempotent
    assert accept["id"] != reject["id"]         # accept vs reject distinct
    assert accept["digest_input"]["decision"] == "accept"
    # non-decision claims keep the 4-field digest exactly as before
    plain = submit_claim(d, base)
    assert "decision" not in plain["digest_input"]


# -- substrate dedupe + export record ------------------------------------------

def test_substrate_dedupe_annotations_drops_identical_identity():
    from dsc03.substrate.context import dedupe_annotations
    desc = issue_fixture()
    duplicate = dict(desc["annotations"][0],
                     id="a-issue-date-copy", status="disputed")
    desc["annotations"] = desc["annotations"] + [duplicate]
    kept = dedupe_annotations(desc)
    targets = [a["target"] for a in kept
               if a["term"] == "mag:publication-date"]
    assert len(targets) == 1


def test_export_record_lists_checks_and_excludes_confidence():
    from dsc03.claims import export_record
    d = descriptor()
    claim = submit_claim(d, {"type": "field:total", "anchors": ["r-issue"],
                             "value": "1.234,56", "origin": "model",
                             "extractive": True, "confidence": 0.7})
    from dsc03.verify import run_ladder
    record = export_record(run_ladder([claim], descriptor=d)[0])
    assert record["status"] == "verified"
    assert all("outcome" in c for c in record["checks"])
    assert "confidence" not in record
    assert record["checks_passed"] >= 1
