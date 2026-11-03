# Tasks

## 1. Contract validation (this proposal)

- [x] 1.1 Validate the change strictly: `openspec validate add-raster-visual-oracles --strict` passes; `spk lint openspec/changes` reports no issues for this change; full `just spec-check` stays green (no code touched yet).

## 2. Owner approval gate

- [x] 2.1 Owner reviews proposal.md and design.md; approval (recorded in beads) authorizes implementation slices below. No implementation before approval.

## 3. Pinned rendering infrastructure

- [x] 3.1 TDD: failing test first — render configuration record (renderer name/version, DPI, page selection, binarization, source simplification) reproduces byte-identical renders; missing renderer yields typed `unavailable`. (sunset-xzy.1: dsc03/visual/render.py RenderConfig + pdftoppm runner + typed Rendered/RenderUnavailable + evidence-class labeling; tests/tracer/test_visual_render.py)
- [x] 3.2 TDD: frame mapping through a declared geometry profile frame resolves pixel↔descriptor coordinates for native, scanned and rotated pinned carriers; incompatible or missing frames produce `unknown`, never `agree`/`differ`. (sunset-xzy.2: dsc03/visual/frames.py typed PixelMapping/UnknownMapping via profiles.resolve_frame; 18 tests + rotated/cropped frame fixtures)

## 4. First two oracle properties (representation levels B and C)

- [x] 4.1 TDD: binarized ink-coverage oracle (level B) over pinned carriers, including the like-with-like source simplification (design D4); outcomes per page/property with evidence class `correlated` or `independent`. (sunset-xzy.3: dsc03/visual/coverage.py — scoped property ink-coverage, D4 dilation from recorded config, declared-frame region mapping, typed outcomes + aggregate rule; 17 tests)
- [x] 4.2 TDD: geometry-mask alignment oracle (level C) comparing descriptor region masks with the simplified source; disagreements retained with region attribution; no winner election. (sunset-xzy.4: dsc03/visual/masks.py — scoped property region-alignment, D4 simplified-source comparison, ink-outside-rect attribution, shared aggregate rule; 15 tests)

## 5. Mutation validation and calibration

- [x] 5.1 TDD: seeded-mutation fixtures (shift, omission, duplication, wrong frame) over committed carriers; each oracle detects exactly the defect classes it claims; claiming classes without a passing mutation demonstration keeps the property `uncalibrated`. (sunset-xzy.5: tests/tracer/test_visual_mutations.py + tests/tracer/fixtures/visual/ — pinned class→oracle mapping [alignment claims shift+wrong frame, coverage claims omission+duplication], 4 seeded demonstrations at full severity each with unmutated baseline control ending agree, differ with region attribution, uncalibrated no-gate path pinned; AGENT-EXECUTED demonstration, human pass supersedes; 10 tests)
- [x] 5.2 Calibration sheet: thresholds derived from recorded runs over varied pages (native text, image-only scan, mixed, rotated, faint); per-page outcomes with `unknown` cases surfaced; no corpus-wide aggregate pass masks unknown pages. The sheet records the design.md calibration-record fields (property, defect classes exercised, carriers, per-page outcomes, thresholds, render configuration). (sunset-xzy.6: fixtures/visual/calibration.json — six D6 fields, 6 carriers mapped to the five varieties, 12 derivation + 2 detection per-page outcomes with ALIGN-001 split recorded, 10 oracle-consumable threshold entries with provenance, faint page honestly uncalibrated → unknown → aggregate blocked + positive control; tests/tracer/test_visual_calibration.py 7 tests; AGENT-EXECUTED measurements, human pass supersedes)

## 6. Integration and documentation

- [x] 6.1 Demo/evaluation reports record visual oracle results as a separate evidence class; conformance labels unchanged (test asserts labels ignore oracle outcomes). (sunset-xzy.7: dsc03/visual/reports.py `record()` — distinct `visual_oracles` section with `non_substitution` note; tests/tracer/test_visual_integration.py 7 tests incl. classify-inertness and passing-oracles/no-readers-stays-`incomplete`; conformance.py untouched. AGENT-EXECUTED spawn glm-5.3-flash + lead verification, REVIEW_REQUIRED caveat — human pass supersedes)
- [x] 6.2 Docs: update `docs/src/` extraction pages and status.md with the oracle contract, evidence-class rules and calibrated limits; no accuracy, completeness or semantic claims. (sunset-xzy.8: docs/src/visual-oracles.md new page — 8-requirement contract, evidence-class rules, calibrated limits, zo5 approval provenance, NOT-deployed-truth framing; reference.md surface + fixture catalog; integrate.md Recipe 3 extension; status.md dated bullet with pre-existing limitation sentences kept verbatim. AGENT-EXECUTED — human pass supersedes)

## 7. Final gate

- [x] 7.1 `just spec-check` ALL GATES PASSED; frozen 0.2 validator still PASS 11; measurement/fixture churn reverted. (sunset-xzy.9 gate: spec-check ALL GATES PASSED — 0.19 --all --strict + spk lint + 1.14.2 --all --strict + composition regression; validator.py test PASS 11; pytest 533 passed + 18 subtests; all sibling tickets .1-.8 closed; git tree clean of fixture/measurement churn; no conformance-label broadening — conformance.py diff empty. Gate executed by lead.)
