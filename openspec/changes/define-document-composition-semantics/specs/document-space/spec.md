# Carrier-relative spatial layout

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## ADDED Requirements
### Requirement: Typed carrier coordinates
The system SHALL interpret geometry only within declared compatible frames or transforms.

#### Scenario: Cross-page comparison without transform
- **GIVEN** two coordinates on different PDF pages without a transform
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the above/below comparison returns unknown rather than false.

### Requirement: Reflow-safe EPUB identity
The system SHALL distinguish stable EPUB spine selectors from temporary viewport geometry.

#### Scenario: EPUB anchor stable across font sizes
- **GIVEN** the same chapter at two font sizes
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** anchor identity is preserved while rendered positions may differ.

### Requirement: Mixed evidence
The system SHALL permit native and OCR observations on one PDF page without forcing either to supersede the other.

#### Scenario: Hybrid PDF keeps provenance separate
- **GIVEN** a hybrid PDF
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the independent native and OCR observations both retain their source provenance.
