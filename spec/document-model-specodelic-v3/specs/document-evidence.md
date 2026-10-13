---
id: document.evidence
kind: intent
statement: "WHEN observations or semantic claims are recorded, THE system SHALL retain evidence, transformation fingerprints and honest uncertainty."
---

# Evidence

Each claim has `origin` source/extracted/inferred/manual/external; evidence links target recorded objects. Missing support can be represented as `asserted_without_evidence`. Conflicting claims coexist and are marked disputed, not prioritized by an implicit authority ordering. Transformation lineage is a DAG.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| links | invariant | `claim targets and evidence references resolve or explicitly use asserted_without_evidence status` | [[document.evidence]] |
| origin | invariant | `each claim distinguishes source, extracted, inferred, manual and external` | [[document.evidence]] |
| replay | invariant | `derived observations carry transformer id/version, source digest, config digest and dependency declarations` | [[document.evidence]] |
| lineage | invariant | `derived-from relation graph is acyclic` | [[document.evidence]] |
| conflict | invariant | `unresolved competing claims remain separate, status disputed, without automatic precedence` | [[document.evidence]] |
| honesty | invariant | `confidence is not invented; replay material missing is distinguishable from conflict` | [[document.evidence]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| relation_support | invariant | `structural edges can retain typed evidence references; absent evidence is unverified, not proof of support` | [[document.evidence]] |
| selector_resolution | invariant | `source selectors are typed and profile-defined; unresolved references are reported, never assumed resolvable` | [[document.evidence]] |
| observation_versions | invariant | `native, OCR, corrected and normalized text remain distinguishable observations with explicit transform lineage` | [[document.evidence]] |

## Model

### States
- `recorded`
- `supported`
- `disputed`
- `unverifiable`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| support | recorded | supported | `support_sufficient AND NOT conflicting_support AND replay_material_available` |
| dispute | recorded | disputed | `conflicting_support` |
| unverifiable | recorded | unverifiable | `NOT conflicting_support AND (support_missing OR replay_material_missing)` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.evidence.links]] | `fixtures/invalid/dangling-evidence.json` | `error includes dangling_reference` |
| check_2 | unit | [[document.evidence.conflict]] | `fixtures/valid/disputed.json` | `validate == valid AND statuses include disputed` |
| check_3 | unit | [[document.evidence.lineage]] | `fixtures/invalid/lineage-cycle.json` | `error includes lineage_cycle` |

## Notes

An unsupported manual assertion is representable and must not be mistaken for independently verified evidence; it may be valid structurally yet unverifiable epistemically.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
