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

## PDF working-example decisions (2026-10-27, proposed)

### Test shape before implementation
Inputs are committed Diario PDF bytes and its two human sheets. Outputs are
validated DSC 0.3 descriptors, a browser-visible linked source/structure/evidence
workspace, and a replay package. Import tests enumerate every input region and
verify geometry, page and attribution. Real Chromium tests select with pointer
and keyboard, exercise zoom/rotation, compare A/B, download, and reopen. A
missing browser/runtime must fail the milestone command rather than skip.

### Import boundary
Use a separate consumer-side human-sheet adapter, not an extraction improvement
claim. Pin source and sheet digests; namespace local IDs by sheet digest and
source index. Preserve original sheets byte-for-byte. Convert normalized boxes
through recorded page frames to a declared DSC geometry profile; retain original
coordinates in pinned provenance. Missing/invalid frames and source mismatch
produce typed refusal or explicit unresolved observations, never guessed boxes.
Human labels remain attributed claims; blank types and derived ranks cannot
become independent human semantic/order judgments. Machine type sidecars stay
separate. Geometry import does not resolve extraction LOSS automatically.

### Browser boundary and reuse
Reuse dsc03 inspection, locators and comparison; reuse the vendored PDF.js and
viewer interaction patterns from the reader workspace where practical. The
annotator remains a collection tool; Lens is a separate read-only consumer.
A local Python entry point may serve the viewer and bridge existing modules;
no mandatory external service or new framework is required. Source and descriptor
bytes are hashed before and after each tested journey.

### Comparison and replay
A/B observations coexist without inferred region identity from position, label
or overlapping boxes. Explicitly select the pair and observable being compared;
unsupported equivalence and absent judgments remain unknown. A replay package
pins both descriptors, source digest, scope, policy version, result and witnesses.
Opening with an externally supplied matching PDF is sufficient for local replay;
source bytes are not bundled by default. Missing/incorrect source is displayed
as nonreplayable/source mismatch. Reopening must reproduce result and locus.

### Rollout
Three outcome slices in order: source-linked human region inspection; attributed
comparison; exported disagreement reopened. Each uses red→green tests, with
optional tidying separately ticketed and committed. No core schema change is
authorized; an unrepresentable case stops with a minimized counterexample.
