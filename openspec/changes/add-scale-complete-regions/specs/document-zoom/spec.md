## ADDED Requirements

### Requirement: Scale ladder with checked containment

Scopes SHALL be ordered document, page, block, line, word, span; a child scope SHALL lie within its parent by raw-text interval containment and by box containment within the declared geometry tolerance; a violation beyond tolerance SHALL be refused with a witness naming child and parent, and sub-tolerance overhang SHALL be recorded, not refused.

#### Scenario: Word outside its line

- **GIVEN** a word whose raw interval exceeds its line interval
- **WHEN** the descriptor is validated
- **THEN** it is refused with a witness naming the word and the line

#### Scenario: Sub-tolerance overhang is kept

- **GIVEN** a word box overhanging its line box by less than the declared tolerance
- **WHEN** the descriptor is validated
- **THEN** it is accepted and the overhang is recorded on the region

### Requirement: Native regions below page level

The native adapter SHALL represent each retained word and line as a region with a selector binding a raw-text interval and a page-frame box, and any side file SHALL be derived from those regions.

#### Scenario: Side file is a derived export

- **GIVEN** a native run with the region table
- **WHEN** the line-map export is deleted and regenerated from the descriptor
- **THEN** the regenerated file is byte-identical to the original

### Requirement: Zoom in is restriction on the ladder

Zooming in on a scope SHALL return exactly the regions within that scope and their internal relations, SHALL record each excluded relation as coverage loss, and restricting twice SHALL equal restricting once to the inner scope, using the restriction semantics of document-views.

#### Scenario: Composed restriction

- **GIVEN** scopes V within U within the document
- **WHEN** the document is restricted to U and then V, and directly to V
- **THEN** both results have identical canonical bytes

### Requirement: Lift without guessing

A claim SHALL be attached at the smallest scope containing all its anchors, and when several scopes qualify equally the result SHALL be a typed ambiguity with no scope selected.

#### Scenario: Anchors across two lines

- **GIVEN** a claim anchored to words on two adjacent lines
- **WHEN** the claim is lifted
- **THEN** it attaches to the smallest block or page containing both lines
