# Change: Bind visual-oracle renders to the crop box and unify the frame vocabulary

## Why

The raster visual oracle renders through poppler `pdftoppm` (`dsc03/visual/render.py`) while extraction uses PyMuPDF, whose word boxes are relative to the crop box. `pdftoppm` is invoked without `-cropbox`, so it renders the media box: on a cropped page the oracle would report false disagreements. Measured on a cropped variant of `agentic-patterns-excerpt.pdf` (agent-executed, chat session 2026-11-24): 23 of 139 words landed on empty pixels; 53 of 139 with rotation added; with `-cropbox`, 1 of 139. A second, verified gap: native extraction emits frames as `source_frame` / `target_frame` / `source_to_target` (`digitization/native.py` page-map), while the oracle's `resolve_pixel_mapping` expects `source_scope` / `origin` / `axes` / `scale` / `rotation` / `crop` (`dsc03/visual/frames.py`) and returns `unresolvable_source_scope` for native frames — a human or agent must bridge the vocabularies by hand. Both facts re-verified against HEAD on 2026-11-24. The repository now also has a second render path (`digitization/render.py`, in-process PyMuPDF, correlated lineage with the extractor), which this change names explicitly so evidence-class labeling stays honest.

## What Changes

- The oracle renders with the crop box, and the rendered pixel extent is checked against the extent computed from the extraction's declared page record (size, rotation, dpi); any difference yields typed `unknown` with reason `page-extent-mismatch`.
- Native extraction emits a frame record that `resolve_pixel_mapping` resolves directly; no hand-written bridge.
- A deterministic rotation/crop-box variant matrix (0/90/180/270, a non-origin crop box, rotation plus crop) is added to the mutation suite; frame resolution must succeed for every fixture and variant.
- The two render paths are labeled: poppler render → `independent` evidence class; in-process PyMuPDF render (digitization review crops) → `correlated`, as the existing labeling already intends.

## Impact

- Affected specs: `document-visual-oracles` (requirements ADDED under this change's deltas; the deployed requirement *Calibrated thresholds with per-page outcomes* is NOT modified by this change — any MODIFIED reconciliation stays deferred, see Non-goals).
- Affected code: `dsc03/visual/render.py`, `dsc03/visual/frames.py`, `dsc03/visual/reports.py`, `digitization/native.py` (page-map frame record), `tests/tracer/` (variant matrix).
- No conformance label changes; results are machinery-level and agent-executed.

## Non-goals (deferred from the reviewed proposal set)

Independent box agreement, scale-free ink statistics, per-page sensitivity certificates, render caching, and tight-ink snapping are deferred: they depend on `add-anchor-derived-identity` (quantized boxes) and `add-scale-complete-regions` (word-level regions). Recorded design tension to resolve when they are proposed: the sensitivity-certificate requirement must not re-introduce aggregate blocking via a permanent `uncertified` state on dense pages (review finding EDGE-002: aggregate blocking); the containment statistic must declare a tolerance rather than refuse sub-point box overhangs (review finding EDGE-005: containment overhang).
