# document-semantics Specification

## Purpose

Retain typed, namespaced domain claims without reinterpreting the structural
core. Semantic vocabulary registration is versioned (`title`, `poem`,
`posting` etc are extension terms, not universal records); claims never
overwrite core structure; cross-edition equivalence is an optional, explicitly
scoped comparison using a named projection and comparator.

## Requirements

### Requirement: Namespaced vocabulary registration

THE system SHALL require every non-core term to be registered with a
namespace and a semantic version.

#### Scenario: Unknown extension term rejected

- **GIVEN** `fixtures/invalid/unknown-extension.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `unknown_term`

### Requirement: Typed annotation claims

THE system SHALL require annotations to declare target, term, value,
provenance status, and evidence references.

#### Scenario: Annotation-bearing descriptor is valid

- **GIVEN** `fixtures/valid/two-regions.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Extension isolation

THE system SHALL forbid extensions from modifying core identity, relation
kinds, or canonicalization.

#### Scenario: Core identity is untouchable

- **WHEN** an extension attempts to alter core identity or relation kinds
- **THEN** the extension is rejected at registration, not applied

### Requirement: Unresolved semantic alternatives are explicit

THE system SHALL reject unregistered extension terms and keep unresolved
semantic alternatives explicit rather than resolved implicitly.

#### Scenario: Disputed semantic claims preserved

- **GIVEN** `fixtures/valid/disputed.json`
- **WHEN** the descriptor is validated
- **THEN** the disputed claims are preserved with their conflict status

### Requirement: No automatic cross-edition equivalence

THE system SHALL never infer cross-edition equivalence automatically; a named
projection and comparator are required.

#### Scenario: Equivalence without declared comparator

- **WHEN** an equivalence claim lacks a named projection and comparator
- **THEN** it is not treated as an inferred equivalence of the core
