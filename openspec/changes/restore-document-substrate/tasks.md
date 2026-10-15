# Implementation tasks

- [x] Pin Sunset HEAD; enumerate deployed OpenSpec capabilities and current 0.3 conformance hooks; record commit, version and drift from README. (done at integration 2026-10-15 — see `proposal.md` § Integration record: HEAD `518a71a`, 7 deployed capability IDs verified)
- [ ] Validate this change against exact deployed OpenSpec and Specodelic schema; adjust naming/linking before merge.
- [ ] Map the six conceptual roles and categorical laws onto existing DSC 0.3 entities, with a table of satisfied/partial/missing evidence.
- [ ] Amend README and status with normative purpose, consumers, honest current capabilities and documented non-goals.
- [ ] Add native PDF fixture and deterministic structural oracle, without OCR.
- [ ] Add EPUB fixture and deterministic spine/navigation/footnote oracle, without forced pagination.
- [ ] Add scanned Ahira and hybrid PDF fixtures with alternate readings and evidence.
- [ ] Add unrelated financial/structured-document fixture to challenge domain independence.
- [ ] Implement typed-relations, determinism, composition, loss and non-invention checks; include negative counterexamples.
- [ ] Run existing `just spec-check`, the available `spk lint` on this change, and all existing 0.3 suites; report raw results.
- [ ] Independently implement or evaluate a second reader; measure agreement, descriptor overhead and unrepresentable cases.
- [ ] Publish conformance matrix distinguishing specification, executable checks, and independent cross-format evidence.
