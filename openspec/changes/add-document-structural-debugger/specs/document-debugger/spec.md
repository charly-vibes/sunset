# Document structural debugger

## ADDED Requirements

### Requirement: Read-only synchronized inspection
The debugger SHALL display source rendering, DSC structural views, and evidence records linked by stable identities without modifying source artifacts or descriptors.

#### Scenario: Select an EPUB region after reflow
- **GIVEN** a native EPUB region linked to an XHTML/CFI selector
- **WHEN** the reader resizes the viewport and selects the region
- **THEN** the same logical region SHALL be resolved; its viewport geometry MAY differ.

### Requirement: Carrier-aware anchors
The debugger SHALL support native PDF and EPUB without OCR and SHALL explicitly classify unavailable and ambiguous source selectors.

#### Scenario: Image and native text on one PDF page
- **GIVEN** a hybrid PDF page with embedded text and raster content
- **WHEN** the overlay displays a region from each origin
- **THEN** both observations SHALL remain distinct and their independent evidence SHALL be accessible.

### Requirement: Inspectable constraints
The debugger SHALL present typed failures and counterexamples for graph, provenance, and order claims without treating unexamined content as passing.

#### Scenario: Wrong reading-order assertion
- **GIVEN** a reviewed fixture whose declared expected order conflicts with the descriptor's order
- **WHEN** a fixture oracle is applied
- **THEN** a reviewable mismatch with specific edge(s), oracle version and source loci SHALL appear, distinct from pure structural DAG validation.

### Requirement: Accessible inspection
The debugger SHALL offer keyboard navigation and redundant visual/text status encoding.

#### Scenario: Keyboard-only evidence inspection
- **GIVEN** a region with a provenance warning
- **WHEN** a keyboard user focuses and activates it
- **THEN** the same source locations, status and details SHALL be available as for a pointer user.

### Requirement: Executable PDF inspection journey
The debugger SHALL provide a local browser workspace linking human-sheet-derived
DSC regions to the matching PDF source, structure and attributed evidence, with
pointer and keyboard operation. Acceptance SHALL execute an actual browser and
SHALL fail if the required browser runtime is unavailable; modeled interaction
alone SHALL NOT satisfy this requirement.

#### Scenario: Inspect a human region on Diario
- **GIVEN** the committed Diario PDF and validated descriptors imported from its existing human sheets
- **WHEN** a reviewer selects a region by overlay or keyboard-accessible structure entry
- **THEN** its page, source highlight, stable identity, sheet attribution and evidence SHALL be visible together
- **AND** the highlight SHALL remain aligned after zoom and rotation while source and descriptor bytes remain unchanged

#### Scenario: Anchor cannot be resolved
- **WHEN** a source digest mismatches or a region lacks a valid coordinate frame
- **THEN** the workspace SHALL display a typed unavailable or mismatch result and SHALL NOT invent a source highlight
