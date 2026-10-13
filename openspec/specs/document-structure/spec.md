# document-structure Specification

## Purpose

Separate physical containment from logical grouping and reading sequence in
DSC 0.2 descriptors. A region's `view` is physical or logical; a logical
region can reference several physical placements via `realizes`; `contains`
is exclusive-parent structural ownership; `precedes` is a strict
partial-order generating edge. Content may be referenced by multiple regions
without copying it.

## Requirements

### Requirement: View declaration

THE system SHALL require each region to declare a physical or logical view,
and only physical regions may carry geometry.

#### Scenario: Descriptor with declared views is valid

- **GIVEN** `fixtures/valid/two-regions.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Containment ownership

THE system SHALL require `contains` edges to give one parent per child and
forbid cycles.

#### Scenario: Containment cycle rejected

- **GIVEN** `fixtures/invalid/cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `containment_cycle`

### Requirement: Reading order partiality

THE system SHALL induce reading order only by `precedes` reachability as a
partial order, and SHALL NOT require or imply a linear order.

#### Scenario: Order cycle rejected

- **GIVEN** `fixtures/invalid/order-cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `order_cycle`

### Requirement: Physical realization of logical regions

THE system SHALL support `realizes` relations connecting physical to logical
regions, including page continuation across physical placements.

#### Scenario: Page continuation represented

- **GIVEN** `fixtures/valid/continuation.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Shared content bindings

THE system SHALL allow multiple regions to reference the same content id
without duplicating content objects.

#### Scenario: Same content id referenced by multiple regions

- **GIVEN** `fixtures/valid/continuation.json`
- **WHEN** the descriptor is validated
- **THEN** the shared content id resolves for every referencing region without
  a duplicate content object

### Requirement: Ambiguity preservation

THE system SHALL keep multiple alternative orderings as separate claims and
SHALL NOT automatically select an arbitrary winner.

#### Scenario: Disputed claims preserved

- **GIVEN** `fixtures/valid/disputed.json`
- **WHEN** the descriptor is validated
- **THEN** the disputed claims are preserved as separate annotations

### Requirement: Structural resolution states

THE system SHALL distinguish structure outcomes of `resolved` (structure
valid, no unresolved alternatives), `ambiguous` (structure valid but
unresolved alternatives exist), and `invalid` (structure not valid).

#### Scenario: Alternative orderings defer to ambiguous

- **WHEN** structure is valid but unresolved alternatives exist
- **THEN** the outcome is `ambiguous`, not a silently chosen ordering
