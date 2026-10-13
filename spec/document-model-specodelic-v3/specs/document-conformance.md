---
id: document.conformance
kind: intent
statement: "WHEN a descriptor or suite is checked, THE system SHALL report per-instance outcomes separately from suite readiness and Specodelic lint."
---

# Conformance

Per-instance outcomes: valid, invalid, unsupported, ambiguous. Suite status: passed, failed, incomplete. Fixture inventory records available vs missing. The reference tests cover JSON descriptors only, not real PDF/EPUB ingestion, nor independent reader agreement.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| levels | invariant | `Specodelic lint, instance validation and suite conformance have separate reported statuses` | [[document.conformance]] |
| errors | invariant | `negative fixtures produce stable typed reasons` | [[document.conformance]] |
| coverage | invariant | `every missing carrier fixture and independent implementation is visible; incomplete does not mean passed` | [[document.conformance]] |
| carriers | invariant | `full suite requires real scanned PDF, text PDF, EPUB and independent nonperiodical input` | [[document.conformance]] |
| independence | invariant | `full suite requires two independently implemented readers with matching canonical results` | [[document.conformance]] |
| reflow | invariant | `EPUB descriptor has no obligatory fixed coordinates; spine, non-linear entries, navigation are distinct` | [[document.conformance]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| layered_validity | invariant | `report schema validity, observation/source coverage and interpretation assessment separately` | [[document.conformance]] |
| adversarial_corpus | invariant | `test columns, page continuation, shared pages, mixed OCR/native text, poetry, EPUB footnotes, conflicting interpretations, coordinate transforms, roundtrip, omission and replay` | [[document.conformance]] |
| ambiguity_success | invariant | `a test may pass by recording two incompatible supported hypotheses without selecting a winner` | [[document.conformance]] |
| no_false_claims | invariant | `v0.2 fixture checks cannot be reported as v0.3 contract validation or real-carrier conformance` | [[document.conformance]] |

## Model

### States
- `unexamined`
- `passed`
- `failed`
- `incomplete`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| pass | unexamined | passed | `all_required_checks_executed AND all_required_checks_pass` |
| fail | unexamined | failed | `any_executed_required_check_fails` |
| incomplete | unexamined | incomplete | `no_executed_required_check_fails AND required_checks_missing` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.conformance.errors]] | `fixtures/invalid/dangling.json` | `error includes dangling_reference` |
| check_2 | unit | [[document.conformance.coverage]] | `coverage.json` | `missing_real_pdf_epub_and_independent_reader_are_explicit` |
| check_3 | unit | [[document.conformance.reflow]] | `fixtures/valid/epub.json` | `validate == valid` |

## Notes

Reference descriptor test success is not full conformance. No external files or releases are asserted executed without evidence.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
