## Context

`dsc03/substrate/context.py` already models claims as wire annotations with `target/term/value/origin/status/evidence` and implements disputes, inheritance, deterministic replay and no-union assembly. This change names claims as a first-class output unit for models and gives them a verification contract. It does not alter the wire; claim records are carried as annotations plus a claim-extension profile (Open Question 1).

## Goals / Non-Goals

Goals: a model-facing output unit that cannot hallucinate extractive text; deterministic, replayable verification; an honest account of what verified means.

Non-goals: judging whether a document's statements are true; model selection; UI (see `add-review-queue-and-audit`); duplicating conflict semantics owned by `document-context`.

## Decisions

1. **Claim id** is a digest of `(type, sorted anchors, canonical value, origin)`. Re-submitting an identical claim is idempotent.
2. **Extractive vs generative.** Extractive: value must equal the declared normalization of the anchored span (mismatch refused `claim.value.mismatch`). Generative (summaries, classifications): value supplied, flagged `value_origin: model`, and capped at `unverified` unless tier 2 or tier 4 settles it.
3. **Normalization registry.** Each pinned claim type declares its normalization: whitespace collapse, Unicode form, decimal separator and grouping (AR `1.234,56`), currency symbols, date formats. Tier 0 and tier 1 read the registry; a type without a registered normalization is `unverified`, never silently compared as raw strings. The initial pack covers the Argentine fixture formats and documents what it does not establish.
4. **Status order and meet.** `verified > agreed > unverified > conflicted`. `verified` requires at least one tier 0 pass plus a tier 1 rule that applies to the claim type; the absence of an applicable rule never yields `verified`. `agreed` is reserved: its producer (tier 2 independent agreement) is deferred with a re-entry trigger (Necessity cuts).
5. **Verifier contract.** `{id, version, digest, applies_to(type), check(claim, descriptor) -> {outcome, reason_code}}`. No network, no clock, no randomness. Registry is pinned by digest in the run configuration.
6. **Confidence.** Any model-reported confidence is stored as metadata outside the semantic digest and is never read by verifiers.
7. **Conflicts.** Two claims with the same scope and type but different values are both retained, each attributed. Resolution requires a declared precedence rule (existing context law), never recency or model preference.
8. **Human decisions** are claims with `origin: human`, reviewer id recorded as non-semantic metadata.
9. **Initial domain pack.** CUIT/CUIL check digit, subtotal plus tax equals total, running-balance continuity, date and currency parse. Scoped to Argentine fixtures; each rule ships with negative fixtures per rule (a verifier bug is a silent false accept otherwise).
10. **Tier 2 deferred.** Independent-agreement machinery (second model run, independence check on producer identity) is not built now: it doubles model spend and no fixture claim type needs autonomy without a domain rule yet. Re-entry trigger in proposal Necessity cuts.

## Reconciliation (task 1.1, done 2026-11-24)

Dispute/conflict retention semantics are owned by **`document-context`** ("Evidence is not truth", "Deterministic semantic rules"): `dsc03/substrate/context.py` keeps incompatible attributed claims disputed/retained and elects no winner without a declared precedence rule (`resolve_bindings`, `elected_winner`). This change reuses those semantics and adds no second mechanism: `dsc03/claims.py:mark_conflicts` retains both attributed claims and marks them `conflicted` without electing, and `dsc03/verify` never promotes a `conflicted` claim. Claim identity dedupe (`dedupe_annotations`) collapses only identical `(term, target, value, origin)` digests — never differing values.

## What "verified" does and does not establish (tasks 5.3)

`verified` means: the claim's anchors resolved, its extractive value equals the registered normalization of the anchored span, and every applicable pinned tier-0/tier-1 check passed as a pure function of claim + descriptor. It does NOT establish that the document's contents are true of the world (no ground-truth oracle ran), and it is bounded by the registry: a missing normalization or missing domain rule yields `unverified` by design. All measured outcomes above are agent-executed against synthetic fixtures; no accuracy or conformance claim is made. Model confidence is stored outside the semantic digest and never read by verifiers (tests: `tests/tracer/test_claims_ladder.py`, `tests/tracer/test_verify_ladder.py`).

## Risks / Trade-offs

- "verified" may be over-read as "true". Mitigation: status name and docs say *passed pinned checks*; export carries the checks that passed.
- Few domain rules means few claims reach `verified`. Mitigation: that is the honest result; tier 2 and the audit gate widen autonomy with evidence.
- A missing normalization could look like a verifier failure. Mitigation: the registry is part of the run configuration; `unverified` reason codes name the missing entry.

## Open Questions

1. Encode claims as annotations with a profile, or add a `claims` section in a later DSC version?
   **Ruled (owner, 2026-11-24, via sunset-gpd gate G2): annotations with a claim-extension profile.** No new wire section; task 2.3 unblocked.
2. Which claim type vocabulary is pinned first (`field:*`, `heading`, `table-cell`)?
