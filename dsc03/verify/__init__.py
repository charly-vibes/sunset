# Purpose: Verifier ladder package (sunset-1x7): pinned pure verifiers with
#   stable reason codes — tier 0 anchor/value checks, tier 1 Argentine
#   domain pack (CUIT check digit, subtotal+tax=total, running balance,
#   date/currency parse), tier 3 adapter over dsc03.visual oracles. Tier 2
#   (independent agreement) is DEFERRED with a re-entry trigger; `agreed`
#   stays reserved in the status order with no producer.
# Responsibilities: Registry of verifiers declaring {id, version, digest,
#   tier, applies_to, check(claim, *, descriptor_claims=()) -> {outcome,
#   reason_code}}; no network, no clock, no randomness — output is a pure
#   function of claim + descriptor; REGISTRY_DIGEST pins the pack; run_ladder
#   applies tier 0 then applicable tier 1 rules and computes status
#   (`verified` requires a tier 0 pass AND a passed applicable tier 1 rule;
#   no applicable rule never yields `verified`).
"""Pinned verifier registry: tiers 0, 1, 3; tier 2 deferred."""
import hashlib

from dsc03.verify.registry import (
    REGISTRY,
    REGISTRY_DIGEST,
    VERIFIERS,
    TIER0,
    TIER1,
    TIER3,
    Verifier,
    run_ladder,
    verifier,
)

__all__ = ["REGISTRY", "REGISTRY_DIGEST", "VERIFIERS", "TIER0", "TIER1",
           "TIER3", "Verifier", "run_ladder", "verifier"]


def registry_digest():
    """Pinned digest of the verifier pack (run configuration input)."""
    return REGISTRY_DIGEST


def _pinning_payload():
    return hashlib.sha256(REGISTRY_DIGEST.encode()).hexdigest()
