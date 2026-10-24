# Structural views and hierarchies

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## ADDED Requirements
### Requirement: Multiple named structural views
The system SHALL preserve overlapping physical and logical hierarchies over the same regions.

#### Scenario: Article spanning two pages keeps both memberships
- **GIVEN** an article spanning two pages
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** both page memberships and the single logical article membership remain accessible.

### Requirement: Partial reading order
The system SHALL model reading order without assuming a unique total sequence.

#### Scenario: Incomparable columns are valid
- **GIVEN** two independent columns
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the validator accepts the columns as incomparable and rejects any declared cycle.

### Requirement: Scoped projection and refinement
The system SHALL report removed edges and superseded links when a view is projected or refined.

#### Scenario: Excluded continuation is reported by projection
- **GIVEN** a cross-page continuation omitted from a one-page projection
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** the projection result reports the excluded link instead of claiming full fidelity.
