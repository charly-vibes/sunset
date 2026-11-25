---
id: document.core.layer
kind: intent
statement: "WHEN a DSC 0.3 descriptor is validated, THE structural core SHALL accept exactly well-typed, internally consistent descriptors under the 0.2 wire contract, returning complete typed outcomes for every shape, identity, graph, geometry, canonicalization, and resource condition."
---

## Constraints

| id | kind | expr | traces_to |
|---|---|---|---|
| exact_shape | invariant | `A 0.3 descriptor carries exactly the 0.2 top-level fields plus views, selectors, interpretations, coverage, and profiles, with version "0.3", and rejects unknown properties, nulls, booleans, floats, duplicate keys, and invalid Unicode` | [[document.core.layer]] |
| text_encoding_scope | invariant | `Object keys and identifiers are ASCII; all other strings are NFC except contents[].value with kind text, whose exact code points survive unchanged` | [[document.core.layer]] |
| digest_format | invariant | `source.sha256 is exactly 64 lowercase hex characters` | [[document.core.layer]] |
| local_identity | invariant | `Ids match [A-Za-z0-9][A-Za-z0-9_.:-]*, are unique across all entity collections with views in their own namespace, and every reference resolves in its declared collection without resolving to entity ids` | [[document.core.layer]] |
| containment_integrity | invariant | `Each named view has exactly one root equal to views[].root with no incoming contains, every other region in that view has exactly one parent, containment is acyclic, and no edge crosses views` | [[document.core.layer]] |
| per_view_reading_order | invariant | `precedes is checked for acyclicity and reachability separately per interpretation, endpoints stay in that view, and geometry or array position implies no order` | [[document.core.layer]] |
| typed_optional_geometry | invariant | `Geometry is optional, physical-region-only, has exactly profile_id/space/x/y/width/height with nonnegative integers, and profile_id resolves to a declared profile whose space names an existing frame` | [[document.core.layer]] |
| canonical_idempotence | invariant | `Serialization uses sorted ASCII keys and UTF-8 without whitespace or trailing newline, never normalizing strings, sorting arrays, or renaming ids, and is idempotent as bytes` | [[document.core.layer]] |
| typed_outcomes | invariant | `Schema validation returns valid or invalid with sorted deduplicated reasons; malformed types yield invalid_shape before lookup, malformed JSON parse_error, missing references dangling_reference, and exhaustion resource_limit, never valid` | [[document.core.layer]] |
| migrated_fixtures_only | invariant | `Legacy fixtures/ scenarios are exercised only through equivalent migrated 0.3 descriptors, and the original 0.2 files are never relabeled as valid 0.3 inputs` | [[document.core.layer]] |
| profile_declaration_shape | invariant | `Each profiles[] object has exactly id, kind, uri, version, sha256 with kind in selector|geometry|carrier-inventory|adapter-manifest|alignment, nonempty uri/version, and a 64-lowercase-hex sha256 over exact artifact bytes` | [[document.core.layer]] |
| local_registry_resolution | invariant | `Profiles resolve from an explicitly supplied local registry at the pinned version and digest, with no network fetch or latest-version fallback` | [[document.core.layer]] |

## Model

### States
- `descriptor_parsed`
- `schema_checked`
- `graph_verified`
- `profiles_resolved`
- `outcome_reported`
- `attempt_incomplete`

### Transitions

| id | from | to | guard |
|---|---|---|---|
| dispatch_version | descriptor_parsed | schema_checked | version dispatches to the 0.3 validator only, with unknown fields, nulls, booleans, floats, duplicate keys, and invalid Unicode refused [[document.core.layer.exact_shape]] [[document.core.layer.typed_outcomes]] |
| enforce_encoding | schema_checked | schema_checked | keys and ids are ASCII and non-text strings satisfy NFC while text values keep exact code points [[document.core.layer.text_encoding_scope]] |
| check_digest | schema_checked | schema_checked | source.sha256 is 64 lowercase hex characters [[document.core.layer.digest_format]] |
| resolve_references | schema_checked | graph_verified | ids are unique across collections and every reference resolves in its declared collection [[document.core.layer.local_identity]] |
| verify_containment | graph_verified | graph_verified | each view has one in-view root, non-roots have exactly one parent, and containment stays acyclic within the view [[document.core.layer.containment_integrity]] |
| check_reading_order | graph_verified | graph_verified | each interpretation is checked independently for cycles and reachability with endpoints in its own view [[document.core.layer.per_view_reading_order]] |
| resolve_geometry | graph_verified | graph_verified | geometry, when present, sits on a physical region with exact fields and a resolvable profile frame [[document.core.layer.typed_optional_geometry]] |
| canonicalize | graph_verified | profiles_resolved | serialization is byte-idempotent without normalizing strings, sorting arrays, or renaming ids [[document.core.layer.canonical_idempotence]] |
| resolve_profiles | profiles_resolved | outcome_reported | declarations match the exact five-field shape and resolve locally at the pinned version and digest [[document.core.layer.profile_declaration_shape]] [[document.core.layer.local_registry_resolution]] |
| report_outcome | outcome_reported | outcome_reported | reasons are sorted, deduplicated, and separated from profile resolution, coverage, and assessment [[document.core.layer.typed_outcomes]] |
| halt_on_exhaustion | schema_checked | attempt_incomplete | a documented size, nesting, or graph limit is exceeded, reported as resource_limit rather than valid [[document.core.layer.typed_outcomes]] |
| port_legacy_fixture | attempt_incomplete | schema_checked | the exercised input is a migrated 0.3 descriptor, never a relabeled 0.2 fixture [[document.core.layer.migrated_fixtures_only]] |

## Properties

| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| shape_rejection | unit | [[document.core.layer.exact_shape]] | `unknown_field_descriptor()` | an unknown property, null, boolean, float, duplicate key, or invalid Unicode yields invalid with invalid_shape |
| text_preserved | unit | [[document.core.layer.text_encoding_scope]] | `decomposed_text_descriptor()` | U+0065 U+0301 survives in a text value while the same sequence in a metadata string fails NFC |
| digest_checked | unit | [[document.core.layer.digest_format]] | `malformed_sha256_fixture()` | a source.sha256 that is not 64 lowercase hex fails with invalid_digest |
| reference_totality | unit | [[document.core.layer.local_identity]] | `cross_collection_collision_fixture()` | a region and selector sharing an id yields duplicate_id and a mistyped profile_id yields dangling_reference |
| single_root_per_view | unit | [[document.core.layer.containment_integrity]] | `two_independent_views_fixture()` | two per-view roots validate without cross-view containment, and a shared root, zero/two-parent region, or cross-view edge is refused |
| order_independence | unit | [[document.core.layer.per_view_reading_order]] | `opposing_interpretations_fixture()` | A->B in i1 and B->A in i2 both validate, while both edges in one interpretation yield order_cycle |
| geometry_frame_check | unit | [[document.core.layer.typed_optional_geometry]] | `missing_frame_geometry_fixture()` | omitted geometry validates and a resolved profile lacking the named space yields invalid_geometry_frame |
| canonical_stability | unit | [[document.core.layer.canonical_idempotence]] | `distinct_unicode_pair_fixture()` | descriptors with U+0065 U+0301 and U+00E9 produce different canonical bytes and each reserializes unchanged |
| outcome_typing | unit | [[document.core.layer.typed_outcomes]] | `array_endpoint_relation_fixture()` | a relation with "from": [] and nested malformed fields return invalid_shape with sorted deduplicated reasons, never an exception |
| fixture_migration_gate | unit | [[document.core.layer.migrated_fixtures_only]] | `legacy_0_2_fixture_input()` | a 0.2 fixture fed to a 0.3 reader does not pass the continuation check; only the migrated descriptor does |
| profile_shape_check | unit | [[document.core.layer.profile_declaration_shape]] | `malformed_profile_declaration()` | an unknown kind, empty uri or version, or non-hex sha256 invalidates the descriptor |
| pin_survival | unit | [[document.core.layer.local_registry_resolution]] | `dual_version_registry_fixture()` | only the pinned version and digest's bytes define offsets, and unavailable or digest-mismatched profiles yield unsupported_profile or profile_digest_mismatch |
