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
