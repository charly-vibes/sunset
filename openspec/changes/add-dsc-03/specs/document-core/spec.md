# document-core (0.3 delta)

## ADDED Requirements

### Requirement: 0.3 descriptor shape

THE 0.3 descriptor SHALL carry all 0.2 mandatory top-level keys with
`version: "0.3"` plus exactly four additional mandatory arrays: `views`,
`selectors`, `interpretations`, `coverage`. Unknown properties SHALL be
invalid; no nulls or floats; ids unique across all instance collections
except view names and coverage entries.

#### Scenario: 0.2 validator rejects 0.3 descriptors

- **WHEN** a 0.3 descriptor is submitted to the frozen 0.2 validator
- **THEN** it is rejected as an invalid version — never reported as valid

### Requirement: Named structural views

THE 0.3 contract SHALL support named views with exact fields `{id, kind,
root}` where `kind` is `physical|logical|carrier`; at least one logical view
is required; regions reference their view via `view_id` and belong to exactly
one view.

#### Scenario: Cross-view containment invalid

- **WHEN** a `contains` edge connects regions of different views
- **THEN** the descriptor is invalid

### Requirement: Scoped canonicalization precondition

Canonical serialization SHALL be defined only for valid NFC JSON inputs;
identical canonical bytes are a structural reproducibility check, not a
source-fidelity claim.

#### Scenario: Reproducibility not fidelity

- **WHEN** two canonicalizations of the same descriptor produce equal bytes
- **THEN** no claim of source fidelity is implied

### Requirement: Entity ids scoped per snapshot

Entity ids SHALL remain snapshot-local and unique across all instance
collections; views have unique ids.

#### Scenario: Id collision across collections

- **WHEN** a region and a selector share an id in one snapshot
- **THEN** the descriptor is invalid
