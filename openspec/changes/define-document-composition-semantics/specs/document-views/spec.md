---
id: document.views
kind: intent
statement: "THE DSC substrate SHALL express multiple named hierarchies and partial orders over shared regions, with deterministic refinement and projection behavior."
---

# Structural views and hierarchies

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| named_view_membership | invariant | `Each containment, order, continuation, and reference edge has a declared view and typed source and target; nodes may occur in several views.` | [[document.views]] |
| containment_acyclic | invariant | `Containment in a hierarchical view is acyclic, root policy is declared, and each edge is between distinct existing nodes.` | [[document.views]] |
| partial_order | invariant | `Reading order has no directed cycle and can leave nodes incomparable; a chosen linearization is recorded as a derived view.` | [[document.views]] |
| projection_fidelity | invariant | `A projection keeps exactly the selected region IDs and internal edges and records excluded edges as coverage/loss.` | [[document.views]] |
| refinement_explicit | invariant | `Refinement preserves established scoped edges or marks supersession/conflict; no silently removed assertion.` | [[document.views]] |
| nonhierarchical_links | invariant | `Cross-page continuation and reference edges remain links, never forced into containment.` | [[document.views]] |

## Model
### States
- `view_checked`
- `view_declared`
- `view_invalid`
- `view_valid`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| index | view_declared | view_checked | `view identifiers and endpoints resolve` [[document.views.named_view_membership]] |
| accept | view_checked | view_valid | `hierarchy and order graphs satisfy stated laws` [[document.views.containment_acyclic]] [[document.views.partial_order]] |
| reject | view_checked | view_invalid | `cycle or illegal endpoint yields counterexample` [[document.views.containment_acyclic]] [[document.views.refinement_explicit]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| view_overlap | unit | [[document.views.named_view_membership]] | `one_region_in_two_views()` | `both memberships survive` |
| cycle_refused | unit | [[document.views.containment_acyclic]] | `three_region_containment_cycle()` | `hierarchy rejected with cycle path` |
| partial_order_ok | unit | [[document.views.partial_order]] | `two_incomparable_regions()` | `no total order inferred` |
| projection | unit | [[document.views.projection_fidelity]] | `two_pages_one_cross_page_link()` | `excluded link reported in coverage` |
| refinement_conflict | unit | [[document.views.refinement_explicit]] | `new_view_deletes_assertion()` | `reports supersession or conflict` |
| links_not_containment | unit | [[document.views.nonhierarchical_links]] | `cross_page_continuation_fixture()` | `continuation and reference edges remain typed links; no parent pointer is invented` |

## ADDED Requirements
### Requirement: Multiple named structural views
The system SHALL preserve overlapping physical and logical hierarchies over the same regions.

#### Scenario: Multiple named structural views fixture
- **GIVEN** Given an article spanning two pages
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given an article spanning two pages, its two page memberships and one logical article membership remain accessible.

### Requirement: Partial reading order
The system SHALL model reading order without assuming a unique total sequence.

#### Scenario: Partial reading order fixture
- **GIVEN** Given two independent columns
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two independent columns, the validator accepts incomparability and rejects a declared cycle.

### Requirement: Scoped projection and refinement
The system SHALL report removed edges and superseded links when a view is projected or refined.

#### Scenario: Scoped projection and refinement fixture
- **GIVEN** Given a cross-page continuation omitted from a one-page projection
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given a cross-page continuation omitted from a one-page projection, the result reports the excluded link rather than claiming full fidelity.

## Requirements
### Requirement: Multiple named structural views
The system SHALL preserve overlapping physical and logical hierarchies over the same regions.

#### Scenario: Multiple named structural views fixture
- **GIVEN** Given an article spanning two pages
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given an article spanning two pages, its two page memberships and one logical article membership remain accessible.

### Requirement: Partial reading order
The system SHALL model reading order without assuming a unique total sequence.

#### Scenario: Partial reading order fixture
- **GIVEN** Given two independent columns
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two independent columns, the validator accepts incomparability and rejects a declared cycle.

### Requirement: Scoped projection and refinement
The system SHALL report removed edges and superseded links when a view is projected or refined.

#### Scenario: Scoped projection and refinement fixture
- **GIVEN** Given a cross-page continuation omitted from a one-page projection
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given a cross-page continuation omitted from a one-page projection, the result reports the excluded link rather than claiming full fidelity.
