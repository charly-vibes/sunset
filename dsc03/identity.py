# Purpose: Anchor-derived record identity for DSC 0.3 identity profiles
#   (sunset-v0j, add-anchor-derived-identity tasks §2.2/§2.3).
# Responsibilities: derive_id — compute the id for one anchor tuple
#   (source_sha256, record_kind, locator_path, profile_id, profile_version) as
#   "a:" + the first 128 bits of SHA-256 over the canonical JSON of the tuple,
#   with typed refusals (stable reasons, never a guessed id) for malformed
#   tuples and an injectable digest callable for collision tests;
#   IdentityRegistry — the admission path tracking id -> anchor within its
#   lifetime, refusing two different anchors that derive the same id with a
#   witness naming both tuples.
# Rationale: add-anchor-derived-identity design Decisions 1-2 and the
#   Collision-refusal requirement: ids are functions of anchors, never of
#   position, producer-local counters or operand order; collisions are
#   detected, never silently merged or renamed. Canonical JSON matches the
#   dsc03.canonical emission form (sort_keys, ensure_ascii=False, compact
#   separators, allow_nan=False).
"""Anchor-derived identity: ids as digests of anchor tuples, with collision refusal."""
import hashlib
import json
import re

# (source_sha256, record_kind, locator_path, profile_id, profile_version)
ANCHOR_FIELDS = (
    "source_sha256",
    "record_kind",
    "locator_path",
    "profile_id",
    "profile_version",
)
ID_PREFIX = "a:"
ID_HEX_CHARS = 32  # 128 bits, lowercase hex

SHA256_RE = re.compile("[0-9a-f]{64}")

# Stable refusal reasons for malformed anchors (typed outcomes, never guesses):
#   anchor_arity         — not a 5-element tuple/list
#   anchor_source_digest — source_sha256 is not 64 lowercase hex chars
#   anchor_field         — record_kind/locator_path/profile_id/profile_version
#                          is not a nonempty string


def canonical_anchor_bytes(anchor):
    """Canonical JSON bytes of the anchor tuple, in dsc03.canonical's form."""
    return json.dumps(
        list(anchor), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def anchor_reason(anchor):
    """Stable refusal reason for a malformed anchor tuple, else None."""
    if not isinstance(anchor, (tuple, list)) or len(anchor) != len(ANCHOR_FIELDS):
        return "anchor_arity"
    source_sha256 = anchor[0]
    if not isinstance(source_sha256, str) or not SHA256_RE.fullmatch(source_sha256):
        return "anchor_source_digest"
    if not all(isinstance(f, str) and f for f in anchor[1:]):
        return "anchor_field"
    return None


def _sha256(raw):
    return hashlib.sha256(raw).digest()


def derive_id(anchor, *, digest=None):
    """Derive the record id for one anchor tuple as a typed outcome.

    Returns ('derived', id) with id = "a:" + lowercase hex of the first 128
    digest bits over the canonical JSON of the tuple, or ('invalid_anchor',
    reason) with reason from anchor_reason. `digest` may inject any
    bytes -> bytes callable (tests force collisions by truncation); the
    default is SHA-256.
    """
    reason = anchor_reason(anchor)
    if reason is not None:
        return "invalid_anchor", reason
    if digest is None:
        digest = _sha256
    return "derived", ID_PREFIX + digest(canonical_anchor_bytes(anchor)).hex()[:ID_HEX_CHARS]


class IdentityRegistry:
    """Admission path for anchor-derived ids within one process lifetime.

    Tracks id -> admitted anchor. Two different anchors deriving the same id
    are refused as a collision with a witness naming BOTH tuples; re-admitting
    the identical anchor is idempotent (same anchor, same id — that is the
    contract, not a collision).
    """

    def __init__(self):
        self._anchors = {}

    def register(self, anchor, *, digest=None):
        """Return ('admitted', id) | ('invalid_anchor', reason) | ('collision', witness).

        The collision witness is {"id", "witness"} where witness lists the
        earlier and the refused anchor tuples (as JSON-able lists).
        """
        status, payload = derive_id(anchor, digest=digest)
        if status != "derived":
            return status, payload
        rid = payload
        anchor = tuple(anchor)
        seen = self._anchors.get(rid)
        if seen is None:
            self._anchors[rid] = anchor
            return "admitted", rid
        if seen == anchor:
            return "admitted", rid
        return "collision", {"id": rid, "witness": [list(seen), list(anchor)]}
