# document-semantics (0.3 delta)

## ADDED Requirements

### Requirement: Semantic claims attach to explicit views

A claim or domain grouping SHALL belong to an explicit structural view;
alternate classifications SHALL NOT mutate physical observations.

#### Scenario: Alternate classification

- **WHEN** a second domain grouping classifies the same physical observations
- **THEN** it is recorded as its own view-backed claim without mutating the
  physical view

### Requirement: Source observations vs claims

Semantic labels and observed strings SHALL have distinct provenance;
unsupported claims SHALL NOT be promoted by schema validity alone.

#### Scenario: Schema-valid unsupported claim

- **WHEN** a schema-valid claim has no supporting evidence
- **THEN** its status is `asserted_without_evidence`, never silently supported
