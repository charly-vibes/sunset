## Context

`classify_outcome` already aggregates per-page retention into `text-complete / text-with-gaps / no-text-read`, which is a meet over a status order. `project` in `dsc03/substrate/views.py` already restricts a descriptor to a scope and records excluded links as coverage loss. The pieces exist at page granularity only, and the in-flight `document-views` delta ("Scoped projection and refinement") proposes the general restriction semantics this change applies below page level.

**Division of ownership (task 1.1, aligned with document-views "Scoped projection and refinement"):** `dsc03/substrate/views.py` owns the general projection semantics — scoped projection keeping selected regions and internal edges, excluded links recorded as coverage loss, refinement and link classification. `dsc03/zoom.py` owns the scale ladder (word < line < block < page) and the operations over it: containment checking with the declared geometry tolerance, `zoom_in` as restriction applied to a ladder scope, and `lift`. zoom never re-states projection law: `zoom_in` calls the views-owned `project` and reports the projection's exclusions as coverage loss.

## Goals / Non-Goals

Goals: one structure from document down to word; zoom operations as pure functions.

Non-goals: layout analysis (blocks from geometry) beyond what the extractor reports; reading-order reconstruction; OCR regions (they reuse the same ladder in a later change); re-stating projection semantics owned by `document-views`.

## Decisions

1. **Containment is checked, not assumed — with a declared tolerance.** A child scope must lie inside its parent: raw-text interval containment is exact; box containment holds within a tolerance declared in the geometry profile (default 0.5 pt). Violations beyond tolerance are refused with a witness naming child and parent; sub-tolerance overhang is recorded on the region, not refused. Rationale: real word boxes overhang line/page boxes by sub-point amounts (kerning, italic overhang); refusing them would mass-reject valid extractions. (Revises the earlier draft's strict refusal.)
2. **Two coordinate systems, one scope.** A word scope carries both a raw-text interval and a frame box; the pair is the anchor (and feeds identity).
3. **Records first, encoding later.** Words ship as expanded records. A dense columnar encoding (one digest per table) is deferred with a measurement trigger: at HEAD the entire line map is 155 KB, so compaction solves a problem that no longer exists at current scale. Re-introduce only when measured descriptor size hurts gate runs or review crops; the contract would be expansion to identical canonical bytes.
4. **zoom_in** returns exactly the regions within the scope, internal edges, and records every excluded edge as coverage loss. Restriction composes: restrict(restrict(D,U),V) equals restrict(D,V) for V within U.
5. **lift** attaches a claim at the smallest scope containing all its anchors; ties and multiple candidates return a typed ambiguity, never a pick.

## Risks / Trade-offs

- Descriptor grows if words are expanded records. Mitigation: measured at task 3.4; the dense table stays deferred until size is a measured problem.
- Page-level `text-complete` can hide unexamined images on that page. Mitigation: zoom_out reports `visual_completeness` alongside text status and never merges the two.
- Additional manifest version. Mitigation: unknown versions are refused as `unsupported-version`, never guessed (existing behaviour).
- `line-map.json` regeneration byte-identity only applies to the new export path; existing recorded runs verify under their manifest version and are not regenerated.

## Open Questions

1. Is a `block` scale in scope for native PDFs (MuPDF block numbers) or deferred until a layout capability exists?
   **Ruled (owner, 2026-11-24, via sunset-gpd gate G6): block scale is in scope — word < line < block < page — using MuPDF block numbers; containment checks uniform per Decision 1.** Task 2.3 unblocked.
   **Boundary (open owner flag on sunset-gpd, 2026-11-24): MuPDF block numbers serve oracle/region statistics and containment ONLY — they MUST NOT enter identity `locator_path`s. Native anchors stay page/transform-granular (add-anchor-derived-identity Decision 1: ordinal segments are position-like and need a pinned selector profile with a geometry-derived order) until a selector-profile delta is ruled. Region ids and word/line/block provenance records that could feed identity must not encode block ordinals.**
