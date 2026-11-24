# RO5U self-review: sunset-v0j anchor-derived identity (2.1-2.4)

## Critical
None.

## High
None.

## Medium
None.

## Low
1. dsc03/profiles.py:131-138 (identity digest grammar) — `digest_spec.get("truncation_bits") == 128` also accepts JSON float `128.0` because Python `==` crosses int/float. Evidence: sibling checks in resolve() use the same `==` style (e.g. `artifact.get("version") != decl["version"]`). Concrete fix: none needed for consistency; if tightening is ever wanted, add `type(...) is int`. Not changed: additive branch must mirror sibling style.
2. dsc03/validator.py:608-612 — the `status != "derived"` branch is unreachable for fields validated in the same rule (source digest, nonempty strings, profile id/version all pre-validated). Evidence: `anchor_reason` reasons `anchor_arity/anchor_source_digest/anchor_field` cannot fire for the assembled tuple. Concrete fix: none — kept deliberately so a future wire change degrades to a typed invalid_shape, never a guessed comparison.

## Verified invariants
- No identity profile declared -> rule inert; existing fixtures byte-identical outcomes (tests/tracer/test_tracer_validate.py 6 passed; fixture_minimal.json untouched).
- Anchor wire: optional {"record_kind","locator_path"}; tuple assembled per design Decision 1 (selectors use their own source_sha256, others d["source"]["sha256"]; record_kind = section singular; profile id/version from the single declared identity profile).
- Reason codes snake_case matching neighbor vocabulary: identity_mismatch, identity_anchor_missing (+ reused invalid_profile/invalid_shape).
