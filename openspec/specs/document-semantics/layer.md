---
id: document.semantics.layer
kind: intent
statement: "WHEN domain claims are registered or assessed in a DSC descriptor, THE semantic layer SHALL keep every claim typed, namespaced, view-bound, and provenance-distinct from observation, never letting claims mutate core structure or equivalence arise without an explicit projection and comparator."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| registered_vocabulary | invariant | `Every non-core term carries a namespace and semantic version, and unregistered extension terms are rejected with unknown_term` | [[document.semantics.layer]] |
| view_bound_claims | invariant | `Annotations keep all 0.2 mandatory fields plus view_id resolving to a named view whose regions or has-content-bound contents cover the target, admitting only the paired optional alignment fields` | [[document.semantics.layer]] |
| extension_isolation | invariant | `Extensions never modify core identity, relation kinds, or canonicalization, and are rejected at registration when they attempt to` | [[document.semantics.layer]] |
| explicit_alternatives | invariant | `Unresolved semantic alternatives stay explicit with their conflict status rather than being resolved implicitly` | [[document.semantics.layer]] |
| scoped_equivalence | invariant | `Cross-edition equivalence is never inferred; it exists only under a named projection and comparator` | [[document.semantics.layer]] |
| provenance_distinction | invariant | `Semantic labels and observed strings carry distinct provenance, schema validity never promotes a claim to supported, no-evidence assertions use asserted_without_evidence except disputed claims, and unverifiable remains an external outcome` | [[document.semantics.layer]] |

## Model

### States
- `vocabulary_registered`
- `claims_bound`
- `alternatives_recorded`
- `equivalence_declared`
- `provenance_reported`
- `claim_rejected`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| register_terms | vocabulary_registered | vocabulary_registered | every non-core term carries a namespace and semantic version, and unknown terms are refused [[document.semantics.layer.registered_vocabulary]] |
| bind_claims | vocabulary_registered | claims_bound | each annotation resolves its view_id and its target is bound in that view, with only alignment fields beyond the mandatory set [[document.semantics.layer.view_bound_claims]] |
| reject_extension | claims_bound | claim_rejected | an extension attempts to alter core identity, relation kinds, or canonicalization [[document.semantics.layer.extension_isolation]] |
| preserve_disputes | claims_bound | alternatives_recorded | unresolved alternatives are kept explicit with their conflict status, never silently resolved [[document.semantics.layer.explicit_alternatives]] |
| declare_equivalence | alternatives_recorded | equivalence_declared | a named projection and comparator are supplied before any cross-edition equivalence is treated as valid [[document.semantics.layer.scoped_equivalence]] |
| separate_provenance | equivalence_declared | provenance_reported | labels and observations keep distinct provenance and no-evidence undisputed claims carry asserted_without_evidence [[document.semantics.layer.provenance_distinction]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| unknown_term_rejected | unit | [[document.semantics.layer.registered_vocabulary]] | `unregistered_extension_descriptor()` | a non-core term without namespace and version yields an error including unknown_term |
| claim_view_binding | unit | [[document.semantics.layer.view_bound_claims]] | `shared_content_two_views_fixture()` | differing claims on shared content each name their view with a binding there, and an unbound claim is invalid rather than implicitly assigned |
| core_untouchable | unit | [[document.semantics.layer.extension_isolation]] | `identity_rewriting_extension()` | an extension altering core identity or relation kinds is rejected at registration and never applied |
| dispute_preservation | unit | [[document.semantics.layer.explicit_alternatives]] | `disputed_claims_descriptor()` | disputed claims survive validation with their conflict status intact |
| equivalence_gate | unit | [[document.semantics.layer.scoped_equivalence]] | `comparatorless_equivalence_claim()` | an equivalence lacking a named projection and comparator is never treated as an inferred core equivalence |
| claim_not_promoted | unit | [[document.semantics.layer.provenance_distinction]] | `evidenceless_undisputed_claim()` | an undisputed claim without evidence keeps status asserted_without_evidence with assessment unverifiable and is never silently supported |
