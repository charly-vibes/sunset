# Tasks: add-dsc-03

Status: **design-only** — nothing here is implemented; fixtures are synthetic
and prove nothing about real PDFs/EPUBs. Acceptance gates live in the bundle's
ACCEPTANCE.md.

## 1. Contract tooling

- [ ] 1.1 Implement the 0.3 descriptor schema validator (views, selectors,
      interpretations, coverage; unknown properties invalid; no nulls/floats)
- [ ] 1.2 Keep the 0.2 validator frozen and rejecting 0.3 descriptors until
      the 0.3 validator exists
- [ ] 1.3 Add 0.3 positive and negative fixtures mirroring the delta scenarios

## 2. Profiles and manifest

- [ ] 2.1 Define the registered selector profile mechanism (syntax, units,
      axes, rotation/crop mapping, versioning)
- [ ] 2.2 Define the versioned adapter manifest grammar and capability names
- [ ] 2.3 Reject undeclared profiles with `unsupported`/`invalid-selector`
      outcomes, never guessed interpretations

## 3. Adapters and coverage

- [ ] 3.1 Implement PDF and EPUB adapters against real carrier fixtures
      (synthetic descriptors do not count)
- [ ] 3.2 Emit `coverage` entries with `unexamined` rather than fabricated
      extraction capabilities
- [ ] 3.3 Keep `schema_valid`, `source_coverage`, and
      `interpretation_assessment` separately reported

## 4. Migration

- [ ] 4.1 Implement the 0.2→0.3 migration per contract §7 (views, preserved
      digests/ids, `asserted_without_evidence`, per-view tree split, reported
      ambiguities) — conversion emits an assumptions report
- [ ] 4.2 Report unknown selector resolution and coordinate-frame definitions

## 5. Conformance

- [ ] 5.1 Build the adversarial corpus (columns, page continuation, shared
      pages, mixed OCR/native, poetry, EPUB footnotes, conflicting
      interpretations, coordinate transforms, roundtrip, omission, replay)
- [ ] 5.2 Run two independent readers to matching canonical results
- [ ] 5.3 Ensure no false claims: 0.2 fixture checks are never reported as 0.3
      contract validation or real-carrier conformance

## 6. Ontology boundaries

- [ ] 6.1 Implement the projection evaluator and boundary fixtures per
      ONTOLOGY-BOUNDARIES.md §7 acceptance checks (O-A01, O-A04, O-A05)
