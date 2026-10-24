---
id: document.purpose.layer
kind: intent
statement: "WHEN systems exchange document descriptions, THE DSC substrate SHALL provide a deterministic, carrier-independent structural contract with explicit evidence and scoped loss, SHALL support domain extensions without redefining core meaning, and SHALL treat extraction reconciliation as a consumer rather than its defining purpose."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| carrier_neutral | invariant | `A descriptor's core structure is not defined in terms of OCR output or fixed pagination; native PDF and reflowable EPUB are first-class carriers` | [[document.purpose.layer]] |
| purpose_consumer_separation | invariant | `Extraction reconciliation is one possible DSC consumer; acceptance of that consumer alone never proves general document-interchange conformance` | [[document.purpose.layer]] |
| three_distinctions | invariant | `Descriptions distinguish carrier observations, logical structure, and attributed interpretation without requiring all three or imposing a single extraction sequence` | [[document.purpose.layer]] |
| scoped_evidence_and_loss | invariant | `Every claimed preservation guarantee has an explicit scope, source evidence or declared limitation; unexamined and unsupported are not silently considered preserved` | [[document.purpose.layer]] |
| extensibility_without_core_redefinition | invariant | `Versioned extension vocabularies may describe articles, postings or poems but never redefine core relationship semantics, source identity or canonicalization` | [[document.purpose.layer]] |
| independent_exchange | invariant | `General conformance requires at least two independently implemented consumers to agree on declared observables for neutral multi-carrier fixtures; shared-schema lint alone is insufficient` | [[document.purpose.layer]] |

## Model

### States
- `purpose_declared`
- `contract_mapped`
- `fixtures_tested`
- `independent_conformance_demonstrated`
- `scope_limited`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| map_contract | purpose_declared | contract_mapped | `mapping from required document roles to current DSC wire and profile contracts has been recorded` [[document.purpose.layer.three_distinctions]] [[document.purpose.layer.extensibility_without_core_redefinition]] |
| test_fixtures | contract_mapped | fixtures_tested | `native PDF and EPUB and scanned and non-periodical fixture oracles have recorded results` [[document.purpose.layer.carrier_neutral]] [[document.purpose.layer.scoped_evidence_and_loss]] |
| prove_exchange | fixtures_tested | independent_conformance_demonstrated | `two independent readers agree within the declared observable scope and report all losses` [[document.purpose.layer.independent_exchange]] |
| state_limit | fixtures_tested | scope_limited | `an unsupported or disputed case is recorded and no generality claim is issued` [[document.purpose.layer.purpose_consumer_separation]] |
| refuse_mapping | purpose_declared | scope_limited | `no defensible mapping from required document roles to current DSC contracts exists; the limitation is recorded and no contract conformance is claimed` [[document.purpose.layer.three_distinctions]] |
| refuse_fixtures | contract_mapped | scope_limited | `a fixture oracle cannot be executed or its recorded result is disputed; the carrier gap is recorded and no preservation claim is issued` [[document.purpose.layer.carrier_neutral]] [[document.purpose.layer.scoped_evidence_and_loss]] |
| retest | scope_limited | purpose_declared | `new evidence or an explicit owner ruling invalidates the recorded limitation; the case re-enters the pipeline from declaration` [[document.purpose.layer.scoped_evidence_and_loss]] |

Refusal transitions (`refuse_mapping`, `refuse_fixtures`) give every failed step of the declared path a classified route into `scope_limited`, so a mapping or fixture failure can never strand the model without an outcome (rule-of-5 EDGE-002). `scope_limited` is deliberately not terminal: `retest` states the escalation semantics — only new evidence or an explicit owner ruling reopens a recorded limitation, and the case restarts from `purpose_declared` so previously recorded results are re-established rather than assumed (rule-of-5 EDGE-004).

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| native_pdf_no_ocr | unit | [[document.purpose.layer.carrier_neutral]] | `native_pdf_fixture_without_ocr()` | `descriptor structurally parses; no OCR prerequisite; preservation/loss reported` |
| epub_no_pages | unit | [[document.purpose.layer.carrier_neutral]] | `reflowable_epub_spine_fixture()` | `spine, navigation, links represented; no fabricated page rectangles` |
| independent_gate | law | [[document.purpose.layer.independent_exchange]] | `two_independent_consumers_on_neutral_fixtures()` | `**identity:** a consumer compared with itself agrees on all declared observables; **associativity:** agreement is transitive across consumer pairs within the declared observable scope; consumer-demo pass alone does not set general-conformant` |
| preserve_scope | unit | [[document.purpose.layer.scoped_evidence_and_loss]] | `document_with_unexamined_attachment()` | `unexamined remains explicit and is not reported preserved` |
| domain_extension | unit | [[document.purpose.layer.extensibility_without_core_redefinition]] | `magazine_and_finance_profiles()` | `same core types unchanged; domain labels namespaced` |
| consumer_not_definition | unit | [[document.purpose.layer.purpose_consumer_separation]] | `reviewer_only_acceptance_report()` | `no general-conformance claim is emitted when only consumer evidence exists` |
| layer_separation | unit | [[document.purpose.layer.three_distinctions]] | `hybrid_observation_structure_claim_fixture()` | `observation, structure and interpretation records remain separately addressable` |
