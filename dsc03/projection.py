# Purpose: Pinned anchor-matched comparison of extractor outputs for DSC 0.3
#   (sunset-r68.12, task 5.2).
# Responsibilities: Compare two extractor outputs through a declared projection
#   pinned by identifier, version and artifact digest plus source digest.
#   Observations are matched by resolved source anchors or an explicit reviewed
#   mapping — never by snapshot-local ids or label similarity. Ambiguous
#   matching stays unresolved (attributed to both sides), never an arbitrary
#   pairing. The comparator reports per-observable matches, false positives,
#   false negatives and unresolved cases against independently reviewed
#   expectations; a case passes only when every required observable matches an
#   allowed expectation (including explicitly allowed unresolved alternatives);
#   any forbidden result fails. Missing projection or oracle makes the check
#   incomplete.
# Rationale: add-dsc-03 document-conformance "Reader independence" (MODIFIED).
"""Pinned projection + comparator: match by anchors, retain alternatives."""
INCOMPLETE = {"status": "incomplete", "reasons": ["missing_projection_or_oracle"],
              "matches": 0, "false_positives": [], "false_negatives": [],
              "unresolved": [], "retained_alternatives": [], "pass": False}

PIN_KEYS = ("projection_id", "version", "projection_sha256", "source_sha256")


def _obs_anchors(o):
    return set(o.get("anchors") or [])


def _incomplete(reason):
    return {**INCOMPLETE, "reasons": [reason]}


def _pin_ok(pin):
    """A pin SHALL name identifier, version, projection digest and source digest."""
    return isinstance(pin, dict) and all(
        isinstance(pin.get(k), str) and bool(pin.get(k)) for k in PIN_KEYS
    )


def _attributed(extractor_a, extractor_b, a, b, anchors):
    """One retained set: both sides' values kept attributed, no winner picked."""
    return {
        "observable": a["observable"],
        "anchors": sorted(anchors),
        "values": [
            {"extractor_id": extractor_a.get("extractor_id"),
             "id": a.get("id"), "value": a.get("values")},
            {"extractor_id": extractor_b.get("extractor_id"),
             "id": b.get("id"), "value": b.get("values")},
        ],
    }


def compare(extractor_a, extractor_b, pin, oracle):
    """Compare two extractor outputs under a pinned projection and oracle.

    pin: {"projection_id","version","projection_sha256","source_sha256",...}
    oracle: {"required": [observable], "allowed_unresolved": [observable],
             "forbidden": [observable]}
    """
    if pin is None or oracle is None:
        return _incomplete("missing_projection_or_oracle")
    if not _pin_ok(pin):
        return _incomplete("invalid_projection_pin")
    obs_a = list(extractor_a.get("observations") or [])
    obs_b = list(extractor_b.get("observations") or [])

    pairs = []          # (a_obs, b_obs)
    ambiguous = []      # observables with >1 candidate pairing
    unmatched_a = []
    unmatched_b = list(obs_b)

    for a in obs_a:
        candidates = [
            b for b in unmatched_b
            if b.get("observable") == a.get("observable")
            and _obs_anchors(a) & _obs_anchors(b)
        ]
        if len(candidates) > 1:
            ambiguous.append(a["observable"])
            continue  # candidates stay unpaired; ambiguity is reported, not resolved
        if not candidates:
            unmatched_a.append(a)
            continue
        b = candidates[0]
        unmatched_b.remove(b)
        pairs.append((a, b))

    matches = 0
    retained = []
    divergent = []
    for a, b in pairs:
        if a.get("values") == b.get("values"):
            matches += 1
        else:
            # value divergence under one anchor pairing: keep both attributed,
            # never silently pick a winner; the observable is unresolved
            divergent.append(a["observable"])
            retained.append(_attributed(
                extractor_a, extractor_b, a, b,
                _obs_anchors(a) & _obs_anchors(b)))

    # both sides hold observations on the same observable but no anchor pairing
    # exists: that is ambiguity (e.g. same text, different anchors), not FP/FN
    a_by_obs = {}
    for a in unmatched_a:
        a_by_obs.setdefault(a["observable"], []).append(a)
    b_by_obs = {}
    for b in unmatched_b:
        b_by_obs.setdefault(b["observable"], []).append(b)

    unresolved = list(dict.fromkeys(ambiguous + divergent))
    for o, av in a_by_obs.items():
        if o in b_by_obs and o not in unresolved:
            unresolved.append(o)
        if o in b_by_obs:
            for a in av:
                for b in b_by_obs[o]:
                    retained.append(_attributed(extractor_a, extractor_b, a, b, set()))

    false_positives = []
    false_negatives = []
    required = set(oracle.get("required") or [])
    for o in a_by_obs:
        if o not in b_by_obs and o not in required:
            false_positives.append(o)
    seen_fn = set()
    for o, av in a_by_obs.items():
        if o not in b_by_obs and o in required:
            false_negatives.append(o)
            seen_fn.add(o)
    for o in b_by_obs:
        if o not in a_by_obs and o in required and o not in seen_fn:
            false_negatives.append(o)
            seen_fn.add(o)

    allowed = set(oracle.get("allowed_unresolved") or [])
    forbidden = set(oracle.get("forbidden") or [])
    matched_obs = matches_done(pairs)
    unresolved_set = set(unresolved)
    # a required observable absent from BOTH sides is the clearest false negative
    for o in required:
        if o not in matched_obs and o not in unresolved_set \
                and o not in seen_fn:
            false_negatives.append(o)
            seen_fn.add(o)
    all_observables = (
        {a.get("observable") for a in obs_a} | {b.get("observable") for b in obs_b}
    )
    reasons = []
    if sorted(all_observables & forbidden):
        reasons.append("forbidden_observable_present")
    # every required observable must be matched or actually unresolved (with
    # both sides attributed); merely being listed as allowed is not enough —
    # a side dropping the observation entirely is a false negative, not an
    # allowed unresolved alternative
    if not all(o in matched_obs or o in unresolved_set for o in required):
        reasons.append("required_observable_unresolved")
    if not unresolved_set <= allowed:
        reasons.append("unresolved_not_allowed")
    return {
        "status": "complete",
        "reasons": sorted(reasons),
        "matches": matches,
        "false_positives": sorted(set(false_positives)),
        "false_negatives": sorted(set(false_negatives)),
        "unresolved": sorted(unresolved_set),
        "retained_alternatives": retained,
        "pass": not reasons,
    }


def matches_done(pairs):
    """Observables that matched exactly (equal values) under a pairing."""
    done = set()
    for a, b in pairs:
        if a.get("values") == b.get("values"):
            done.add(a["observable"])
    return done
