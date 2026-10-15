---
id: document.debugger
kind: intent
statement: "WHEN a reader inspects a DSC description with a source document, THE document debugger SHALL show structural regions, evidence and typed diagnostics using stable source locators without mutating the source or requiring OCR for native documents."
---

# Document structural debugger

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| read_only | invariant | `Inspection does not alter input descriptor or source bytes` | [[document.debugger]] |
| carrier_locators | invariant | `PDF geometry and EPUB stable selectors use declared carrier-specific coordinate domains; transient viewport coordinates are never persistent EPUB identity` | [[document.debugger]] |
| bidirectional_navigation | invariant | `A region selection resolves to all available source loci and evidence; missing or multiple matches are explicitly reported` | [[document.debugger]] |
| scoped_structure | invariant | `Containment, reading order, overlap and alternative structural views are displayed without inventing a total order` | [[document.debugger]] |
| typed_diagnostics | invariant | `Check results distinguish validated violation, review/dispute, unsupported and unexamined; every violation links to its rule and smallest available witness` | [[document.debugger]] |
| evidence_truth_boundary | invariant | `Human or extractor annotations are attributed claims and not automatically semantically true` | [[document.debugger]] |
| accessibility | invariant | `All inspector actions are keyboard operable with non-color status labels` | [[document.debugger]] |

## Model

### States
- `unloaded`
- `loaded`
- `inspecting`
- `diagnostic_selected`
- `unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| load | unloaded | loaded | input references parse and source/descriptor hashes recorded [[document.debugger.read_only]] |
| inspect | loaded | inspecting | selected view and locator domain declared [[document.debugger.carrier_locators]] [[document.debugger.scoped_structure]] |
| select_diagnostic | inspecting | diagnostic_selected | diagnostic has a stable code and scoped source or graph witness [[document.debugger.typed_diagnostics]] [[document.debugger.bidirectional_navigation]] |
| unsupported_source | loaded | unsupported | source carrier or locator unsupported with classified reason [[document.debugger.typed_diagnostics]] |
| return_to_inspection | diagnostic_selected | inspecting | inspection state retained [[document.debugger.accessibility]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| unchanged_bytes | unit | [[document.debugger.read_only]] | `frozen_descriptor_source()` | `sha256(input_before) == sha256(input_after)` |
| pdf_epub_no_ocr | unit | [[document.debugger.carrier_locators]] | `native_pdf_and_epub_samples()` | `inspection succeeds with OCR disabled; anchors persist after zoom or reflow` |
| ambiguous_selector | unit | [[document.debugger.bidirectional_navigation]] | `two_matching_selector_targets()` | `ambiguity reported and neither target auto-selected` |
| partial_order | unit | [[document.debugger.scoped_structure]] | `two_legal_topological_sorts()` | `view preserves partial order; display sort not asserted as unique` |
| witnessed_failure | unit | [[document.debugger.typed_diagnostics]] | `cycle_and_bad_reference_fixtures()` | `correct stable rule IDs and minimal available witness emitted` |
| no_truth_inference | unit | [[document.debugger.evidence_truth_boundary]] | `two_conflicting_extractor_claims()` | `both claims retained with attribution and no automatic winner` |
| keyboard_navigation | unit | [[document.debugger.accessibility]] | `keyboard_only_selection_flow()` | `every inspected detail reachable without pointer` |

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

## Requirements

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
