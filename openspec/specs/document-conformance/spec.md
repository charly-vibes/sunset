# document-conformance Specification

## Purpose

Report per-instance outcomes (`valid`, `invalid`, `unsupported`, `ambiguous`)
separately from suite readiness (`passed`, `failed`, `incomplete`) and from
Specodelic lint. Fixture inventory records available vs missing. The reference
tests cover JSON descriptors only — not real PDF/EPUB ingestion, nor
independent reader agreement.

## Requirements

### Requirement: Separated reporting levels

THE system SHALL report Specodelic lint, instance validation, and suite
conformance as separate statuses.

#### Scenario: Lint pass is not conformance pass

- **WHEN** lint passes but suite checks are missing
- **THEN** suite status is `incomplete`, not `passed`

### Requirement: Stable typed error reasons

THE system SHALL produce stable typed reasons for negative fixtures.

#### Scenario: Dangling reference typed

- **GIVEN** `fixtures/invalid/dangling.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `dangling_reference`

### Requirement: Visible coverage of missing fixtures and implementations

THE system SHALL keep every missing carrier fixture and independent
implementation visible; `incomplete` SHALL NOT mean `passed`.

#### Scenario: Coverage gap explicit

- **GIVEN** `coverage.json`
- **WHEN** coverage is assessed
- **THEN** missing real PDF, real EPUB, and independent reader entries are
  explicit

### Requirement: Carrier fixture requirements for full conformance

THE full suite SHALL require a real scanned PDF, a real text PDF, an EPUB,
and an independent nonperiodical input.

#### Scenario: Suite without real carriers is incomplete

- **WHEN** only synthetic JSON fixtures exist
- **THEN** suite status is `incomplete`

### Requirement: Reader independence

THE full suite SHALL require two independently implemented readers with
matching canonical results.

#### Scenario: Single implementation

- **WHEN** only one implementation exists
- **THEN** suite status is `incomplete`

### Requirement: EPUB reflow

THE system SHALL impose no obligatory fixed coordinates on EPUB descriptors;
spine order, non-linear entries, and navigation are distinct.

#### Scenario: EPUB descriptor valid

- **GIVEN** `fixtures/valid/epub.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Suite status transitions

THE system SHALL move suite status from `unexamined` to `passed` (all required
checks executed and passing), `failed` (any executed required check fails), or
`incomplete` (no executed check fails but required checks are missing).

#### Scenario: Missing required checks

- **WHEN** no executed check fails but required checks are missing
- **THEN** suite status is `incomplete`
