# Implementation tasks and acceptance gates

- [ ] 0.1 Pin Sunset revision and enumerate deployed DSC capabilities, schema/profile/selector formats and existing diagnostics; record exact SHA and compatibility matrix.
- [x] 0.2 Validate dual-format specification deltas with target `spk lint`, `openspec validate` and repo gates; record commands and outputs. Do not silently assume archived dual-format tables survive. (2026-11-25: `spk lint openspec` ok 9 files 0 issues; `openspec validate --specs --strict` 8/8; `openspec validate add-document-structural-debugger --type change --strict` valid; `SUNSET_PYTHON=.venv/bin/python just spec-check` ALL GATES PASSED 20/20 incl. `npx @fission-ai/openspec@1.14.2 validate --all --strict`; adapters/comparison layer.md browser-gate rows added per owner requests.)
- [x] 1.1 Implement read-only descriptor loader and validated inspection index; no implicit OCR or network. (sunset-xx7.1: dsc03/inspect.py; typed diagnostics model incl. agent-executed pass — human pass supersedes)
- [x] 1.2 Implement PDF fixed-coordinate, scan-image, EPUB locator adapters and explicit mixed-mode observations; preserve intrinsic vs display coordinates. (sunset-xx7.2: dsc03/locators.py)
- [x] 1.3 Implement synchronized source/structure/evidence selection including missing/ambiguous selector states and scoped alternative reading orders. (sunset-xx7.2: dsc03/locators.py)
- [ ] 1.4 Implement diagnostic model with typed results and exact source/witness links; include keyboard/a11y behavior.
- [x] 2.1 Implement versioned, scoped observable comparators and non-equivalence witness reporting. (sunset-xx7.3: dsc03/compare.py)
- [x] 2.2 Add composition/identity/associativity fixture probes and unsupported-domain reporting; no categorical runtime. (sunset-xx7.3: probe_identity/probe_associativity)
- [x] 2.3 Export deterministic minimized counterexamples and replay fixtures, with privacy/rights and redaction states. (sunset-xx7.3: export_counterexample, fixtures/debugger-goldens/)
- [ ] 3.1 Add goldens for native PDF, EPUB, Ahira scan, hybrid PDF and non-periodical financial statement (the user-supplied issue is a useful baseline, not an automatic public redistributable fixture).
- [ ] 3.2 Add negative fixtures: wrong order, cycle, dangling target, selector ambiguity, unsupported span, edition mismatch, conflicting evidence, incomplete coverage.
- [x] 3.3 Run viewer interaction, accessibility, keyboard, offline, rotation, EPUB reflow, performance and malformed-input tests. (sunset-xx7.4a: test_debugger_a11y.py; performance = measured wall-time only, no win claims)
- [x] 3.4 Re-run with independent implementation and compare canonical diagnostics on pinned fixtures. (sunset-xx7.4b: agent-executed second reader, labeled AGENT-EXECUTED in fixtures/debugger-goldens/second-reader-agreement.org — 2 agree / 0 disagree / 1 not_replayable; OWNER GATE REMAINS OPEN, human pass supersedes)
- [ ] 4.1 Document usage, provenance, model limits and required adapters; demo direct annotation-to-source evidence and exported replayable wrong-reading-order witness.
- [ ] 4.2 Demonstrate source descriptor unchanged byte-for-byte after inspection; no DSC core wire modifications.

## Done means

All acceptance fixtures pass; each declared negative counterexample fails with expected diagnostic code and witness; two independent implementations agree on frozen comparison outputs; core input descriptors remain unchanged; unknown/unsupported never masquerades as pass; native PDF/EPUB run without OCR; `spk` and OpenSpec checks actually run and outputs are recorded.

## 5. PDF working example (amendment pending approval)

- [x] 5.1 Source-linked human region inspection: first fail region-import and real-browser selection tests, then import the existing human sheets into valid DSC 0.3 and expose pointer/keyboard source-to-evidence navigation with tested page-frame transforms; preserve original bytes and explicit unknowns. (sunset-5bu 2026-11-25: dsc03/visual/sheet_import.py import_sheets — 6 sheets/203 regions accounted, typed refusals, provenance flags; review.py import-inspection mode + region_to_source_px; SPA pointer/keyboard journeys fail-not-skip; tests/tracer/test_sheet_import.py + test_source_linked_inspection_browser.py)
- [x] 5.2 Attributed reading comparison: first fail a real-browser A/B inspection test, then show selected observations, explicit comparison scope, outcomes and witnesses without inferred identity or an automatic winner. (sunset-36n 2026-11-25: review.py ab-comparison mode over dsc03.compare.scoped_compare with pinned counterexamples; no winner/cross-reader/pairing field machine-scanned; tests/tracer/test_ab_comparison_browser.py fail-not-skip)
- [x] 5.3 Reopen a source-linked disagreement: first fail real-browser export/reopen and wrong-source tests, then export pinned replay inputs, reopen with matching local PDF, reproduce outcome/locus and record a runnable example with its limits. Browser gates must fail rather than skip when unavailable; run just spec-check. Any optional refactoring is a separate ticket/commit. (sunset-j1c 2026-11-25: review.py reopen_counterexample — replayed/source-digest-mismatch/not-replayable/invalid-bundle typed states + CLI reopen; SPA export-download and offline reopen port; tests/tracer/test_disagreement_reopen_browser.py; spec-check ALL GATES PASSED 2026-11-25)
