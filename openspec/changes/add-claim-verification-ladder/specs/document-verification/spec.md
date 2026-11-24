## ADDED Requirements

### Requirement: Status order and conservative aggregation

Claim status SHALL be ordered `verified`, `agreed`, `unverified`, `conflicted` — where `agreed` is reserved for agreement machinery not built under this change — and the status of a scope SHALL be the meet of its claims' statuses, excluding rejected claims.

#### Scenario: One weak claim

- **GIVEN** a page with nine verified claims and one unverified claim
- **WHEN** the page status is aggregated
- **THEN** the page status is unverified

### Requirement: Verified requires an applicable passed rule

A claim SHALL reach `verified` only after anchor and value checks pass and at least one domain rule applicable to its type passes, and the absence of an applicable rule SHALL NOT yield `verified`.

#### Scenario: No rule for the type

- **GIVEN** a claim of a type with no registered domain rule
- **WHEN** all tier zero checks pass
- **THEN** the status is unverified

### Requirement: Verifiers are pinned pure functions

A verifier SHALL declare id, version, digest and applicable types, SHALL be pinned by digest in the run configuration, and SHALL return an outcome and reason code as a function of the claim and descriptor only, without network, clock or randomness.

#### Scenario: Determinism

- **GIVEN** a pinned verifier and a fixed claim and descriptor
- **WHEN** it runs twice in separate processes
- **THEN** both results are identical

### Requirement: Confidence is not evidence

Model-reported confidence SHALL NOT influence any claim status and SHALL be stored outside the semantic digest.

#### Scenario: Confidence changed

- **GIVEN** a claim resubmitted with a different confidence value
- **WHEN** statuses are recomputed
- **THEN** all statuses and the semantic digest are unchanged
