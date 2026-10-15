# Implementation tasks and acceptance gates

- [ ] 0.1 Pin Sunset revision and enumerate deployed DSC capabilities, schema/profile/selector formats and existing diagnostics; record exact SHA and compatibility matrix.
- [ ] 0.2 Validate dual-format specification deltas with target `spk lint`, `openspec validate` and repo gates; record commands and outputs. Do not silently assume archived dual-format tables survive.
- [ ] 1.1 Implement read-only descriptor loader and validated inspection index; no implicit OCR or network.
- [ ] 1.2 Implement PDF fixed-coordinate, scan-image, EPUB locator adapters and explicit mixed-mode observations; preserve intrinsic vs display coordinates.
- [ ] 1.3 Implement synchronized source/structure/evidence selection including missing/ambiguous selector states and scoped alternative reading orders.
- [ ] 1.4 Implement diagnostic model with typed results and exact source/witness links; include keyboard/a11y behavior.
- [ ] 2.1 Implement versioned, scoped observable comparators and non-equivalence witness reporting.
- [ ] 2.2 Add composition/identity/associativity fixture probes and unsupported-domain reporting; no categorical runtime.
- [ ] 2.3 Export deterministic minimized counterexamples and replay fixtures, with privacy/rights and redaction states.
- [ ] 3.1 Add goldens for native PDF, EPUB, Ahira scan, hybrid PDF and non-periodical financial statement (the user-supplied issue is a useful baseline, not an automatic public redistributable fixture).
- [ ] 3.2 Add negative fixtures: wrong order, cycle, dangling target, selector ambiguity, unsupported span, edition mismatch, conflicting evidence, incomplete coverage.
- [ ] 3.3 Run viewer interaction, accessibility, keyboard, offline, rotation, EPUB reflow, performance and malformed-input tests.
- [ ] 3.4 Re-run with independent implementation and compare canonical diagnostics on pinned fixtures.
- [ ] 4.1 Document usage, provenance, model limits and required adapters; demo direct annotation-to-source evidence and exported replayable wrong-reading-order witness.
- [ ] 4.2 Demonstrate source descriptor unchanged byte-for-byte after inspection; no DSC core wire modifications.

## Done means

All acceptance fixtures pass; each declared negative counterexample fails with expected diagnostic code and witness; two independent implementations agree on frozen comparison outputs; core input descriptors remain unchanged; unknown/unsupported never masquerades as pass; native PDF/EPUB run without OCR; `spk` and OpenSpec checks actually run and outputs are recorded.
