## 1. Reconciliation

- [ ] 1.1 Align conflict retention with in-flight `document-context` ("Evidence is not truth", "Deterministic semantic rules"); record which capability owns dispute semantics in design.md

## 2. Claims

- [ ] 2.1 RED: unresolved anchor refused `claim.anchor.unresolved`
- [ ] 2.2 RED: extractive value differing from normalized anchored text refused `claim.value.mismatch`; missing normalization admits at `unverified` with reason
- [ ] 2.3 Implement claim record, id derivation and idempotent resubmission
- [ ] 2.4 Implement the normalization registry (whitespace, Unicode, AR decimal/currency `1.234,56`, dates); seed from the fixture formats
- [ ] 2.5 Generative claims flagged and capped at unverified

## 3. Status

- [ ] 3.1 Status order, meet aggregation and `rejected` exclusion
- [ ] 3.2 Conflict retention with attribution; no winner without declared rule
- [ ] 3.3 Confidence stored outside semantic digest; test that changing it changes no status

## 4. Verifier registry

- [ ] 4.1 Contract, registry pinned by digest, determinism test (same input, same output, no I/O)
- [ ] 4.2 Tier 0 verifiers
- [ ] 4.3 Tier 1 domain pack with negative fixtures per rule (CUIT/CUIL, subtotal+tax=total, running balance, date/currency parse)
- [ ] 4.4 Deferred (phase 2, gated): tier 2 agreement — only when a claim type needs autonomy without an applicable domain rule; adds the producer-independence check and the `agreed` producer
- [ ] 4.5 Tier 3 adapter over `dsc03/visual` oracles

## 5. Evidence

- [ ] 5.1 Human decisions as `origin: human` claims
- [ ] 5.2 Export record lists which checks passed per claim
- [ ] 5.3 Docs: what "verified" does and does not establish; agent-executed caveat
