# document-conformance (0.3 delta)

## ADDED Requirements

### Requirement: Layered validity reporting

Reports SHALL distinguish `schema_valid`, `source_coverage`, and
`interpretation_assessment` independently.

#### Scenario: Three-way report

- **WHEN** a descriptor with omissions and disputed interpretations is reported
- **THEN** all three layers are reported separately

### Requirement: Adversarial corpus

The 0.3 conformance corpus SHALL cover columns, page continuation, shared
pages, mixed OCR/native text, poetry, EPUB footnotes, conflicting
interpretations, coordinate transforms, roundtrip, omission, and replay.

#### Scenario: Corpus gate

- **WHEN** the corpus is missing a listed adversarial case
- **THEN** suite status is `incomplete`

### Requirement: Ambiguity can pass

The system SHALL pass a test that records two incompatible supported
hypotheses without selecting a winner.

#### Scenario: Two hypotheses recorded

- **WHEN** a fixture records two incompatible supported interpretations
- **THEN** the check passes with both preserved

### Requirement: No false claims

v0.2 fixture checks SHALL NOT be reported as v0.3 contract validation or
real-carrier conformance.

#### Scenario: Honest version scoping

- **WHEN** only 0.2 fixtures have been exercised
- **THEN** reports claim 0.2 coverage only
