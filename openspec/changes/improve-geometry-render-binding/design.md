## Context

`dsc03/visual/render.py` shells out to poppler `pdftoppm` as the independent-lineage renderer (deployed spec: Pinned render configuration; design D2). PyMuPDF extraction coordinates are crop-box-relative; `pdftoppm` without `-cropbox` renders the media box. `resolve_pixel_mapping` (`dsc03/visual/frames.py`) parses `source_scope` strings and refuses everything else as `unresolvable_source_scope`; native page-map records carry `source_frame` / `target_frame` / `source_to_target` / `source_origin` / `source_dimensions` instead. Separately, `digitization/render.py` renders in-process with PyMuPDF — same lineage as the extractor, so its crops are correlated evidence by construction and must stay out of oracle evaluation.

## Goals / Non-Goals

Goals: no false disagreements on cropped pages; native frames resolve without a bridge; variant coverage in the mutation suite; honest lineage labels for both render paths.

Non-Goals: replacing the poppler renderer; text correctness; visual completeness; the deferred geometry statistics (box agreement, scale-free stats, certificates, cache, snapping — see proposal Non-goals).

## Decisions

1. **Render with the crop box.** `pdftoppm -cropbox` (poppler ≥ 0.26 supports the flag). Alternative considered: render media box and transform coordinates — rejected, it duplicates crop math that both tools already implement differently.
2. **Extent binding.** Expected pixel extent is `ceil(width_pt * dpi / 72)` × `ceil(height_pt * dpi / 72)` — matching poppler pdftoppm's render convention after declared rotation — for rotations 90 and 270 the rendered extent swaps width and height — taken from the extraction's page record (never from the render). Mismatch → `unknown(page-extent-mismatch)`. This converts a silent misalignment into a typed refusal.
3. **One frame record.** The native page-map gains the fields `resolve_pixel_mapping` needs (`source_scope`, `origin`, `axes`, `scale`, `rotation`, `crop`) derived from the existing `source_frame` / `source_to_page` / `cropbox` data. No bridge module; the oracle imports nothing from digitization.
4. **Variant matrix as RED tests first.** Variants generated deterministically from each fixture (PyMuPDF save with rotation set / cropbox set); a frame that fails to resolve for any variant fails the suite.
5. **Two-path labeling.** `dsc03/visual/render.py` stays poppler (`independent`); `digitization/render.py` stays PyMuPDF (`correlated`). Oracle evaluation reads only independent renders. No new cache in this change.

## Risks / Trade-offs

- Older poppler builds may not support `-cropbox` → mitigation: availability is already typed `unavailable` in the existing render configuration; the pin gains a feature check.
- Adding fields to the native page-map changes the manifest → mitigation: artifacts are digested per run; no cross-version compat is claimed, and replay verifies within a run.
- The measured baseline (23/139) is agent-executed from a chat session on 2026-11-24, not from `fixtures/visual/` → mitigation: executed — task 1.2 re-measured at HEAD before implementation numbers were recorded in status.md (158/405 on the cropped fixture; docs/src/status.md, agent-executed 2026-11-24).

## Migration Plan

1. Re-measure the cropped-page baseline at HEAD (record in docs/src/status.md as agent-executed).
2. RED: variant-matrix tests for frame resolution and extent binding.
3. Implement crop-box render, extent check, native frame record.
4. Re-run the visual review gate (`just visual-review` path) and record outcomes.

## Open Questions

1. Should the poppler pin record a minimum version (feature check for `-cropbox`) in the pinned render configuration? (default: yes)
2. Does the `document-visual-oracles` requirement *Calibrated thresholds with per-page outcomes* need a MODIFIED delta once statistics change? Deferred with the rest of the geometry work; this change does not touch calibration.
