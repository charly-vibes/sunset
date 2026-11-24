## 1. Reconciliation

- [x] 1.1 Align conflict retention with in-flight `document-context` ("Evidence is not truth", "Deterministic semantic rules"); record which capability owns dispute semantics in design.md

## 2. Claims

- [x] 2.1 RED: unresolved anchor refused `claim.anchor.unresolved`
- [x] 2.2 RED: extractive value differing from normalized anchored text refused `claim.value.mismatch`; missing normalization admits at `unverified` with reason
- [x] 2.3 Implement claim record, id derivation and idempotent resubmission
- [x] 2.4 Implement the normalization registry (whitespace, Unicode, AR decimal/currency `1.234,56`, dates); seed from the fixture formats
- [x] 2.5 Generative claims flagged and capped at unverified

## 3. Status

- [x] 3.1 Status order, meet aggregation and `rejected` exclusion
- [x] 3.2 Conflict retention with attribution; no winner without declared rule
- [x] 3.3 Confidence stored outside semantic digest; test that changing it changes no status

## 4. Verifier registry

- [x] 4.1 Contract, registry pinned by digest, determinism test (same input, same output, no I/O)
- [x] 4.2 Tier 0 verifiers
- [x] 4.3 Tier 1 domain pack with negative fixtures per rule (CUIT/CUIL, subtotal+tax=total, running balance, date/currency parse)
- [ ] 4.4 Deferred (phase 2, gated): tier 2 agreement — only when a claim type needs autonomy without an applicable domain rule; adds the producer-independence check and the `agreed` producer
- [x] 4.5 Tier 3 adapter over `dsc03/visual` oracles (done 2026-11-24: `visual.ink-agreement` v2 checks ink presence per anchor's quantized box against a `visual:render:page` descriptor fact through the shared `_pixels` gate — snap.py pt→px mapping, raw-mask fraction vs declared `INK_FRACTION_THRESHOLD` 0.01; typed pass / fail with witness / unsupported family incl. MaskUnavailable reasons; render is never carried on the claim; adapter-only, never auto-run; byte-identical across processes; ink PRESENCE only, not a glyph/text comparison. 4.4 stays unticked — deferred.)

## 5. Evidence

- [x] 5.1 Human decisions as `origin: human` claims
- [x] 5.2 Export record lists which checks passed per claim
- [x] 5.3 Docs: what "verified" does and does not establish; agent-executed caveat
