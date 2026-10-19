# document-adapters Specification

## Purpose

Preserve declared source-native observations via an applicable adapter
without requiring OCR. An adapter result is separate from document validity;
one page may combine text glyphs, raster images, vector shapes, and OCR
observations, each with its own provenance. Source carrier is not a binary
native/scanned class. Format-specific adapters are optional modules;
structured JSON is the mandatory baseline adapter. PDF native and EPUB adapter
execution is not claimed.
## Requirements
### Requirement: Adapter dispatch

THE system SHALL select one applicable adapter by declared format and version,
and SHALL NOT conjoin mutually exclusive carrier rules.

#### Scenario: Mixed-carrier descriptor dispatches

- **GIVEN** `fixtures/valid/mixed-pdf.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: PDF observation typing

THE system SHALL support PDF observation types including page, glyph, raster,
vector, and annotations, each with per-observation source evidence.

#### Scenario: Mixed PDF observations valid

- **GIVEN** `fixtures/valid/mixed-pdf.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: EPUB observation typing

THE system SHALL support EPUB observation types including manifest, XHTML
tree, spine sequence with `linear` flag, navigation, and links, with no
fabricated page geometry.

#### Scenario: EPUB descriptor valid without page geometry

- **GIVEN** `fixtures/valid/epub.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid` with no fixed page geometry

### Requirement: Structured JSON baseline

THE system SHALL require structured JSON observation import as the baseline
adapter; HTML, Markdown, and CSV adapters are optional independently declared
profiles.

#### Scenario: JSON-only descriptor valid

- **GIVEN** `fixtures/valid/two-regions.json`
- **WHEN** the descriptor is validated
- **THEN** the outcome is `valid`

### Requirement: Preservation declaration

THE system SHALL require each adapter to declare its capabilities and
preserved fields, and its omitted or approximated fields.

#### Scenario: Capabilities declared

- **WHEN** an adapter result is produced
- **THEN** preserved and omitted/approximated fields are both declared

### Requirement: Adapter replay metadata

THE system SHALL require adapter results to record source sha256, adapter id
and version, configuration digest, and dependencies, or an explicit
`unavailable` fingerprint.

#### Scenario: Unavailable fingerprint is typed

- **WHEN** an adapter cannot produce a configuration digest
- **THEN** it records the literal `unavailable`, never a fabricated value

### Requirement: Typed failure results

THE system SHALL report `unsupported`, `error`, and `ambiguous` as typed
results; partial output SHALL never masquerade as complete.

#### Scenario: Unsupported carrier result

- **GIVEN** `fixtures/results/unsupported.json`
- **WHEN** the result is checked
- **THEN** the result status is `unsupported`

### Requirement: Adapter outcome states

THE system SHALL distinguish adapter outcomes `observed` (adapter selected,
extraction complete, preservation checks pass), `unsupported` (no matching
adapter or blocked encryption), `ambiguous` (multiple incompatible
observations), and `failed` (adapter error or malformed input).

#### Scenario: No matching adapter

- **WHEN** no adapter matches the declared carrier format
- **THEN** the outcome is `unsupported`

### Requirement: Independent coverage inventory

An adapter-produced descriptor SHALL declare exactly one `carrier-inventory`
profile and one `adapter-manifest` profile. A descriptor without an adapter
run MAY have neither, with empty coverage; its source coverage is `unexamined`.
Having only one declaration is invalid. Profiles are pinned by document-core's
declaration mechanism. Inventory selection SHALL be independent of the adapter's
supported feature list; an adapter SHALL NOT shrink it to hide unsupported work.

#### Scenario: Inventory shrunk to hide unsupported work

- **WHEN** an adapter's supported feature list excludes a source feature
- **THEN** the inventory is still declared with that feature; shrinking it to
  hide unsupported work is invalid

### Requirement: Coverage inventory artifact grammar

The inventory artifact SHALL be JSON with exactly `version`, `source_format`,
`features`. Features are unique objects with exactly `name`, `scope_kind`, where
scope_kind is `document|pdf-page|epub-resource`. Names are nonempty namespaced
strings.

#### Scenario: Inventory artifact carries an extra field

- **WHEN** an inventory artifact includes a field other than `version`,
  `source_format` or `features`
- **THEN** coverage verification fails with `invalid_coverage_inventory`

### Requirement: Minimum feature inventory per format

For PDF, the minimum inventory SHALL include `pdf:glyphs`, `pdf:images`,
`pdf:vectors`, `pdf:annotations` (page scopes), and `pdf:attachments` (document
scope). EPUB SHALL include `epub:manifest`, `epub:spine`, `epub:navigation`
(document), and `epub:resources` (resource scopes). Structured JSON SHALL include
`json:regions`, `json:contents`, `json:relations`, `json:evidence` (document).
Additional features MAY be added; omitting these minimums is invalid inventory.

#### Scenario: Inventory conceals a feature

- **WHEN** a PDF inventory omits `pdf:attachments`
- **THEN** coverage verification fails with `invalid_coverage_inventory`

### Requirement: Adapter manifest grammar

The adapter manifest SHALL be JSON with exactly `version`, `adapter_id`,
`adapter_version`, `source_format`, `features`; features is a unique array of
supported inventory feature names. Metadata strings are nonempty, profile and
artifact versions SHALL match, and source_format SHALL match the descriptor.
Manifest features outside the inventory are invalid.

#### Scenario: Adapter manifest mismatches the descriptor

- **WHEN** an adapter manifest repeats a feature name, omits a version, or
  declares a source_format other than the descriptor's
- **THEN** coverage verification fails with `invalid_coverage`

### Requirement: Manifest-bounded coverage claims

Every inventory feature, including ones not supported by the adapter, SHALL
receive coverage. An entry claiming `preserved`, `transformed` or
`approximated` SHALL name a feature in the manifest; omission, unsupported and
unexamined outcomes remain available for all inventory features.

#### Scenario: Adapter does not support attachments

- **WHEN** a PDF adapter's manifest lists glyphs but not attachments
- **THEN** attachment coverage is still required and cannot be omitted

### Requirement: Coverage entry identity and pinning

Coverage entries SHALL have exactly `inventory_id`, `manifest_id`, `feature`,
`scope`, `status`, `reason`, `adapter_id`, `adapter_version`, `config_sha256`.
The first two reference the corresponding declared profiles; feature comes
from the inventory; adapter identity/version SHALL match the manifest and
config_sha256 SHALL be lowercase hex of length 64 or `unavailable`.

#### Scenario: Coverage entry with an undeclared field

- **WHEN** a coverage entry carries a field other than the nine declared ones
- **THEN** the descriptor is invalid

### Requirement: Single-run coverage entries

All entries in a descriptor SHALL describe one adapter run and the same
configuration. Multiple runs SHALL use separate snapshots rather than
conflicting dispositions.

#### Scenario: Entries span two adapter runs

- **WHEN** a descriptor mixes coverage entries from two adapter runs or two
  configurations
- **THEN** the entries are invalid; a second run is recorded as a separate
  snapshot, not as conflicting dispositions

### Requirement: Coverage scope grammar

Scope SHALL identify a source portion independently of extracted regions:
`document` for document features, `page:N` (1-based, no leading zeros) for PDF
pages, or `resource:PATH` for EPUB archive members (exact case-sensitive archive
path). The scope kind determines the grammar. Duplicate/ambiguous member paths
prevent complete inventory enumeration. PDF page scopes cover every source
page; EPUB resource scopes cover every non-directory archive member, including
unsupported assets.

#### Scenario: Malformed page scope

- **WHEN** a coverage entry names the scope `page:01` or an EPUB archive path
  that differs only in letter case
- **THEN** the entry is invalid under the scope grammar

### Requirement: Complete scope enumeration

Enumeration SHALL be checked against source bytes. If it cannot be completed,
exactly one `*` scope with `unexamined` status SHALL replace all entries for
that feature; no guessed finite scope list is allowed. An enumerated empty
domain has no per-unit entries and is reported as empty, not as observed
content.

#### Scenario: Unknown scope count or duplicate dispositions

- **WHEN** page enumeration cannot finish
- **THEN** the feature has one `*` / `unexamined` entry
- **AND** duplicate page entries or combining `*` with page entries is invalid

### Requirement: Unique coverage dispositions

There SHALL be exactly one disposition per `(inventory_id,feature,scope)`.
Duplicate entries are invalid even if statuses agree. Status is
`preserved|transformed|approximated|omitted|unsupported|unexamined`; reason is
nonempty except for `preserved`.

#### Scenario: Same scope dispositioned twice

- **WHEN** two coverage entries describe the same
  `(inventory_id,feature,scope)`
- **THEN** the descriptor is invalid, even if both entries agree

### Requirement: Least-preserving status precedence

For a scope containing mixed outcomes, the least-preserving status SHALL apply
using this precedence, highest first:
`unexamined > unsupported > omitted > approximated > transformed > preserved`.
Reason SHALL identify the partial loss. The same rule computes feature-wide
summary status over all scopes; unknown scope enumeration is always unexamined.
Summaries SHALL NOT replace the per-scope entries or imply completeness outside
the inventory.

#### Scenario: One page omitted

- **WHEN** pages 1 through 9 preserve glyphs and page 10 omits them
- **THEN** ten entries identify those scopes, page 10 explains the loss, and
  glyph summary status is `omitted`, not `preserved`

#### Scenario: Partial loss within a page

- **WHEN** half the glyphs on page 1 are retained and half omitted
- **THEN** `page:1` is `omitted` with a partial-loss explanation

### Requirement: Absence and unavailability honesty

Features absent from the source SHALL be preserved only after verified
inspection establishes absence; `unavailable` means replay unverifiable.

#### Scenario: Preserved without verified absence

- **WHEN** coverage marks a feature `preserved` although its absence in the
  source was never verified by inspection
- **THEN** that disposition is invalid

### Requirement: Declared coordinate frames

A geometry profile SHALL define named frames with units, origin, axes, scale,
rotation/crop mapping and source page/resource binding. It SHALL specify how
integer coordinates represent any subunit precision. A resolved profile lacking
the named frame yields `invalid_geometry_frame`; an unavailable declared
profile yields `unsupported_profile`. Non-axis-aligned approximations SHALL
be declared in coverage rather than claimed as exact rectangles.

#### Scenario: Rotated source

- **WHEN** a frame describes a rotated/cropped PDF page
- **THEN** the verifier uses that frame's mapping and the reference case's
  pinned renderer and pixel tolerance, not a guessed coordinate convention

### Requirement: Partial results carry loss accounting

A valid descriptor SHALL NOT prove complete observation. Reports SHALL retain
all per-scope dispositions, inventory/manifest digests and enumeration results.
Missing entries, duplicate scopes or manifest mismatches yield
`invalid_coverage`; unavailable inventories yield unexamined source coverage.
No aggregate SHALL claim preservation when a required scope was not examined.

#### Scenario: Valid but incomplete

- **WHEN** schema validation passes but a required page's coverage is absent
- **THEN** source coverage verification fails with `invalid_coverage`, separately
  from the valid schema result

