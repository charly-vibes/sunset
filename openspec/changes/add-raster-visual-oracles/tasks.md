# Tasks

## 1. Contract validation (this proposal)

- [ ] 1.1 Validate the change strictly: `openspec validate add-raster-visual-oracles --strict` passes; `spk lint openspec/changes` reports no issues for this change; full `just spec-check` stays green (no code touched yet).

## 2. Owner approval gate

- [ ] 2.1 Owner reviews proposal.md and design.md; approval (recorded in beads) authorizes implementation slices below. No implementation before approval.

## 3. Pinned rendering infrastructure

- [ ] 3.1 TDD: failing test first — render configuration record (renderer name/version, DPI, page selection, binarization, source simplification) reproduces byte-identical renders; missing renderer yields typed `unavailable`.
- [ ] 3.2 TDD: frame mapping through a declared geometry profile frame resolves pixel↔descriptor coordinates for native, scanned and rotated pinned carriers; incompatible or missing frames produce `unknown`, never `agree`/`differ`.

## 4. First two oracle properties (representation levels B and C)

- [ ] 4.1 TDD: binarized ink-coverage oracle (level B) over pinned carriers, including the like-with-like source simplification (design D4); outcomes per page/property with evidence class `correlated` or `independent`.
- [ ] 4.2 TDD: geometry-mask alignment oracle (level C) comparing descriptor region masks with the simplified source; disagreements retained with region attribution; no winner election.

## 5. Mutation validation and calibration

- [ ] 5.1 TDD: seeded-mutation fixtures (shift, omission, duplication, wrong frame) over committed carriers; each oracle detects exactly the defect classes it claims; claiming classes without a passing mutation demonstration keeps the property `uncalibrated`.
- [ ] 5.2 Calibration sheet: thresholds derived from recorded runs over varied pages (native text, image-only scan, mixed, rotated, faint); per-page outcomes with `unknown` cases surfaced; no corpus-wide aggregate pass masks unknown pages. The sheet records the design.md calibration-record fields (property, defect classes exercised, carriers, per-page outcomes, thresholds, render configuration).

## 6. Integration and documentation

- [ ] 6.1 Demo/evaluation reports record visual oracle results as a separate evidence class; conformance labels unchanged (test asserts labels ignore oracle outcomes).
- [ ] 6.2 Docs: update `docs/src/` extraction pages and status.md with the oracle contract, evidence-class rules and calibrated limits; no accuracy, completeness or semantic claims.

## 7. Final gate

- [ ] 7.1 `just spec-check` ALL GATES PASSED; frozen 0.2 validator still PASS 11; measurement/fixture churn reverted.
