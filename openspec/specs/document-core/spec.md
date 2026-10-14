# document-core Specification

## Purpose

Validate the typed structure of a DSC 0.2 document descriptor (JSON wire
contract per the bundle's `CONTRACT-0.2.md`) and return complete error
reasons. Object identifiers are snapshot-local; canonical form is an
RFC 8785-style subset (ASCII key sorting, NFC strings, integers, no floats,
duplicate-key rejection). The reference implementation is
`spec/document-model-specodelic-v3/validator.py`.
## Requirements
### Requirement: Descriptor shape validation

The 0.3 validator SHALL require exactly the 0.2 top-level fields plus five
mandatory arrays: `views`, `selectors`, `interpretations`, `coverage`, and
`profiles`, with `version` equal to `"0.3"`. Unknown properties, nulls,
booleans, floats, duplicate JSON keys and invalid Unicode scalar sequences
SHALL be invalid. Object keys and identifiers SHALL be ASCII; other strings
SHALL be NFC except `contents[].value` when `kind` is `text`. This exception
preserves exact source code points without implicit normalization. Changes to
nested shapes are specified by the structure, evidence, semantics and adapter
deltas; all other 0.2 fields remain unchanged. These are breaking wire changes.

#### Scenario: Version dispatch

- **WHEN** a descriptor declares `"0.3"`
- **THEN** only the 0.3 validator may validate it; the frozen 0.2 validator
  rejects it and is never upgraded in place

#### Scenario: Undeclared field

- **WHEN** an otherwise valid descriptor includes an unknown property
- **THEN** it is invalid with `invalid_shape`

#### Scenario: Decomposed original text

- **WHEN** a text value contains `U+0065 U+0301`
- **THEN** those two code points are allowed unchanged; an otherwise identical
  non-text metadata string must satisfy NFC

### Requirement: Source digest format

THE system SHALL require `source.sha256` to be 64 lowercase hex characters.

#### Scenario: Bad digest rejected

- **WHEN** `source.sha256` is not 64 lowercase hex characters
- **THEN** validation fails with `invalid_digest`

### Requirement: Snapshot-local identity and referential integrity

The system SHALL require ASCII ids matching `[A-Za-z0-9][A-Za-z0-9_.:-]*`
and uniqueness across regions, contents, relations, annotations, evidence,
selectors, interpretations and profiles. View ids SHALL be unique in their
own namespace. Coverage entries have no ids. Each reference SHALL resolve in
its declared collection; view references cannot resolve to entity ids.

#### Scenario: Id collision across collections

- **WHEN** a region and selector share an id
- **THEN** the descriptor is invalid with `duplicate_id`

#### Scenario: Wrong reference type

- **WHEN** a selector's `profile_id` names a content object
- **THEN** the descriptor is invalid with `dangling_reference`

### Requirement: Containment tree integrity

The system SHALL require one root per named view, equal to `views[].root` and
belonging to that view. The root has no incoming `contains`; every other
region in that view has exactly one. Containment SHALL be acyclic within each
view and SHALL NOT cross views. There is no global single-root rule.

#### Scenario: Independent roots

- **WHEN** a physical view and a logical view each have one valid tree
- **THEN** their two roots are valid without cross-view containment

#### Scenario: Invalid ownership

- **WHEN** a root belongs to another view, a non-root has zero or two parents,
  or a `contains` edge crosses views
- **THEN** the descriptor is invalid

### Requirement: Reading order is a strict partial order

The system SHALL check `precedes` acyclicity and reachability separately for
each reading-order interpretation. Both endpoints SHALL belong to its view.
The union of interpretations SHALL NOT be tested as one order. Geometry and
array positions SHALL NOT imply order or require a total order.

#### Scenario: Opposing hypotheses

- **WHEN** interpretation `i1` contains `A -> B` and `i2` contains `B -> A`
  in the same view, with no other edges
- **THEN** both orders are valid and remain distinct

#### Scenario: Cycle within a hypothesis

- **WHEN** both edges occur in `i1`
- **THEN** the descriptor is invalid with `order_cycle`

### Requirement: Optional typed geometry

Geometry SHALL remain optional and allowed only on physical regions. When
present its exact fields SHALL be `profile_id`, `space`, `x`, `y`, `width`,
`height`; coordinates and extents are nonnegative integers, including zero
extents. `profile_id` SHALL reference a declared geometry profile, and `space`
SHALL name a frame in that profile. Frame resolution follows the adapter delta.

#### Scenario: Geometry omitted

- **WHEN** a region has no geometry
- **THEN** this does not invalidate the descriptor

#### Scenario: Missing frame

- **WHEN** a resolved geometry profile lacks the named frame
- **THEN** the outcome is `invalid_geometry_frame`

### Requirement: Canonicalization stability

The system SHALL serialize valid 0.3 descriptors using the 0.2 JSON algorithm
(sorted ASCII object keys, UTF-8, no insignificant whitespace or trailing
newline), with the revised text NFC exception. It SHALL NOT normalize strings,
sort arrays or rename ids during canonicalization. Canonicalization SHALL be
idempotent as bytes; it does not establish source fidelity or equivalence
between independently generated descriptors.

#### Scenario: Distinct Unicode snapshots

- **WHEN** otherwise identical text descriptors contain `U+0065 U+0301` and
  `U+00E9`, respectively
- **THEN** their canonical bytes differ, and each survives parse/reserialize
  unchanged

### Requirement: Validation outcome states

Descriptor schema validation SHALL return `valid` or `invalid` with sorted,
deduplicated reason codes, separately from profile resolution, source coverage
and interpretive assessment. Malformed field types SHALL yield `invalid_shape`
before reference lookup or graph traversal; malformed JSON SHALL yield
`parse_error`. A known well-typed but missing reference yields
`dangling_reference`. Resource exhaustion SHALL be reported as an incomplete
validation attempt with `resource_limit`, never as a valid descriptor.
Implementations SHALL document input size, nesting and graph limits.

#### Scenario: Array-valued relation endpoint

- **WHEN** an otherwise valid descriptor has a relation with `"from": []`
- **THEN** validation returns `invalid` with `invalid_shape`, not an exception

#### Scenario: Malformed nested fields

- **WHEN** an id, relation kind, annotation target, or evidence reference is
  an object or array where a string is required
- **THEN** validation returns `invalid_shape` without a host-language traceback

### Requirement: Version-scoped conformance fixtures

Retained capability scenarios referring to legacy `fixtures/` SHALL be ported
to equivalent 0.3 descriptors before exercising a 0.3 implementation. The
original files SHALL remain 0.2 fixtures and SHALL NOT be relabeled as valid
0.3 inputs. Missing migrated fixtures make those checks incomplete.

#### Scenario: Legacy continuation fixture

- **WHEN** the continuation behavior is tested against a 0.3 reader
- **THEN** the test uses a migrated per-view descriptor; accepting the original
  0.2 fixture as if it were 0.3 does not pass the check

### Requirement: Pinned profile declarations

Each `profiles[]` object SHALL have exactly `id`, `kind`, `uri`, `version`,
`sha256`. Kind SHALL be `selector|geometry|carrier-inventory|adapter-manifest|
alignment`. URI and version are nonempty strings; sha256 is 64 lowercase hex
over exact artifact bytes. The URI is a lookup hint, not identity. Readers
SHALL resolve the declared version and digest from an explicitly supplied
local registry; no network fetch or latest-version fallback is implicit.
Selector and geometry objects SHALL bind through `profile_id`.

#### Scenario: Version pin survives registry changes

- **WHEN** two registry versions exist for a selector and its declaration pins
  version `1` and digest `h1`
- **THEN** only those bytes may define its offsets, even if version `2` is newer

#### Scenario: Unavailable or tampered profile

- **WHEN** a well-formed declaration is unavailable locally or its kind/version
  is not implemented
- **THEN** profile resolution is `unsupported_profile`, independently of schema
  validity; supplied bytes with a different digest yield `profile_digest_mismatch`
- **AND** neither case is reported as verified or interpreted by guessing

