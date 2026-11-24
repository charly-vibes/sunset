# Purpose: Deterministic audit sampling, Wilson false-accept upper bound,
#   and the evidence-gated autonomy decision (sunset-3oq tasks 4.1-4.4,
#   5.1-5.2).
# Responsibilities: (1) draw_sample — seeded, recorded-rate per-claim-type
#   draw from auto-accepted claims, identical across processes; (2)
#   wilson_upper — Wilson score interval upper bound at a recorded
#   confidence, nonzero at zero errors; (3) gate_open — a claim type is
#   exported without review only when its human-audited false-accept upper
#   bound meets the ruling (sunset-gpd G3, 2026-11-24: 95% confidence,
#   bound <= 1%, audited sample >= 30 per type, human-labeled audits only —
#   Decision 7: agent-executed audits never count) and otherwise stays
#   queued, including when no audit data exists; (4) metrics_report — the
#   labeled per-type record: auto-accept rate, audited false-accept upper
#   bound, human seconds per item, human-rejected count kept separate (false
#   rejects are not measured by the audit, design Decision 8).
# Rationale: the decision to skip review must be backed by a measured
#   false-accept rate, not by trust in the verifiers; evidence classes stay
#   separate.
"""Audit sampler, Wilson bound, autonomy gate, labeled metrics."""
import math
import random
from statistics import NormalDist

# Owner ruling (sunset-gpd gate G3, 2026-11-24; design.md Open Question 1):
# autonomy gate opens when the Wilson false-accept upper bound at 95%
# confidence is <= 1% AND the audited sample is >= 30 per claim type,
# human-labeled audits only.
GATE_CONFIDENCE = 0.95
GATE_THRESHOLD = 0.01
GATE_MIN_AUDITED = 30

HUMAN = "human"
AGENT_EXECUTED = "agent-executed"


# -- 4.1 deterministic sampler ---------------------------------------------------

def draw_sample(claims, seed, rate, min_count=0):
    """Seeded per-claim-type draw from the auto-accepted claims given.

    Returns (sample, config) where config records the seed, rate and
    minimum count. Iteration is over claim ids sorted, and the RNG is
    keyed per claim type, so the draw is identical across processes.
    A type with fewer eligible claims than ``min_count`` keeps all of them
    (the minimum is a floor on intent, never a fabrication of audits).
    """
    by_type = {}
    for claim in sorted(claims, key=lambda c: c["id"]):
        by_type.setdefault(claim["type"], []).append(claim)
    sample = []
    for claim_type in sorted(by_type):
        rng = random.Random(json_key(seed, claim_type))
        chosen = [c for c in by_type[claim_type] if rng.random() < rate]
        if min_count and len(chosen) < min_count:
            # top up deterministically from the unchosen, in sorted id order
            picked = {c["id"] for c in chosen}
            chosen = chosen + [c for c in by_type[claim_type]
                               if c["id"] not in picked][:min_count - len(chosen)]
        sample.extend(chosen)
    sample.sort(key=lambda c: c["id"])
    config = {"seed": seed, "rate": rate, "min_count": min_count}
    return sample, config


def json_key(seed, claim_type):
    import json
    return json.dumps([seed, claim_type], sort_keys=True)


# -- 4.2 Wilson upper bound --------------------------------------------------------

def wilson_upper(errors, n, confidence=GATE_CONFIDENCE):
    """Wilson score interval upper bound for the error proportion.

    With zero errors the bound is z^2/(n+z^2) — strictly positive, so zero
    observed errors still yield a nonzero bound (design Decision 5).
    """
    if n <= 0:
        raise ValueError("no audited claims: the bound is undefined")
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = errors / n
    denominator = 1 + z * z / n
    center = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center + spread) / denominator


# -- 4.3 evidence-gated autonomy ---------------------------------------------------

def gate_open(claim_type, audit_records, confidence=GATE_CONFIDENCE,
              threshold=GATE_THRESHOLD, min_audited=GATE_MIN_AUDITED):
    """Whether the claim type exports without review.

    Only `human`-labeled audit records count (Decision 7). No audit data,
    or only agent-executed audits, means the type stays queued. Human
    records are aggregated per type before the bound is computed.
    """
    human = [r for r in audit_records
             if r["claim_type"] == claim_type and r["evidence_class"] == HUMAN]
    if not human:
        return False
    n = sum(r["n"] for r in human)
    errors = sum(r["errors"] for r in human)
    if n < min_audited:
        return False
    return wilson_upper(errors, n, confidence=confidence) <= threshold


# -- 5.1/5.2 labeled metrics ---------------------------------------------------------

def metrics_report(claim_type, auto_accepted, total_claims, audit,
                   confidence=GATE_CONFIDENCE, human_seconds=(),
                   human_rejected=0):
    """The recorded per-type measurement; measurements, not targets.

    ``audit`` is the audited sample outcome with its evidence_class label;
    only human-labeled audits produce a bound (agent-executed audits are
    recorded but never feed the gate, so no bound is reported for them).
    False rejects are NOT measured by auditing auto-accepted claims; the
    human-rejected count is reported separately (design Decision 8).
    """
    report = {
        "claim_type": claim_type,
        "auto_accept_rate": (auto_accepted / total_claims
                             if total_claims else None),
        "evidence_class": audit["evidence_class"],
        "human_seconds_per_item": (sum(human_seconds) / len(human_seconds)
                                   if human_seconds else None),
        "human_rejected": human_rejected,
    }
    if audit["evidence_class"] == HUMAN and audit["n"]:
        report["false_accept_upper_bound"] = wilson_upper(
            audit["errors"], audit["n"], confidence=confidence)
        report["audit_confidence"] = confidence
        report["audited_count"] = audit["n"]
    return report
