---
id: document.ontology.boundaries.layer
kind: intent
statement: "WHEN out-of-core semantics appear in a DSC 0.3 document, THE ontology boundary rules SHALL dispose of each feature through explicit, provenance-declared projection or typed refusal, never silently coercing it into core relations."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| no_silent_coercion | invariant | `Unsupported semantic relationships are never rewritten as core contains/precedes/realizes without a declared equivalence` | [[document.ontology.boundaries.layer]] |
| explicit_disposition | invariant | `Each evaluated out-of-core feature is exactly represented, explicitly projected, or reported with a declared unsupported/unexamined/loss outcome` | [[document.ontology.boundaries.layer]] |
| profile_isolation | invariant | `A registered profile never redefines core identity, relations, canonical form, or validity rules` | [[document.ontology.boundaries.layer]] |
| mapping_provenance | invariant | `A projection declares source/target version, rules, scope, evidence, and losses before it is applied as a valid mapping` | [[document.ontology.boundaries.layer]] |
| inference_isolation | invariant | `Derived ontology statements are marked derived in their provenance, never presented as direct source observations` | [[document.ontology.boundaries.layer]] |
| conditional_roundtrip | invariant | `Roundtrip fidelity is claimed only for a specified observable subset and tested domain; claims beyond it are rejected` | [[document.ontology.boundaries.layer]] |

## Model

### States
- `features_evaluated`
- `disposition_declared`
- `projected`
- `reported_unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| evaluate_features | features_evaluated | disposition_declared | every evaluated feature carries an explicit disposition or typed refusal [[document.ontology.boundaries.layer.explicit_disposition]] |
| apply_projection | disposition_declared | projected | provenance declaration is complete and no core rule is redefined [[document.ontology.boundaries.layer.mapping_provenance]] [[document.ontology.boundaries.layer.profile_isolation]] |
| refuse_unsupported | disposition_declared | reported_unsupported | no declared equivalence exists and the loss manifest records the outcome [[document.ontology.boundaries.layer.no_silent_coercion]] [[document.ontology.boundaries.layer.explicit_disposition]] |
| audit_provenance | projected | projected | derived statements carry derived provenance, never direct-observation labels [[document.ontology.boundaries.layer.inference_isolation]] |
| scope_fidelity_claim | projected | projected | a roundtrip claim names its observable subset and tested domain before acceptance [[document.ontology.boundaries.layer.conditional_roundtrip]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| no_core_rewrite | unit | [[document.ontology.boundaries.layer.no_silent_coercion]] | `coercion_attempt_fixture()` | an out-of-core relation without a declared equivalence never appears as contains/precedes/realizes |
| disposition_totality | unit | [[document.ontology.boundaries.layer.explicit_disposition]] | `evaluated_feature_corpus()` | every evaluated feature ends in exactly-represented, projected, or typed unsupported/unexamined/loss outcome |
| profile_rejection | unit | [[document.ontology.boundaries.layer.profile_isolation]] | `core_rule_redefining_profile()` | a profile attempt to redefine a core rule is rejected |
| provenance_required | unit | [[document.ontology.boundaries.layer.mapping_provenance]] | `projection_without_declaration()` | a projection omitting its declaration is not applied as a valid mapping |
| derived_labels | unit | [[document.ontology.boundaries.layer.inference_isolation]] | `derived_statement_probe()` | derived statements carry derived provenance in every emitted descriptor |
| bounded_fidelity | unit | [[document.ontology.boundaries.layer.conditional_roundtrip]] | `unbounded_fidelity_claim()` | a full-fidelity roundtrip claim beyond the tested subset is rejected |
