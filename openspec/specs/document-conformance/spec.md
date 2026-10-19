# document-conformance Specification

## Purpose

Report per-instance outcomes (`valid`, `invalid`, `unsupported`, `ambiguous`)
separately from suite readiness (`passed`, `failed`, `incomplete`) and from
Specodelic lint. Fixture inventory records available vs missing. The reference
tests cover JSON descriptors only — not real PDF/EPUB ingestion, nor
independent reader agreement.
## Requirements
### Requirement: Separated reporting levels

THE system SHALL report Specodelic lint, instance validation, and suite
conformance as separate statuses.

#### Scenario: Lint pass is not conformance pass

- **WHEN** lint passes but suite checks are missing
- **THEN** suite status is `incomplete`, not `passed`

### Requirement: Stable typed error reasons

THE system SHALL produce stable typed reasons for negative fixtures.

#### Scenario: Dangling reference typed

- **GIVEN** `fixtures/invalid/dangling.json`
- **WHEN** the descriptor is validated
- **THEN** the error includes `dangling_reference`

### Requirement: Visible coverage of missing fixtures and implementations

THE system SHALL keep every missing carrier fixture and independent
implementation visible; `incomplete` SHALL NOT mean `passed`.

#### Scenario: Coverage gap explicit

- **GIVEN** `coverage.json`
- **WHEN** coverage is assessed
- **THEN** missing real PDF, real EPUB, and independent reader entries are
  explicit

### Requirement: Carrier fixture requirements for full conformance

THE full suite SHALL require a real scanned PDF, a real text PDF, an EPUB,
and an independent nonperiodical input.

#### Scenario: Suite without real carriers is incomplete

- **WHEN** only synthetic JSON fixtures exist
- **THEN** suite status is `incomplete`

### Requirement: Reader independence

Full conformance SHALL require two independently implemented descriptor readers
and a separate, declared comparison of extractor outputs. For the SAME valid
DSC input, readers SHALL preserve ids, array order and exact text and emit
identical canonical bytes. This tests serialization, not extraction quality.

#### Scenario: Readers of one snapshot

- **WHEN** two independent readers parse the same descriptor
- **THEN** their canonical bytes match exactly, including non-NFC text values

#### Scenario: Missing comparison or independent implementation

- **WHEN** only one reader exists, or a required comparison declaration is absent
- **THEN** full suite status is `incomplete`

### Requirement: Pinned projection and comparator

Different extractor outputs SHALL NOT be compared by whole-descriptor bytes.
Their evaluation SHALL pin a common projection and comparator by identifier,
version and artifact digest, plus source digest, implementation versions,
configuration/dependency fingerprints, tested observable subset, expected
observations, geometry renderer/tolerance and unresolved-case policy.

#### Scenario: Comparison without a pinned projection

- **WHEN** extractor outputs are evaluated without a declared projection and
  comparator pin
- **THEN** the check is incomplete, not a pass

### Requirement: Anchored matching without silent resolution

The projection SHALL match entities by resolved source anchors or an
independently reviewed explicit mapping, never by snapshot-local ids or label
similarity. It SHALL retain alternative interpretations as attributed sets and
list losses. Ambiguous matching SHALL remain unresolved, not become an arbitrary
pairing.

#### Scenario: Different local ids

- **WHEN** extractors identify the same anchored observation as `a7` and `b2`
- **THEN** the declared projection may match them by verified anchors without
  requiring descriptor byte equality or claiming cross-edition identity

#### Scenario: Competing interpretations

- **WHEN** outputs preserve opposing orders allowed by the reference oracle
- **THEN** comparison retains both with attribution and may pass; silently
  discarding an expected alternative fails

### Requirement: Comparator reporting completeness

The comparator SHALL report per-observable matches, false positives, false
negatives and unresolved cases against independently reviewed expectations.
A case passes only when every required observable matches an allowed expectation,
including explicitly allowed unresolved alternatives; any forbidden result fails.
Missing projection, oracle, scope or tolerance makes that check incomplete.

#### Scenario: False positives unreported

- **WHEN** a comparison omits false positives, false negatives or unresolved
  cases from its report
- **THEN** the case is incomplete, not passed

### Requirement: Pinned rerun divergence is explained

Pinned reruns of one extractor SHALL additionally report equality or explained
divergence; explained divergence is not a claim of deterministic reproduction.

#### Scenario: Pinned rerun diverges

- **WHEN** a pinned rerun of one extractor produces different output
- **THEN** the rerun reports the divergence with an explanation; it does not
  claim deterministic reproduction

### Requirement: EPUB reflow

THE system SHALL impose no obligatory fixed coordinates on EPUB descriptors;
spine order, non-linear entries, and navigation are distinct.

#### Scenario: EPUB descriptor valid

- **GIVEN** `fixtures/valid/epub.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Suite status transitions

THE system SHALL move suite status from `unexamined` to `passed` (all required
checks executed and passing), `failed` (any executed required check fails), or
`incomplete` (no executed check fails but required checks are missing).

#### Scenario: Missing required checks

- **WHEN** no executed check fails but required checks are missing
- **THEN** suite status is `incomplete`

### Requirement: First-consumer demonstration

Before claiming demonstrated adoption value, the project SHALL evaluate a
historical-periodical review workflow using one real multi-page issue, two
extractors, DSC exchange, and a separate reviewing consumer. The issue SHALL
include columns, continuation, native/OCR disagreement, and a deliberately
unsupported or unexamined feature.

#### Scenario: Untested product hypothesis

- **WHEN** no real carrier demonstration and native-output baseline exist
- **THEN** workflow benefit remains `unproven`, regardless of spec lint results

### Requirement: Independent annotations before extraction

Independent annotations SHALL be prepared before viewing extraction results,
with disagreements retained. The demo is narrower than full PDF/EPUB conformance
and SHALL NOT be reported as release conformance.

#### Scenario: Annotations prepared after extraction

- **WHEN** annotations were prepared after extraction results were viewed
- **THEN** the independent-annotation gate fails; the run may not claim
  demonstrated adoption value

### Requirement: Demonstration publication set

The evaluation SHALL publish source/license/digest, selected observations,
reviewer tasks, native-output baseline, pinned configurations, output artifacts,
and raw results.

#### Scenario: Publication set incomplete

- **WHEN** the evaluation omits pinned configurations, output artifacts or raw
  results
- **THEN** demonstrated adoption value is not claimable

### Requirement: Reference oracle precedes extraction

Before either extraction is evaluated, the reference set SHALL identify a
nonempty set of resolvable observations and separately list allowed unresolved
cases. Every expected-resolvable observation must resolve to its correct source
fragment; unresolved is acceptable only for those predeclared cases. Zero
incorrect anchors may be marked verified. All seeded disagreements and omissions
must survive export/import. Dropping any one is a functional failure.

#### Scenario: Unresolved case not predeclared

- **WHEN** an observation fails to resolve although it was not listed as an
  allowed unresolved case
- **THEN** the demonstration is a functional failure

### Requirement: Demonstration measured against native outputs

Review time, correct decisions, descriptor bytes and peak memory SHALL be
measured against the same review tasks using native extractor outputs.
Unsupported benefit claims are prohibited.

#### Scenario: Traceability succeeds but review becomes slower

- **WHEN** all functional gates pass but DSC increases measured review time
- **THEN** traceability may be reported as demonstrated; a speed benefit may not

