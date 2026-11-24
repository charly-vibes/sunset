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
