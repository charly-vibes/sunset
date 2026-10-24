---
id: document.views.layer
kind: intent
statement: "THE DSC substrate SHALL express multiple named hierarchies and partial orders over shared regions, with deterministic refinement and projection behavior."
---

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| named_view_membership | invariant | `Each containment, order, continuation, and reference edge has a declared view and typed source and target; nodes may occur in several views.` | [[document.views.layer]] |
| containment_acyclic | invariant | `Containment in a hierarchical view is acyclic, root policy is declared, and each edge is between distinct existing nodes.` | [[document.views.layer]] |
| partial_order | invariant | `Reading order has no directed cycle and can leave nodes incomparable; a chosen linearization is recorded as a derived view.` | [[document.views.layer]] |
| projection_fidelity | invariant | `A projection keeps exactly the selected region IDs and internal edges and records excluded edges as coverage/loss.` | [[document.views.layer]] |
| refinement_explicit | invariant | `Refinement preserves established scoped edges or marks supersession/conflict; no silently removed assertion.` | [[document.views.layer]] |
| nonhierarchical_links | invariant | `Cross-page continuation and reference edges remain links, never forced into containment.` | [[document.views.layer]] |

## Model
### States
- `view_checked`
- `view_declared`
- `view_invalid`
- `view_valid`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| index | view_declared | view_checked | `view identifiers and endpoints resolve` [[document.views.layer.named_view_membership]] |
| accept | view_checked | view_valid | `hierarchy and order graphs satisfy stated laws` [[document.views.layer.containment_acyclic]] [[document.views.layer.partial_order]] [[document.categorical.model.layer.relational_spans]] |
| reject | view_checked | view_invalid | `cycle or illegal endpoint yields counterexample` [[document.views.layer.containment_acyclic]] [[document.views.layer.refinement_explicit]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| view_overlap | unit | [[document.views.layer.named_view_membership]] | `one_region_in_two_views()` | `both memberships survive` |
| cycle_refused | unit | [[document.views.layer.containment_acyclic]] | `three_region_containment_cycle()` | `hierarchy rejected with cycle path` |
| partial_order_ok | unit | [[document.views.layer.partial_order]] | `two_incomparable_regions()` | `no total order inferred` |
| projection | unit | [[document.views.layer.projection_fidelity]] | `two_pages_one_cross_page_link()` | `excluded link reported in coverage` |
| refinement_conflict | unit | [[document.views.layer.refinement_explicit]] | `new_view_deletes_assertion()` | `reports supersession or conflict` |
| links_not_containment | unit | [[document.views.layer.nonhierarchical_links]] | `cross_page_continuation_fixture()` | `continuation and reference edges remain typed links; no parent pointer is invented` |
