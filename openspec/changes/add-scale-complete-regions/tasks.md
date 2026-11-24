## 1. Reconciliation

- [ ] 1.1 Align this change's restriction wording with in-flight `document-views` "Scoped projection and refinement"; record the division (views owns general projection semantics; zoom owns the scale ladder and operations) in design.md

## 2. Scale ladder

- [ ] 2.1 RED: word outside its line refused with witness; sub-tolerance overhang accepted and recorded
- [ ] 2.2 Implement ladder scopes and containment checks (raw interval exact; box within declared tolerance from the geometry profile)
- [ ] 2.3 Decide Open Question 1 (block scale) with the owner

## 3. Native regions

- [ ] 3.1 RED: words and lines appear as regions with interval+box selectors; side files regenerate byte-identically from the descriptor
- [ ] 3.2 Emit words in the native adapter; `line-map.json` / `page-map.json` become derived exports
- [ ] 3.3 Manifest version 3 (words/lines as descriptor regions); unknown versions refused as `unsupported-version`; record region-table size vs the 155 KB / 421-line baseline at HEAD in docs/src/status.md as agent-executed measurement
- [ ] 3.4 Follow-up (deferred, gated on 3.3 measurement): dense columnar region encoding with expansion-equivalence test — only if measured descriptor size hurts gate runs or review crops

## 4. Zoom operations

- [ ] 4.1 RED: composed restriction equals direct restriction; excluded edges recorded as coverage loss
- [ ] 4.2 RED: lift returns typed ambiguity on equal candidates
- [ ] 4.3 Implement `dsc03/zoom.py`; wire `zoom_in` to the views projection semantics
- [ ] 4.4 Follow-up (deferred): `zoom_out` retention meet below page level — only when a consumer needs it; claim-status meet is specified in document-verification

## Completion notes (2026-11-24)

- 1.1: views/zoom ownership division recorded in design.md Context (views owns general projection semantics; zoom owns the scale ladder and operations).
- 2.1: RED first in `tests/tracer/test_scale_ladder.py` (word outside its line refused with child/parent witness; sub-tolerance overhang accepted and recorded); implemented in `dsc03/zoom.py::containment`.
- 2.2: ladder order word < line < block < page enforced (`invalid-ladder-order`); raw interval containment exact; box containment within the geometry profile's declared tolerance (`tolerance` key, default 0.5 pt).
- 2.3: owner ruling recorded in design.md Open Questions (sunset-gpd G6, 2026-11-24): block in scope; MuPDF block numbers never enter identity locator paths.
- 3.1: RED first in `tests/tracer/test_native_word_regions.py` (word/line/block regions with interval+box selectors; line-map.json/page-map.json regenerate byte-identically via `export_line_map`/`export_page_map`).
- 3.2: words/lines/blocks emitted in `digitization/native.py` as descriptor regions anchored at kind-scoped raw-interval locators; side files are derived exports written from the descriptor.
- 3.3: manifest version 3; other versions refused as `unsupported-version` (inspection pre-digest check); region-table measurement appended to docs/src/status.md (agent-executed).
- 4.1: RED first in `tests/tracer/test_zoom_ops.py` (composed restriction equals direct restriction by canonical bytes; excluded edges reported as coverage loss).
- 4.2: RED first in `tests/tracer/test_zoom_ops.py` (typed ambiguity `equal-candidates` on disjoint equal page scopes; no scope selected).
- 4.3: `dsc03/zoom.py` implements restrict/zoom_in via the views-owned `project` (projection coverage entries lifted into the report so restriction composes), plus `lift` and `ladder_report`.
