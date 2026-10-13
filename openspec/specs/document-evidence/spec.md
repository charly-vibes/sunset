# document-evidence Specification

## Purpose

Retain evidence, transformation fingerprints, and honest uncertainty for every
recorded observation or semantic claim. Each claim has an `origin`
(source/extracted/inferred/manual/external); missing support can be
represented as `asserted_without_evidence`; conflicting claims coexist and are
marked disputed; transformation lineage is a DAG.

## Requirements

### Requirement: Evidence link resolution

THE system SHALL require claim targets and evidence references to resolve, or
the claim to explicitly use the `asserted_without_evidence` status.

#### Scenario: Dangling evidence rejected

- **GIVEN** `fixtures/invalid/dangling-evidence.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `dangling_reference`

### Requirement: Origin typing

THE system SHALL distinguish claim origins source, extracted, inferred,
manual, and external.

#### Scenario: Origin recorded per claim

- **WHEN** a claim is recorded
- **THEN** its origin is one of the five typed values

### Requirement: Replay material for derived observations

THE system SHALL require derived observations to carry transformer id/version,
source digest, configuration digest, and dependency declarations.

#### Scenario: Replay material recorded

- **WHEN** a derived observation is recorded without replay material
- **THEN** it is distinguishable from a supported observation

### Requirement: Acyclic transformation lineage

THE system SHALL require the `derived-from` relation graph to be acyclic.

#### Scenario: Lineage cycle rejected

- **GIVEN** `fixtures/invalid/lineage-cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `lineage_cycle`

### Requirement: Dispute preservation

THE system SHALL keep unresolved competing claims separate with status
`disputed`, without automatic precedence.

#### Scenario: Competing claims coexist

- **GIVEN** `fixtures/valid/disputed.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid` and statuses include `disputed`

### Requirement: Honest uncertainty

THE system SHALL NOT invent confidence, and missing replay material SHALL be
distinguishable from conflict.

#### Scenario: Unverifiable claim is typed

- **WHEN** a claim lacks support or replay material without any conflict
- **THEN** the outcome is `unverifiable`, not `disputed` or `supported`

### Requirement: Evidence status transitions

THE system SHALL move a recorded claim to `supported` (support sufficient, no
conflicting support, replay material available), `disputed` (conflicting
support), or `unverifiable` (no conflict but support or replay material
missing).

#### Scenario: Unsupported manual assertion stays unverifiable

- **WHEN** a manual assertion has no evidence and no conflict
- **THEN** it is structurally valid yet epistemically `unverifiable`
