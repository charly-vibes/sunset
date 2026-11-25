# document-evidence

## MODIFIED Requirements

### Requirement: Selector outcome codes

With a resolved profile, malformed locators/ranges SHALL yield
`invalid_selector`; missing profile references SHALL yield
`dangling_reference`; unavailable declared profiles SHALL yield
`unsupported_profile` at resolution, not invented interpretation. Replay
SHALL additionally yield `version_mismatch` when a selector's pinned
`source_sha256` differs from the current descriptor source digest, and
SHALL NOT apply the selector or return `replayed` in that case.

#### Scenario: Malformed locator under known profile

- **WHEN** a resolved text profile receives a reversed or out-of-bounds range
- **THEN** selector validation returns `invalid_selector`

#### Scenario: Revised descriptor after anchoring

- **GIVEN** an evidence record whose selector pins digest `aaa…`
- **WHEN** the descriptor's source digest is now `bbb…`
- **THEN** replay returns `version_mismatch` naming both digests; the
  revised content is never reinterpreted and no `replayed` status is emitted

## ADDED Requirements

### Requirement: Anchor scheme version and replay digest equality

Text-range/anchor selector profiles SHALL declare an `anchor_scheme_version`;
profiles lacking it SHALL be refused at resolution. Replay SHALL verify each
internal selector's pinned `source_sha256` equals the descriptor source
digest BEFORE applying it, returning `version_mismatch` otherwise; a
selector SHALL never apply to revised content. No `ambiguous` replay status
exists: pinned-profile application is deterministic; ambiguity belongs to
projection comparison and locator resolution.

#### Scenario: Profile without a scheme version

- **WHEN** a selector profile is resolved that omits `anchor_scheme_version`
- **THEN** the profile is refused with a reason naming the missing field,
  before any selector application

#### Scenario: Digest-equal replay is unchanged

- **GIVEN** a descriptor whose source digest equals every selector pin
- **WHEN** an evidence record is replayed
- **THEN** the outcome is `replayed` exactly as before this change
