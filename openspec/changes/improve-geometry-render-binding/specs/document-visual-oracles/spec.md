## ADDED Requirements

### Requirement: Crop-box render binding

Oracle renders SHALL use the crop box, and the rendered pixel extent SHALL equal the extent computed from the extraction's declared page size, rotation and dpi; any difference SHALL yield `unknown` with reason `page-extent-mismatch`.

#### Scenario: Cropped page renders aligned

- **GIVEN** a page whose crop box differs from its media box
- **WHEN** the page is rendered and extracted word boxes are mapped through the frame
- **THEN** the rendered extent equals the declared extent and word boxes land on their rendered text

#### Scenario: Rotated page extent

- **GIVEN** a page with declared rotation 90 or 270
- **WHEN** the page is rendered
- **THEN** the expected extent uses swapped width and height and the rendered pixels match it

#### Scenario: Extent mismatch is typed

- **GIVEN** a render whose pixel extent differs from the declared extent
- **WHEN** the oracle runs
- **THEN** the outcome is `unknown` with reason `page-extent-mismatch`

### Requirement: Native frames resolve without a bridge

Native extraction SHALL emit frame records that `resolve_pixel_mapping` resolves directly to a pixel mapping, and a frame that fails to resolve for any fixture or variant SHALL fail the suite.

#### Scenario: Variant matrix resolves

- **GIVEN** each fixture rendered with rotations 0, 90, 180, 270, a non-origin crop box, and rotation plus crop
- **WHEN** the native frame record of each variant is resolved
- **THEN** every frame yields a pixel mapping and none yields `unresolvable_source_scope`

### Requirement: Render lineage labeling covers both paths

Each render SHALL record its renderer lineage, the poppler path labeled `independent` and the in-process PyMuPDF path labeled `correlated`, and oracle evaluation SHALL NOT read `correlated` renders.

#### Scenario: Review crop never feeds an oracle

- **GIVEN** a review crop rendered by the in-process PyMuPDF path
- **WHEN** oracle evaluation enumerates its inputs
- **THEN** the crop is absent and its lineage label reads `correlated`
