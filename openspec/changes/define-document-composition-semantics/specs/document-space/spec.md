---
id: document.space
kind: intent
statement: "THE DSC substrate SHALL represent stable source locators and spatial predicates relative to explicit coordinate frames, independent of transient rendering and OCR."
---

# Carrier-relative spatial layout

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| carrier_coordinate_frames | invariant | `Each geometric observation identifies carrier, source identifier, coordinate frame and units or a stable nongeometric selector.` | [[document.space]] |
| frame_compatibility | invariant | `Spatial predicates operate only on compatible frames or with an explicit pinned transform; otherwise return unknown with reason.` | [[document.space]] |
| geometry_transform | invariant | `When an invertible view transform is available, source geometry transformed forward and back is equivalent under a declared numeric tolerance.` | [[document.space]] |
| epub_stable_identity | invariant | `EPUB logical location is identified by spine resource and stable selector; viewport XY never provides persistent element identity.` | [[document.space]] |
| mixed_observations | invariant | `Native PDF text, vector, raster and OCR observations may coexist with separately declared origin and evidence.` | [[document.space]] |
| spatial_order_separation | invariant | `No above/left-of/overlap relation automatically implies reading order or containment.` | [[document.space]] |

## Model
### States
- `located`
- `source_declared`
- `spatial_evaluated`
- `spatial_unknown`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| locate | source_declared | located | `typed locator resolves in declared frame` [[document.space.carrier_coordinate_frames]] |
| compare | located | spatial_evaluated | `frames compatible or transformed` [[document.space.frame_compatibility]] [[document.space.geometry_transform]] |
| unknown | located | spatial_unknown | `incomparable or absent frames` [[document.space.frame_compatibility]] [[document.space.epub_stable_identity]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| pdf_rotation | unit | [[document.space.carrier_coordinate_frames]] | `page_box_rotation_90()` | `normalized source locus matches expected transformed geometry` |
| cross_page_unknown | unit | [[document.space.frame_compatibility]] | `two_regions_on_different_pages()` | `above returns unknown` |
| epub_reflow | unit | [[document.space.geometry_transform]] | `same_epub_section_two_viewports()` | `stable selector unchanged while XY may differ` |
| native_ocr_coexist | unit | [[document.space.epub_stable_identity]] | `hybrid_pdf_page()` | `native and OCR observations coexist without forced equality` |
| spatial_not_order | unit | [[document.space.mixed_observations]] | `overlapping_figure_caption()` | `no precedes inferred` |
| no_spatial_reading_order | unit | [[document.space.spatial_order_separation]] | `two_column_layout_fixture()` | `above/left-of/overlap never emit a precedes or contains edge` |

## ADDED Requirements
### Requirement: Typed carrier coordinates
The system SHALL interpret geometry only within declared compatible frames or transforms.

#### Scenario: Typed carrier coordinates fixture
- **GIVEN** Given two coordinates on different PDF pages without a transform
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two coordinates on different PDF pages without a transform, their above/below comparison is unknown, not false.

### Requirement: Reflow-safe EPUB identity
The system SHALL distinguish stable EPUB spine selectors from temporary viewport geometry.

#### Scenario: Reflow-safe EPUB identity fixture
- **GIVEN** Given the same chapter at two font sizes
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given the same chapter at two font sizes, anchor identity is preserved while rendered positions may differ.

### Requirement: Mixed evidence
The system SHALL permit native and OCR observations on one PDF page without forcing either to supersede the other.

#### Scenario: Mixed evidence fixture
- **GIVEN** Given a hybrid PDF
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given a hybrid PDF, independent observations retain their source provenance.

## Requirements
### Requirement: Typed carrier coordinates
The system SHALL interpret geometry only within declared compatible frames or transforms.

#### Scenario: Typed carrier coordinates fixture
- **GIVEN** Given two coordinates on different PDF pages without a transform
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two coordinates on different PDF pages without a transform, their above/below comparison is unknown, not false.

### Requirement: Reflow-safe EPUB identity
The system SHALL distinguish stable EPUB spine selectors from temporary viewport geometry.

#### Scenario: Reflow-safe EPUB identity fixture
- **GIVEN** Given the same chapter at two font sizes
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given the same chapter at two font sizes, anchor identity is preserved while rendered positions may differ.

### Requirement: Mixed evidence
The system SHALL permit native and OCR observations on one PDF page without forcing either to supersede the other.

#### Scenario: Mixed evidence fixture
- **GIVEN** Given a hybrid PDF
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given a hybrid PDF, independent observations retain their source provenance.
