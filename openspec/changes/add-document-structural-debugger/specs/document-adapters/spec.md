# Human observation sheet import

## ADDED Requirements

### Requirement: Attributed human region import
A human-sheet adapter SHALL import existing region observations into valid DSC
0.3 without modifying source sheets or requiring DSC core wire changes. Every
input region SHALL be preserved with pinned source/sheet provenance, or accounted
for by an explicit typed unresolved/refusal result. Local IDs SHALL be scoped to
the originating sheet; blank types, machine-inferred types and derived order
SHALL NOT become independent human judgments.

#### Scenario: Preserve the accepted human geometry corpus
- **GIVEN** the six owner-accepted sheets containing 203 regions and their matching PDFs
- **WHEN** the adapter imports the sheets
- **THEN** every region SHALL retain its sheet attribution, source page and original geometry provenance
- **AND** each resolvable box SHALL use a declared coordinate profile and a validated DSC selector
- **AND** same local IDs from different sheets SHALL remain distinct

#### Scenario: Refuse unsupported frame conversion
- **WHEN** a sheet has a mismatched source digest, invalid box or missing required frame
- **THEN** the adapter SHALL return a typed refusal or unresolved observation with the input region reference instead of guessing geometry
