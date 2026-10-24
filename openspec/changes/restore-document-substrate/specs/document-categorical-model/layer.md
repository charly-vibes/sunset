---
id: document.categorical.model.layer
kind: intent
statement: "WHEN DSC descriptions and transformations are specified, THE categorical foundation SHALL define typed instances and relational links, lawful composition on declared domains, and observational preservation criteria without assuming that extraction is invertible or that domain annotations are true."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| schema_instance | invariant | `The declared typed schema K has well-defined object kinds and reference arrows; an instance I:K→Set gives finite typed collections and total in-scope reference functions where declared mandatory` | [[document.categorical.model.layer]] |
| relational_spans | invariant | `Many-to-many containment alternatives, evidence support and interpretation links are represented as typed relation instances with source and target projections, not arbitrarily collapsed into total functions` | [[document.categorical.model.layer]] |
| composition_laws | invariant | `Typed, scope-compatible mappings satisfy identity and associativity on declared observables; incompatible mappings are rejected before composition` | [[document.categorical.model.layer]] |
| loss_aware_mappings | invariant | `Every transformation defines its domain, versioned dependencies, observable preservation claim and unrepresented or altered features; no inverse is assumed` | [[document.categorical.model.layer]] |
| non_invention | invariant | `A derived interpretation never becomes a direct source observation and an evidenced assertion is not automatically a true semantic fact` | [[document.categorical.model.layer]] |
| factorization_limit | invariant | `When relevant source distinctions disappear in a reduced representation, no downstream mapper may claim that all corresponding observables were preserved without additional evidence` | [[document.categorical.model.layer]] |
| conditional_equivalence | invariant | `Cross-carrier equivalence is assessed only under an explicit relation and scope with independently justified alignment of content, never assumed from matching filenames or titles` | [[document.categorical.model.layer]] |

## Model

### States
- `schema_declared`
- `instance_typed`
- `mapping_checked`
- `law_checked`
- `law_refuted_or_unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| type_instance | schema_declared | instance_typed | `all mandatory references have typed in-scope targets and relationship instances satisfy arity rules` [[document.categorical.model.layer.schema_instance]] [[document.categorical.model.layer.relational_spans]] |
| check_mapping | instance_typed | mapping_checked | `transformation source, target, versions, scope and recorded loss are declared` [[document.categorical.model.layer.loss_aware_mappings]] [[document.categorical.model.layer.conditional_equivalence]] |
| verify_laws | mapping_checked | law_checked | `applicable identity, composition, provenance and observational tests pass within their stated scope` [[document.categorical.model.layer.composition_laws]] [[document.categorical.model.layer.non_invention]] |
| report_limits | mapping_checked | law_refuted_or_unsupported | `a witnessed counterexample or unsupported evaluator is reported without claiming formal verification` [[document.categorical.model.layer.factorization_limit]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| bad_target_rejected | unit | [[document.categorical.model.layer.schema_instance]] | `relation_with_array_or_missing_endpoint()` | `typed validation rejects with classified failure, never crashes` |
| many_to_many | unit | [[document.categorical.model.layer.relational_spans]] | `one_region_in_two_views_fixture()` | `both scoped memberships retained; neither silently preferred` |
| composition_identity | law | [[document.categorical.model.layer.composition_laws]] | `applicable_mappings_with_identity()` | `**identity:** observable(compose(identity,f),x) == observable(f(x)) and dual right identity holds for every applicable f; **associativity:** bracketing agreement on declared observables, separately witnessed by composition_associativity` |
| composition_associativity | law | [[document.categorical.model.layer.composition_laws]] | `three_compatible_mapping_fixtures()` | `**identity:** the identity mapping leaves every applicable instance observably unchanged; **associativity:** observable(compose(h,compose(g,f),x)) == observable(compose(compose(h,g),f,x)) with equal reported loss scope` |
| sign_position_counterexample | unit | [[document.categorical.model.layer.factorization_limit]] | `same_text_different_column_signs()` | `text_only_mapping cannot certify sign preservation and identifies lost positional distinction` |
| no_unfounded_equivalence | unit | [[document.categorical.model.layer.conditional_equivalence]] | `similarly_titled_different_editions()` | `cross-carrier identity/equivalence not inferred without alignment oracle` |
| evidence_not_truth | unit | [[document.categorical.model.layer.non_invention]] | `two_conflicting_attributed_claims()` | `both attributed claims retained; no automatic truth winner` |
| loss_manifest_declared | unit | [[document.categorical.model.layer.loss_aware_mappings]] | `mapping_with_unrepresentable_feature()` | `mapping's declared loss lists the unrepresented feature and no inverse is asserted` |
