---
id: document.adapters
kind: intent
statement: "WHEN a carrier is ingested, THE system SHALL preserve declared source-native observations via an applicable adapter without requiring OCR."
---

# Adapters

An adapter result is separate from document validity. One page may combine text glyphs, raster images, vector shapes and OCR observations. Each observation has its own provenance. Source carrier is not a binary native/scanned class. Format-specific adapters are optional modules; structured JSON is the mandatory baseline adapter. PDF native and EPUB adapter execution is not claimed.

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| dispatch | invariant | `select one applicable adapter by declared format and version; do not conjoin mutually exclusive carrier rules` | [[document.adapters]] |
| pdf | invariant | `PDF observation types include page, glyph, raster, vector and annotations; per-observation source evidence` | [[document.adapters]] |
| epub | invariant | `EPUB observation types include manifest, XHTML tree, spine sequence with linear flag, navigation and links; no fabricated page geometry` | [[document.adapters]] |
| structured | invariant | `JSON observation import is required baseline; HTML, Markdown, CSV adapters are optional independently declared profiles` | [[document.adapters]] |
| preservation | invariant | `each adapter declares capabilities/preserved fields and omitted/approximated fields` | [[document.adapters]] |
| replay | invariant | `adapter result records source sha256, id, version, configuration digest and dependencies or explicit unavailable fingerprint` | [[document.adapters]] |
| failure | invariant | `unsupported, error, and ambiguous are typed results; partial output never masquerades as complete` | [[document.adapters]] |

## DSC 0.3 proposed constraints (design-only; implementation pending)

**Version scoping:** Original Constraints/Model/Properties above/below document the v0.2 baseline. Where incompatible (notably one global root or unscoped ordering), the v0.3 rules in this section and `CONTRACT.md` supersede them for 0.3 descriptors; v0.2 validation remains unchanged.


| id | kind | expr | traces_to |
|---|---|---|---|
| coverage_manifest | invariant | `adapter capabilities and per-feature preserved/transformed/approximated/omitted/unsupported/unexamined statuses are explicit and versioned` | [[document.adapters]] |
| coordinates | invariant | `any geometry frame specifies units, origin, axes, scale, rotation and crop mapping in a declared profile` | [[document.adapters]] |
| source_selectors | invariant | `PDF and EPUB source anchors use carrier-specific registered selector profiles; no implicit offset conventions` | [[document.adapters]] |
| partial_results | invariant | `valid JSON is not proof of complete source observation; partial result carries coverage and loss report` | [[document.adapters]] |

## Model

### States
- `received`
- `observed`
- `unsupported`
- `ambiguous`
- `failed`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| extract | received | observed | `adapter_selected AND extraction_complete AND applicable_preservation_checks_pass` |
| unsupported | received | unsupported | `no_matching_adapter OR blocked_encryption` |
| defer | received | ambiguous | `multiple_incompatible_observations` |
| fail | received | failed | `adapter_error OR malformed_input` |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| check_1 | unit | [[document.adapters.dispatch]] | `fixtures/valid/mixed-pdf.json` | `validate == valid` |
| check_2 | unit | [[document.adapters.epub]] | `fixtures/valid/epub.json` | `validate == valid AND no_fixed_page_geometry` |
| check_3 | unit | [[document.adapters.structured]] | `fixtures/valid/two-regions.json` | `validate == valid` |
| check_4 | unit | [[document.adapters.failure]] | `fixtures/results/unsupported.json` | `result_status == unsupported` |

## Notes

Adapter fixture descriptors are manually authored representative outputs, NOT extracted from verified PDF/EPUB binaries. Raw extraction correctness remains UNKNOWN until genuine carrier fixtures are supplied.

## DSC 0.3 conformance note

These additions refer to the proposed [0.3 contract](../CONTRACT.md). Existing `check_*` rows exercise **0.2 only**. See [acceptance matrix](../ACCEPTANCE.md) for unimplemented tests.
