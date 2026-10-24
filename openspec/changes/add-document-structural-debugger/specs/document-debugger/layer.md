---
id: document.debugger.layer
kind: intent
statement: "WHEN a reader inspects a DSC description with a source document, THE document debugger SHALL show structural regions, evidence and typed diagnostics using stable source locators without mutating the source or requiring OCR for native documents."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| read_only | invariant | `Inspection does not alter input descriptor or source bytes` | [[document.debugger.layer]] |
| carrier_locators | invariant | `PDF geometry and EPUB stable selectors use declared carrier-specific coordinate domains; transient viewport coordinates are never persistent EPUB identity` | [[document.debugger.layer]] |
| bidirectional_navigation | invariant | `A region selection resolves to all available source loci and evidence; missing or multiple matches are explicitly reported` | [[document.debugger.layer]] |
| scoped_structure | invariant | `Containment, reading order, overlap and alternative structural views are displayed without inventing a total order` | [[document.debugger.layer]] |
| typed_diagnostics | invariant | `Check results distinguish validated violation, review/dispute, unsupported and unexamined; every violation links to its rule and smallest available witness` | [[document.debugger.layer]] |
| evidence_truth_boundary | invariant | `Human or extractor annotations are attributed claims and not automatically semantically true` | [[document.debugger.layer]] |
| accessibility | invariant | `All inspector actions are keyboard operable with non-color status labels` | [[document.debugger.layer]] |

## Model

### States
- `unloaded`
- `loaded`
- `inspecting`
- `diagnostic_selected`
- `unsupported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| load | unloaded | loaded | input references parse and source/descriptor hashes recorded [[document.debugger.layer.read_only]] |
| inspect | loaded | inspecting | selected view and locator domain declared [[document.debugger.layer.carrier_locators]] [[document.debugger.layer.scoped_structure]] |
| select_diagnostic | inspecting | diagnostic_selected | diagnostic has a stable code and scoped source or graph witness [[document.debugger.layer.typed_diagnostics]] [[document.debugger.layer.bidirectional_navigation]] [[document.purpose.layer.scoped_evidence_and_loss]] |
| unsupported_source | loaded | unsupported | source carrier or locator unsupported with classified reason [[document.debugger.layer.typed_diagnostics]] |
| return_to_inspection | diagnostic_selected | inspecting | inspection state retained [[document.debugger.layer.accessibility]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| unchanged_bytes | unit | [[document.debugger.layer.read_only]] | `frozen_descriptor_source()` | `sha256(input_before) == sha256(input_after)` |
| pdf_epub_no_ocr | unit | [[document.debugger.layer.carrier_locators]] | `native_pdf_and_epub_samples()` | `inspection succeeds with OCR disabled; anchors persist after zoom or reflow` |
| ambiguous_selector | unit | [[document.debugger.layer.bidirectional_navigation]] | `two_matching_selector_targets()` | `ambiguity reported and neither target auto-selected` |
| partial_order | unit | [[document.debugger.layer.scoped_structure]] | `two_legal_topological_sorts()` | `view preserves partial order; display sort not asserted as unique` |
| witnessed_failure | unit | [[document.debugger.layer.typed_diagnostics]] | `cycle_and_bad_reference_fixtures()` | `correct stable rule IDs and minimal available witness emitted` |
| no_truth_inference | unit | [[document.debugger.layer.evidence_truth_boundary]] | `two_conflicting_extractor_claims()` | `both claims retained with attribution and no automatic winner` |
| keyboard_navigation | unit | [[document.debugger.layer.accessibility]] | `keyboard_only_selection_flow()` | `every inspected detail reachable without pointer` |
