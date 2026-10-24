# Categorical foundation

## Purpose

Use category theory as a compact specification of typing and laws, not as a new mandatory wire format or runtime framework.

## ADDED Requirements

### Requirement: Typed categorical document instances
The model SHALL provide a declared typed schema interpretable as a finite Set-valued instance, with relational spans for many-to-many associations.

#### Scenario: Overlapping document hierarchies
- **GIVEN** a region participating in two logical views
- **WHEN** the instance is interpreted
- **THEN** both memberships SHALL survive and no unique reading order SHALL be invented.

### Requirement: Scoped compositional transformations
Mappings SHALL declare source/target types, domains, observable scope and loss, and SHALL meet identity and associativity checks over applicable finite fixtures.

#### Scenario: Text-only flattening loses meaning
- **GIVEN** two statement layouts whose flattened text is identical but whose sign-bearing column positions differ
- **WHEN** a text-only mapper claims semantic-sign preservation
- **THEN** conformance SHALL reject that claim or record the missing positional evidence as a limitation.

### Requirement: No unjustified categorical equivalence
The system SHALL NOT assert invertibility, adjunction or cross-carrier semantic isomorphism without explicit definitions and proofs or bounded evidence.

#### Scenario: Similar titles are not an alignment oracle
- **GIVEN** two carriers whose documents share a title or filename but whose content corresponds to different editions
- **WHEN** a cross-carrier comparison is requested without a declared alignment relation and scope
- **THEN** the outcome SHALL be recorded as unsupported or unexamined, never as equivalent.
