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
| assembly_join_commutative | invariant | `Under a declared identity profile on every operand, compose(A,B) and compose(B,A) are canonically equal: record ids derive from their anchors, never from operand order or array position.` | [[document.assembly.layer]] |
| assembly_join_idempotent | invariant | `For an anchor-derived part in canonical emission form, compose(A,A) is canonically equal to A, and re-assembling an assembled result changes nothing.` | [[document.assembly.layer]] |
| refusal_absorbing | invariant | `A classified refusal composes to itself with any operand on either side; a refusal is never dropped, unwrapped into an operand, or turned into an assembly.` | [[document.assembly.layer]] |

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
| join_commutative | law | [[document.assembly.layer.assembly_join_commutative]] | `anchor_derived_pair()` | `**identity:** canonical(compose(A,empty)) == canonical(A) == canonical(compose(empty,A)) for anchor-derived parts under the declared identity profile; **associativity:** bracketing agreement over anchor-derived parts, separately witnessed by associate_three; **commutativity:** canonical(compose(A,B)) == canonical(compose(B,A)); merged sections emit ascending by id, and the derived region id sets agree in both orders` |
| join_idempotent | law | [[document.assembly.layer.assembly_join_idempotent]] | `anchor_derived_part()` | `**identity:** canonical(compose(A,empty)) == canonical(A) for an anchor-derived part in canonical emission form; **associativity:** canonical(compose(compose(A,B),C)) == canonical(compose(A,compose(B,C))) for jointly compatible anchor-derived triples; **idempotence:** canonical(compose(A,A)) == canonical(A), and canonical((A ⊕ B) ⊕ (A ⊕ B)) == canonical(A ⊕ B)` |
| refusal_absorbs | law | [[document.assembly.layer.refusal_absorbing]] | `conflicting_anchor_pair()` | `**identity:** composing a classified refusal with the empty part yields the same classified refusal envelope; **associativity:** bracketing never unwraps a refusal operand — compose(compose(R,X),Y) and compose(R,compose(X,Y)) both stay the classified refusal envelope verbatim; **absorption:** compose(refusal, X) == refusal == compose(X, refusal) for every operand X — part, empty part, or another refusal` |
