# Change: Scale-complete regions and zoom operations in the descriptor

## Why

Zoom stops at the page, and word-level structure no longer exists anywhere. Verified by running the native route at HEAD (2026-11-24, `agentic-patterns-excerpt.pdf`):

- The descriptor carries 6 page-level selectors (`native-page-1..6`) and 8 regions (root, logical root, `pg1..pg6`) — nothing below page granularity.
- Word records are absent from the output entirely: there is no `word-map.json`; `line-map.json` holds 421 lines (155 KB) with 17-digit float boxes and a 64-character source digest repeated per line, hashed separately from the descriptor. Nothing binds the sidecar to the descriptor.
- `raw.txt` holds 36,497 bytes; `search.txt` reflows it; the descriptor's `contents` hold page blobs.

A structure that cannot zoom below the page cannot support word-level claims, word-level review crops, or scope-based parallel model work. (An earlier draft of this change cited a 3.9 MB `word-map.json` with 8,703 words; that artifact no longer exists at HEAD — the numbers above supersede it.)

## What Changes

- Define a **scale ladder** (document, page, block, line, word, span) as nested scopes with a decidable containment check: raw-text interval containment always; frame-box containment within a declared tolerance (sub-tolerance overhang is recorded, not refused — real boxes overhang by sub-point amounts due to kerning).
- The native adapter represents retained words and lines as regions in the physical view with selectors binding a raw-text interval and a page-frame box. Side files (`line-map.json`, `page-map.json`) become derived exports, never the source of truth.
- Define three pure operations: `zoom_in` (restriction), `lift` (attach a claim at the smallest enclosing scope) and, via existing assembly, `glue`. (`zoom_out` deferred — see Necessity cuts.)
- `zoom_in` is defined as the scale-ladder application of the scoped projection already proposed for `document-views` (in-flight `define-document-composition-semantics`); this change adds the ladder and the operations, not a second projection semantics.

## Necessity cuts (2026-11-24 audit)

- **Dense region table**: deferred. Words ship as expanded records; at HEAD the whole line map is 155 KB, so size is not yet a measured problem. Re-introduce when measured descriptor size makes gate runs or review crops slow. (An earlier draft justified this encoding with a 3.9 MB sidecar that no longer exists at HEAD.)
- **zoom_out**: deferred. The page-level meet already exists (`classify_outcome`); claim-status meet over a scope is specified in `document-verification`. Re-introduce only when a consumer needs retention-status meet below page level.

## Impact

- Affected specs: new capability `document-zoom` (all requirements ADDED); reconciliation task 1.1 aligns requirement wording with in-flight `document-views` "Scoped projection and refinement" so restriction semantics are stated once.
- Affected code: `digitization/native.py`, `digitization/native_inspection.py`, `digitization/replay.py` (manifest version bump), `dsc03/projection.py`, `dsc03/coverage.py`, new `dsc03/zoom.py`.
- Manifest: a version-3 native manifest declares words and lines as descriptor regions; version-2 manifests keep verifying as before.
- Size is tracked as a measurement in tasks, not a normative threshold.
- Depends on `add-anchor-derived-identity` for stable scope ids.
