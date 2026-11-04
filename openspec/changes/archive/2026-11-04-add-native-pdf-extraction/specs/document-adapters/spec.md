## Purpose

Define the local native-PDF consumer baseline using existing DSC adapters,
evidence and coverage contracts. These are proposed additions, not claims of
current runtime support.

## ADDED Requirements

### Requirement: Automatic native PDF consumer

The local extraction consumer SHALL accept a PDF and a new output directory without preauthored observations, OCR or network access. It SHALL default to all pages with recorded native extraction settings, support explicit one-based page selection, and produce validated DSC, searchable text and source mappings accessible through local inspection.

#### Scenario: Native PDF without recognition configuration

- **GIVEN** a two-page PDF with embedded text and known word positions
- **WHEN** the user invokes native extraction with source and output only
- **THEN** both pages produce source-linked text, valid DSC and inspectable mappings with zero OCR, model or network calls

#### Scenario: Selected pages only

- **WHEN** native extraction selects page 2 of a two-page PDF
- **THEN** text mappings identify PDF page 2 and coverage declares page 1 outside the selected scope

### Requirement: Native text source mappings

Each extracted word SHALL bind the source SHA256, PDF page, exact raw text span and bounding box in a declared frame. Line grouping, rotation and coordinate transforms SHALL be explicit. Search normalization SHALL retain raw text and map each search token to raw spans and source word boxes under pinned offset and normalization profiles.

#### Scenario: Repeated words and normalization

- **GIVEN** repeated words on separate lines with distinct boxes and raw whitespace
- **WHEN** search text collapses whitespace
- **THEN** every occurrence maps to its own raw span and source word box while exact raw Unicode, whitespace and line grouping remain available

#### Scenario: Rotated page

- **WHEN** extraction reads text on a rotated PDF page
- **THEN** the declared page frame and transform locate each word box on the corresponding source page without assuming zero rotation

### Requirement: Native extraction repeatability

Native extraction SHALL record extractor identity, version, dependency fingerprints and effective configuration digest. Identical PDF bytes, selected pages and pinned extraction settings/dependencies SHALL produce byte-identical semantic artifacts. The manifest SHALL declare this artifact set and digest separately from run paths, IDs, timestamps and measurements.

#### Scenario: Two fresh local runs

- **WHEN** the same PDF is extracted twice with the same pinned settings and dependencies into distinct directories
- **THEN** DSC, raw/search text and source-mapping bytes and semantic digests match, while execution envelope fields may differ

### Requirement: Native extraction partiality and failures

The native route SHALL retain scoped unsupported/unexamined coverage and SHALL NOT treat a text layer as complete visual coverage. Textless pages SHALL remain explicitly unresolved without automatic OCR. Invalid page selections, malformed or unreadable/encrypted inputs, and existing output directories SHALL produce explicit non-success results without overwriting existing data.

#### Scenario: Mixed native and scanned content

- **GIVEN** one page with native text and a raster region and another page with no native text
- **WHEN** native extraction completes its supported observations
- **THEN** retained native text is inspectable, unsupported raster content and the textless page are explicit, and the run reports partial output rather than full-document success

#### Scenario: Invalid input preserves existing data

- **WHEN** the user supplies an invalid page, malformed or unreadable/encrypted PDF, or an existing output directory
- **THEN** extraction returns an explicit non-success result without overwriting existing data or invoking OCR or network services
