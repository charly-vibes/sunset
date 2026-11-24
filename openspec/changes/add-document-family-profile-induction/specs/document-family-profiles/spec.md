## ADDED Requirements

### Requirement: Family profile artifacts

A learned document-family profile SHALL be a versioned artifact with a sha256
over its exact bytes declaring: family scope, induction input digests, compiled
rules, counterexample record, held-out validation record, and a caveats block.
A family profile SHALL NOT introduce descriptor sections, relation kinds, or
descriptor profile kinds.

#### Scenario: Complete inspectable artifact

- **GIVEN** an accepted family profile artifact
- **WHEN** its bytes are verified against the declared sha256 and read
- **THEN** all seven declared components are present, and the compiled rules are inspectable without running any learning machinery

#### Scenario: Artifact incompleteness is typed

- **GIVEN** a candidate profile artifact missing its held-out validation record
- **WHEN** the artifact is checked for acceptance
- **THEN** a typed refusal names the missing component

### Requirement: Deterministic compilation

Compilation from recorded inputs to rules SHALL be a pure function: identical
recorded inputs and compiler version SHALL produce byte-identical rules. The
extraction path SHALL apply only compiled rules and SHALL NOT perform model,
provider, or network inference during profile application.

#### Scenario: Recompilation reproduces rules

- **GIVEN** the same recorded observations, proposed model and compiler version
- **WHEN** compilation runs twice in separate processes
- **THEN** both runs emit byte-identical rules

#### Scenario: No inference while applying a profile

- **GIVEN** a compiled profile applied to a new document
- **WHEN** the application step completes
- **THEN** it records zero model, provider and network calls, and every emitted structure derives only from the compiled rules and recorded observations

### Requirement: Counterexample testing before acceptance

A candidate profile SHALL be tested against its recorded counterexample suite
before acceptance, and an unresolved counterexample SHALL keep the profile
rejected.

#### Scenario: Counterexample blocks acceptance

- **GIVEN** a candidate profile with one unresolved recorded counterexample
- **WHEN** acceptance is evaluated
- **THEN** the profile stays rejected and the witness names the failing case

### Requirement: Held-out edition validation

Profile acceptance SHALL require reconstruction validation on editions absent
from the induction input set, with the measured reconstruction agreement
recorded in the artifact. Induction-set performance alone SHALL NOT justify
acceptance, and a held-out validation record SHALL be a prerequisite for any
proposal to expand normative DSC core.

#### Scenario: Acceptance refused without held-out record

- **GIVEN** a candidate profile validated only on its induction editions
- **WHEN** acceptance is evaluated
- **THEN** acceptance is refused and the refusal names the missing held-out record

#### Scenario: Held-out editions are disjoint

- **GIVEN** a profile whose validation record names its held-out editions
- **WHEN** the edition digests are compared against the induction input digests
- **THEN** the sets are disjoint; any overlap is a typed refusal

### Requirement: Typed abstention

When a compiled profile's declared preconditions or evidence sufficiency fail
for a document, the wrapper SHALL abstain with a typed outcome naming the
unsatisfied condition and SHALL NOT emit profile-derived structure. Output
produced without a firing profile SHALL be labeled unprofiled.

#### Scenario: Insufficient evidence abstains

- **GIVEN** a document missing a declared required content class
- **WHEN** the profile is applied
- **THEN** the outcome is a typed abstention naming that condition, no profile-derived structure is emitted, and the emitted output is labeled unprofiled

### Requirement: Hypothesis-typed profile contributions

Profile-derived graphic-region candidates SHALL be recorded as typed hypotheses
carrying provenance naming the profile version used, SHALL NOT be represented
as source observations, and a projection of profile knowledge SHALL NOT be
applied without declared provenance naming source profile version, rules, scope
and losses.

#### Scenario: Graphic candidate stays hypothesis

- **GIVEN** a compiled profile proposes a graphic-region candidate on a page
- **WHEN** the contribution is recorded
- **THEN** it keeps hypothesis typing with provenance naming the profile version, and is never a source observation

#### Scenario: Projection without provenance is not applied

- **GIVEN** a profile-derived projection whose provenance declaration is missing
- **WHEN** the wrapper attempts to apply it
- **THEN** the projection is refused with a typed outcome, not applied

### Requirement: No core expansion by profiles

A family profile SHALL NOT redefine or extend core identity, relations,
canonical form, or validity rules, and its learning machinery SHALL remain
outside descriptor content. Promoting any profile-derived mechanism into
normative DSC core SHALL require a separate owner-approved change citing a
held-out validation record.

#### Scenario: Profile overreach refused

- **GIVEN** a profile rule that attempts to alter record identity or validity rules
- **WHEN** the profile is compiled or applied
- **THEN** the overreach is refused with a typed outcome

### Requirement: Caveats travel

A family profile artifact and every report citing profile-derived measurements
SHALL carry the provenance caveats declared at induction. Claims SHALL NOT be
made beyond the machinery that produced the numbers.

#### Scenario: Report inherits caveats

- **GIVEN** a report citing a measurement produced under a family profile
- **WHEN** the report is emitted
- **THEN** it carries the artifact's caveats block, and no accuracy or conformance claim appears beyond what the producing machinery supports
