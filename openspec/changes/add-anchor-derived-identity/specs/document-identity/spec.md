## ADDED Requirements

### Requirement: Anchor-derived identifiers

Under a pinned identity profile, the id of every region, content, selector and evidence record SHALL be a digest of its anchor tuple (source digest, record kind, locator path, profile id and version) and SHALL NOT depend on position, producer-local counters or operand order.

#### Scenario: Independent derivation

- **GIVEN** the same source bytes and the same locator
- **WHEN** two separate processes derive the record id
- **THEN** both ids are identical

#### Scenario: Page selection does not change ids

- **GIVEN** a native extraction of pages 1–6 and another of pages 3,1
- **WHEN** ids for page 3 records are compared
- **THEN** they are identical

### Requirement: Collision refusal

Two records that derive the same id from different anchor tuples SHALL be refused with a witness naming both tuples, and SHALL NOT be merged or renamed silently.

#### Scenario: Forced collision

- **GIVEN** a test derivation function truncated to force a collision
- **WHEN** both records are admitted
- **THEN** admission is refused and the witness lists both tuples

### Requirement: Canonical order for set-like sections

Under the identity profile, set-like sections SHALL serialize in ascending id order, and sequence meaning SHALL be carried only by explicit relations, never by array position.

#### Scenario: Permutation invariance

- **GIVEN** a valid descriptor and a permutation of its set-like arrays
- **WHEN** both canonical readers serialize each
- **THEN** all four outputs are byte-identical

### Requirement: Exact quantized geometry

Under the identity profile, geometry SHALL be integers in a declared quantum with a declared rounding rule, and the quantization SHALL be recorded as an explicit transform naming quantum, rule and extractor version.

#### Scenario: Rotation round trip

- **GIVEN** a quantized box and a declared 90-degree frame transform
- **WHEN** the box is transformed forward and back
- **THEN** the result equals the original with tolerance zero

### Requirement: Explicit relabeling

Migration from label ids SHALL emit a recorded old-to-new table as evidence and SHALL NOT alter any content value.

#### Scenario: Migrated descriptor

- **GIVEN** a valid label-id descriptor
- **WHEN** it is migrated to the identity profile
- **THEN** every content value is unchanged and the relabel table maps every old id
