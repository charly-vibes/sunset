# Tasks and gates

- [ ] Pin Sunset HEAD; inspect deployed capability and DSC 0.3 wire names; record compatibility matrix and exact commit.
- [ ] Run `spk lint` and graph over proposed dual-format specs, with version and logs; fix any actual errors.
- [ ] Run Sunset's documented spec gate and strict OpenSpec validation; verify dual-format preservation across archival workflow.
- [x] Define stable canonical equality, explicit ID namespace collision behavior, and assembly boundary compatibility. (sunset-905.1, 2026-10-15: design-decisions-assembly.md D1/D2; consumer-side dsc03/substrate/assembly.py)
- [x] Implement and run identity, associativity, incompatible shared-ID, and non-invented-order fixtures. (sunset-905.1, 2026-10-15: tests/substrate/test_assembly_laws.py — 9 fixtures incl. compatible_pair, shared_id_merges; machinery-level, kernel stays partial)
- [x] Implement view cycle, incomparable reading order, cross-page link projection, and refinement diagnostics. (sunset-905.2, 2026-10-15: tests/substrate/test_views_space_context.py + dsc03/substrate/views.py — 6 views fixtures; machinery-level, kernel stays partial)
- [x] Implement PDF coordinate-frame/rotation tests, EPUB reflow stable anchors, hybrid native/OCR observations. (sunset-905.2, 2026-10-15: dsc03/substrate/space.py — 7 space fixtures, typed unknowns, no OCR runs)
- [x] Implement context inheritance, conflicting attributed claims, quoted author, and reproducibility fixtures. (sunset-905.2, 2026-10-15: dsc03/substrate/context.py — 6 context fixtures incl. same_pinned_input replay)
- [x] Run on Ahira *Diario de Poesía* sampled pages, real native PDF, real EPUB, and financial statement; link all source evidence. (sunset-905.3, 2026-10-27: owner waived EPUB because app does not render it; three PDF runs and digest-pinned evidence in hitl/sunset-905.3/composition-results.org. Partial result: 203 geometry references absent from adapters; no general conformance claim.)
- [x] Have two independent readers canonicalize the same fixtures; compare outputs and classify disagreements. (sunset-905.3, 2026-10-27: six owner-accepted human sheets; two independent canonical implementations agree per same machine descriptor; PyMuPDF/pdftotext outputs compared separately. UNKNOWN/LOSS/DISAGREE retained; owner accepted the documented partial results and closure on 2026-10-27. Human readers did not execute canonical serialization.)
- [ ] Expose failed laws and source witnesses to Sunset Lens, with read-only counterexample export.
- [ ] Document unimplemented operations and unknowns; do not imply passing tests without execution.
