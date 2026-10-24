---
id: document.assembly.layer
kind: intent
statement: "WHEN typed region parts and scope-compatible relations are supplied, THE DSC substrate SHALL assemble them deterministically without losing identity, inventing order, or silently accepting incompatible boundaries."
---

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| assembly_compatible | invariant | `Partial assembly accepts only aligned namespace, compatible region identity, and jointly satisfiable structural constraints; rejected operands produce smallest known witness.` | [[document.assembly.layer]] |
| assembly_identity | invariant | `An empty scoped part acts as left and right identity up to canonical representation.` | [[document.assembly.layer]] |
| assembly_associative | invariant | `For any jointly compatible triple A B C whose combined constraints do not depend on assembly grouping, both bracketings produce canonically equivalent parts, links, claims, and loss metadata.` | [[document.assembly.layer]] |
| order_not_implicit | invariant | `Assembly does not infer total reading order or semantic meaning by position or concatenation.` | [[document.assembly.layer]] |
| boundaries_preserved | invariant | `Shared region IDs refer to a single source identity; composed boundary links preserve original edges and provenance.` | [[document.assembly.layer]] |

## Model
### States
- `assembled`
- `parts_ready`
- `refused`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| assemble | parts_ready | assembled | `all references resolve and boundaries are compatible` [[document.assembly.layer.assembly_compatible]] [[document.assembly.layer.assembly_identity]] [[document.categorical.model.layer.schema_instance]] |
| refuse | parts_ready | refused | `any collision or jointly inconsistent constraint produces a classified witness` [[document.assembly.layer.assembly_compatible]] [[document.assembly.layer.boundaries_preserved]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| compatible_pair | unit | [[document.assembly.layer.assembly_compatible]] | `two_parts_distinct_ids()` | `compose(A,B) succeeds and preserves nodes and edges` |
| duplicate_conflict | unit | [[document.assembly.layer.assembly_compatible]] | `same_id_conflicting_source()` | `compose(A,B) refuses with id witness` |
| left_right_identity | law | [[document.assembly.layer.assembly_identity]] | `assembly_and_empty()` | `**identity:** canonical(compose(A,empty)) == canonical(A) == canonical(compose(empty,A)) for every applicable part A; **associativity:** bracketing agreement, separately witnessed by associate_three` |
| associate_three | law | [[document.assembly.layer.assembly_associative]] | `jointly_compatible_triple()` | `**identity:** the empty scoped part leaves every applicable assembly canonically unchanged; **associativity:** canonical(compose(compose(A,B),C)) == canonical(compose(A,compose(B,C))) for jointly compatible triples` |
| no_invented_order | unit | [[document.assembly.layer.order_not_implicit]] | `two_unrelated_regions()` | `assembly has no precedes edge` |
| shared_id_merges | unit | [[document.assembly.layer.boundaries_preserved]] | `same_id_identical_claims()` | `a shared region ID composes into a single identity retaining original edges and provenance` |
