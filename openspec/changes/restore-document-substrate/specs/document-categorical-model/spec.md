---
id: document.categorical.model
kind: intent
statement: "WHEN DSC descriptions and transformations are specified, THE categorical foundation SHALL define typed instances and relational links, lawful composition on declared domains, and observational preservation criteria without assuming that extraction is invertible or that domain annotations are true."
---

# Categorical foundation

## Purpose

Use category theory as a compact specification of typing and laws, not as a new mandatory wire format or runtime framework.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| schema_instance | invariant | `The declared typed schema K has well-defined object kinds and reference arrows; an instance I:K→Set gives finite typed collections and total in-scope reference functions where declared mandatory` | [[document.categorical.model]] |
| relational_spans | invariant | `Many-to-many containment alternatives, evidence support and interpretation links are represented as typed relation instances with source and target projections, not arbitrarily collapsed into total functions` | [[document.categorical.model]] |
| composition_laws | invariant | `Typed, scope-compatible mappings satisfy identity and associativity on declared observables; incompatible mappings are rejected before composition` | [[document.categorical.model]] |
| loss_aware_mappings | invariant | `Every transformation defines its domain, versioned dependencies, observable preservation claim and unrepresented or altered features; no inverse is assumed` | [[document.categorical.model]] |
| non_invention | invariant | `A derived interpretation never becomes a direct source observation and an evidenced assertion is not automatically a true semantic fact` | [[document.categorical.model]] |
| factorization_limit | invariant | `When relevant source distinctions disappear in a reduced representation, no downstream mapper may claim that all corresponding observables were preserved without additional evidence` | [[document.categorical.model]] |
| conditional_equivalence | invariant | `Cross-carrier equivalence is assessed only under an explicit relation and scope with independently justified alignment of content, never assumed from matching filenames or titles` | [[document.categorical.model]] |

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
| type_instance | schema_declared | instance_typed | `all mandatory references have typed in-scope targets and relationship instances satisfy arity rules` [[document.categorical.model.schema_instance]] [[document.categorical.model.relational_spans]] |
| check_mapping | instance_typed | mapping_checked | `transformation source, target, versions, scope and recorded loss are declared` [[document.categorical.model.loss_aware_mappings]] [[document.categorical.model.conditional_equivalence]] |
| verify_laws | mapping_checked | law_checked | `applicable identity, composition, provenance and observational tests pass within their stated scope` [[document.categorical.model.composition_laws]] [[document.categorical.model.non_invention]] |
| report_limits | mapping_checked | law_refuted_or_unsupported | `a witnessed counterexample or unsupported evaluator is reported without claiming formal verification` [[document.categorical.model.factorization_limit]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| bad_target_rejected | unit | [[document.categorical.model.schema_instance]] | `relation_with_array_or_missing_endpoint()` | `typed validation rejects with classified failure, never crashes` |
| many_to_many | unit | [[document.categorical.model.relational_spans]] | `one_region_in_two_views_fixture()` | `both scoped memberships retained; neither silently preferred` |
| composition_identity | law | [[document.categorical.model.composition_laws]] | `applicable_mappings_with_identity()` | `**identity:** observable(compose(identity,f),x) == observable(f(x)) and dual right identity holds for every applicable f; **associativity:** bracketing agreement on declared observables, separately witnessed by composition_associativity` |
| composition_associativity | law | [[document.categorical.model.composition_laws]] | `three_compatible_mapping_fixtures()` | `**identity:** the identity mapping leaves every applicable instance observably unchanged; **associativity:** observable(compose(h,compose(g,f),x)) == observable(compose(compose(h,g),f,x)) with equal reported loss scope` |
| sign_position_counterexample | unit | [[document.categorical.model.factorization_limit]] | `same_text_different_column_signs()` | `text_only_mapping cannot certify sign preservation and identifies lost positional distinction` |
| no_unfounded_equivalence | unit | [[document.categorical.model.conditional_equivalence]] | `similarly_titled_different_editions()` | `cross-carrier identity/equivalence not inferred without alignment oracle` |
| evidence_not_truth | unit | [[document.categorical.model.non_invention]] | `two_conflicting_attributed_claims()` | `both attributed claims retained; no automatic truth winner` |
| loss_manifest_declared | unit | [[document.categorical.model.loss_aware_mappings]] | `mapping_with_unrepresentable_feature()` | `mapping's declared loss lists the unrepresented feature and no inverse is asserted` |

## ADDED Requirements

### Requirement: Typed categorical document instances
The model SHALL provide a declared typed schema interpretable as a finite Set-valued instance, with relational spans for many-to-many associations.

#### Scenario: Overlapping document hierarchies
- **GIVEN** a region participating in two logical views
- **WHEN** the instance is interpreted
- **THEN** both memberships SHALL survive and no unique reading order SHALL be invented.

### Requirement: Scoped compositional transformations
Mappings SHALL declare source/target types, domains, observable scope and loss, and SHALL meet identity and associativity checks over applicable finite fixtures.

#### Scenario: Text-only flattening loses meaning
- **GIVEN** two statement layouts whose flattened text is identical but whose sign-bearing column positions differ
- **WHEN** a text-only mapper claims semantic-sign preservation
- **THEN** conformance SHALL reject that claim or record the missing positional evidence as a limitation.

### Requirement: No unjustified categorical equivalence
The system SHALL NOT assert invertibility, adjunction or cross-carrier semantic isomorphism without explicit definitions and proofs or bounded evidence.

#### Scenario: Similar titles are not an alignment oracle
- **GIVEN** two carriers whose documents share a title or filename but whose content corresponds to different editions
- **WHEN** a cross-carrier comparison is requested without a declared alignment relation and scope
- **THEN** the outcome SHALL be recorded as unsupported or unexamined, never as equivalent.

## Requirements

### Requirement: Typed categorical document instances
The model SHALL provide a declared typed schema interpretable as a finite Set-valued instance, with relational spans for many-to-many associations.

#### Scenario: Overlapping document hierarchies
- **GIVEN** a region participating in two logical views
- **WHEN** the instance is interpreted
- **THEN** both memberships SHALL survive and no unique reading order SHALL be invented.

### Requirement: Scoped compositional transformations
Mappings SHALL declare source/target types, domains, observable scope and loss, and SHALL meet identity and associativity checks over applicable finite fixtures.

#### Scenario: Text-only flattening loses meaning
- **GIVEN** two statement layouts whose flattened text is identical but whose sign-bearing column positions differ
- **WHEN** a text-only mapper claims semantic-sign preservation
- **THEN** conformance SHALL reject that claim or record the missing positional evidence as a limitation.

### Requirement: No unjustified categorical equivalence
The system SHALL NOT assert invertibility, adjunction or cross-carrier semantic isomorphism without explicit definitions and proofs or bounded evidence.

#### Scenario: Similar titles are not an alignment oracle
- **GIVEN** two carriers whose documents share a title or filename but whose content corresponds to different editions
- **WHEN** a cross-carrier comparison is requested without a declared alignment relation and scope
- **THEN** the outcome SHALL be recorded as unsupported or unexamined, never as equivalent.
