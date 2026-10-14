# document-semantics Specification

## Purpose

Retain typed, namespaced domain claims without reinterpreting the structural
core. Semantic vocabulary registration is versioned (`title`, `poem`,
`posting` etc are extension terms, not universal records); claims never
overwrite core structure; cross-edition equivalence is an optional, explicitly
scoped comparison using a named projection and comparator.
## Requirements
### Requirement: Namespaced vocabulary registration

THE system SHALL require every non-core term to be registered with a
namespace and a semantic version.

#### Scenario: Unknown extension term rejected

- **GIVEN** `fixtures/invalid/unknown-extension.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `unknown_term`

### Requirement: Typed annotation claims

Annotations SHALL retain the 0.2 mandatory fields `id`, `target`, `term`,
`value`, `origin`, `status`, `evidence` and add mandatory `view_id` resolving
to a named view. If target is a region, that region SHALL belong to this view;
if content, a `has-content` edge SHALL bind it to a region in this view.
Only the paired optional alignment fields defined in document-evidence are
additionally allowed. Semantic labels SHALL NOT mutate observed content.

#### Scenario: Shared text in two views

- **WHEN** two claims classify shared content differently in two views
- **THEN** each claim identifies its view and the content has a binding in
  that view; neither changes the physical observation

#### Scenario: Unbound claim

- **WHEN** a claim names a view without a target binding there
- **THEN** it is invalid, rather than assigned a view implicitly

### Requirement: Extension isolation

THE system SHALL forbid extensions from modifying core identity, relation
kinds, or canonicalization.

#### Scenario: Core identity is untouchable

- **WHEN** an extension attempts to alter core identity or relation kinds
- **THEN** the extension is rejected at registration, not applied

### Requirement: Unresolved semantic alternatives are explicit

THE system SHALL reject unregistered extension terms and keep unresolved
semantic alternatives explicit rather than resolved implicitly.

#### Scenario: Disputed semantic claims preserved

- **GIVEN** `fixtures/valid/disputed.json`
- **WHEN** the descriptor is validated
- **THEN** the disputed claims are preserved with their conflict status

### Requirement: No automatic cross-edition equivalence

THE system SHALL never infer cross-edition equivalence automatically; a named
projection and comparator are required.

#### Scenario: Equivalence without declared comparator

- **WHEN** an equivalence claim lacks a named projection and comparator
- **THEN** it is not treated as an inferred equivalence of the core

### Requirement: Source observations vs claims

Semantic labels and observed strings SHALL have distinct provenance.
Schema validity SHALL NOT promote a claim to supported. No-evidence assertions
SHALL use `asserted_without_evidence`, except explicitly disputed claims may
retain the 0.2 empty-evidence representation. Assessment `unverifiable` is an
external report outcome, not a new annotation status.

#### Scenario: Unsupported undisputed claim

- **WHEN** an undisputed claim has no supporting evidence
- **THEN** its annotation status is `asserted_without_evidence` and its assessment
  is unverifiable, never silently supported

