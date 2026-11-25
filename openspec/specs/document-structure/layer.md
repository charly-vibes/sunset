---
id: document.structure.layer
kind: intent
statement: "WHEN a DSC 0.2 descriptor organizes regions, THE structure layer SHALL separate physical containment, logical grouping, and reading sequence through typed views, exclusive ownership, scoped partial order, and declared realization — never collapsing alternatives into a silently chosen ordering."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| exact_view_shape | invariant | `Views have exactly id, kind (physical, logical, carrier) and root with at least one logical view; regions reference views by view_id and only physical regions carry geometry` | [[document.structure.layer]] |
| exclusive_containment | invariant | `Containment ownership is enforced per named view per document-core's tree integrity; different segmentations use different views, never contradictory ownership in one tree` | [[document.structure.layer]] |
| scoped_partial_order | invariant | `Reading order arises only from precedes reachability inside one interpretation; each precedes carries interpretation_id, no other relation may, the interpretation is reading-order and its view matches both endpoints; uniqueness is (kind,from,to,interpretation_id) for precedes and (kind,from,to) otherwise` | [[document.structure.layer]] |
| physical_to_logical | invariant | `realizes connects physical to logical regions, including page continuation across physical placements` | [[document.structure.layer]] |
| shared_content_refs | invariant | `Multiple regions reference the same content id without duplicating content objects` | [[document.structure.layer]] |
| alternatives_kept | invariant | `Multiple alternative orderings persist as separate claims with no automatic winner selected` | [[document.structure.layer]] |
| tri_state_resolution | invariant | `Structure outcomes are resolved (valid, no unresolved alternatives), ambiguous (valid but unresolved alternatives exist), or invalid (structure not valid)` | [[document.structure.layer]] |
| interpretation_shape | invariant | `Interpretations have exactly id, kind (reading-order, segmentation), view_id, origin, status, evidence; evidence references resolve, supported requires at least one and asserted_without_evidence none; competing interpretations coexist without automatic winner` | [[document.structure.layer]] |
| declared_linearization | invariant | `A total-order export declares its interpretation id and named versioned deterministic policy, reports incomparable regions, never writes tie-break edges back as observed order, and leaves EPUB navigation profile-defined` | [[document.structure.layer]] |
| profiled_alignment | invariant | `realizes allows many-to-many placements; fine-grained alignment requires selectors bound by the annotation's declared alignment_profile_id and selector_ids, and no universal alignment is inferred from unprofiled strings` | [[document.structure.layer]] |

## Model

### States
- `views_declared`
- `ownership_checked`
- `order_scoped`
- `realizations_bound`
- `outcomes_classified`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| declare_views | views_declared | views_declared | view objects are exactly shaped, at least one logical view exists, and geometry appears only on physical regions [[document.structure.layer.exact_view_shape]] |
| check_ownership | views_declared | ownership_checked | each view's containment tree satisfies integrity with segmentations separated into distinct views [[document.structure.layer.exclusive_containment]] |
| scope_order | ownership_checked | order_scoped | every precedes names a reading-order interpretation whose view matches both endpoints and no other relation carries interpretation_id [[document.structure.layer.scoped_partial_order]] |
| bind_realizations | order_scoped | realizations_bound | realizes edges run physical to logical and shared content ids resolve without duplication [[document.structure.layer.physical_to_logical]] [[document.structure.layer.shared_content_refs]] |
| keep_alternatives | realizations_bound | realizations_bound | competing interpretations and alternative orderings coexist with no automatic winner [[document.structure.layer.alternatives_kept]] [[document.structure.layer.interpretation_shape]] |
| classify_outcome | realizations_bound | outcomes_classified | structure validity and unresolved alternatives map to resolved, ambiguous, or invalid [[document.structure.layer.tri_state_resolution]] |
| audit_export | outcomes_classified | outcomes_classified | a total-order export names interpretation and policy, reports incomparable regions, and writes no tie-back edges [[document.structure.layer.declared_linearization]] |
| check_alignment | realizations_bound | realizations_bound | character-level alignment claims exist only under a declared alignment profile bound to paired selector ids [[document.structure.layer.profiled_alignment]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| carrier_view_isolated | unit | [[document.structure.layer.exact_view_shape]] | `epub_carrier_fixture()` | a carrier view preserves the EPUB resource tree with its own root and implies no page geometry |
| per_view_tree_integrity | unit | [[document.structure.layer.exclusive_containment]] | `competing_segmentations_fixture()` | two segmentations of one article validate as independent views each with a valid containment tree |
| duplicate_edges_rejected | unit | [[document.structure.layer.scoped_partial_order]] | `repeated_precedes_fixture()` | the same edge in two interpretations is valid while a repeat in one interpretation is duplicate_edge |
| continuation_realized | unit | [[document.structure.layer.physical_to_logical]] | `page_continuation_fixture()` | a page-continuation descriptor with realizes placements validates |
| content_shared_not_copied | unit | [[document.structure.layer.shared_content_refs]] | `shared_content_fixture()` | a shared content id resolves for every referencing region with no duplicate content object |
| disputed_orders_preserved | unit | [[document.structure.layer.alternatives_kept]] | `disputed_structure_fixture()` | disputed claims survive as separate annotations with no winner chosen |
| ambiguity_not_resolved | unit | [[document.structure.layer.tri_state_resolution]] | `unresolved_alternatives_fixture()` | valid structure with unresolved alternatives yields ambiguous, never a silently chosen ordering |
| unsupported_interpretation_typed | unit | [[document.structure.layer.interpretation_shape]] | `evidenceless_interpretation_fixture()` | a reading-order interpretation without evidence may be asserted_without_evidence but cannot be supported |
| export_policy_named | unit | [[document.structure.layer.declared_linearization]] | `incomparable_export_fixture()` | an export of a total order over incomparable regions names policy and incomparables, and an undeclared export is invalid independent of descriptor validity |
| unprofiled_alignment_unclaimed | unit | [[document.structure.layer.profiled_alignment]] | `region_only_realizes_fixture()` | a consumer with only region-level realizes edges may use placements but cannot claim character alignment |
