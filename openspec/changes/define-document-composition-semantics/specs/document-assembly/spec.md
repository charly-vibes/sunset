# Document assembly

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## ADDED Requirements
### Requirement: Typed partial assembly
The system SHALL compose compatible parts while preserving typed identity and the existing relations.

#### Scenario: Continuation across magazine pages
- **GIVEN** two regions on separate magazine pages and a continuation relation
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** assembly retains both regions and their continuation without assuming a single page or a total reading order.

### Requirement: Algebraic assembly laws
The system SHALL meet identity and associativity under canonical equivalence for jointly compatible parts.

#### Scenario: Bracketing and identity equivalence
- **GIVEN** three jointly compatible parts
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** both bracketings and the empty assembly produce canonically equivalent results.

### Requirement: Reject incompatible parts
The system SHALL refuse conflicting identities or structural constraints with a finite witness.

#### Scenario: Conflicting origins under one region ID
- **GIVEN** conflicting intrinsic origins under the same region ID
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** assembly refuses the composition with a finite witness instead of silently renaming the source.
