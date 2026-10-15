---
id: document.context
kind: intent
statement: "THE DSC substrate SHALL make domain meanings explicit as attributed, scoped claims with deterministic context availability and no automatic promotion of evidence into semantic truth."
---

# Scoped semantic context

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| claims_attributed | invariant | `Semantic claims name target, vocabulary, value, source/evidence, context scope, and status; unsupported claims remain visible.` | [[document.context]] |
| context_scoped | invariant | `Bindings are inherited only when the declared rule permits it, and are marked as inherited rather than directly observed.` | [[document.context]] |
| shadow_conflict | invariant | `Overrides require explicit scope policy; incompatible active bindings remain disputed unless a deterministic declared precedence rule applies.` | [[document.context]] |
| no_truth_laundering | invariant | `Extractor or editor assertions are attributed interpretations, not facts confirmed by their parent region.` | [[document.context]] |
| no_generic_meaning_union | invariant | `Assembling regions does not by itself union their semantic truth; domain-specific compositional rules must be pinned.` | [[document.context]] |
| deterministic_interpretation | invariant | `Pinned observations, rule versions, scopes and context produce canonically equal claims or the same classified unknown/conflict outcome.` | [[document.context]] |

## Model
### States
- `claims_checked`
- `claims_disputed`
- `claims_ready`
- `context_resolved`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| resolve | claims_ready | context_resolved | `bindings and rule versions exist` [[document.context.context_scoped]] |
| interpret | context_resolved | claims_checked | `rules evaluate with attributed evidence` [[document.context.claims_attributed]] [[document.context.no_truth_laundering]] [[document.categorical.model.non_invention]] |
| dispute | context_resolved | claims_disputed | `conflicting scope bindings cannot be resolved under policy` [[document.context.shadow_conflict]] [[document.context.no_generic_meaning_union]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| publication_date | unit | [[document.context.claims_attributed]] | `issue_date_child_article()` | `context available as issue metadata; not narrated date` |
| quoted_author | unit | [[document.context.context_scoped]] | `article_author_and_quote()` | `author not automatically assigned to quote` |
| context_dispute | unit | [[document.context.shadow_conflict]] | `two_views_conflicting_date()` | `disagreement retained unless precedence declared` |
| same_pinned_input | unit | [[document.context.deterministic_interpretation]] | `same_observations_rules_twice()` | `canonical results equivalent` |
| uncertain_ocr | unit | [[document.context.no_truth_laundering]] | `text_with_disputed_transcription()` | `claim retains uncertainty and evidence` |
| no_union_on_assembly | unit | [[document.context.no_generic_meaning_union]] | `two_views_composed_meanings()` | `composed claims do not union semantic truth; composed meaning requires a pinned domain rule` |

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

## Requirements
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
