# Change: Claims as the model-facing output unit with a pinned verification ladder

## Why

Models cannot yet expose results to Sunset in a form that can be checked. Free-text output cannot be tied to the page, and nothing decides when a result is trustworthy enough to skip a human. The goal: models propose, deterministic verifiers decide, humans see only what verifiers cannot settle.

The DSC context layer already has attributed annotations (`target/term/value/origin/status/evidence`, `dsc03/substrate/context.py`) and the "no truth laundering" law. Verified at HEAD: disputes, deterministic replay and no-union assembly are implemented there. What is missing is the unit models emit, the status vocabulary, and a verifier contract.

## What Changes

- Add a **claim** record: type, anchors, value, origin, status. Extractive claims derive their value from the anchored span; a model cannot supply it.
- Add a **normalization registry**: each claim type declares its value normalization (whitespace, decimal and currency formats — AR fixtures use `1.234,56`); extractive comparison and tier-1 rules read the registry, never ad-hoc string logic.
- Add a status order `verified > agreed > unverified > conflicted`, plus `rejected` (human) excluded from export. Aggregation over a scope is the meet.
- Add a **verifier ladder**: tier 0 anchor and value checks, tier 1 domain rules (check digits, arithmetic, dates, currency), tier 3 visual oracles, tier 4 human. Tier 2 (independent agreement) is deferred — see Necessity cuts; `agreed` stays in the status order as reserved.
- Verifiers are pinned, pure functions with stable reason codes.
- Model self-reported confidence is never an input to status.
- Disagreeing claims at one scope are retained, attributed, with no winner unless a declared rule applies.

## Impact

- Affected specs: new capabilities `document-claims`, `document-verification` (all requirements ADDED); reconciliation task 1.1 aligns claim retention with in-flight `document-context` ("Evidence is not truth", "Deterministic semantic rules") so conflict semantics are stated once.
- Depends on `add-anchor-derived-identity` (claim ids) and `add-scale-complete-regions` (anchors at word level, `lift`).
- Reuses: `dsc03` annotations and evidence, `dsc03/visual` oracles as tier 3, `dsc03/compare` for tier 2 matching by anchor.
- Affected code: new `dsc03/claims.py`, `dsc03/verify/` (registry, tiers 0 and 1), fixtures from `invoice-arca-redacted`, `bank-statement-ca-excerpt`.
- No conformance label changes; domain verifiers claim arithmetic and format consistency only, not truth of the document's contents.

## Necessity cuts (2026-11-24 audit)

- **Tier 2 independent agreement**: deferred. Autonomy v1 runs on tier-1 rules + human audit; `agreed` stays in the status order as reserved with no producer. Trigger: a claim type needs autonomy but has no applicable domain rule. This also halves model spend (no second-run requirement).
