# document-adapters Specification

## Purpose

Preserve declared source-native observations via an applicable adapter
without requiring OCR. An adapter result is separate from document validity;
one page may combine text glyphs, raster images, vector shapes, and OCR
observations, each with its own provenance. Source carrier is not a binary
native/scanned class. Format-specific adapters are optional modules;
structured JSON is the mandatory baseline adapter. PDF native and EPUB adapter
execution is not claimed.

## Requirements

### Requirement: Adapter dispatch

THE system SHALL select one applicable adapter by declared format and version,
and SHALL NOT conjoin mutually exclusive carrier rules.

#### Scenario: Mixed-carrier descriptor dispatches

- **GIVEN** `fixtures/valid/mixed-pdf.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: PDF observation typing

THE system SHALL support PDF observation types including page, glyph, raster,
vector, and annotations, each with per-observation source evidence.

#### Scenario: Mixed PDF observations valid

- **GIVEN** `fixtures/valid/mixed-pdf.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: EPUB observation typing

THE system SHALL support EPUB observation types including manifest, XHTML
tree, spine sequence with `linear` flag, navigation, and links, with no
fabricated page geometry.

#### Scenario: EPUB descriptor valid without page geometry

- **GIVEN** `fixtures/valid/epub.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid` with no fixed page geometry

### Requirement: Structured JSON baseline

THE system SHALL require structured JSON observation import as the baseline
adapter; HTML, Markdown, and CSV adapters are optional independently declared
profiles.

#### Scenario: JSON-only descriptor valid

- **GIVEN** `fixtures/valid/two-regions.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Preservation declaration

THE system SHALL require each adapter to declare its capabilities and
preserved fields, and its omitted or approximated fields.

#### Scenario: Capabilities declared

- **WHEN** an adapter result is produced
- **THEN** preserved and omitted/approximated fields are both declared

### Requirement: Adapter replay metadata

THE system SHALL require adapter results to record source sha256, adapter id
and version, configuration digest, and dependencies, or an explicit
`unavailable` fingerprint.

#### Scenario: Unavailable fingerprint is typed

- **WHEN** an adapter cannot produce a configuration digest
- **THEN** it records the literal `unavailable`, never a fabricated value

### Requirement: Typed failure results

THE system SHALL report `unsupported`, `error`, and `ambiguous` as typed
results; partial output SHALL never masquerade as complete.

#### Scenario: Unsupported carrier result

- **GIVEN** `fixtures/results/unsupported.json`
- **WHEN** the result is checked
- **THEN** the result status is `unsupported`

### Requirement: Adapter outcome states

THE system SHALL distinguish adapter outcomes `observed` (adapter selected,
extraction complete, preservation checks pass), `unsupported` (no matching
adapter or blocked encryption), `ambiguous` (multiple incompatible
observations), and `failed` (adapter error or malformed input).

#### Scenario: No matching adapter

- **WHEN** no adapter matches the declared carrier format
- **THEN** the outcome is `unsupported`
