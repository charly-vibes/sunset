# Purpose: Claims as the model-facing output unit (sunset-1x7,
#   add-claim-verification-ladder): anchored, extractive-derivable claim
#   records with stable refusal reason codes, a pinned normalization
#   registry, the status order with meet aggregation, conflict retention,
#   idempotent identity, and confidence kept outside the semantic digest.
# Responsibilities: Provide (1) submit_claim — resolve anchors against a
#   descriptor (dangling anchor refused `claim.anchor.unresolved`), derive
#   extractive values from the anchored text through the normalization
#   registry (mismatch refused `claim.value.mismatch`; registered type whose
#   span fails to parse refused `claim.value.unparseable`; unregistered type
#   admitted at `unverified` with `claim.normalization.unregistered`), flag
#   generative claims and cap them at `unverified`; (2) claim_id +
#   add_claim — digest identity over (type, sorted anchors, canonical value,
#   origin[, decision]) with idempotent resubmission; (3)
#   STATUS_ORDER / meet_status —
#   `verified > agreed > unverified > conflicted`, `rejected` excluded from
#   aggregation, no producer for `agreed` under this change; (4)
#   mark_conflicts — same scope+type, different values: both retained,
#   attributed, `conflicted`, no winner without a declared rule; (5)
#   human_decision — reviewer corrections as `origin: human` claims that
#   never overwrite the model claim. Never judges document truth; statuses
#   name passed pinned checks only.
# Rationale: models cannot hallucinate extractive text when values must
#   equal the declared normalization of the anchored span; dispute/conflict
#   retention semantics stay owned by document-context
#   (dsc03/substrate/context.py) — this module defers to them (tasks 1.1).
"""Claims: anchored records, normalization registry, status meet."""
import hashlib
import re
import unicodedata

# -- status vocabulary ----------------------------------------------------------

STATUS_ORDER = ("verified", "agreed", "unverified", "conflicted")
# `agreed` is RESERVED: its producer (tier 2 independent agreement) is
# deferred with a re-entry trigger (proposal Necessity cuts). No code in
# this change emits it.
REJECTED = "rejected"  # human-only; excluded from aggregation

ANCHOR_UNRESOLVED = "claim.anchor.unresolved"
VALUE_MISMATCH = "claim.value.mismatch"
NORMALIZATION_UNREGISTERED = "claim.normalization.unregistered"
VALUE_UNPARSEABLE = "claim.value.unparseable"

# -- normalization registry (tasks 2.4) ------------------------------------------

_DECIMAL_FORMATS = {
    # AR fixtures: '.' grouping, ',' decimal separator (1.234,56)
    "ar": (".", ","),
}


def normalize_whitespace(text):
    """NFC-normalize, then collapse all whitespace runs to single spaces."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def normalize_decimal(text, fmt="ar"):
    """Normalize a decimal string to canonical `1234.56` form.

    Refuses mixed/invalid grouping by returning None (tier-1 parse rules
    surface the typed failure; no silent raw-string comparison).
    """
    grouping, decimal = _DECIMAL_FORMATS[fmt]
    text = normalize_whitespace(text).replace(" ", "")
    for symbol in ("$", "ARS", "€", "USD"):
        text = text.replace(symbol, "")
    text = text.strip()
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    # canonical form (as stored on admitted claims) passes through
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return ("-" + text) if negative else text
    if decimal not in text:
        # integer part only: grouping dots must be well-formed
        if "." in text:
            return None
        canon = text
    else:
        int_part, _, frac = text.partition(decimal)
        if not frac.isdigit() or not int_part:
            return None
        if "." in int_part and len(int_part.split(".")[-1]) != 3:
            return None
        canon = int_part.replace(".", "") + "." + frac
    if not canon or not canon.replace(".", "").isdigit():
        return None
    return ("-" + canon) if negative else canon


def normalize_date(text):
    """Normalize AR/common date formats to ISO yyyy-mm-dd; None if invalid."""
    text = normalize_whitespace(text)
    parts = None
    for sep in ("/", "-", "."):
        bits = text.split(sep)
        if len(bits) == 3 and all(b.isdigit() for b in bits):
            parts = bits
            break
    if parts is None:
        return None
    a, b, c = parts
    try:
        if len(c) == 4:  # dd/mm/yyyy
            d, m, y = int(a), int(b), int(c)
        elif len(a) == 4:  # yyyy-mm-dd
            y, m, d = int(a), int(b), int(c)
        else:
            return None
    except ValueError:
        return None
    import datetime
    try:
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return None


def normalize_currency(text, fmt="ar"):
    """Currency-qualified decimal: `$ 1.234,56` -> `1234.56`; None invalid."""
    return normalize_decimal(text, fmt)


REGISTRY = {
    "field:total": normalize_currency,
    "field:subtotal": normalize_currency,
    "field:tax": normalize_currency,
    "field:amount": normalize_currency,
    "field:balance": normalize_currency,
    "field:prior-balance": normalize_currency,
    "field:cuit": lambda text: normalize_whitespace(text).replace("-", ""),
    "field:date": normalize_date,
}


def normalize(claim_type, text):
    """Registry lookup; None when the type has no registered normalization."""
    fn = REGISTRY.get(claim_type)
    return None if fn is None else fn(text)


# -- identity (design decision 1) ------------------------------------------------

def claim_id(claim_type, anchors, canonical_value, origin, decision=None):
    """Digest of (type, sorted anchors, canonical value, origin[, decision]).

    `decision` extends the identity for human decision claims: two
    decisions about the same value (accept vs reject) must never collide
    into one id and silently drop each other.
    """
    payload = {
        "type": claim_type, "anchors": sorted(anchors),
        "value": canonical_value, "origin": origin,
    }
    if decision is not None:
        payload["decision"] = decision
    return "c:" + hashlib.sha256(json_bytes(payload)).hexdigest()[:32]


def json_bytes(obj):
    import json
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


class Refusal(Exception):
    """A typed, classified claim refusal with a stable reason code."""

    def __init__(self, reason_code, detail=""):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


# -- anchoring -------------------------------------------------------------------

def anchored_text(desc, anchors):
    """Text of every content linked to the anchored regions (has-content).

    Raises Refusal(ANCHOR_UNRESOLVED) when any anchor id is not a region or
    content of the descriptor.
    """
    region_ids = {r["id"] for r in desc.get("regions", [])}
    content_ids = {c["id"] for c in desc.get("contents", [])}
    for anchor in anchors:
        if anchor not in region_ids and anchor not in content_ids:
            raise Refusal(ANCHOR_UNRESOLVED, anchor)
    out = []
    for rel in desc.get("relations", []):
        if rel["kind"] == "has-content" and rel["from"] in anchors:
            for c in desc.get("contents", []):
                if c["id"] == rel["to"] and c.get("kind") == "text":
                    out.append(c["value"])
    # an anchor may BE a content: its own text is the anchored span
    for c in desc.get("contents", []):
        if c["id"] in anchors and c.get("kind") == "text":
            out.append(c["value"])
    return "\n".join(out)


# -- submission -------------------------------------------------------------------

def submit_claim(desc, spec):
    """Resolve, normalize and admit a claim; raises Refusal when the spec
    violates the anchoring or extractive-value requirements.

    Generative claims are flagged value_origin `model` and capped at
    `unverified`. Confidence is stored outside digest_input.
    """
    claim_type = spec["type"]
    anchors = sorted(spec["anchors"])
    origin = spec["origin"]
    extractive = bool(spec.get("extractive", True))
    value = spec["value"]

    if extractive:
        text = anchored_text(desc, anchors)
        registered = claim_type in REGISTRY
        normalized_span = normalize(claim_type, text)
        if not registered:
            # genuine registry miss: the span is admitted as-is at
            # `unverified` and flagged — never silently compared
            reasons = [{"code": NORMALIZATION_UNREGISTERED, "type": claim_type}]
            canonical = normalize_whitespace(text)
        elif normalized_span is None:
            # registered but the anchored span does not parse: refusing is
            # typed and honest — storing the raw span as canonical would
            # discard the model value and make a same-origin corrected
            # resubmission collide on id
            raise Refusal(VALUE_UNPARSEABLE,
                          f"{claim_type!r} cannot parse anchored {text!r}")
        else:
            normalized_value = normalize(claim_type, value)
            if normalized_value != normalized_span:
                raise Refusal(VALUE_MISMATCH,
                              f"{value!r} vs anchored {text!r}")
            canonical = normalized_value
            reasons = []
        value_origin = "anchored"
        status = "unverified"
    else:
        # generative: value supplied by the model, capped at unverified
        canonical = value
        value_origin = "model"
        reasons = [{"code": "claim.generative.capped"}]
        status = "unverified"

    confidence = spec.get("confidence")
    digest_input = {
        "type": claim_type, "anchors": anchors,
        "value": canonical, "origin": origin,
    }
    decision = spec.get("decision")
    if decision is not None:
        digest_input["decision"] = decision
    claim = {
        "id": claim_id(claim_type, anchors, canonical, origin, decision),
        "type": claim_type,
        "anchors": anchors,
        "value": canonical,
        "value_origin": value_origin,
        "origin": origin,
        "status": status,
        "reasons": reasons,
        "checks": [],
        "digest_input": digest_input,  # semantic digest covers these fields only
        "confidence": confidence,      # metadata: outside the semantic digest
    }
    if origin == "human":
        claim["reviewer"] = spec.get("reviewer")  # non-semantic metadata
    return claim


def add_claim(claims, claim):
    """Idempotent insertion: identical identity creates no duplicate."""
    if any(c["id"] == claim["id"] for c in claims):
        return list(claims)
    return list(claims) + [claim]


# -- status aggregation (tasks 3.1) -----------------------------------------------

def meet_status(claims):
    """Meet over the status order, excluding `rejected` claims.

    `rejected` (human) never weakens a scope's status; it is excluded from
    export per the proposal.
    """
    statuses = [c["status"] for c in claims if c["status"] != REJECTED]
    if not statuses:
        return "unverified"
    ranks = {s: i for i, s in enumerate(STATUS_ORDER)}
    return max(statuses, key=lambda s: ranks.get(s, len(STATUS_ORDER)))


def mark_conflicts(claims):
    """Same scope (anchors) and type with different canonical values: BOTH
    retained, each attributed, both `conflicted`. No winner is elected —
    resolution needs a declared precedence rule (document-context law),
    never recency or model preference.
    """
    out = [dict(c) for c in claims]
    groups = {}
    for c in out:
        groups.setdefault((c["type"], tuple(sorted(c["anchors"]))), []).append(c)
    for group in groups.values():
        values = {c["value"] for c in group}
        if len(values) > 1:
            for c in group:
                c["status"] = "conflicted"
    return out


def human_decision(desc, spec):
    """A human acceptance/rejection/correction as an `origin: human` claim;
    the model claim it concerns is never overwritten (caller keeps both)."""
    spec = dict(spec, origin="human")
    return submit_claim(desc, spec)


# -- substrate reconciliation (tasks 1.1, 2.3) -----------------------------------

def annotation_identity(annotation):
    """The claim identity of a wire annotation (target/term/value/origin)."""
    return claim_id(annotation["term"], [annotation["target"]],
                    annotation["value"], annotation["origin"])


def export_record(claim):
    """The export view of a claim: status plus exactly which checks passed.
    Confidence and reviewer ids are non-semantic metadata and are excluded;
    `rejected` claims are excluded from export by the caller."""
    return {
        "id": claim["id"], "type": claim["type"], "status": claim["status"],
        "checks": [{"id": c["id"], "outcome": c["outcome"]}
                   for c in claim.get("checks", [])],
        "checks_passed": sum(1 for c in claim.get("checks", [])
                             if c["outcome"] == "pass"),
    }
