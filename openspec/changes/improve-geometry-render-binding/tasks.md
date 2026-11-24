## 1. Baseline re-measurement

- [ ] 1.1 RED: generate the rotation/crop variant matrix from `fixtures/carriers/` fixtures; assert `resolve_pixel_mapping` resolves every native frame — expect failure at HEAD (`unresolvable_source_scope`)
- [ ] 1.2 RED: cropped-page oracle run — expect false word misses at HEAD; record counts in docs/src/status.md as agent-executed (chat baseline 2026-11-24: 23/139, superseded by this run)

## 2. Implementation

- [ ] 2.1 `pdftoppm -cropbox` with a feature/pin check in the render configuration
- [ ] 2.2 Extent binding: declared page record → expected pixels; `unknown(page-extent-mismatch)` on mismatch
- [ ] 2.3 Native page-map frame record (`source_scope`, `origin`, `axes`, `scale`, `rotation`, `crop`) derived from existing fields; delete no existing fields
- [ ] 2.4 Variant matrix passes (frame resolution + extent binding) for all fixtures

## 3. Lineage labeling

- [ ] 3.1 RED: oracle evaluation rejects `correlated`-labeled renders (in-process PyMuPDF review crops)
- [ ] 3.2 Label both render paths in their outputs; record in reports

## 4. Gates and records

- [ ] 4.1 `just spec-check` green; visual review outcomes recorded as machinery-level, agent-executed
- [ ] 4.2 File follow-up beads for the deferred geometry statistics (box agreement, scale-free stats, certificates, cache, snapping) blocked on `add-anchor-derived-identity` and `add-scale-complete-regions`, carrying the EDGE-002/EDGE-005 design tensions
