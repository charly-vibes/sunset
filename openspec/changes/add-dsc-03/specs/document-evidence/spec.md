# document-evidence (0.3 delta)

## ADDED Requirements

### Requirement: Relation-level evidence

Structural edges (`contains`, `precedes`, `realizes`, `has-content`) SHALL be
able to retain typed evidence references; absent evidence SHALL mean
*unverified assertion*, not support.

#### Scenario: Unsupported structural edge

- **WHEN** a structural edge carries no evidence references
- **THEN** it is reported as unverified, not supported

### Requirement: Typed profile-defined source selectors

Source selectors SHALL be typed (`pdf-area|pdf-object|pdf-text-range|
epub-resource|epub-fragment|text-range|external`) and defined by a registered
profile; unresolved references SHALL be reported, never assumed resolvable.

#### Scenario: Unsupported selector profile

- **WHEN** a selector references an unregistered profile
- **THEN** the outcome is unsupported/invalid-selector, never a guessed
  interpretation

### Requirement: Distinguishable text observations

Native, OCR, corrected, and normalized text SHALL remain separate content
objects with explicit transform lineage whenever the strings differ; they are
never silently overwritten.

#### Scenario: Hyphenation applied

- **WHEN** hyphenation or ligature expansion is applied
- **THEN** the transform is recorded in lineage and the original observation
  remains distinct
