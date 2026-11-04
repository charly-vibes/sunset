# document-adapters delta: distinguish-native-extraction-outcomes

## ADDED Requirements

### Requirement: Distinct native extraction outcomes

Every native extraction run SHALL report exactly one outcome: `text-complete` (every selected page contributed retained native text), `text-with-gaps` (some selected pages or regions are unexamined or failed while others contributed text), or `no-text-read` (no selected page contributed retained text). Non-text observations (images, vectors, annotations) SHALL be recorded in coverage rows and SHALL NOT collapse these outcomes.

#### Scenario: Logo-only approximation

- **GIVEN** a page with a native text layer and an image region
- **WHEN** native extraction completes its supported observations
- **THEN** the outcome is `text-complete` and the image is recorded as `approximated` in coverage rows

#### Scenario: Textless page among text pages

- **GIVEN** a selection with one textless page and pages with retained text
- **WHEN** native extraction completes
- **THEN** the outcome is `text-with-gaps` and the textless page stays explicitly unexamined

### Requirement: Outcome exit-code contract

The digitization CLI SHALL return exit 0 for `text-complete` and exit 2 for `text-with-gaps` and `no-text-read`. `visual_completeness: not-established` SHALL be reported independently and SHALL NOT influence the exit code. Scripts SHALL distinguish gap-bearing outcomes by the reported status, not by exit code.

#### Scenario: Textless selection does not fail differently

- **GIVEN** a selection where no page has a text layer
- **WHEN** the CLI reports the run outcome
- **THEN** the exit code is 2 and the status is `no-text-read`

#### Scenario: Visual completeness does not drive exit

- **GIVEN** a `text-complete` run with `visual_completeness: not-established`
- **WHEN** the CLI exits
- **THEN** the exit code is 0

### Requirement: Outcome vocabulary versioning

Native run manifests SHALL declare the outcome vocabulary version. A tool reading a manifest whose outcome vocabulary it does not support SHALL report `unsupported-version` and SHALL NOT infer outcome semantics from coverage rows or exit codes.

#### Scenario: Legacy manifest rejected explicitly

- **GIVEN** a manifest carrying only the legacy `partial` status
- **WHEN** inspect or replay reads it
- **THEN** the tool reports `unsupported-version` with exit 4 instead of guessing the outcome
