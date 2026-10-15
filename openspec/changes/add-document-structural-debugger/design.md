# Design: Sunset Lens

## Pipeline and boundaries

`Source viewer adapter + DSC descriptor + validator reports -> inspection index -> read-only overlay / structural graph / evidence panel -> comparison and counterexample export`.

The existing DSC descriptor is authoritative for claimed structure; the native document is authoritative for what its carrier actually contains, not for inferred semantic truth. The tool never silently rewrites the descriptor. Source adapter extraction and rendering are separately versioned; OCR is optional and never required for native PDF or EPUB.

## Core views

1. **Source**: PDF.js page coordinates, image pixel coordinates, or EPUB XHTML CFI/DOM range locators. Show source-native text and images and provenance; persist source-relative selectors, never transient EPUB viewport rectangles.
2. **Structure**: selected view, logical/physical regions, containment, relations, reading-order partial graph, alternative orders. Empty/unknown/ambiguous remain distinguishable.
3. **Evidence**: direct/derived/declarative origin, selector resolution state, transformation chain, loss/coverage and conflicting claims. One region may have several observations and one observation may support several claims.
4. **Diagnostics**: rule ID, severity, machine-checked/heuristic/manual status, smallest available witness, scope, provenance and navigation. Status categories: pass, violated, disputed, unsupported, unexamined (not a single success boolean).

## Coordinate contracts

- PDF: `(source_hash, page_index, crop_box or media_box reference, affine_transform_version, geometry)`; render rotation/crop/scale explicitly. Geometry is optional.
- Images/scans: `(source_hash, image_index, intrinsic_width,height, orientation, shape)`.
- EPUB: `(source_hash, spine_item_href, stable DOM/CFI or text selector, selector_version)` and per-render computed viewport geometry, never viewport coordinates as canonical references.
- Missing or unresolved locators produce an explicit diagnostic rather than a guessed selection. Multiple matches remain ambiguous.

## Interactive behaviors

Click an overlay selects the corresponding DSC identity. Selecting a tree node highlights all anchored source locations. Filters for physical/logical view, observation origin, rule status and comparison side do not change serialized descriptors. Relationship arrows are scoped to the chosen view. Reading order is a DAG/partial order; a topological order is only a display choice and is labeled as such. Focus and keyboard navigation mirror mouse operation; color is not the only error signal.

## Categorical debugger

Do not install a categorical programming runtime. Treat declared mappings as typed partial transformations, with composed result/error/evidence effects. Compare paths only if endpoints, declared observable scope, canonicalization and versioned equivalence policy are compatible. Verify identities and associativity on finite fixtures; expose mismatches or unsupported evaluation with witnesses. Never claim equivalence solely from matching names/titles or apparent layout similarity.

## Comparison result schema (proposal, not a change to DSC)

`{case_id, source_refs, descriptor_refs, mapping_chain_ids, observable_scope, comparator_id, outcome, differences[], evidence_refs[], limitations[]}`. `outcome` is `equivalent | different | disputed | unsupported | unexamined`; each difference cites path, normalized old/new values and locations where possible. `different` is not automatically a rule violation.

## Counterexample bundle

JSON manifest with source hashes and acquisition/redaction instructions; descriptor snapshot or immutable hash reference; diagnostic rule and version; smallest witnessed region/relation subgraph; relevant selectors; interpretation/mapping versions; expected vs observed results; deterministic replay command. No secret text by default: explicit redaction can omit bytes, recording `replayable=false` unless a secure fixture is supplied. Source license/rights remain attached.

## Test strategy

- Fixtures: Ahira/Diario de Poesía scanned page, native text PDF with rotated/cropped page, EPUB with reflow/navigation, hybrid PDF with native text and image-based regions, financial statement with sign-from-position.
- Inject mutations: dangling relation, containment cycle, swapped reading order, missing selector, duplicated IDs, unsupported source region, conflicting annotations, incorrect cross-edition equivalence.
- Golden results: deterministic diagnostic code, witness subgraph, expected selector resolution and comparator outcomes. Independent readers compare canonical output bytes after declared canonicalization.
- Browser/viewer tests: clicks, keyboard, scroll/zoom/rotation, EPUB viewport resize, disconnected/offline usage, malformed/huge inputs, adverse text, inaccessible source.
- Performance and accessibility: establish fixture-specific budgets from measured baselines rather than inventing numeric targets in advance. WCAG AA and keyboard operation are release requirements; audit results required.

## Risks and mitigations

- Viewer-induced geometric confusion: preserve locator-space transforms; test rotations/crops.
- Overclaiming truth: label validation vs source alignment vs human judgement.
- Rich UI dictating core: enforce adapter-only boundary; new DSC primitives require separate proposal.
- Reproducibility/privacy: content-addressed fixtures with redaction and explicit replay limitations.
- Proposal dependency drift: pin upstream spec versions and verify identifiers before implementation.

## Alternatives rejected

An integrated document editor (adds mutation semantics), OCR-first overlay (excludes native EPUB/PDF), and pre-emptively extending DSC wire (no counterexample yet).
