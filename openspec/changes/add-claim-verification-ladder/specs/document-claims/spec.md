## ADDED Requirements

### Requirement: Claims are anchored

Every claim SHALL cite at least one anchor that resolves to a region or selector in the descriptor, and a claim with an unresolvable anchor SHALL be refused with reason code `claim.anchor.unresolved`.

#### Scenario: Dangling anchor

- **GIVEN** a claim citing an id that is not in the descriptor
- **WHEN** the claim is submitted
- **THEN** it is refused with `claim.anchor.unresolved`

### Requirement: Extractive values derive from anchors

For an extractive claim the value SHALL equal the declared normalization of the anchored text, and a differing supplied value SHALL be refused with reason code `claim.value.mismatch`; a claim type without a registered normalization SHALL NOT be compared and SHALL NOT reach `verified`.

#### Scenario: Model alters a digit

- **GIVEN** an extractive claim anchored to the text `1234`
- **WHEN** it is submitted with the value `1235`
- **THEN** it is refused with `claim.value.mismatch`

#### Scenario: Missing normalization is honest

- **GIVEN** a claim type with no registered normalization
- **WHEN** the claim is submitted with a plausible value
- **THEN** it is admitted at `unverified` with a reason code naming the missing registry entry

### Requirement: Idempotent claim identity

A claim id SHALL be a digest of its type, sorted anchors, canonical value and origin, so resubmitting an identical claim SHALL create no duplicate.

#### Scenario: Retry

- **GIVEN** a claim already admitted
- **WHEN** the same claim is submitted again
- **THEN** the claim set is unchanged

### Requirement: Conflicts are retained

Claims with the same scope and type but different values SHALL both be retained with their origins, and no value SHALL be selected without a declared precedence rule.

#### Scenario: Two models disagree

- **GIVEN** two claims for `field:total` with different values
- **WHEN** the claim set is read
- **THEN** both are present, each attributed, with status `conflicted`

### Requirement: Human decisions are claims

A human acceptance, rejection or correction SHALL be recorded as a claim with origin `human`, and it SHALL NOT overwrite or delete the model claim it concerns.

#### Scenario: Correction

- **GIVEN** a model claim a reviewer corrects
- **WHEN** the correction is saved
- **THEN** a new human-origin claim exists and the model claim remains
