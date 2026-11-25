---
id: document.evidence.layer
kind: intent
statement: "WHEN an observation or semantic claim is recorded, THE evidence layer SHALL retain typed origin, resolvable bindings, replayable transformation lineage, and honest uncertainty so every claim is verifiable, disputed, or explicitly unverifiable — never silently invented support."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| resolvable_targets | invariant | `Every claim target and supplied evidence reference resolves, even when the claim is asserted_without_evidence; that status permits an empty evidence array but never a dangling target or reference` | [[document.evidence.layer]] |
| complete_bindings | invariant | `Each evidence object retains id, origin, source_ref, optional transform and declares mandatory unique content_ids and selector_ids; an opaque source_ref alone is never treated as a verified source anchor` | [[document.evidence.layer]] |
| typed_origins | invariant | `Every recorded claim carries exactly one of the five typed origins: source, extracted, inferred, manual, external` | [[document.evidence.layer]] |
| exact_replay_material | invariant | `A transform has exactly id, version, config_sha256, dependencies, inputs, outputs; inputs/outputs are nonempty, distinct, disjoint; outputs equal the record's content_ids as a set; missing replay material cannot be labeled reproducible` | [[document.evidence.layer]] |
| producer_uniqueness | invariant | `Each content participating in a transform has exactly one producing evidence record, and derived-from edges equal the set of input producers` | [[document.evidence.layer]] |
| acyclic_lineage | invariant | `The derived-from relation graph contains no cycles` | [[document.evidence.layer]] |
| disputed_preserved | invariant | `Unresolved competing claims stay separate with status disputed and no automatic precedence is applied` | [[document.evidence.layer]] |
| no_invented_confidence | invariant | `Confidence is never invented; missing replay material is distinguishable from conflict` | [[document.evidence.layer]] |
| honest_status_transition | invariant | `A recorded claim moves to supported only with sufficient non-conflicting support and replay material; disputed with conflicting support; unverifiable when no conflict but support or replay material is missing` | [[document.evidence.layer]] |
| structural_edge_evidence | invariant | `Structural edges allow optional resolvable evidence id arrays; missing or empty evidence reports unverified, and derived-from never carries evidence` | [[document.evidence.layer]] |
| selector_shape | invariant | `Selectors have exactly id, kind, profile_id, source_sha256, target, locator with a kind from the allowed set, a resolvable target and a nonempty locator, all bounded by the declared profile's rules` | [[document.evidence.layer]] |
| digest_pinning | invariant | `An internal selector's source_sha256 equals the descriptor source digest; an external selector pins the external resource's digest rather than trusting its URI` | [[document.evidence.layer]] |
| profiled_text_ranges | invariant | `A text-range target is text content whose profile declares offset unit, endpoint convention and Unicode segmentation version; offsets index the exact target value without normalization` | [[document.evidence.layer]] |
| typed_selector_outcomes | invariant | `Range boundaries are in bounds and respect declared units; malformed locators or ranges yield invalid_selector, missing profile references dangling_reference, unavailable declared profiles unsupported_profile` | [[document.evidence.layer]] |
| distinct_text_snapshots | invariant | `Native, OCR, corrected and normalized text stay distinct content objects whenever code-point sequences differ; normalization is an explicit bound transform, never part of canonical serialization, and selectors measure the exact original snapshot` | [[document.evidence.layer]] |
| paired_alignment_fields | invariant | `Alignment annotations carry alignment_profile_id and selector_ids together, never one alone; the profile defines arity, endpoint roles, pairing, targets and verification without new core relation kinds` | [[document.evidence.layer]] |

## Model

### States
- `claim_recorded`
- `bindings_resolved`
- `lineage_bound`
- `status_classified`
- `selectors_validated`
- `snapshots_distinguished`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| resolve_targets | claim_recorded | bindings_resolved | every claim target and evidence reference resolves, including asserted_without_evidence claims [[document.evidence.layer.resolvable_targets]] [[document.evidence.layer.complete_bindings]] |
| type_origin | claim_recorded | bindings_resolved | the claim carries one of the five typed origins [[document.evidence.layer.typed_origins]] |
| bind_transform | bindings_resolved | lineage_bound | replay material is exactly shaped, outputs equal content_ids, and each input has its producer edge [[document.evidence.layer.exact_replay_material]] [[document.evidence.layer.producer_uniqueness]] |
| check_acyclic | lineage_bound | lineage_bound | the derived-from graph admits no cycle [[document.evidence.layer.acyclic_lineage]] |
| classify_status | lineage_bound | status_classified | support, conflict, and replay availability map to supported, disputed, or unverifiable without invented confidence [[document.evidence.layer.honest_status_transition]] [[document.evidence.layer.no_invented_confidence]] [[document.evidence.layer.disputed_preserved]] |
| verify_edges | status_classified | status_classified | structural edges report unverified without evidence and derived-from carries none [[document.evidence.layer.structural_edge_evidence]] |
| validate_selectors | bindings_resolved | selectors_validated | selectors match the exact shape, profile-bounded kinds, pinned digests, and typed outcome codes [[document.evidence.layer.selector_shape]] [[document.evidence.layer.digest_pinning]] [[document.evidence.layer.typed_selector_outcomes]] |
| measure_ranges | selectors_validated | selectors_validated | text-range offsets follow the profile's unit, endpoint, and segmentation declarations on the exact target value [[document.evidence.layer.profiled_text_ranges]] |
| distinguish_snapshots | selectors_validated | snapshots_distinguished | differing code-point sequences survive as distinct objects with normalization as an explicit transform [[document.evidence.layer.distinct_text_snapshots]] |
| bind_alignment | snapshots_distinguished | snapshots_distinguished | alignment annotations pair profile id and selector ids, verified only under the declared profile [[document.evidence.layer.paired_alignment_fields]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| no_dangling_targets | unit | [[document.evidence.layer.resolvable_targets]] | `unsupported_claim_fixture()` | an asserted_without_evidence annotation naming a missing target is invalid with dangling_reference |
| traceable_source_binding | unit | [[document.evidence.layer.complete_bindings]] | `source_evidence_binding_fixture()` | content c0 and selector s0 both resolve and the dangling binding is rejected |
| origin_in_enum | unit | [[document.evidence.layer.typed_origins]] | `recorded_claim_corpus()` | every recorded claim's origin is one of the five typed values |
| replay_shape_exact | unit | [[document.evidence.layer.exact_replay_material]] | `native_to_corrected_to_normalized_fixture()` | transform inputs/outputs identify the exact chained content ids and any missing replay material cannot be labeled reproducible |
| single_producer_per_content | unit | [[document.evidence.layer.producer_uniqueness]] | `broken_lineage_fixture()` | a missing producer, self-input output, or non-input declared parent fails with invalid_transform_binding |
| lineage_has_no_cycles | unit | [[document.evidence.layer.acyclic_lineage]] | `lineage_cycle_fixture()` | validating a cyclic lineage descriptor reports lineage_cycle |
| disputes_coexist | unit | [[document.evidence.layer.disputed_preserved]] | `disputed_claims_fixture()` | the disputed descriptor validates and statuses include disputed with no winner applied |
| uncertainty_typed | unit | [[document.evidence.layer.no_invented_confidence]] | `unsupported_manual_assertion_fixture()` | a claim lacking support or replay material without conflict yields unverifiable, never disputed or supported |
| status_matches_support | unit | [[document.evidence.layer.honest_status_transition]] | `support_matrix_corpus()` | each recorded claim's status equals the outcome implied by its support, conflict, and replay availability |
| unverified_edges_reported | unit | [[document.evidence.layer.structural_edge_evidence]] | `bare_structural_edge_fixture()` | a structural edge without evidence references is reported unverified and derived-from rejects evidence |
| selector_kind_bounded | unit | [[document.evidence.layer.selector_shape]] | `profile_mismatched_selector_fixture()` | a selector kind outside its profile's allowed set fails under the profile's declared rules |
| external_digest_pinned | unit | [[document.evidence.layer.digest_pinning]] | `unpinned_external_selector_fixture()` | an external selector trusting its URI without a pinned digest is invalid |
| offset_units_respected | unit | [[document.evidence.layer.profiled_text_ranges]] | `scalar_vs_byte_range_fixture()` | a scalar half-open [1,2) selects é in AéB while a byte profile requires [1,3) |
| selector_codes_typed | unit | [[document.evidence.layer.typed_selector_outcomes]] | `malformed_range_fixture()` | a reversed or out-of-bounds range under a resolved profile returns invalid_selector |
| normalization_explicit | unit | [[document.evidence.layer.distinct_text_snapshots]] | `nfc_transform_pair_fixture()` | U+0065 U+0301 and U+00E9 snapshots survive separately with per-snapshot scalar ranges uninterchanged |
| alignment_pairs_declared | unit | [[document.evidence.layer.paired_alignment_fields]] | `four_selector_alignment_fixture()` | only the profile-declared ordered pairs align, not the Cartesian product, and one-field annotations are rejected |
