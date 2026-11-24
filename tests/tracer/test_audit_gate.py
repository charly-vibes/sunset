# Purpose: RED-first tests for sunset-3oq audit and autonomy gate (tasks
#   4.1-4.3, 5.1-5.2): deterministic seeded sampling, Wilson false-accept
#   upper bound (nonzero at zero errors), evidence-class-gated autonomy
#   (agent-executed audits never open the gate; no audit data stays queued),
#   and the labeled per-type metrics record.
# Responsibilities: Exercise dsc03.audit_gate only; agent-executed numbers.
"""Audit sampler, Wilson bound, autonomy gate, metrics tests."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from dsc03.claims import add_claim, claim_id


def type_claims(n, prefix):
    return [{"id": claim_id("field:total", [f"r-{prefix}-{i}"],
                            "1234.56", "model"), "type": "field:total"}
            for i in range(n)]


# -- 4.1 deterministic sampler ---------------------------------------------------

def test_seeded_sample_identical_on_repeat_draw():
    from dsc03.audit_gate import draw_sample
    cs = type_claims(50, "a")
    s1, cfg1 = draw_sample(cs, seed=7, rate=0.5, min_count=5)
    s2, cfg2 = draw_sample(cs, seed=7, rate=0.5, min_count=5)
    assert [c["id"] for c in s1] == [c["id"] for c in s2]
    assert cfg1["seed"] == 7 and cfg1["rate"] == 0.5


def test_sampler_rate_bounds_sample_size():
    from dsc03.audit_gate import draw_sample
    cs = type_claims(100, "b")
    sample, cfg = draw_sample(cs, seed=3, rate=0.2, min_count=0)
    assert 0 < len(sample) < 100
    assert {c["id"] for c in sample} <= {c["id"] for c in cs}


# -- 4.2 Wilson upper bound --------------------------------------------------------

def test_wilson_upper_nonzero_at_zero_errors():
    from dsc03.audit_gate import wilson_upper
    bound = wilson_upper(0, 30, confidence=0.95)
    assert 0.0 < bound
    assert bound < wilson_upper(0, 5, confidence=0.95)  # more audits tighten


def test_wilson_upper_monotone_in_errors_and_confidence():
    from dsc03.audit_gate import wilson_upper
    assert wilson_upper(1, 30) > wilson_upper(0, 30)
    assert wilson_upper(1, 30, confidence=0.99) > wilson_upper(1, 30,
                                                              confidence=0.95)


# -- 4.3 gate -----------------------------------------------------------------------

def _record(errors, n, evidence_class="human", claim_type="field:total"):
    return {"claim_type": claim_type, "errors": errors, "n": n,
            "evidence_class": evidence_class}


def test_gate_closed_when_no_audit_data():
    from dsc03.audit_gate import gate_open
    assert gate_open("field:total", []) is False


def test_agent_executed_audits_never_open_gate():
    from dsc03.audit_gate import gate_open
    # agent-executed audits that would satisfy every threshold
    records = [_record(0, 200, evidence_class="agent-executed")]
    assert gate_open("field:total", records) is False


def test_gate_opens_on_human_audits_meeting_ruling():
    from dsc03.audit_gate import gate_open
    # zero errors still need enough audits: Wilson bound at n=30 is ~11%,
    # the 1% ruling needs roughly 370+ audited claims
    assert gate_open("field:total", [_record(0, 400)]) is True
    # below the minimum audited count: closed
    assert gate_open("field:total", [_record(0, 29)]) is False
    # bound above the 1% threshold: closed (perfect audits at n=30, errors at n=400)
    assert gate_open("field:total", [_record(0, 30)]) is False
    assert gate_open("field:total", [_record(2, 400)]) is False


def test_ruling_constants_recorded():
    import dsc03.audit_gate as gate
    assert gate.GATE_CONFIDENCE == 0.95
    assert gate.GATE_THRESHOLD <= 0.01
    assert gate.GATE_MIN_AUDITED >= 30


# -- 5.1/5.2 metrics -----------------------------------------------------------------

def test_metrics_record_evidence_class_and_separate_rejects():
    from dsc03.audit_gate import metrics_report
    report = metrics_report(
        claim_type="field:total",
        auto_accepted=90,
        total_claims=100,
        audit={"errors": 0, "n": 30, "evidence_class": "human"},
        confidence=0.95,
        human_seconds=[12.0, 8.0],
        human_rejected=4,
    )
    assert report["claim_type"] == "field:total"
    assert report["auto_accept_rate"] == 0.9
    assert 0 < report["false_accept_upper_bound"] <= 0.15
    assert report["evidence_class"] == "human"
    assert report["human_seconds_per_item"] == 10.0
    assert report["human_rejected"] == 4
    # false rejects are NOT part of the audited bound
    assert "false_reject_rate" not in report
