# Tasks: add-dsc-03

Status: **design-only** for DSC 0.3. The review correction and specification
composition test are complete, but no 0.3 validator, concrete carrier profile,
adapter or benchmark is implemented. Active capability scenarios supplement
and supersede conflicting details in the preserved ACCEPTANCE.md draft.
Implementation remains tracked by Beads sunset-r68. Every implementation item
starts with its failing scenario, implements the minimum behavior, then passes
its focused checks. Any behavior-preserving refactor needs a separate ticket.

## 0. Review corrections

- [x] 0.1 Resolve seven review findings and define the first-consumer gate;
      reproduce the additive-delta failure, replace conflicting requirements,
      pass isolated OpenSpec composition and existing gates (sunset-6pi).

## 1. Contract tooling

- [ ] 1.1 Begin with malformed-field, Unicode, independent-root and scoped-order
      tests; implement the revised 0.3 schema outside the frozen bundle.
- [ ] 1.2 Add a preservation/version-dispatch regression proving the frozen 0.2
      validator is unchanged and rejects 0.3, even after a successor exists.
- [ ] 1.3 Turn remaining capability scenarios into positive/negative fixtures
      and implement their checks, including typed references and content lineage.

## 2. Profiles and manifest

- [ ] 2.1 Test missing/tampered/unsupported profiles first; implement the defined
      profile declarations and local resolver, then concrete selector/frame profiles.
- [ ] 2.2 Test missing mandatory inventory features and manifest mismatches;
      implement the defined inventory/manifest grammar and carrier enumeration.
- [ ] 2.3 Test wrong offset units, malformed ranges and frame mappings; implement
      selector/frame verification without guessed interpretation.

## 3. Adapters and coverage

- [ ] 3.1 Start with independently annotated real PDF/EPUB fixtures and implement
      adapters that preserve source observations (synthetic descriptors do not count).
- [ ] 3.2 Test one omitted page, partial-page loss, duplicates and unknown scope
      enumeration; implement scoped coverage and conservative summaries.
- [ ] 3.3 Test valid-schema/failed-coverage and supported/disputed cases; implement
      separate schema, profile, source-coverage and interpretation reports.

## 4. Migration

- [ ] 4.1 Start with legacy cross-view containment and conflicting orders;
      implement reported migration to per-view trees without guessing evidence.
- [ ] 4.2 Test missing frames/profiles, unavailable original text and absent
      adapter runs; preserve digests/ids and report unexamined or unrecoverable data.

## 5. Conformance

- [ ] 5.1 Build the adversarial corpus from independent expectations (columns,
      continuation, shared pages, OCR/native, poetry, EPUB links, opposing orders,
      transforms, roundtrip, omission, replay and exact Unicode text).
- [ ] 5.2 Test two independent readers for canonical-byte agreement on the SAME
      snapshot; separately compare extractor outputs through the pinned common
      projection, reviewed anchor mapping and oracle defined by document-conformance.
- [ ] 5.3 Test report labels against intentionally incomplete suites so 0.2
      fixtures and spec lint can never be reported as 0.3/real-carrier conformance.
- [ ] 5.4 Execute the first-consumer demonstration against native-output review,
      publishing functional results, review effort and representation overhead.

## 6. Ontology boundaries

- [ ] 6.1 After the first-consumer demonstration, start with boundary fixtures
      O-A01, O-A04 and O-A05 and implement the projection evaluator; profile
      resolution or schema validity alone must never imply semantic equivalence.
