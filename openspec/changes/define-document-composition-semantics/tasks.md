# Tasks and gates

- [ ] Pin Sunset HEAD; inspect deployed capability and DSC 0.3 wire names; record compatibility matrix and exact commit.
- [ ] Run `spk lint` and graph over proposed dual-format specs, with version and logs; fix any actual errors.
- [ ] Run Sunset's documented spec gate and strict OpenSpec validation; verify dual-format preservation across archival workflow.
- [x] Define stable canonical equality, explicit ID namespace collision behavior, and assembly boundary compatibility. (sunset-905.1, 2026-10-15: design-decisions-assembly.md D1/D2; consumer-side dsc03/substrate/assembly.py)
- [x] Implement and run identity, associativity, incompatible shared-ID, and non-invented-order fixtures. (sunset-905.1, 2026-10-15: tests/substrate/test_assembly_laws.py — 9 fixtures incl. compatible_pair, shared_id_merges; machinery-level, kernel stays partial)
- [ ] Implement view cycle, incomparable reading order, cross-page link projection, and refinement diagnostics.
- [ ] Implement PDF coordinate-frame/rotation tests, EPUB reflow stable anchors, hybrid native/OCR observations.
- [ ] Implement context inheritance, conflicting attributed claims, quoted author, and reproducibility fixtures.
- [ ] Run on Ahira *Diario de Poesía* sampled pages, real native PDF, real EPUB, and financial statement; link all source evidence.
- [ ] Have two independent readers canonicalize the same fixtures; compare outputs and classify disagreements.
- [ ] Expose failed laws and source witnesses to Sunset Lens, with read-only counterexample export.
- [ ] Document unimplemented operations and unknowns; do not imply passing tests without execution.
