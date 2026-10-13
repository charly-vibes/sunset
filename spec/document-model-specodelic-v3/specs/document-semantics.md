---
id: document.semantics
kind: intent
statement: "WHEN a domain annotation is added, THE system SHALL retain typed, namespaced claims without reinterpreting the structural core."
---

# Semantics

Semantic vocabulary registration is versioned. `title`, `poem`, `posting` etc are extension terms, not universal records. Claims do not overwrite core structure. Edition equivalence is an optional explicitly scoped comparison using a named projection and comparator.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| namespace | invariant | `every non-core term is registered with namespace and semantic version` | [[document.semantics]] |
| claims | invariant | `annotations declare target, term, value, provenance status and evidence references` | [[document.semantics]] |
| extension | invariant | `an extension cannot modify core identity, relation kinds or canonicalization` | [[document.semantics]] |
| unknown | invariant | `unregistered extension terms reject; unresolved semantic alternatives are explicit` | [[document.semantics]] |
| equivalence | invariant | `cross-edition equivalence never inferred automatically; named projection and comparator required` | [[document.semantics]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| semantic_views | invariant | `a claim or domain grouping belongs to an explicit structural view; alternate classifications do not mutate physical observations` | [[document.semantics]] |
| source_vs_claim | invariant | `semantic labels and observed strings have distinct provenance; unsupported claims cannot be promoted by schema validity alone` | [[document.semantics]] |

## Model

### States
- `uninterpreted`
- `interpreted`
- `needs_review`
- `rejected`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| interpret | uninterpreted | interpreted | `claim_valid AND no_unresolved_claim_conflict` |
| review | uninterpreted | needs_review | `claim_valid AND unresolved_claim_conflict` |
| reject | uninterpreted | rejected | `NOT claim_valid` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.semantics.namespace]] | `fixtures/invalid/unknown-extension.json` | `error includes unknown_term` |
| check_2 | unit | [[document.semantics.claims]] | `fixtures/valid/two-regions.json` | `validate == valid` |
| check_3 | unit | [[document.semantics.unknown]] | `fixtures/valid/disputed.json` | `disputed_claims_preserved` |

## Notes

Domain vocabulary and equivalence comparator implementations are extension responsibilities. The sample `demo@1` vocabulary is a fixture, not a globally adopted standard.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
