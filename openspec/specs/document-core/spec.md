# document-core Specification

## Purpose

Validate the typed structure of a DSC 0.2 document descriptor (JSON wire
contract per the bundle's `CONTRACT-0.2.md`) and return complete error
reasons. Object identifiers are snapshot-local; canonical form is an
RFC 8785-style subset (ASCII key sorting, NFC strings, integers, no floats,
duplicate-key rejection). The reference implementation is
`spec/document-model-specodelic-v3/validator.py`.

## Requirements

### Requirement: Descriptor shape validation

WHEN a document instance is submitted, THE system SHALL validate its typed
structure against the 0.2 contract (top-level keys `version`, `id`, `source`,
`regions`, `contents`, `relations`, `annotations`, `evidence`,
`vocabularies`; no unknown keys) and return complete error reasons.

#### Scenario: Unknown top-level field rejected

- **WHEN** a descriptor carries a field outside the 0.2 contract
- **THEN** validation fails with `invalid_shape`
- **AND** the error set names the reason rather than silently ignoring the field

#### Scenario: Wrong version rejected

- **WHEN** a descriptor declares `version` other than `"0.2"`
- **THEN** validation fails with `invalid_shape`

### Requirement: Source digest format

THE system SHALL require `source.sha256` to be 64 lowercase hex characters.

#### Scenario: Bad digest rejected

- **WHEN** `source.sha256` is not 64 lowercase hex characters
- **THEN** validation fails with `invalid_digest`

### Requirement: Snapshot-local identity and referential integrity

THE system SHALL require entity ids to be unique across all instance
collections within a snapshot and every reference to resolve.

#### Scenario: Dangling reference rejected

- **GIVEN** `fixtures/invalid/dangling.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `dangling_reference`

#### Scenario: Dangling evidence rejected

- **GIVEN** `fixtures/invalid/dangling-evidence.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `dangling_reference`

#### Scenario: Duplicate id rejected

- **WHEN** two instance objects share an id in one snapshot
- **THEN** validation fails with `duplicate_id`

### Requirement: Containment tree integrity

THE system SHALL require every region except a declared root to have exactly
one parent via `contains` and the `contains` graph to be acyclic.

#### Scenario: Containment cycle rejected

- **GIVEN** `fixtures/invalid/cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `containment_cycle`

### Requirement: Reading order is a strict partial order

THE system SHALL require `precedes` edges to be acyclic and SHALL treat
reachability as a strict partial order, not a required total order; no order
is inferred from geometry.

#### Scenario: Order cycle rejected

- **GIVEN** `fixtures/invalid/order-cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `order_cycle`

### Requirement: Optional typed geometry

THE system SHALL treat region geometry as optional and, when present, require
a named `space` and nonnegative extents.

#### Scenario: Geometry omitted

- **WHEN** a region declares no geometry
- **THEN** the descriptor remains valid

### Requirement: Canonicalization stability

THE system SHALL define a canonical serialization such that
`canonicalize(parse(canonicalize(x))) == canonicalize(x)` as bytes, with NFC
string precondition, integer-only numbers and duplicate-key rejection.

#### Scenario: Canonical roundtrip is stable

- **GIVEN** `fixtures/valid/two-regions.json`
- **WHEN** the descriptor is canonicalized, parsed, and canonicalized again
- **THEN** both canonical byte strings are equal

### Requirement: Validation outcome states

THE system SHALL report one of `valid` or `invalid` per descriptor, where
`valid` requires all core checks to pass and `invalid` follows any core check
failure (including JSON parse errors reported as `parse_error`).

#### Scenario: Valid descriptor accepted

- **GIVEN** any fixture under `fixtures/valid/`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

#### Scenario: Invalid descriptor rejected

- **GIVEN** any fixture under `fixtures/invalid/`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `invalid` with typed reasons
