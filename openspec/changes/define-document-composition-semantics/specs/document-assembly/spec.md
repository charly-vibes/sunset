---
id: document.assembly
kind: intent
statement: "WHEN typed region parts and scope-compatible relations are supplied, THE DSC substrate SHALL assemble them deterministically without losing identity, inventing order, or silently accepting incompatible boundaries."
---

# Document assembly

## Purpose
This is a proposed normative design, not a claim of existing implementation. Interfaces and assertions rely on the earlier `restore-document-substrate` proposal; verify integration against pinned Sunset HEAD.

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| assembly_compatible | invariant | `Partial assembly accepts only aligned namespace, compatible region identity, and jointly satisfiable structural constraints; rejected operands produce smallest known witness.` | [[document.assembly]] |
| assembly_identity | invariant | `An empty scoped part acts as left and right identity up to canonical representation.` | [[document.assembly]] |
| assembly_associative | invariant | `For any jointly compatible triple A B C whose combined constraints do not depend on assembly grouping, both bracketings produce canonically equivalent parts, links, claims, and loss metadata.` | [[document.assembly]] |
| order_not_implicit | invariant | `Assembly does not infer total reading order or semantic meaning by position or concatenation.` | [[document.assembly]] |
| boundaries_preserved | invariant | `Shared region IDs refer to a single source identity; composed boundary links preserve original edges and provenance.` | [[document.assembly]] |

## Model
### States
- `assembled`
- `parts_ready`
- `refused`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| assemble | parts_ready | assembled | `all references resolve and boundaries are compatible` [[document.assembly.assembly_compatible]] [[document.assembly.assembly_identity]] [[document.categorical.model.schema_instance]] |
| refuse | parts_ready | refused | `any collision or jointly inconsistent constraint produces a classified witness` [[document.assembly.assembly_compatible]] [[document.assembly.boundaries_preserved]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| compatible_pair | unit | [[document.assembly.assembly_compatible]] | `two_parts_distinct_ids()` | `compose(A,B) succeeds and preserves nodes and edges` |
| duplicate_conflict | unit | [[document.assembly.assembly_compatible]] | `same_id_conflicting_source()` | `compose(A,B) refuses with id witness` |
| left_right_identity | law | [[document.assembly.assembly_identity]] | `assembly_and_empty()` | `**identity:** canonical(compose(A,empty)) == canonical(A) == canonical(compose(empty,A)) for every applicable part A; **associativity:** bracketing agreement, separately witnessed by associate_three` |
| associate_three | law | [[document.assembly.assembly_associative]] | `jointly_compatible_triple()` | `**identity:** the empty scoped part leaves every applicable assembly canonically unchanged; **associativity:** canonical(compose(compose(A,B),C)) == canonical(compose(A,compose(B,C))) for jointly compatible triples` |
| no_invented_order | unit | [[document.assembly.order_not_implicit]] | `two_unrelated_regions()` | `assembly has no precedes edge` |
| shared_id_merges | unit | [[document.assembly.boundaries_preserved]] | `same_id_identical_claims()` | `a shared region ID composes into a single identity retaining original edges and provenance` |

## ADDED Requirements
### Requirement: Typed partial assembly
The system SHALL compose compatible parts while preserving typed identity and the existing relations.

#### Scenario: Typed partial assembly fixture
- **GIVEN** Given two regions on separate magazine pages and a continuation relation
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two regions on separate magazine pages and a continuation relation, assembly retains both nodes and their continuation without assuming a single page or total reading order.

### Requirement: Algebraic assembly laws
The system SHALL meet identity and associativity under canonical equivalence for jointly compatible parts.

#### Scenario: Algebraic assembly laws fixture
- **GIVEN** Given three jointly compatible parts
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given three jointly compatible parts, both bracketings and empty assembly produce equivalent canonical results.

### Requirement: Reject incompatible parts
The system SHALL refuse conflicting identities or structural constraints with a finite witness.

#### Scenario: Reject incompatible parts fixture
- **GIVEN** Given conflicting intrinsic origins under the same region ID
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given conflicting intrinsic origins under the same region ID, assembly rejects rather than silently renaming the source.

## Requirements
### Requirement: Typed partial assembly
The system SHALL compose compatible parts while preserving typed identity and the existing relations.

#### Scenario: Typed partial assembly fixture
- **GIVEN** Given two regions on separate magazine pages and a continuation relation
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given two regions on separate magazine pages and a continuation relation, assembly retains both nodes and their continuation without assuming a single page or total reading order.

### Requirement: Algebraic assembly laws
The system SHALL meet identity and associativity under canonical equivalence for jointly compatible parts.

#### Scenario: Algebraic assembly laws fixture
- **GIVEN** Given three jointly compatible parts
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given three jointly compatible parts, both bracketings and empty assembly produce equivalent canonical results.

### Requirement: Reject incompatible parts
The system SHALL refuse conflicting identities or structural constraints with a finite witness.

#### Scenario: Reject incompatible parts fixture
- **GIVEN** Given conflicting intrinsic origins under the same region ID
- **WHEN** the corresponding deterministic rule is evaluated
- **THEN** Given conflicting intrinsic origins under the same region ID, assembly rejects rather than silently renaming the source.
