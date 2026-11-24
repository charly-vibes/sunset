# Purpose: Derived review queue (sunset-3oq, add-review-queue-and-audit):
#   a pure function of claims and recorded crop references producing the
#   items a human must settle, plus the non-destructive decision actions
#   (accept / reject / edit) that create `origin: human` claims via
#   dsc03.claims.human_decision.
# Responsibilities: (1) review_queue — exactly the claims whose status is
#   `unverified` or `conflicted` (human `rejected` never queued), ordered by
#   scope (sorted anchors), then claim type, then claim id; (2) item content:
#   crop reference (render profile digest, page frame, box), canonical value,
#   verifier reason codes, every retained alternative with its origin;
#   (3) decide — accept/reject/edit recorded as human claims; the model claim
#   is never mutated and no queue item is ever written back into claims.
# Rationale: design decisions 1-3; the queue derives, it does not curate,
# and decisions are evidence, not edits of model output.
"""Derived review queue and human decision actions."""
from dsc03.claims import (REJECTED, REGISTRY, VALUE_UNPARSEABLE, Refusal,
                          human_decision, normalize)

QUEUE_STATUSES = ("unverified", "conflicted")


def review_queue(claims, crop_references=None):
    """The review queue: items for claims with status `unverified` or
    `conflicted`, in deterministic (scope, type, id) order. Same inputs,
    same queue — no timestamp, no RNG, no curation."""
    crop_references = crop_references or {}
    items = []
    for claim in claims:
        if claim["status"] not in QUEUE_STATUSES:
            continue
        scope = sorted(claim["anchors"])
        # every retained alternative on the same scope+type, with origin
        alternatives = [
            {"value": other["value"], "origin": other["origin"]}
            for other in claims
            if other["type"] == claim["type"]
            and sorted(other["anchors"]) == scope
        ]
        anchor_ids = set(scope)
        crop = next((crop_references[a] for a in scope
                     if a in crop_references), None)
        items.append({
            "claim_id": claim["id"],
            "claim_type": claim["type"],
            "status": claim["status"],
            "scope": scope,
            "value": claim["value"],
            "reason_codes": sorted(r["code"] for r in claim.get("reasons", [])),
            "alternatives": alternatives,
            "crop": crop,
        })
    items.sort(key=lambda i: (tuple(i["scope"]), i["claim_type"],
                              i["claim_id"]))
    return items


def decide(desc, claim, action, value=None, reviewer=None):
    """Record a reviewer decision as an `origin: human` claim; the model
    claim is never modified (the caller keeps both).

    The decision (accept | reject | edit) is part of the human claim's
    digest identity, so accept and reject of the same value never collide
    into one id and silently drop each other.

    - accept: a human claim repeating the claim's canonical value and
      anchors. Generative claims (`value_origin == "model"`) are recorded
      generative-of-human: their value never came from the anchored span,
      so routing them through the extractive path would refuse
      `claim.value.mismatch` and crash verdict ingestion.
    - reject: a human claim with status REJECTED (excluded from meet/export).
    - edit: a human claim with the adjusted value normalized through the
      registry (raw string only for unregistered types; unparseable values
      refused typed), or anchors via ``anchors=`` — recorded
      generative-of-human so it is capped at `unverified` and never
      silently validated against the model's span.
    """
    # a generative claim's value did not come from the anchored span: the
    # human decision mirrors it generatively (capped at `unverified`)
    extractive = claim.get("value_origin") != "model"
    if action == "accept":
        spec = {"type": claim["type"], "anchors": claim["anchors"],
                "value": claim["value"], "extractive": extractive,
                "decision": "accept"}
    elif action == "reject":
        spec = {"type": claim["type"], "anchors": claim["anchors"],
                "value": claim["value"], "extractive": extractive,
                "decision": "reject"}
    elif action == "edit":
        if value is None:
            raise ValueError("edit requires a value")
        if claim["type"] in REGISTRY:
            canonical = normalize(claim["type"], value)
            if canonical is None:
                raise Refusal(VALUE_UNPARSEABLE,
                              f"edit value {value!r} not parseable as "
                              f"{claim['type']!r}")
        else:
            canonical = value  # unregistered: no normalization to apply
        spec = {"type": claim["type"], "anchors": claim["anchors"],
                "value": canonical, "extractive": False, "decision": "edit"}
    else:
        raise ValueError(f"unknown action {action!r}")
    human = human_decision(desc, spec)
    if action == "reject":
        human["status"] = REJECTED
    human["reviewer"] = reviewer  # non-semantic metadata
    return human
