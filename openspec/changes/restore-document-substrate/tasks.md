# Implementation tasks

- [x] Pin Sunset HEAD; enumerate deployed OpenSpec capabilities and current 0.3 conformance hooks; record commit, version and drift from README. (done at integration 2026-10-15 — see `proposal.md` § Integration record: HEAD `518a71a`, 7 deployed capability IDs verified)
- [x] Validate this change against exact deployed OpenSpec and Specodelic schema; adjust naming/linking before merge. (verified again 2026-10-15 sunset-7hs: `openspec validate --changes restore-document-substrate --strict` valid; `spk lint openspec/changes` 0 issues)
- [x] Map the six conceptual roles and categorical laws onto existing DSC 0.3 entities, with a table of satisfied/partial/missing evidence. ([mapping.md](mapping.md), sunset-7hs)
- [x] Amend README and status with normative purpose, consumers, honest current capabilities and documented non-goals. (sunset-7hs; no conformance-claim language upgraded)
- [x] Add native PDF fixture and deterministic structural oracle, without OCR. (`budgeting-basics-excerpt.pdf`; `dsc03/substrate/oracles.py::native_pdf_oracle`, sunset-7hs)
- [x] Add EPUB fixture and deterministic spine/navigation/footnote oracle, without forced pagination. (`sunset-carrier-sample.epub`; `epub_oracle`; footnote-backlink counterexample synthetic, sunset-7hs)
- [x] Add scanned Ahira and hybrid PDF fixtures with alternate readings and evidence. (`diario-de-poesia-excerpt.pdf` scanned with derived OCR + competing reading orders; `resumen-periodical-excerpt.pdf` p6 hybrid, sunset-7hs)
- [x] Add unrelated financial/structured-document fixture to challenge domain independence. (`invoice-arca-redacted.pdf`; core-only logical grouping + namespaced roles, sunset-7hs)
- [x] Implement typed-relations, determinism, composition, loss and non-invention checks; include negative counterexamples. (`dsc03/substrate/laws.py` + gate tests, sunset-7hs)
- [x] Run existing `just spec-check`, the available `spk lint` on this change, and all existing 0.3 suites; report raw results. (2026-10-15 sunset-7hs: openspec strict 7/7, spk lint 0 issues, pytest 193 passed, frozen validator PASS 11 descriptor fixtures, ALL GATES PASSED)
- [x] Independently implement or evaluate a second reader; measure agreement, descriptor overhead and unrepresentable cases. (`dsc03/substrate/reader_b.py`; machinery-level, agent-executed — table in docs/src/conformance-matrix.md, sunset-7hs)
- [x] Publish conformance matrix distinguishing specification, executable checks, and independent cross-format evidence. ([docs/src/conformance-matrix.md](../../../docs/src/conformance-matrix.md), sunset-7hs; real-carrier conformance unclaimed)
