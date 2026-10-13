---
id: document.core
kind: intent
statement: "WHEN a document instance is submitted, THE system SHALL validate its typed structure and return complete error reasons."
---

# Core

The normative v0.2 JSON contract is CONTRACT.md. Object identifiers are snapshot-local; stable means unchanged under canonical roundtrip, not stable across re-extraction. Unknown keys are rejected. JSON UTF-8 canonical form: RFC 8785-style key sorting subset defined in CONTRACT.md (ASCII names, strings NFC, integers, no floats). The reference implementation uses sorted compact JSON, encoding UTF-8.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| instance_shape | invariant | `all required arrays and object fields match CONTRACT.md; unknown fields forbidden` | [[document.core]] |
| identity | invariant | `all instance ids are unique inside a document snapshot and every reference resolves` | [[document.core]] |
| containment | invariant | `every region except declared root has exactly one parent; contains edges are acyclic` | [[document.core]] |
| order | invariant | `precedes edges are acyclic; reachability defines strict partial order, not total order` | [[document.core]] |
| geometry | invariant | `coordinates are optional; if provided geometry has named space and nonnegative extent` | [[document.core]] |
| canonical | invariant | `canonicalize(parse(canonicalize(x))) == canonicalize(x) as bytes` | [[document.core]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| versioning | invariant | `v0.3 descriptors add views, selectors, interpretations, coverage; v0.2 validator is version-specific and must reject v0.3 until upgraded` | [[document.core]] |
| scoped_identity | invariant | `entity ids are snapshot-local and unique across all instance collections; views have unique ids` | [[document.core]] |
| multi_view | invariant | `each named view has exactly one declared root, contains is confined to that view and acyclic` | [[document.core]] |
| canonical_precondition | invariant | `canonical serialization is defined only for valid NFC JSON inputs; identical canonical bytes are a structural reproducibility check, not source fidelity` | [[document.core]] |

## Model

### States
- `unvalidated`
- `valid`
- `invalid`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| accept | unvalidated | valid | `all_core_checks_pass` |
| reject | unvalidated | invalid | `any_core_check_fails` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.core.instance_shape]] | `fixtures/valid/two-regions.json` | `validate == valid` |
| check_2 | unit | [[document.core.identity]] | `fixtures/invalid/dangling.json` | `error includes dangling_reference` |
| check_3 | unit | [[document.core.containment]] | `fixtures/invalid/cycle.json` | `error includes containment_cycle` |
| check_4 | unit | [[document.core.order]] | `fixtures/invalid/order-cycle.json` | `error includes order_cycle` |
| check_5 | unit | [[document.core.canonical]] | `fixtures/valid/two-regions.json` | `canonical_roundtrip_equal` |

## Notes

The predicates are implemented by `python3 validator.py test`; Specodelic lint alone cannot execute these domain-specific properties. Both transition guards are complementary after schema parsing; invalid JSON also rejects with parse_error.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
