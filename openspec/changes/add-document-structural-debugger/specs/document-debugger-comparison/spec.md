# Document debugging comparisons and counterexamples

## ADDED Requirements

### Requirement: Scoped comparisons
The debugger SHALL compare representations only under compatible, declared observables and equivalence rules, preserving difference versus unknown.

#### Scenario: Text flattening loses transaction sign
- **GIVEN** two physical layouts with identical flattened text but different sign-bearing column positions
- **WHEN** text-only equivalence is requested for signed amounts
- **THEN** the result SHALL be unsupported or different, not equivalent, unless additional sign evidence is supplied.

### Requirement: Composition and diagram witnesses
The debugger SHALL test declared identity and associativity properties for compatible mappings and report minimal counterexamples or unsupported evaluators.

#### Scenario: Composition violates a preservation claim
- **GIVEN** composable transformations with a declared retained-feature scope
- **WHEN** the paths produce different scoped observables
- **THEN** the result SHALL identify the conflicting mapping path and observable, with applicable loss metadata.

### Requirement: Export a replayable counterexample
The debugger SHALL export enough pinned inputs, policy identifiers, witnesses and instructions to independently reproduce a diagnostic, or explicitly mark the result nonreplayable if source bytes are withheld.

#### Scenario: Confidential input redacted
- **GIVEN** a failing financial statement with private content
- **WHEN** the user exports a redacted counterexample without redistributable source bytes
- **THEN** the bundle SHALL omit the protected bytes and mark replayability limits instead of fabricating a reproducible source.

### Requirement: Independent-reader agreement
The debugger SHALL expose canonical comparison outputs suitable for independent conformance tests.

#### Scenario: Two readers
- **GIVEN** a frozen descriptor pair, declared policy and scope
- **WHEN** independent implementations compare them
- **THEN** normalized result codes and witness references SHALL agree.

### Requirement: Browser comparison and replay journey
The debugger SHALL let a reviewer inspect two attributed observations under an
explicit observable scope, export a disagreement and reopen it with pinned
inputs. It SHALL preserve unsupported and unknown outcomes and SHALL NOT infer
cross-reader region identity or choose a correct reading automatically.

#### Scenario: Inspect two human readings
- **GIVEN** two source-linked observations from the Diario A/B sheets
- **WHEN** the reviewer explicitly selects them and a supported comparison scope
- **THEN** both attributions, source loci, comparison policy, result and available witnesses SHALL be visible in the browser
- **AND** missing judgments SHALL remain unknown rather than agreement

#### Scenario: Reopen an exported disagreement
- **WHEN** the reviewer exports a disagreement and reopens it with the matching local PDF
- **THEN** pinned descriptors, source digest, observable scope, policy/version and witnesses SHALL reproduce the result and selected source locus
- **AND** source bytes SHALL be omitted by default and replayability limits SHALL be explicit

#### Scenario: Reopen without matching source
- **WHEN** a package is opened without its source or with a different PDF
- **THEN** the browser SHALL report unavailable or mismatched source and SHALL NOT claim successful source replay
