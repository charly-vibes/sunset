# Purpose: Ontology boundary projection evaluator (sunset-r68.14, task 6.1).
# Responsibilities: Evaluate a declared projection P: DSC[version, profiles] ->
#   TargetOntology[version] against the ontology-boundary rules, starting with
#   acceptance checks O-A01 (out-of-core relations never coerced into core
#   contains/precedes/realizes without a declared equivalence), O-A04 (losses
#   declared in a manifest, exactly one disposition per feature; semantic
#   equivalence never claimed without an entailment policy) and O-A05
#   (roundtrip fidelity claimed only for a specified observable subset and
#   tested domain; a full-fidelity badge is rejected). A projection that omits
#   its provenance declaration is not applied as a valid mapping. Profile
#   resolution or schema validity alone never implies semantic equivalence.
# Rationale: add-dsc-03 document-ontology-boundaries deltas; research-bundle
#   ONTOLOGY-BOUNDARIES.md sections 5 (projection contract) and 7 (checks).
"""Boundary projection evaluator: O-A01, O-A04, O-A05; no silent coercion."""
CORE_RELATION_KINDS = {"contains", "precedes", "realizes", "has-content"}
LOSS_DISPOSITIONS = {
    "preserved", "transformed", "approximated", "omitted", "unsupported",
    "unexamined",
}
LOSSY = LOSS_DISPOSITIONS - {"preserved", "transformed"}

PROVENANCE_KEYS = (
    "projection_id", "version", "source", "target", "rules", "scope",
    "equivalence",
)


def _reason(reasons, new):
    if new not in reasons:
        reasons.append(new)


def _has_provenance(projection):
    return isinstance(projection, dict) and all(
        projection.get(k) not in (None, "", [], {}) for k in PROVENANCE_KEYS
    )


def _losses(projection):
    losses = projection.get("losses")
    return losses if isinstance(losses, dict) else {}


def _o_a01(projection):
    """Non-coercion: each out-of-core source relation is either emitted via a
    declared equivalence / registered profile, or explicitly reported
    unsupported; never silently rewritten as a core relation kind."""
    reasons = []
    coerced = []
    src_rels = projection.get("source_relations") or []
    outputs = projection.get("output_relations") or []
    profiles = {p.get("id") for p in (projection.get("profiles") or [])
                if isinstance(p, dict)}
    for out_rel in outputs:
        if not isinstance(out_rel, dict):
            continue
        kind = out_rel.get("kind")
        if kind not in CORE_RELATION_KINDS:
            continue
        derived = out_rel.get("derived_from")
        via = out_rel.get("via")
        if derived in src_rels and derived not in CORE_RELATION_KINDS \
                and via not in ("declared_equivalence", "registered_profile"):
            coerced.append({
                "source_relation": derived,
                "output_kind": kind,
                "via": via,
            })
            _reason(reasons, "coerced_relation")
    return {"pass": not reasons, "reasons": reasons, "coerced": coerced,
            "profiles": sorted(p for p in profiles if p)}


def _o_a04(projection):
    """Loss manifest: every feature in the declared coverage inventory carries
    exactly one disposition with a justification when lossy; unmapped
    predicates are undeclared losses; a semantic-equivalence claim requires an
    entailment policy."""
    reasons = []
    losses = _losses(projection)
    inventory = projection.get("coverage_inventory") or []

    undeclared = [f for f in inventory if f not in losses]
    if undeclared:
        _reason(reasons, "undeclared_loss")

    disposition_errors = []
    for feature, entry in losses.items():
        if not isinstance(entry, dict) or entry.get("disposition") not in LOSS_DISPOSITIONS:
            disposition_errors.append({"feature": feature,
                                       "error": "invalid_or_missing_disposition"})
            _reason(reasons, "invalid_loss_disposition")
            continue
        disposition = entry["disposition"]
        if disposition in LOSSY and not (entry.get("justification") or "").strip():
            disposition_errors.append({"feature": feature,
                                       "error": "lossy_disposition_without_justification"})
            _reason(reasons, "loss_without_justification")

    if projection.get("equivalence") == "semantic" \
            and not (projection.get("entailment_policy") or "").strip():
        _reason(reasons, "semantic_equivalence_without_entailment_policy")

    return {
        "pass": not reasons,
        "reasons": reasons,
        "undeclared": undeclared,
        "disposition_errors": disposition_errors,
    }


def _o_a05(projection):
    """Conditional roundtrip: a roundtrip claim must name its observable
    subset and tested domain; 'full' fidelity is never earned by a
    text-only (or otherwise partial) projection."""
    reasons = []
    rt = projection.get("roundtrip")
    if isinstance(rt, dict) and rt.get("claimed"):
        subset = rt.get("subset")
        domain = rt.get("tested_domain")
        if rt.get("scope") == "full" or not subset or not domain:
            _reason(reasons, "unearned_full_fidelity_claim")
    return {"pass": not reasons, "reasons": reasons}


def roundtrip(projection, observations):
    """Evaluate obs(Q(P(x))) against the declared roundtrip subset.

    Every evaluated observable is reported honestly: 'preserved' or 'failed'.
    A failure INSIDE the promised subset breaks the claim; a failure OUTSIDE
    it (e.g. geometry under a text-only projection) is an explicit failure
    that does not break the scoped claim — it is never silently recast as
    preserved. Returns per-observable outcomes and whether the claim, as
    scoped, is honored.
    """
    rt = projection.get("roundtrip") or {}
    subset = set(rt.get("subset") or [])
    outcomes = {}
    for name, pair in (observations or {}).items():
        outcomes[name] = "preserved" if pair.get("equal") else "failed"
    honored = bool(subset) and not any(
        v == "failed" for name, v in outcomes.items() if name in subset
    )
    return {
        "outcomes": outcomes,
        "claim_honored": honored,
        "subset": sorted(subset),
        "tested_domain": rt.get("tested_domain") or [],
    }


def equivalence_claim(claim):
    """Decide an equivalence claim. Profile resolution and schema validity are
    necessary context but never sufficient: a declared equivalence criterion
    (with an entailment policy for semantic equivalence) is required."""
    reasons = []
    criterion = (claim or {}).get("equivalence")
    if not criterion:
        _reason(reasons, "no_declared_equivalence_criterion")
    if criterion == "semantic" and not (claim or {}).get("entailment_policy"):
        _reason(reasons, "semantic_equivalence_without_entailment_policy")
    return {"granted": not reasons, "reasons": reasons}


def evaluate(projection):
    """Evaluate one declared projection against O-A01, O-A04 and O-A05.

    A projection that omits its provenance declaration is not applied as a
    valid mapping (status incomplete, pass false).
    """
    if not _has_provenance(projection):
        return {
            "status": "incomplete",
            "reasons": ["missing_provenance"],
            "checks": {
                "o-a01": {"pass": False, "reasons": ["missing_provenance"], "coerced": []},
                "o-a04": {"pass": False, "reasons": ["missing_provenance"],
                          "undeclared": [], "disposition_errors": []},
                "o-a05": {"pass": False, "reasons": ["missing_provenance"]},
            },
            "pass": False,
        }
    checks = {
        "o-a01": _o_a01(projection),
        "o-a04": _o_a04(projection),
        "o-a05": _o_a05(projection),
    }
    reasons = sorted({r for c in checks.values() for r in c["reasons"]})
    return {
        "status": "complete",
        "reasons": reasons,
        "checks": checks,
        "pass": all(c["pass"] for c in checks.values()),
    }
