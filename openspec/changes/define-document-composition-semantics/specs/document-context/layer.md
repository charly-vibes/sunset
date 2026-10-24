---
id: document.context.layer
kind: intent
statement: "THE DSC substrate SHALL make domain meanings explicit as attributed, scoped claims with deterministic context availability and no automatic promotion of evidence into semantic truth."
---

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| claims_attributed | invariant | `Semantic claims name target, vocabulary, value, source/evidence, context scope, and status; unsupported claims remain visible.` | [[document.context.layer]] |
| context_scoped | invariant | `Bindings are inherited only when the declared rule permits it, and are marked as inherited rather than directly observed.` | [[document.context.layer]] |
| shadow_conflict | invariant | `Overrides require explicit scope policy; incompatible active bindings remain disputed unless a deterministic declared precedence rule applies.` | [[document.context.layer]] |
| no_truth_laundering | invariant | `Extractor or editor assertions are attributed interpretations, not facts confirmed by their parent region.` | [[document.context.layer]] |
| no_generic_meaning_union | invariant | `Assembling regions does not by itself union their semantic truth; domain-specific compositional rules must be pinned.` | [[document.context.layer]] |
| deterministic_interpretation | invariant | `Pinned observations, rule versions, scopes and context produce canonically equal claims or the same classified unknown/conflict outcome.` | [[document.context.layer]] |

## Model
### States
- `claims_checked`
- `claims_disputed`
- `claims_ready`
- `context_resolved`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| resolve | claims_ready | context_resolved | `bindings and rule versions exist` [[document.context.layer.context_scoped]] |
| interpret | context_resolved | claims_checked | `rules evaluate with attributed evidence` [[document.context.layer.claims_attributed]] [[document.context.layer.no_truth_laundering]] [[document.categorical.model.layer.non_invention]] |
| dispute | context_resolved | claims_disputed | `conflicting scope bindings cannot be resolved under policy` [[document.context.layer.shadow_conflict]] [[document.context.layer.no_generic_meaning_union]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| publication_date | unit | [[document.context.layer.claims_attributed]] | `issue_date_child_article()` | `context available as issue metadata; not narrated date` |
| quoted_author | unit | [[document.context.layer.context_scoped]] | `article_author_and_quote()` | `author not automatically assigned to quote` |
| context_dispute | unit | [[document.context.layer.shadow_conflict]] | `two_views_conflicting_date()` | `disagreement retained unless precedence declared` |
| same_pinned_input | unit | [[document.context.layer.deterministic_interpretation]] | `same_observations_rules_twice()` | `canonical results equivalent` |
| uncertain_ocr | unit | [[document.context.layer.no_truth_laundering]] | `text_with_disputed_transcription()` | `claim retains uncertainty and evidence` |
| no_union_on_assembly | unit | [[document.context.layer.no_generic_meaning_union]] | `two_views_composed_meanings()` | `composed claims do not union semantic truth; composed meaning requires a pinned domain rule` |
