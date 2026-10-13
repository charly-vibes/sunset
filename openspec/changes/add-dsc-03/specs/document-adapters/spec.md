# document-adapters (0.3 delta)

## ADDED Requirements

### Requirement: Coverage manifest per adapter

The system SHALL expose adapter capabilities and per-feature status
(`preserved|transformed|approximated|omitted|unsupported|unexamined`),
versioned and carried in `coverage` entries with adapter id/version and configuration
fingerprint (or literal `unavailable`, meaning replay UNVERIFIABLE).

#### Scenario: Unexamined feature recorded

- **WHEN** an adapter did not examine a declared feature
- **THEN** the coverage entry records `unexamined`, not a fabricated capability

### Requirement: Declared coordinate frames

Any geometry frame SHALL specify units, origin, axes, scale, rotation, and
crop mapping in a declared, versioned profile; a missing frame definition
yields `invalid_geometry_frame`.

#### Scenario: Missing frame definition

- **WHEN** geometry references a `space` with no registered coordinate-frame
  definition
- **THEN** the outcome is `invalid_geometry_frame`

### Requirement: Carrier-specific source selectors

PDF and EPUB source anchors SHALL use carrier-specific registered selector
profiles with no implicit offset conventions.

#### Scenario: Implicit offset convention rejected

- **WHEN** a selector locator relies on an undeclared offset convention
- **THEN** it is unsupported, not guessed

### Requirement: Partial results carry loss accounting

A valid descriptor SHALL NOT be proof of complete source observation; partial
results SHALL carry `coverage` and a loss report.

#### Scenario: Valid but incomplete

- **WHEN** an adapter omits features while producing a schema-valid descriptor
- **THEN** the descriptor is valid AND the omissions are visible in `coverage`
