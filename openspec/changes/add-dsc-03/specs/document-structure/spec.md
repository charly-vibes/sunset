# document-structure (0.3 delta)

## ADDED Requirements

### Requirement: Independent named views

Independent physical, logical, and carrier views SHALL have independent
containment trees, with cross-view linkage only via explicit `realizes` or a
registered alignment; cross-view `contains` is invalid.

#### Scenario: Carrier view preserves native structure

- **WHEN** a `carrier` view preserves native EPUB structure
- **THEN** it implies no page geometry

### Requirement: Reading-order hypotheses are named and separate

Each `precedes` edge SHALL belong to exactly one named reading-order
interpretation with its own DAG; incompatible hypotheses SHALL NOT be merged.

#### Scenario: Competing interpretations coexist

- **WHEN** two supported reading-order interpretations disagree
- **THEN** both are recorded separately with no winner selected

### Requirement: Explicit linearization policy

A total exported reading sequence SHALL require a named tie-break/linearization
policy with explicit handling of incomparable regions.

#### Scenario: Incomparable regions reported

- **WHEN** a consumer exports a total order without a declared policy
- **THEN** the export is invalid and incomparable elements are reported

### Requirement: Many-to-many realization with declared alignment

`realizes` SHALL be many-to-many; fine-grained location alignment SHALL
require declared selectors and a profile.

#### Scenario: Fine-grained alignment without profile

- **WHEN** alignment is asserted without declared selectors and profile
- **THEN** no universal alignment semantics are asserted
