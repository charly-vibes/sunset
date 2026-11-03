# document-visual-oracles Specification

## Purpose
Define raster-based validation oracles: what independently rendered source
pages may establish about extracted observations, how renders and coordinate
frames are pinned, which checks stay correlated, and which claims raster
comparisons can never make. These checks complement — never replace — reader
agreement, extractor comparison and reviewed anchor mapping. They apply to
carriers with renderable pages (PDF); formats the pinned renderer cannot
rasterize (e.g. EPUB) are out of scope and report `unknown`.

## Requirements

### Requirement: Pinned render configuration

THE system SHALL record renderer name, version, DPI, page selection and binarization settings for every oracle render, and identical configurations SHALL reproduce byte-identical renders. An unavailable renderer SHALL yield a typed `unavailable` outcome instead of skipping the check.

#### Scenario: Reproducible render

- **WHEN** the same page is rendered twice from one recorded configuration
- **THEN** the render bytes are identical

#### Scenario: Renderer unavailable

- **WHEN** the pinned renderer executable is missing
- **THEN** the oracle result is `unavailable`, not `agree`

### Requirement: Declared frame mapping

A visual oracle SHALL map pixel coordinates to descriptor geometry only through a declared geometry profile frame. Comparisons under incompatible, missing or ambiguous frames SHALL produce `unknown`, never `agree` or `differ`.

#### Scenario: Rotated page

- **GIVEN** a descriptor with a declared rotated-page frame and pinned pixel tolerance
- **WHEN** the oracle compares region masks against the rendered page
- **THEN** the comparison uses that frame's mapping, not a guessed coordinate convention

#### Scenario: Missing frame

- **WHEN** a region references no declared geometry frame
- **THEN** its comparison outcome is `unknown`

### Requirement: Labeled evidence class

Every oracle result SHALL carry an evidence class: `correlated` when extraction and rendering share an implementation lineage, `independent` otherwise. Correlated results SHALL NOT support accuracy claims; they demonstrate sensitivity only.

#### Scenario: Shared library

- **GIVEN** extraction and render both use PyMuPDF
- **WHEN** the oracle reports an outcome
- **THEN** the result is labeled `correlated` and no accuracy claim is recorded

#### Scenario: Distinct renderer

- **GIVEN** PyMuPDF extraction rendered independently by poppler
- **WHEN** the oracle reports an outcome
- **THEN** the result may be labeled `independent`

### Requirement: Scoped property claims

Each oracle SHALL declare the single property it evaluates, such as ink coverage or region alignment. A passing oracle SHALL NOT establish text correctness, reading order, semantic grouping or visual completeness, and every reported outcome SHALL carry the evaluated property as a field,
limiting the claim to that property.

#### Scenario: Coverage pass with wrong order

- **GIVEN** an ink-coverage oracle passes on a page whose extracted reading order is wrong
- **THEN** the report records the ink-coverage pass while reading order remains unestablished

### Requirement: Mutation-validated sensitivity

An oracle property SHALL be demonstrated, using seeded mutations (shift, omission, duplication, wrong frame) on pinned carriers, to detect each defect class it claims. Properties without a recorded mutation demonstration SHALL be `uncalibrated` and SHALL NOT gate any decision — conformance labeling, demonstration-suite acceptance and aggregate outcomes are the only decisions an oracle could gate, and none may consume uncalibrated results.

#### Scenario: Seeded shift detected

- **GIVEN** every region box is shifted 12 pixels in a mutation fixture
- **WHEN** the alignment oracle runs
- **THEN** the page outcome is `differ` and the property is eligible for calibration

#### Scenario: Undemonstrated class

- **WHEN** a property claims omission detection without a seeded-omission demonstration
- **THEN** the property stays `uncalibrated` and cannot gate any decision

### Requirement: Calibrated thresholds with per-page outcomes

Thresholds SHALL come from recorded calibration over varied pinned carriers, and outcomes SHALL be reported per page and per property as `agree`, `differ`, `unknown` or `unavailable`. No aggregate SHALL report pass while any page is `unknown` or `unavailable`, or its property `uncalibrated`.

#### Scenario: Faint scan

- **GIVEN** a degraded scan page below render-confidence limits
- **WHEN** the oracle runs
- **THEN** the page outcome is `unknown` and the aggregate does not report pass

### Requirement: No silent resolution

Visual disagreements SHALL be retained and attributed to their source regions. No oracle SHALL elect a winner, smooth differences or mutate extracted observations.

#### Scenario: Mask disagreement

- **WHEN** an extracted region mask disagrees with the rendered ink
- **THEN** the disagreement is retained with region identifiers and neither reading is replaced

### Requirement: Distinct evidence class in demonstrations

Visual oracle results SHALL be recorded separately from reader agreement, extractor comparison and reviewed anchor mapping, and SHALL NOT substitute for any of them in conformance labels or demonstration suites.

#### Scenario: Oracles cannot complete a suite

- **GIVEN** a demonstration suite with passing visual oracles but no independent readers
- **WHEN** conformance is labeled
- **THEN** the label stays `incomplete`, unchanged by the oracle results
