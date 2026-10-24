# Scoped semantic context

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## ADDED Requirements
### Requirement: Scoped interpretation
The system SHALL expose inherited context separately from directly observed source claims.

#### Scenario: Poem issue date stays publication context
- **GIVEN** a poem in a magazine with issue date
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the issue date remains publication context and is not treated as the date described by the poem.

### Requirement: Evidence is not truth
The system SHALL preserve attributed conflicting claims and uncertainty without silently electing a winner.

#### Scenario: Disputed transcription stays attributed
- **GIVEN** disagreeing OCR and manual transcription
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** both transcriptions remain available with their sources and status, and neither silently wins.

### Requirement: Deterministic semantic rules
The system SHALL evaluate versioned rules on pinned inputs and return stable claim sets or typed errors.

#### Scenario: Repeated evaluation yields identical claims
- **GIVEN** the same source evaluated twice under the same scope and rule version
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the two runs produce outputs that match under canonical equality.
