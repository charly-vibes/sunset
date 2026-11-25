---
id: document.conformance.layer
kind: intent
statement: "WHEN instance outcomes, suite readiness and lint results are reported, THE conformance reporting rules SHALL keep each level separate and typed, keep every gap visible as incomplete rather than passed, and pin every cross-extractor comparison to declared projections, oracles and comparators, never silently resolving ambiguity."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| separated_levels | invariant | `Specodelic lint, instance validation and suite conformance are reported as separate statuses; a lint pass never implies a conformance pass` | [[document.conformance.layer]] |
| typed_reasons | invariant | `Every negative fixture validation produces a stable typed reason, such as dangling_reference, instead of an untyped error` | [[document.conformance.layer]] |
| gaps_stay_visible | invariant | `Every missing carrier fixture and independent implementation stays explicitly visible; incomplete never becomes passed` | [[document.conformance.layer]] |
| full_requires_carriers | invariant | `Full suite status is reached only with a real scanned PDF, a real text PDF, an EPUB and an independent nonperiodical input present` | [[document.conformance.layer]] |
| reader_independence | invariant | `Full conformance requires two independently implemented readers whose canonical bytes match exactly, preserving ids, array order and exact non-NFC text, plus a declared comparison of extractor outputs` | [[document.conformance.layer]] |
| pinned_comparison | invariant | `Extractor outputs are compared only under a projection and comparator pinned by identifier, version, artifact digest, source digest, implementation versions, configuration fingerprints, tested subset, expected observations, renderer/tolerance and unresolved-case policy` | [[document.conformance.layer]] |
| anchored_matching | invariant | `Entities are matched only by resolved source anchors or independently reviewed explicit mappings; alternative interpretations are retained as attributed sets with listed losses, and ambiguity stays unresolved` | [[document.conformance.layer]] |
| complete_comparator_report | invariant | `A case passes only when the comparator reports per-observable matches, false positives, false negatives and unresolved cases against reviewed expectations; missing projection, oracle, scope or tolerance leaves it incomplete` | [[document.conformance.layer]] |
| explained_rerun_divergence | invariant | `Pinned reruns report equality or explained divergence and never claim deterministic reproduction` | [[document.conformance.layer]] |
| epub_no_fixed_coordinates | invariant | `EPUB descriptors impose no obligatory fixed coordinates; spine order, non-linear entries and navigation remain distinct and validate as valid` | [[document.conformance.layer]] |
| suite_status_transitions | invariant | `Suite status moves from unexamined to passed (all required checks executed and passing), failed (any executed required check fails) or incomplete (required checks missing without executed failures)` | [[document.conformance.layer]] |
| demo_requires_real_carrier | invariant | `Demonstrated adoption value is claimable only after evaluating a historical-periodical review workflow on one real multi-page issue with columns, continuation, native/OCR disagreement and a deliberately unsupported or unexamined feature; otherwise it stays unproven` | [[document.conformance.layer]] |
| annotations_before_extraction | invariant | `Independent annotations are prepared before extraction results are viewed, disagreements retained, and the narrower demo is never reported as release conformance` | [[document.conformance.layer]] |
| demo_publication_set | invariant | `The evaluation publishes source/license/digest, selected observations, reviewer tasks, native-output baseline, pinned configurations, output artifacts and raw results before adoption value is claimable` | [[document.conformance.layer]] |
| oracle_precedes_extraction | invariant | `The reference set resolves every expected-resolvable observation to its correct source fragment before evaluation, predeclares allowed unresolved cases, verifies zero incorrect anchors, and all seeded disagreements and omissions survive export/import; dropping any one is a functional failure` | [[document.conformance.layer]] |
| measured_against_native | invariant | `Review time, correct decisions, descriptor bytes and peak memory are measured against the same tasks on native extractor outputs; unsupported benefit claims are prohibited` | [[document.conformance.layer]] |

## Model

### States
- `levels_reported`
- `gaps_assessed`
- `comparison_pinned`
- `matching_performed`
- `outcomes_reported`
- `demo_gated`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| report_levels | levels_reported | gaps_assessed | lint, instance validation and suite statuses are reported separately with typed reasons for negative fixtures [[document.conformance.layer.separated_levels]] [[document.conformance.layer.typed_reasons]] |
| assess_gaps | gaps_assessed | comparison_pinned | missing carriers, implementations and fixture inventory remain visible and suite status follows the unexamined/passed/failed/incomplete transitions [[document.conformance.layer.gaps_stay_visible]] [[document.conformance.layer.full_requires_carriers]] [[document.conformance.layer.suite_status_transitions]] [[document.conformance.layer.epub_no_fixed_coordinates]] |
| pin_comparison | comparison_pinned | matching_performed | projection and comparator pins are declared and readers are independent with byte-identical canonical output [[document.conformance.layer.pinned_comparison]] [[document.conformance.layer.reader_independence]] |
| match_entities | matching_performed | outcomes_reported | matching uses resolved anchors or reviewed mappings with alternatives retained and rerun divergence explained [[document.conformance.layer.anchored_matching]] [[document.conformance.layer.explained_rerun_divergence]] |
| report_outcomes | outcomes_reported | demo_gated | comparator reports are complete against reviewed expectations [[document.conformance.layer.complete_comparator_report]] |
| gate_demo | demo_gated | demo_gated | the demonstration ran on a real carrier with pre-extraction annotations, a full publication set, a resolvable reference oracle and native-output measurements [[document.conformance.layer.demo_requires_real_carrier]] [[document.conformance.layer.annotations_before_extraction]] [[document.conformance.layer.demo_publication_set]] [[document.conformance.layer.oracle_precedes_extraction]] [[document.conformance.layer.measured_against_native]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| lint_not_conformance | unit | [[document.conformance.layer.separated_levels]] | `lint_pass_missing_suite_checks()` | suite status is incomplete, never passed, when required suite checks are missing |
| typed_negative_reasons | unit | [[document.conformance.layer.typed_reasons]] | `dangling_reference_fixture()` | validating the dangling descriptor yields an error containing dangling_reference |
| gap_visibility | unit | [[document.conformance.layer.gaps_stay_visible]] | `coverage_with_missing_carriers()` | coverage.json lists missing real PDF, real EPUB and independent reader entries explicitly |
| carrier_gate | unit | [[document.conformance.layer.full_requires_carriers]] | `synthetic_json_only_suite()` | a suite with only synthetic JSON fixtures reports incomplete |
| canonical_reader_bytes | unit | [[document.conformance.layer.reader_independence]] | `two_reader_same_snapshot()` | both readers emit identical canonical bytes preserving ids, array order and non-NFC text |
| comparison_requires_pin | unit | [[document.conformance.layer.pinned_comparison]] | `unpinned_extractor_comparison()` | evaluating extractor outputs without a pinned projection and comparator yields incomplete, not pass |
| no_arbitrary_pairing | unit | [[document.conformance.layer.anchored_matching]] | `competing_interpretation_outputs()` | opposing allowed orders are retained with attribution and snapshot-local ids or label similarity never drive a match |
| comparator_report_totality | unit | [[document.conformance.layer.complete_comparator_report]] | `comparison_omitting_false_positives()` | a comparison omitting false positives, false negatives or unresolved cases is incomplete |
| rerun_explains_divergence | unit | [[document.conformance.layer.explained_rerun_divergence]] | `diverging_pinned_rerun()` | a diverging pinned rerun reports the divergence with an explanation and no determinism claim |
| epub_flow_validity | unit | [[document.conformance.layer.epub_no_fixed_coordinates]] | `epub_descriptor_fixture()` | fixtures/valid/epub.json validates as valid without fixed-coordinate obligations |
| suite_transition_closedness | unit | [[document.conformance.layer.suite_status_transitions]] | `suite_with_missing_required_checks()` | no executed failure with missing required checks yields exactly incomplete |
| unproven_without_demo | unit | [[document.conformance.layer.demo_requires_real_carrier]] | `spec_only_adoption_claim()` | adoption value stays unproven when no real carrier demonstration and native baseline exist |
| annotation_ordering_gate | unit | [[document.conformance.layer.annotations_before_extraction]] | `annotations_after_extraction_run()` | annotations prepared after viewing extraction fail the independent-annotation gate |
| publication_set_completeness | unit | [[document.conformance.layer.demo_publication_set]] | `evaluation_missing_raw_results()` | an evaluation omitting pinned configurations, artifacts or raw results cannot claim adoption value |
| oracle_resolvability | unit | [[document.conformance.layer.oracle_precedes_extraction]] | `undeclared_unresolved_observation()` | an unpredeclared unresolved observation marks the demonstration a functional failure |
| native_baseline_measurement | unit | [[document.conformance.layer.measured_against_native]] | `dsc_slower_review_metrics()` | increased measured review time permits traceability claims but forbids speed benefit claims |
