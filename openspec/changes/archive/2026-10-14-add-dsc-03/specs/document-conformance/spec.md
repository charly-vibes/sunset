# document-conformance (0.3 delta)

## ADDED Requirements

### Requirement: Layered validity reporting

Reports SHALL distinguish `schema_valid`, `source_coverage`, and
`interpretation_assessment` independently, and report profile resolution
separately. A schema-valid declaration whose profile cannot be resolved SHALL
NOT be presented as a verified selector, geometry frame or coverage result.

#### Scenario: Three-way report

- **WHEN** a descriptor with omissions and disputed interpretations is reported
- **THEN** all three layers and any profile-resolution failures are reported
  separately

### Requirement: Adversarial corpus

The 0.3 conformance corpus SHALL cover columns, page continuation, shared
pages, mixed OCR/native text, poetry, EPUB footnotes, conflicting
interpretations, coordinate transforms, roundtrip, omission, and replay.

#### Scenario: Corpus gate

- **WHEN** the corpus is missing a listed adversarial case
- **THEN** suite status is `incomplete`

### Requirement: Ambiguity can pass

The system SHALL pass a test that records two incompatible supported
hypotheses without selecting a winner.

#### Scenario: Two hypotheses recorded

- **WHEN** a fixture records two incompatible supported interpretations
- **THEN** the check passes with both preserved

### Requirement: No false claims

v0.2 fixture checks SHALL NOT be reported as v0.3 contract validation or
real-carrier conformance.

#### Scenario: Honest version scoping

- **WHEN** only 0.2 fixtures have been exercised
- **THEN** reports claim 0.2 coverage only

## MODIFIED Requirements

### Requirement: Reader independence

Full conformance SHALL require two independently implemented descriptor readers
and a separate, declared comparison of extractor outputs. For the SAME valid
DSC input, readers SHALL preserve ids, array order and exact text and emit
identical canonical bytes. This tests serialization, not extraction quality.

Different extractor outputs SHALL NOT be compared by whole-descriptor bytes.
Their evaluation SHALL pin a common projection and comparator by identifier,
version and artifact digest, plus source digest, implementation versions,
configuration/dependency fingerprints, tested observable subset, expected
observations, geometry renderer/tolerance and unresolved-case policy. The
projection SHALL match entities by resolved source anchors or an independently
reviewed explicit mapping, never by snapshot-local ids or label similarity.
It SHALL retain alternative interpretations as attributed sets and list losses.
Ambiguous matching SHALL remain unresolved, not become an arbitrary pairing.

The comparator SHALL report per-observable matches, false positives, false
negatives and unresolved cases against independently reviewed expectations.
A case passes only when every required observable matches an allowed expectation,
including explicitly allowed unresolved alternatives; any forbidden result fails.
Missing projection, oracle, scope or tolerance makes that check incomplete.
Pinned reruns of one extractor SHALL additionally report equality or explained
divergence; explained divergence is not a claim of deterministic reproduction.

#### Scenario: Readers of one snapshot

- **WHEN** two independent readers parse the same descriptor
- **THEN** their canonical bytes match exactly, including non-NFC text values

#### Scenario: Different local ids

- **WHEN** extractors identify the same anchored observation as `a7` and `b2`
- **THEN** the declared projection may match them by verified anchors without
  requiring descriptor byte equality or claiming cross-edition identity

#### Scenario: Competing interpretations

- **WHEN** outputs preserve opposing orders allowed by the reference oracle
- **THEN** comparison retains both with attribution and may pass; silently
  discarding an expected alternative fails

#### Scenario: Missing comparison or independent implementation

- **WHEN** only one reader exists, or a required comparison declaration is absent
- **THEN** full suite status is `incomplete`

## ADDED Requirements

### Requirement: First-consumer demonstration

Before claiming demonstrated adoption value, the project SHALL evaluate a
historical-periodical review workflow using one real multi-page issue, two
extractors, DSC exchange, and a separate reviewing consumer. The issue SHALL
include columns, continuation, native/OCR disagreement, and a deliberately
unsupported or unexamined feature. Independent annotations SHALL be prepared
before viewing extraction results, with disagreements retained. The demo is
narrower than full PDF/EPUB conformance and SHALL NOT be reported as release
conformance.

The evaluation SHALL publish source/license/digest, selected observations,
reviewer tasks, native-output baseline, pinned configurations, output artifacts,
and raw results. Before either extraction is evaluated, the reference set SHALL
identify a nonempty set of resolvable observations and separately list allowed
unresolved cases. Every expected-resolvable observation must resolve to its
correct source fragment; unresolved is acceptable only for those predeclared
cases. Zero incorrect anchors may be marked verified. All seeded disagreements
and omissions must survive export/import.
Dropping any one is a functional failure. Review time, correct decisions,
descriptor bytes and peak memory SHALL be measured against the same review
tasks using native extractor outputs. Unsupported benefit claims are prohibited.

#### Scenario: Traceability succeeds but review becomes slower

- **WHEN** all functional gates pass but DSC increases measured review time
- **THEN** traceability may be reported as demonstrated; a speed benefit may not

#### Scenario: Untested product hypothesis

- **WHEN** no real carrier demonstration and native-output baseline exist
- **THEN** workflow benefit remains `unproven`, regardless of spec lint results
