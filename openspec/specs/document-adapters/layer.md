---
id: document.adapters.layer
kind: intent
statement: "WHEN a source carrier is digitized, THE adapter layer SHALL dispatch through a declared adapter, preserve source-native observations with explicit provenance and honest coverage, and report typed outcomes, never letting partial output masquerade as complete or unexamined content pass as preserved."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| single_adapter_dispatch | invariant | `Exactly one applicable adapter is selected from the declared format and version, with mutually exclusive carrier rules never conjoined` | [[document.adapters.layer]] |
| pdf_observation_typing | invariant | `PDF observations are typed as page, glyph, raster, vector, or annotation, each carrying per-observation source evidence` | [[document.adapters.layer]] |
| epub_observation_typing | invariant | `EPUB observations cover manifest, XHTML tree, linear-flagged spine, navigation, and links without fabricated page geometry` | [[document.adapters.layer]] |
| json_baseline_mandatory | invariant | `Structured JSON import is always available as the baseline adapter while HTML, Markdown, and CSV remain optional declared profiles` | [[document.adapters.layer]] |
| preservation_declared | invariant | `An adapter result declares its capabilities, preserved fields, and omitted or approximated fields before it is accepted` | [[document.adapters.layer]] |
| replay_metadata_recorded | invariant | `An adapter result records source sha256, adapter id and version, configuration digest, and dependencies, or the literal unavailable fingerprint` | [[document.adapters.layer]] |
| typed_failure_results | invariant | `Unsupported, error, and ambiguous outcomes are reported as typed results and partial output never masquerades as complete` | [[document.adapters.layer]] |
| outcome_states_distinguished | invariant | `Every run outcome is exactly one of observed, unsupported, ambiguous, or failed, each bound to its defined trigger` | [[document.adapters.layer]] |
| inventory_independence | invariant | `Exactly one carrier-inventory and one adapter-manifest profile are declared for an adapter run, and the inventory is never shrunk to hide unsupported work` | [[document.adapters.layer]] |
| inventory_grammar | invariant | `The inventory artifact carries exactly version, source_format, and features, whose entries carry exactly name and scope_kind` | [[document.adapters.layer]] |
| minimum_inventory_per_format | invariant | `The inventory includes the minimum per-format feature set and may add features but never omit them` | [[document.adapters.layer]] |
| manifest_grammar | invariant | `The adapter manifest carries exactly version, adapter_id, adapter_version, source_format, and features, with versions matched, source_format aligned to the descriptor, and features inside the inventory` | [[document.adapters.layer]] |
| manifest_bounded_claims | invariant | `A preserved, transformed, or approximated claim names a manifest feature while omission, unsupported, and unexamined remain available for all inventory features` | [[document.adapters.layer]] |
| coverage_entry_identity | invariant | `A coverage entry carries exactly the nine declared fields with adapter identity matching the manifest and a 64-hex or unavailable config_sha256` | [[document.adapters.layer]] |
| single_run_entries | invariant | `All coverage entries in a descriptor describe one adapter run and one configuration, with additional runs in separate snapshots` | [[document.adapters.layer]] |
| scope_grammar | invariant | `A coverage scope is document, page:N (1-based, no leading zeros), or resource:PATH (exact case-sensitive archive path) matching its feature's scope kind` | [[document.adapters.layer]] |
| complete_enumeration | invariant | `Enumeration is checked against source bytes, collapsing to one * unexamined scope only when it cannot complete, never guessing a finite scope list` | [[document.adapters.layer]] |
| unique_dispositions | invariant | `Exactly one disposition exists per (inventory_id,feature,scope) with a status from the closed vocabulary and a nonempty reason except for preserved` | [[document.adapters.layer]] |
| precedence_least_preserving | invariant | `Mixed outcomes collapse to the least-preserving status by precedence unexamined > unsupported > omitted > approximated > transformed > preserved, for scopes and feature summaries alike` | [[document.adapters.layer]] |
| absence_honesty | invariant | `Summaries never replace per-scope entries or imply completeness outside the inventory, and preserved claims on absent features follow verified inspection only` | [[document.adapters.layer]] |
| declared_coordinate_frames | invariant | `Geometry references a named profile frame with units, origin, axes, transforms, and source binding, with subunit precision represented explicitly` | [[document.adapters.layer]] |
| partial_loss_accounting | invariant | `Reports retain all per-scope dispositions, profile digests, and enumeration results, and no aggregate claims preservation over an unexamined required scope` | [[document.adapters.layer]] |
| native_consumer_local | invariant | `Native PDF extraction runs locally from source and output paths alone, defaulting to all pages with recorded settings, honoring explicit one-based selection, without OCR, models, or network` | [[document.adapters.layer]] |
| native_source_mappings | invariant | `Each extracted word binds source SHA256, page, exact raw span, and a bounding box in a declared frame, with search tokens mapping back to raw spans under pinned profiles` | [[document.adapters.layer]] |
| native_repeatability | invariant | `Identical PDF bytes, selected pages, and pinned settings and dependencies produce byte-identical semantic artifacts with the envelope declared separately` | [[document.adapters.layer]] |
| native_partiality_honest | invariant | `The native route retains scoped unsupported and unexamined coverage, leaves textless pages unresolved, and fails explicitly without overwriting existing data` | [[document.adapters.layer]] |
| native_outcome_vocabulary | invariant | `Every native run reports exactly one of text-complete, text-with-gaps, or no-text-read, with non-text observations confined to coverage rows` | [[document.adapters.layer]] |
| exit_code_contract | invariant | `Exit 0 corresponds to text-complete, exit 2 to gap-bearing outcomes, and visual completeness is reported independently of the exit code` | [[document.adapters.layer]] |
| outcome_versioning | invariant | `Run manifests declare the outcome vocabulary version, and unsupported vocabulary yields an explicit unsupported-version report without inferring semantics` | [[document.adapters.layer]] |

## Model

### States
- `carrier_received`
- `adapter_selected`
- `observations_extracted`
- `coverage_declared`
- `outcome_reported`
- `native_run_reported`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| dispatch_adapter | carrier_received | adapter_selected | exactly one applicable adapter matches the declared format and version without conjoined carrier rules [[document.adapters.layer.single_adapter_dispatch]] |
| type_observations | adapter_selected | observations_extracted | every observation is typed with per-observation source evidence and no fabricated geometry [[document.adapters.layer.pdf_observation_typing]] [[document.adapters.layer.epub_observation_typing]] [[document.adapters.layer.json_baseline_mandatory]] |
| declare_preservation | observations_extracted | coverage_declared | capabilities, preserved fields, replay metadata, and omitted/approximated fields are all declared, with typed results for unsupported/error/ambiguous [[document.adapters.layer.preservation_declared]] [[document.adapters.layer.replay_metadata_recorded]] [[document.adapters.layer.typed_failure_results]] |
| bind_outcome_state | coverage_declared | outcome_reported | the run outcome is exactly one of observed, unsupported, ambiguous, or failed [[document.adapters.layer.outcome_states_distinguished]] |
| verify_coverage_profiles | coverage_declared | coverage_declared | inventory and manifest profiles satisfy their grammars, minimums, identity pinning, and single-run scope with manifest-bounded claims [[document.adapters.layer.inventory_independence]] [[document.adapters.layer.inventory_grammar]] [[document.adapters.layer.minimum_inventory_per_format]] [[document.adapters.layer.manifest_grammar]] [[document.adapters.layer.manifest_bounded_claims]] [[document.adapters.layer.coverage_entry_identity]] [[document.adapters.layer.single_run_entries]] |
| check_scope_entries | coverage_declared | coverage_declared | every entry's scope matches the grammar, enumeration is complete against source bytes, and dispositions are unique per (inventory_id,feature,scope) [[document.adapters.layer.scope_grammar]] [[document.adapters.layer.complete_enumeration]] [[document.adapters.layer.unique_dispositions]] |
| collapse_summary_status | coverage_declared | coverage_declared | mixed outcomes collapse to the least-preserving status and summaries stay honest about absence and completeness [[document.adapters.layer.precedence_least_preserving]] [[document.adapters.layer.absence_honesty]] |
| account_partial_loss | outcome_reported | outcome_reported | all dispositions, digests, and enumeration results are retained and no aggregate claims preservation over an unexamined scope [[document.adapters.layer.partial_loss_accounting]] |
| frame_geometry | coverage_declared | coverage_declared | geometry resolves through a declared named frame or reports invalid_geometry_frame/unsupported_profile [[document.adapters.layer.declared_coordinate_frames]] |
| run_native_extraction | carrier_received | native_run_reported | extraction runs locally with recorded settings and page selection, reproducible bytes, honest partiality, and explicit failures without overwriting [[document.adapters.layer.native_consumer_local]] [[document.adapters.layer.native_repeatability]] [[document.adapters.layer.native_partiality_honest]] |
| map_native_words | native_run_reported | native_run_reported | each word binds source, page, raw span, and framed box, with search tokens mapped to raw spans [[document.adapters.layer.native_source_mappings]] |
| classify_native_outcome | native_run_reported | outcome_reported | the run reports exactly one vocabulary outcome with exit code per contract and version pinned [[document.adapters.layer.native_outcome_vocabulary]] [[document.adapters.layer.exit_code_contract]] [[document.adapters.layer.outcome_versioning]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| exclusive_dispatch | unit | [[document.adapters.layer.single_adapter_dispatch]] | `mixed_carrier_descriptor()` | the mixed carrier dispatches to exactly one adapter and validates |
| pdf_evidence_bound | unit | [[document.adapters.layer.pdf_observation_typing]] | `mixed_pdf_observation_fixture()` | every PDF observation carries its own source evidence |
| epub_no_geometry | unit | [[document.adapters.layer.epub_observation_typing]] | `epub_descriptor_fixture()` | a valid EPUB descriptor asserts no fixed page geometry |
| json_baseline_present | unit | [[document.adapters.layer.json_baseline_mandatory]] | `json_only_descriptor()` | a JSON-only descriptor validates with no optional adapter module installed |
| preservation_complete | unit | [[document.adapters.layer.preservation_declared]] | `adapter_result_producer()` | each adapter result declares preserved and omitted/approximated fields |
| replay_fingerprint_typed | unit | [[document.adapters.layer.replay_metadata_recorded]] | `undigestable_configuration_fixture()` | an adapter that cannot digest its configuration records the literal `unavailable` |
| failure_not_complete | unit | [[document.adapters.layer.typed_failure_results]] | `unsupported_carrier_result_fixture()` | an unsupported carrier reports status `unsupported` with no partial output presented as complete |
| outcome_exactly_one | unit | [[document.adapters.layer.outcome_states_distinguished]] | `no_matching_adapter_probe()` | a carrier with no matching adapter reports exactly outcome `unsupported` |
| inventory_unshrunk | unit | [[document.adapters.layer.inventory_independence]] | `feature_hiding_adapter_fixture()` | an inventory excludes nothing merely because the adapter's supported list omits it |
| inventory_closed_fields | unit | [[document.adapters.layer.inventory_grammar]] | `extra_field_inventory_fixture()` | an inventory with an extra field fails verification with `invalid_coverage_inventory` |
| minimum_features_enforced | unit | [[document.adapters.layer.minimum_inventory_per_format]] | `pdf_inventory_missing_attachments()` | a PDF inventory omitting `pdf:attachments` fails with `invalid_coverage_inventory` |
| manifest_closed_fields | unit | [[document.adapters.layer.manifest_grammar]] | `mismatched_manifest_fixture()` | a manifest with a repeated feature, missing version, or wrong source_format fails with `invalid_coverage` |
| claims_manifest_bounded | unit | [[document.adapters.layer.manifest_bounded_claims]] | `attachments_unsupported_pdf_adapter()` | attachments still require coverage when the manifest lists only glyphs |
| entry_field_closure | unit | [[document.adapters.layer.coverage_entry_identity]] | `undeclared_entry_field_fixture()` | a coverage entry with a tenth field invalidates the descriptor |
| entries_one_run | unit | [[document.adapters.layer.single_run_entries]] | `two_run_entry_mix_fixture()` | entries from two runs or configurations are invalid as a single descriptor |
| scope_grammar_typed | unit | [[document.adapters.layer.scope_grammar]] | `malformed_scope_fixture()` | `page:01` and a case-variant EPUB archive path are rejected by the scope grammar |
| enumeration_star_only | unit | [[document.adapters.layer.complete_enumeration]] | `unfinishable_page_enumeration()` | an unfinishable enumeration yields one `*`/unexamined entry and combining `*` with page entries is invalid |
| disposition_unique | unit | [[document.adapters.layer.unique_dispositions]] | `duplicate_disposition_fixture()` | two entries for one (inventory_id,feature,scope) are invalid even when agreeing |
| precedence_collapses_down | unit | [[document.adapters.layer.precedence_least_preserving]] | `one_omitted_page_fixture()` | pages 1-9 preserved with page 10 omitted summarize glyphs as `omitted` |
| absence_verified_first | unit | [[document.adapters.layer.absence_honesty]] | `unverified_absence_fixture()` | a `preserved` claim without verified source absence is invalid |
| frame_declared_required | unit | [[document.adapters.layer.declared_coordinate_frames]] | `rotated_page_frame_fixture()` | rotated-page geometry resolves through the declared frame and pinned renderer, not a guessed convention |
| loss_fully_accounted | unit | [[document.adapters.layer.partial_loss_accounting]] | `missing_page_coverage_fixture()` | schema-valid output with an absent required page still fails with `invalid_coverage` |
| native_zero_network | unit | [[document.adapters.layer.native_consumer_local]] | `two_page_native_pdf()` | native extraction on source and output alone performs zero OCR, model, or network calls |
| word_span_binding | unit | [[document.adapters.layer.native_source_mappings]] | `repeated_words_lines_fixture()` | whitespace-collapsed search maps every occurrence to its raw span and word box |
| rerun_bytes_identical | unit | [[document.adapters.layer.native_repeatability]] | `double_extraction_run()` | two pinned reruns produce matching semantic bytes with only envelope fields differing |
| native_failure_preserves | unit | [[document.adapters.layer.native_partiality_honest]] | `encrypted_pdf_existing_output()` | invalid inputs return non-success without overwriting existing data |
| outcome_gap_explicit | unit | [[document.adapters.layer.native_outcome_vocabulary]] | `textless_page_selection()` | a selection with a textless page reports `text-with-gaps` with the page unexamined |
| exit_code_fixed | unit | [[document.adapters.layer.exit_code_contract]] | `no_text_selection_probe()` | a `no-text-read` run exits 2 and a `text-complete` run with unestablished visual completeness exits 0 |
| vocabulary_pinned | unit | [[document.adapters.layer.outcome_versioning]] | `legacy_partial_manifest()` | a legacy-only manifest reports `unsupported-version` with exit 4 |
