# Document purpose

## Purpose

Restore the general document-description substrate objective. This is a normative *new capability* defining the design boundary, not a claim of present implementation.

## ADDED Requirements

### Requirement: General-purpose document description
The DSC specification SHALL define deterministic structural interchange independently of an extraction-review workflow.

#### Scenario: A non-periodical consumer
- **GIVEN** a structured financial statement represented with core regions, relations, annotations and evidence
- **WHEN** a conforming reader consumes its descriptor
- **THEN** it SHALL recover the declared structure without adding a financial primitive to the core.

### Requirement: Native format support
The system SHALL allow native PDF and EPUB adapters without requiring OCR or false fixed pages.

#### Scenario: EPUB navigation
- **GIVEN** a reflowable EPUB with a spine, a hyperlink and a footnote backlink
- **WHEN** it is represented in DSC
- **THEN** those source-native distinctions SHALL remain recoverable within declared capabilities and backlinks SHALL NOT silently become reading-order relations.

### Requirement: Honest acceptance boundary
A reviewer-workflow demonstration SHALL NOT be labeled as general independent document-interchange conformance without corresponding cross-carrier independent-consumer evidence.

#### Scenario: Reviewer-only pass is not general conformance
- **GIVEN** the first-consumer extraction-review benchmark passes on all periodical fixtures
- **WHEN** the acceptance narrative is written
- **THEN** it SHALL NOT claim general document-interchange conformance unless the independent multi-carrier consumer gate has also been demonstrated or is explicitly recorded as not yet demonstrated.
