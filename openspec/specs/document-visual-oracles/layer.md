---
id: document.visual.oracles.layer
kind: intent
statement: "WHEN raster-based visual oracles validate extracted observations, THE visual oracle rules SHALL pin renders and coordinate frames, label every result with an evidence class and one evaluated property, stay calibrated before gating anything, and retain disagreements without electing winners or substituting for reader agreement."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| pinned_render | invariant | `Every oracle render records renderer name, version, DPI, page selection and binarization; identical configurations reproduce byte-identical renders; an unavailable renderer yields typed unavailable instead of skipping` | [[document.visual.oracles.layer]] |
| declared_frame | invariant | `Pixel coordinates map to descriptor geometry only through a declared geometry profile frame; incompatible, missing or ambiguous frames produce unknown, never agree or differ` | [[document.visual.oracles.layer]] |
| labeled_evidence_class | invariant | `Every oracle result carries correlated or independent evidence class; correlated results never support accuracy claims and demonstrate sensitivity only` | [[document.visual.oracles.layer]] |
| scoped_property_claims | invariant | `Each oracle declares and reports the single property it evaluates; a pass never establishes text correctness, reading order, semantic grouping or visual completeness` | [[document.visual.oracles.layer]] |
| mutation_validated_sensitivity | invariant | `Each claimed defect class is demonstrated by seeded mutations on pinned carriers; properties without such a demonstration stay uncalibrated and gate no decision, including conformance labeling, demonstration-suite acceptance and aggregate outcomes` | [[document.visual.oracles.layer]] |
| calibrated_thresholds | invariant | `Thresholds come from recorded calibration over varied pinned carriers; outcomes are reported per page and per property as agree/differ/unknown/unavailable; no aggregate reports pass while any page is unknown or unavailable or its property uncalibrated` | [[document.visual.oracles.layer]] |
| no_silent_resolution | invariant | `Visual disagreements are retained and attributed to their source regions; no oracle elects a winner, smooths differences or mutates extracted observations` | [[document.visual.oracles.layer]] |
| distinct_evidence_record | invariant | `Visual oracle results are recorded separately from reader agreement, extractor comparison and reviewed anchor mapping and never substitute for any of them in conformance labels or demonstration suites` | [[document.visual.oracles.layer]] |
| renderable_carriers_only | invariant | `Oracles apply only to carriers with renderable pages; formats the pinned renderer cannot rasterize report unknown` | [[document.visual.oracles.layer]] |

## Model

### States
- `render_pinned`
- `frame_mapped`
- `comparison_run`
- `results_classified`
- `aggregate_reported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| record_configuration | render_pinned | frame_mapped | renderer, version, DPI, page selection and binarization are recorded and unavailable renderers yield typed unavailable [[document.visual.oracles.layer.pinned_render]] [[document.visual.oracles.layer.renderable_carriers_only]] |
| map_frames | frame_mapped | comparison_run | every compared region references a declared, compatible and unambiguous geometry frame [[document.visual.oracles.layer.declared_frame]] |
| run_comparison | comparison_run | results_classified | thresholds are calibrated and disagreements are retained with region attribution [[document.visual.oracles.layer.calibrated_thresholds]] [[document.visual.oracles.layer.no_silent_resolution]] |
| classify_results | results_classified | aggregate_reported | every result carries its evidence class and single evaluated property, and claimed defect classes have mutation demonstrations [[document.visual.oracles.layer.labeled_evidence_class]] [[document.visual.oracles.layer.scoped_property_claims]] [[document.visual.oracles.layer.mutation_validated_sensitivity]] |
| audit_substitution | aggregate_reported | aggregate_reported | oracle results are recorded separately and never substitute for readers, extractor comparison or anchor mapping in labels [[document.visual.oracles.layer.distinct_evidence_record]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| render_determinism | unit | [[document.visual.oracles.layer.pinned_render]] | `twice_rendered_page_config()` | two renders from one recorded configuration produce identical bytes and a missing renderer yields unavailable |
| unknown_without_frame | unit | [[document.visual.oracles.layer.declared_frame]] | `region_without_geometry_frame()` | a region referencing no declared frame compares as unknown, never agree or differ |
| correlated_never_accuracy | unit | [[document.visual.oracles.layer.labeled_evidence_class]] | `shared_pymupdf_extraction_and_render()` | a shared-lineage result is labeled correlated and records no accuracy claim |
| single_property_scope | unit | [[document.visual.oracles.layer.scoped_property_claims]] | `ink_coverage_pass_wrong_order_page()` | a coverage pass on a wrongly ordered page records the coverage property while reading order stays unestablished |
| uncalibrated_gates_nothing | unit | [[document.visual.oracles.layer.mutation_validated_sensitivity]] | `omission_claim_without_seed_demo()` | a property claiming omission detection without a seeded demonstration stays uncalibrated and gates no decision |
| aggregate_never_false_pass | unit | [[document.visual.oracles.layer.calibrated_thresholds]] | `degraded_scan_page_outcome()` | an aggregate over an unknown page reports no pass |
| disagreement_retention | unit | [[document.visual.oracles.layer.no_silent_resolution]] | `mask_disagreement_fixture()` | a mask disagreement is retained with region identifiers and neither reading is replaced |
| oracle_not_suite_completing | unit | [[document.visual.oracles.layer.distinct_evidence_record]] | `oracle_pass_without_readers_suite()` | a suite with passing oracles but no independent readers stays labeled incomplete |
| nonrasterizable_unknown | unit | [[document.visual.oracles.layer.renderable_carriers_only]] | `epub_under_pinned_renderer()` | an EPUB carrier the pinned renderer cannot rasterize reports unknown |
