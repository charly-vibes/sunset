---
id: document.purpose
kind: intent
statement: "WHEN systems exchange document descriptions, THE DSC substrate SHALL provide a deterministic, carrier-independent structural contract with explicit evidence and scoped loss, SHALL support domain extensions without redefining core meaning, and SHALL treat extraction reconciliation as a consumer rather than its defining purpose."
---

# Document purpose

## Purpose

Restore the general document-description substrate objective. This is a normative *new capability* defining the design boundary, not a claim of present implementation.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| carrier_neutral | invariant | `A descriptor's core structure is not defined in terms of OCR output or fixed pagination; native PDF and reflowable EPUB are first-class carriers` | [[document.purpose]] |
| purpose_consumer_separation | invariant | `Extraction reconciliation is one possible DSC consumer; acceptance of that consumer alone never proves general document-interchange conformance` | [[document.purpose]] |
| three_distinctions | invariant | `Descriptions distinguish carrier observations, logical structure, and attributed interpretation without requiring all three or imposing a single extraction sequence` | [[document.purpose]] |
| scoped_evidence_and_loss | invariant | `Every claimed preservation guarantee has an explicit scope, source evidence or declared limitation; unexamined and unsupported are not silently considered preserved` | [[document.purpose]] |
| extensibility_without_core_redefinition | invariant | `Versioned extension vocabularies may describe articles, postings or poems but never redefine core relationship semantics, source identity or canonicalization` | [[document.purpose]] |
| independent_exchange | invariant | `General conformance requires at least two independently implemented consumers to agree on declared observables for neutral multi-carrier fixtures; shared-schema lint alone is insufficient` | [[document.purpose]] |

## Model

### States
- `purpose_declared`
- `contract_mapped`
- `fixtures_tested`
- `independent_conformance_demonstrated`
- `scope_limited`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| map_contract | purpose_declared | contract_mapped | `mapping from required document roles to current DSC wire and profile contracts has been recorded` [[document.purpose.three_distinctions]] [[document.purpose.extensibility_without_core_redefinition]] |
| test_fixtures | contract_mapped | fixtures_tested | `native PDF and EPUB and scanned and non-periodical fixture oracles have recorded results` [[document.purpose.carrier_neutral]] [[document.purpose.scoped_evidence_and_loss]] |
| prove_exchange | fixtures_tested | independent_conformance_demonstrated | `two independent readers agree within the declared observable scope and report all losses` [[document.purpose.independent_exchange]] |
| state_limit | fixtures_tested | scope_limited | `an unsupported or disputed case is recorded and no generality claim is issued` [[document.purpose.purpose_consumer_separation]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| native_pdf_no_ocr | unit | [[document.purpose.carrier_neutral]] | `native_pdf_fixture_without_ocr()` | `descriptor structurally parses; no OCR prerequisite; preservation/loss reported` |
| epub_no_pages | unit | [[document.purpose.carrier_neutral]] | `reflowable_epub_spine_fixture()` | `spine, navigation, links represented; no fabricated page rectangles` |
| independent_gate | law | [[document.purpose.independent_exchange]] | `two_independent_consumers_on_neutral_fixtures()` | `**identity:** a consumer compared with itself agrees on all declared observables; **associativity:** agreement is transitive across consumer pairs within the declared observable scope; consumer-demo pass alone does not set general-conformant` |
| preserve_scope | unit | [[document.purpose.scoped_evidence_and_loss]] | `document_with_unexamined_attachment()` | `unexamined remains explicit and is not reported preserved` |
| domain_extension | unit | [[document.purpose.extensibility_without_core_redefinition]] | `magazine_and_finance_profiles()` | `same core types unchanged; domain labels namespaced` |
| consumer_not_definition | unit | [[document.purpose.purpose_consumer_separation]] | `reviewer_only_acceptance_report()` | `no general-conformance claim is emitted when only consumer evidence exists` |
| layer_separation | unit | [[document.purpose.three_distinctions]] | `hybrid_observation_structure_claim_fixture()` | `observation, structure and interpretation records remain separately addressable` |

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

## Requirements

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
