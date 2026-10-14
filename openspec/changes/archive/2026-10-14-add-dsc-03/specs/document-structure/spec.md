# document-structure (0.3 delta)

## MODIFIED Requirements

### Requirement: View declaration

The system SHALL require `views[]` objects with exactly `id`, `kind`, `root`;
kind is `physical|logical|carrier`. At least one logical view is required.
Regions SHALL replace `view` with `view_id` referencing one view, and retain
`id`, `kind` and optional geometry. Only physical regions may carry geometry.

#### Scenario: Carrier structure

- **WHEN** a carrier view preserves an EPUB resource tree
- **THEN** it has its own root and implies no page geometry

### Requirement: Containment ownership

The system SHALL enforce containment ownership per named view according to
document-core's Containment tree integrity requirement. Different segmentations
SHALL use different views, not contradictory ownership in one tree.

#### Scenario: Competing segmentations

- **WHEN** one segmentation divides an article into two regions and another
  into three
- **THEN** each has an independent view and valid containment tree

### Requirement: Reading order partiality

The system SHALL induce partial order only through `precedes` reachability
inside one interpretation, following document-core's scoped order rule.
Each `precedes` SHALL have `interpretation_id`; no other relation kind may
have it. The referenced interpretation must be `reading-order` and its view
must match both endpoints. Duplicate-edge uniqueness SHALL be
`(kind,from,to,interpretation_id)` for `precedes`, `(kind,from,to)` otherwise.

#### Scenario: Same edge in independent orders

- **WHEN** `A -> B` occurs once in each of two interpretations
- **THEN** it is valid; repeating it in the same interpretation is `duplicate_edge`

## ADDED Requirements

### Requirement: Named interpretations

Interpretations SHALL have exactly `id`, `kind`, `view_id`, `origin`, `status`,
`evidence`. Kind is `reading-order|segmentation`; origin and status use the
0.2 annotation enums. Evidence references SHALL resolve; `supported` requires
at least one, `asserted_without_evidence` requires none. A segmentation
interpretation attributes its view's tree. Support is attribution, not truth.
Competing interpretations SHALL coexist without an automatic winner.

#### Scenario: Unsupported interpretation

- **WHEN** a reading-order interpretation has no evidence
- **THEN** it can be `asserted_without_evidence`, but cannot be `supported`

### Requirement: Explicit linearization policy

A consumer exporting a total reading sequence SHALL declare an interpretation
id and a named, versioned deterministic linearization policy in its export
report. It SHALL report incomparable regions and SHALL NOT write the policy's
tie-break edges back as observed order. EPUB navigation and spine semantics
SHALL remain profile-defined rather than becoming universal `precedes` edges.

#### Scenario: Incomparable regions

- **WHEN** a consumer exports a total order for incomparable regions
- **THEN** its report names the policy and incomparable regions; an export
  without this declaration is invalid, independently of descriptor validity

### Requirement: Many-to-many realization with declared alignment

`realizes` SHALL connect physical to logical regions and allow many-to-many
placements. Fine-grained alignment SHALL require selectors and a declared
alignment profile, bound by the annotation's `alignment_profile_id` and
`selector_ids` fields defined in document-evidence. No universal alignment
semantics SHALL be inferred from unprofiled strings.

#### Scenario: Fine-grained alignment without a profile

- **WHEN** a consumer receives only region-level `realizes` edges
- **THEN** it may use those placements but cannot claim character alignment
