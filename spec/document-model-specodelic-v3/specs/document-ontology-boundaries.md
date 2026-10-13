---
id: document.ontology-boundaries
kind: intent
statement: "WHEN a document concept exceeds DSC core expressivity, THE system SHALL explicitly route it to a registered extension, declared projection, or documented limitation without silently changing its meaning."
---

# Ontology boundaries

Normative design policy: [ONTOLOGY-BOUNDARIES.md](../ONTOLOGY-BOUNDARIES.md). This is a proposed DSC 0.3 capability specification; no validator/adapter implementation is claimed.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| no_silent_coercion | invariant | `unsupported semantic relationships are never rewritten as core contains/precedes/realizes without declared equivalence` | [[document.ontology-boundaries]] |
| explicit_boundary | invariant | `each evaluated out-of-core feature is exactly represented, explicitly projected, or reported with a declared unsupported/unexamined/loss outcome` | [[document.ontology-boundaries]] |
| profile_isolation | invariant | `registered profile cannot redefine core identity, relations, canonical form, or validity rules` | [[document.ontology-boundaries]] |
| mapping_provenance | invariant | `projection declares source/target version, rules, scope, evidence and losses` | [[document.ontology-boundaries]] |
| inference_isolation | invariant | `derived ontology statements are never misrepresented as direct source observations` | [[document.ontology-boundaries]] |
| conditional_roundtrip | invariant | `roundtrip fidelity is claimed only for a specified observable subset and tested domain` | [[document.ontology-boundaries]] |

## Model

### States
- `unassessed`
- `represented`
- `projected`
- `unsupported`
- `unexamined`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| native | unassessed | represented | `faithful_core_or_registered_profile_encoding_verified` |
| map | unassessed | projected | `declared_projection_evaluated_with_losses` |
| fail | unassessed | unsupported | `evaluated_and_no_adequate_representation` |
| defer | unassessed | unexamined | `feature_not_evaluated` |

These states describe the disposition of a scoped **feature**, not whether an entire document is conformant. A document may contain several dispositions.

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|
| boundary_1 | acceptance | [[document.ontology-boundaries.no_silent_coercion]] | `ONTOLOGY-BOUNDARIES.md#7-proposed-acceptance-checks-unimplemented` | `O-A01_no_fake_core_relation` |
| boundary_2 | acceptance | [[document.ontology-boundaries.mapping_provenance]] | `ONTOLOGY-BOUNDARIES.md#7-proposed-acceptance-checks-unimplemented` | `O-A04_loss_manifest` |
| boundary_3 | acceptance | [[document.ontology-boundaries.conditional_roundtrip]] | `ONTOLOGY-BOUNDARIES.md#7-proposed-acceptance-checks-unimplemented` | `O-A05_no_unearned_full_fidelity` |

## Notes

Properties are proposed acceptance obligations, not executable fixture filenames. See the ontology document and ACCEPTANCE.md. Domain-specific meaning and reasoners remain outside the DSC core.
