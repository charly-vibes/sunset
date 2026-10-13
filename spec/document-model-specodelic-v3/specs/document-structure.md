---
id: document.structure
kind: intent
statement: "WHEN regions are assembled into document structure, THE system SHALL separate physical containment from logical grouping and reading sequence."
---

# Structure

Region `view` is physical or logical. A logical region can reference several physical placements via `realizes` relations. `contains` is exclusive-parent structural ownership; `precedes` is a strict partial-order generating edge. No order is inferred from x/y geometry. Content may be referenced by multiple regions without copying it.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| views | invariant | `regions declare physical or logical view; only physical regions can have geometry` | [[document.structure]] |
| containment | invariant | `contains edges have one parent per child and cannot cycle` | [[document.structure]] |
| order | invariant | `precedes DAG induces a partial order by reachability, not a required linear order` | [[document.structure]] |
| realization | invariant | `realizes connects physical to logical region and supports page continuation` | [[document.structure]] |
| shared_content | invariant | `content bindings may reference the same content id more than once without duplicate content objects` | [[document.structure]] |
| ambiguity | invariant | `multiple alternative orderings stay separate claims; no automatic arbitrary selection` | [[document.structure]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| named_views | invariant | `independent physical, logical and carrier views have independent containment trees, with cross-view linkage only via explicit realization or registered alignment` | [[document.structure]] |
| order_hypotheses | invariant | `precedes edges belong to exactly one named reading-order interpretation; each interpretation has its own DAG; incompatible hypotheses are not merged` | [[document.structure]] |
| linearization | invariant | `a total exported reading sequence requires a named tie-break/linearization policy and explicit handling of incomparable regions` | [[document.structure]] |
| fragment_mapping | invariant | `realization is many-to-many; fine-grained location alignment requires declared selectors and profile` | [[document.structure]] |

## Model

### States
- `raw`
- `resolved`
- `ambiguous`
- `invalid`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| resolve | raw | resolved | `structure_valid AND no_unresolved_alternatives` |
| defer | raw | ambiguous | `structure_valid AND unresolved_alternatives_exist` |
| reject | raw | invalid | `NOT structure_valid` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.structure.containment]] | `fixtures/invalid/cycle.json` | `error includes containment_cycle` |
| check_2 | unit | [[document.structure.order]] | `fixtures/invalid/order-cycle.json` | `error includes order_cycle` |
| check_3 | unit | [[document.structure.realization]] | `fixtures/valid/continuation.json` | `validate == valid` |
| check_4 | unit | [[document.structure.shared_content]] | `fixtures/valid/continuation.json` | `same_content_id_referenced_by_multiple_regions` |

## Notes

Reader order, EPUB spine order, navigation order and CSS display order are distinct. No formatting flatten is mandated for poems, tables or images.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
