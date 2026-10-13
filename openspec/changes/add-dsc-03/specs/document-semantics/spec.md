# document-semantics (0.3 delta)

## MODIFIED Requirements

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

## ADDED Requirements

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
