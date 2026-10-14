# document-ontology-boundaries Specification

## Purpose
Ontology boundary rules for DSC 0.3: how out-of-core semantics (relations
beyond `contains`/`precedes`/`realizes`) are represented without silent
coercion. Derived from the bundle's `ONTOLOGY-BOUNDARIES.md` (acceptance
checks O-A01, O-A04, O-A05); executable projection evaluator in
`dsc03/boundaries.py`.
## Requirements
### Requirement: No silent coercion

Unsupported semantic relationships SHALL NEVER be rewritten as core
`contains`/`precedes`/`realizes` without a declared equivalence.

#### Scenario: Out-of-core relationship

- **WHEN** a feature's relationship has no core or registered-profile encoding
- **THEN** it is not silently coerced into a core relation (acceptance check
  O-A01)

### Requirement: Explicit boundary disposition

Each evaluated out-of-core feature SHALL be exactly represented, explicitly
projected, or reported with a declared unsupported/unexamined/loss outcome.

#### Scenario: Loss manifest

- **WHEN** a projection is applied
- **THEN** its losses are declared in a manifest (acceptance check O-A04)

### Requirement: Profile isolation

A registered profile SHALL NOT redefine core identity, relations, canonical
form, or validity rules.

#### Scenario: Profile overreach

- **WHEN** a profile attempts to redefine a core rule
- **THEN** the profile is rejected

### Requirement: Mapping provenance

A projection SHALL declare source/target version, rules, scope, evidence, and
losses.

#### Scenario: Projection without provenance

- **WHEN** a projection omits its declaration
- **THEN** it is not applied as a valid mapping

### Requirement: Inference isolation

Derived ontology statements SHALL NEVER be misrepresented as direct source
observations.

#### Scenario: Derived statement labeled

- **WHEN** an ontology statement is derived rather than observed
- **THEN** its provenance marks it as derived

### Requirement: Conditional roundtrip

Roundtrip fidelity SHALL be claimed only for a specified observable subset
and tested domain.

#### Scenario: Unearned full-fidelity claim

- **WHEN** full-fidelity roundtrip is claimed beyond a tested subset
- **THEN** the claim is rejected (acceptance check O-A05)

