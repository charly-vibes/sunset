# Tasks: add-dsc-03

Status: **partially implemented** for DSC 0.3. The 0.3 validator, profile
grammar, coverage verification, evidence lineage/replay, migration and
conformance labeling live in the repo-root `dsc03/` package with their
scenario tests under `tests/tracer/` (tracer bullet: beads sunset-r68.1,
demo run in `docs/src/tracer-bullet.org`). Not implemented: real PDF/EPUB
adapters (item 3.1), the adversarial corpus and two-reader comparison
(items 5.1-5.2), the first-consumer demonstration (item 5.4) and ontology
projections (item 6.1) — these are HITL-blocked on real carrier files,
independent readers and human review (beads sunset-r68.11-r68.14). The
frozen 0.2 executable under `spec/document-model-specodelic-v3/` remains
unchanged. Every implementation item started with its failing scenario,
implemented the minimum behavior, then passed its focused checks. Any
behavior-preserving refactor needs a separate ticket.

## 0. Review corrections

- [x] 0.1 Resolve seven review findings and define the first-consumer gate;
      reproduce the additive-delta failure, replace conflicting requirements,
      pass isolated OpenSpec composition and existing gates (sunset-6pi).

## 1. Contract tooling

- [x] 1.1 Begin with malformed-field, Unicode, independent-root and scoped-order
      tests; implement the revised 0.3 schema outside the frozen bundle.
- [x] 1.2 Add a preservation/version-dispatch regression proving the frozen 0.2
      validator is unchanged and rejects 0.3, even after a successor exists.
- [x] 1.3 Turn remaining capability scenarios into positive/negative fixtures
      and implement their checks, including typed references and content lineage.

## 2. Profiles and manifest

- [x] 2.1 Test missing/tampered/unsupported profiles first; implement the defined
      profile declarations and local resolver, then concrete selector/frame profiles.
- [x] 2.2 Test missing mandatory inventory features and manifest mismatches;
      implement the defined inventory/manifest grammar and carrier enumeration.
- [x] 2.3 Test wrong offset units, malformed ranges and frame mappings; implement
      selector/frame verification without guessed interpretation.

## 3. Adapters and coverage

- [x] 3.1 Start with independently annotated real PDF/EPUB fixtures and implement
      adapters that preserve source observations (synthetic descriptors do not count).
      Implemented in dsc03/adapters.py against the committed carriers in
      fixtures/carriers/ (sunset-r68.11); HITL two-reader agreement (5.1/5.2)
      remains separate and does not gate this item.
- [x] 3.2 Test one omitted page, partial-page loss, duplicates and unknown scope
      enumeration; implement scoped coverage and conservative summaries.
- [x] 3.3 Test valid-schema/failed-coverage and supported/disputed cases; implement
      separate schema, profile, source-coverage and interpretation reports.

## 4. Migration

- [x] 4.1 Start with legacy cross-view containment and conflicting orders;
      implement reported migration to per-view trees without guessing evidence.
- [x] 4.2 Test missing frames/profiles, unavailable original text and absent
      adapter runs; preserve digests/ids and report unexamined or unrecoverable data.

## 5. Conformance

- [x] 5.1 Build the adversarial corpus from independent expectations (columns,
      continuation, shared pages, OCR/native, poetry, EPUB links, opposing orders,
      transforms, roundtrip, omission, replay and exact Unicode text).
      Implemented as dsc03/corpus.py (machinery-only builder + gate) with
      carrier cases reusing the committed real fixtures; covers BOTH the
      tasks.md list (EPUB links) and the delta requirement's "EPUB footnotes"
      as separate cases (sunset-r68.12).
- [x] 5.2 Test two independent readers for canonical-byte agreement on the SAME
      snapshot; separately compare extractor outputs through the pinned common
      projection, reviewed anchor mapping and oracle defined by document-conformance.
      DONE (2026-10-15, sunset-r68.12): machinery in dsc03/canonical.py (two
      independent readers, byte-identical output incl. non-NFC text) and
      dsc03/projection.py (pinned anchor-matched comparator; ambiguity stays
      unresolved; alternatives retained). Anchor mapping REVIEWED: owner
      accepted the rule-of-5 independent review (TypeSafe-verified findings,
      all fixed) as the review of record and anchor_mapping_reviewed is True.
      Recorded deviation: the review was agent-executed, not two independent
      human readers; a human pass supersedes it.
- [x] 5.3 Test report labels against intentionally incomplete suites so 0.2
      fixtures and spec lint can never be reported as 0.3/real-carrier conformance.
- [x] 5.4 Execute the first-consumer demonstration against native-output review,
      publishing functional results, review effort and representation overhead.
      DONE (2026-10-15, sunset-r68.13): dsc03/demo.py runs the pinned workflow
      (pdftotext 26.01 + PyMuPDF 1.28.2 + tesseract spa over the committed
      demo issue); two extractor snapshots with canonical reader agreement;
      pinned projection vs reviewer oracle: 3 matched pages, 3 attributed
      unresolved alternatives (retained, allowed), 0 FP/FN, pass; reviewing
      consumer executed twice (DSC vs native) — R3/R5 correct only via DSC
      (agent-executed deviation recorded; human pass supersedes). Raw results
      in fixtures/demo/measurement.json; workflow benefit = traceability
      demonstrated, speed not claimed (review time delta +4e-06 s, agent
      time). Never release conformance.

## 6. Ontology boundaries

- [x] 6.1 After the first-consumer demonstration, start with boundary fixtures
      O-A01, O-A04 and O-A05 and implement the projection evaluator; profile
      resolution or schema validity alone must never imply semantic equivalence.
      DONE (2026-10-15, sunset-r68.14): dsc03/boundaries.py evaluates declared
      projections against O-A01 (out-of-core relations never coerced into
      contains/precedes/realizes without a declared equivalence), O-A04
      (exactly one loss disposition per inventory feature, justification for
      lossy dispositions, semantic equivalence requires an entailment policy)
      and O-A05 (roundtrip claimed only for a named subset and tested domain;
      scoped claim honored while geometry explicitly fails; full-fidelity
      badge rejected). Projections without provenance are not applied.
      equivalence_claim(): profiles-resolved + schema-valid never ground an
      equivalence claim without a declared criterion. Committed fixtures
      (compliant + counterexample per check) under fixtures/boundaries/;
      11 new tests (tests/tracer/test_ontology_boundaries.py).
