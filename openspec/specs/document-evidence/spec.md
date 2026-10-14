# document-evidence Specification

## Purpose

Retain evidence, transformation fingerprints, and honest uncertainty for every
recorded observation or semantic claim. Each claim has an `origin`
(source/extracted/inferred/manual/external); missing support can be
represented as `asserted_without_evidence`; conflicting claims coexist and are
marked disputed; transformation lineage is a DAG.
## Requirements
### Requirement: Evidence link resolution

All claim targets and supplied evidence references SHALL resolve even when a
claim is `asserted_without_evidence`. That status permits an empty evidence
array; it does not permit a dangling target or reference. Each 0.3 evidence
object SHALL retain `id`, `origin`, `source_ref`, optional `transform`, and
add mandatory `content_ids` and `selector_ids` arrays of unique typed ids.
`content_ids` identifies observations produced by this evidence record;
`selector_ids` identifies supporting source or content anchors. An empty
binding asserts no content or anchor support. Opaque `source_ref` alone SHALL
NOT be treated as a verified source anchor.

#### Scenario: Unsupported claim still has a target

- **WHEN** an annotation with `asserted_without_evidence` names a missing target
- **THEN** it is invalid with `dangling_reference`

#### Scenario: Source observation binding

- **WHEN** source evidence `e0` lists content `c0` and selector `s0`
- **THEN** both ids resolve, and a verifier can trace `c0` to the source through
  `s0`; a dangling binding is invalid

### Requirement: Origin typing

THE system SHALL distinguish claim origins source, extracted, inferred,
manual, and external.

#### Scenario: Origin recorded per claim

- **WHEN** a claim is recorded
- **THEN** its origin is one of the five typed values

### Requirement: Replay material for derived observations

A transform SHALL have exactly `id`, `version`, `config_sha256`, `dependencies`,
`inputs`, `outputs`. Inputs and outputs SHALL be nonempty arrays of distinct
content ids, disjoint from each other. Outputs SHALL equal the containing
evidence record's `content_ids` as a set. Transformer id/version are nonempty;
config_sha256 is 64 lowercase hex; dependencies are nonempty pinned identifier
strings. Missing replay material cannot be labeled reproducible.

Each content participating in a transform SHALL have exactly one producing
evidence record; other support may be attached via annotations. For every
input, the transform evidence SHALL have a `derived-from` edge to that input's
producer (child to parent). These edges SHALL equal the set of input producers,
and SHALL be acyclic. Both content bindings and evidence edges are required;
an opaque locator or matching string is not a substitute.

#### Scenario: Native to corrected to normalized

- **GIVEN** source evidence `e0` produces `c0`
- **WHEN** `e1` transforms `c0` into `c1` and `e2` transforms `c1` into `c2`
- **THEN** inputs/outputs identify those exact content ids and lineage contains
  `e1 -> e0` and `e2 -> e1`; all three values remain available

#### Scenario: Broken content lineage

- **WHEN** an input lacks a producer, an output is its own input, or a declared
  parent is not an input producer
- **THEN** validation fails with `invalid_transform_binding`

### Requirement: Acyclic transformation lineage

THE system SHALL require the `derived-from` relation graph to be acyclic.

#### Scenario: Lineage cycle rejected

- **GIVEN** `fixtures/invalid/lineage-cycle.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `lineage_cycle`

### Requirement: Dispute preservation

THE system SHALL keep unresolved competing claims separate with status
`disputed`, without automatic precedence.

#### Scenario: Competing claims coexist

- **GIVEN** `fixtures/valid/disputed.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid` and statuses include `disputed`

### Requirement: Honest uncertainty

THE system SHALL NOT invent confidence, and missing replay material SHALL be
distinguishable from conflict.

#### Scenario: Unverifiable claim is typed

- **WHEN** a claim lacks support or replay material without any conflict
- **THEN** the outcome is `unverifiable`, not `disputed` or `supported`

### Requirement: Evidence status transitions

THE system SHALL move a recorded claim to `supported` (support sufficient, no
conflicting support, replay material available), `disputed` (conflicting
support), or `unverifiable` (no conflict but support or replay material
missing).

#### Scenario: Unsupported manual assertion stays unverifiable

- **WHEN** a manual assertion has no evidence and no conflict
- **THEN** it is structurally valid yet epistemically `unverifiable`

### Requirement: Relation-level evidence

Structural edges (`contains`, `precedes`, `realizes`, `has-content`) SHALL
allow optional `evidence` arrays of evidence ids. Supplied ids SHALL resolve;
missing or empty evidence means an unverified assertion. `derived-from`
SHALL NOT carry evidence. Evidence existence does not prove source fidelity.

#### Scenario: Unsupported structural edge

- **WHEN** a structural edge carries no evidence references
- **THEN** it is reported as unverified, not supported

### Requirement: Typed profile-defined source selectors

Selectors SHALL have exactly `id`, `kind`, `profile_id`, `source_sha256`,
`target`, `locator`. Kind is `pdf-area|pdf-object|pdf-text-range|epub-resource|
epub-fragment|text-range|external`; target references a region or content;
locator is nonempty. The declared selector profile SHALL define allowed kinds,
locator grammar, dereferencing and failure rules. An internal selector's
source_sha256 SHALL equal the descriptor source digest; an external selector
SHALL pin the external resource's digest, never trust its URI alone.

A `text-range` target SHALL be text content. Its profile SHALL declare offset
unit (UTF-8 bytes, Unicode scalar values, or grapheme clusters), half-open or
closed endpoints, and the applicable Unicode segmentation version. Offsets
SHALL index the exact target value without normalization. Range boundaries
SHALL be in bounds and respect the declared units. With a resolved profile,
malformed locators/ranges yield `invalid_selector`; missing profile references
yield `dangling_reference`; unavailable declared profiles yield
`unsupported_profile` at resolution, not invented interpretation.

#### Scenario: Different offset units

- **WHEN** a scalar-index profile selects half-open range `[1,2)` in `AéB`
- **THEN** it selects `é`; a byte-index profile must use `[1,3)` for that character

#### Scenario: Malformed locator under known profile

- **WHEN** a resolved text profile receives a reversed or out-of-bounds range
- **THEN** selector validation returns `invalid_selector`

### Requirement: Distinguishable text observations

Native, OCR, corrected and normalized text SHALL remain distinct content
objects whenever code-point sequences differ. Normalization SHALL be an
explicit transform with input/output bindings, algorithm and version; it is
never part of canonical serialization. Original non-NFC text SHALL remain
readable as text, with selectors measured on that exact snapshot.

#### Scenario: Unicode normalization changes offsets

- **WHEN** `c0` contains `U+0065 U+0301` and NFC produces `c1` containing `U+00E9`
- **THEN** both objects survive; scalar ranges `[0,2)` on `c0` and `[0,1)` on
  `c1` address their respective snapshots and are not silently interchanged

### Requirement: Profile-bound alignment annotations

Annotations SHALL optionally carry `alignment_profile_id` and `selector_ids`
together, never one alone. The first SHALL reference a declared alignment
profile; the second SHALL be a nonempty ordered array of selector ids. The
profile SHALL define arity, endpoint roles, fragment pairing, allowed targets,
and alignment verification. This adds no new core relation kind.

#### Scenario: Two fragment pairs

- **WHEN** an annotation supplies four selectors under a profile defining
  ordered source/target pairs
- **THEN** only those declared pairs are aligned, not their Cartesian product

