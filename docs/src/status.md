> *I scanned the menu options*
> *I did not have a choice*
> *I'd like to teach the world to sing*
> *But I do not have a voice*
>
> — A Sunset, PULP

# Status

**sunset** is **experimental**.

- Hosts the DSC (Document Structural Core) specification corpus.
- Orientation: [What is DSC and why](what-is-dsc.md) — the docs entry point.
- Executable truth: DSC 0.2 only — `spec/document-model-specodelic-v3/validator.py`
  (frozen at 0.2), `PASS 11 descriptor fixtures`.
- DSC 0.3 machinery is implemented (`dsc03/` package, tests under
  `tests/tracer/`, gate `just spec-check`). The 0.3 capability deltas were
  deployed to the openspec specs on 2026-10-15 from the archived change
  [`openspec/changes/archive/2026-10-14-add-dsc-03/`](../../openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md)
  (now 7 deployed capabilities). No real-carrier conformance is claimed:
  `dsc03/conformance.py` labels remain honest and scoped.
- **Substrate gates (sunset-7hs, 2026-10-15):** the
  [restore-document-substrate](../../openspec/changes/restore-document-substrate/proposal.md)
  implementable tasks are executed: the six conceptual roles and nine design
  §4 laws are mapped onto deployed 0.3 entities with a
  satisfied/partial/missing table ([mapping.md](../../openspec/changes/restore-document-substrate/mapping.md));
  deterministic oracles (native PDF without OCR, EPUB spine/navigation,
  scanned-with-derived-OCR, hybrid coexistence, financial domain
  independence) and law checks with negative counterexamples run in the
  separate consumer harness `tests/substrate/` (machinery
  `dsc03/substrate/`); a second independent scripted reading path is measured
  ([conformance matrix](conformance-matrix.md) — machinery-level,
  agent-executed, NOT human review). Purpose/consumers/non-goals are now
  stated normatively in the [README](../../README.md#purpose-consumers-non-goals)
  without upgrading any conformance-claim language. No wire changes; the
  substrate spec deltas remain undeployed pending review; recorded
  expressivity findings live in mapping.md § "Unresolved expressivity
  findings".
- The first-consumer demo's pinned extractors originally reaped children
  via `os.wait4` before draining stdout — a pipe-buffer deadlock that hung
  the suite once page output exceeded the buffer (surfaced 2026-10-18
  during sunset-905.3 gate runs). Fixed by `dsc03.demo.run_pinned`
  (file-backed stdout, WNOHANG polling, hung child killed after timeout);
  regression tests in `test_first_consumer_demo.py::TestPinnedRunner`.
- The sunset-905.3 two-human-readers gate remains open: the reader-grok /
  reader-claude sheet sets returned via cotorreo were ingested as a labeled
  agent-executed agreement run (owner ruling b, 2026-10-18) — see
  `hitl/sunset-905.3/agreement-matrix-agent-run.md` (55 observables: 27
  AGREE, 14 COMPATIBLE, 8 UNKNOWN, 6 DISAGREE retained; a human pass
  supersedes).
- Recorded deviations across the 0.3 work (each human pass supersedes):
  reviewer personas, reader annotations and review times in the
  [first-consumer demonstration](tracer-bullet.org) are agent-executed; the
  anchor-mapping review of record was agent-executed rule-of-5
  (TypeSafe-verified), accepted by the owner in sunset-r68.12; the
  documentation-suite review of record (sunset-msj.6) was likewise
  agent-executed — every runnable claim reproduces verbatim, links resolve,
  and the fixture catalog matches disk — with the same standing caveat:
  a human pass supersedes.
- Active openspec deltas include the review corrections; the preserved
  research draft is historical input where its details differ.
- Three proposed (not deployed) openspec changes are integrated as of
  2026-10-15, grounded and strictly validated against this checkout
  (`spk lint` 0 issues each; provenance in each change's `proposal.md`):
  [`restore-document-substrate`](../../openspec/changes/restore-document-substrate/proposal.md)
  (general purpose + categorical laws, additive) — **implemented at the gate
  level 2026-10-15 (sunset-7hs), see the substrate-gates bullet above**;
  [`define-document-composition-semantics`](../../openspec/changes/define-document-composition-semantics/proposal.md)
  (assembly/views/space/context laws, additive, depends on the former) and
  [`add-document-structural-debugger`](../../openspec/changes/add-document-structural-debugger/proposal.md)
  (read-only Sunset Lens debugger, optional consumer). No wire changes and no
  implementation are claimed; the proposals' conformance fixtures and
  second-reader gates are unexecuted and tracked in beads
  (sunset-7hs, sunset-905, sunset-xx7).
- The baseline's [known validation limitations](baseline-limitations.md)
  remain visible. The proposal composition regression checks specification
  replacement only, not 0.3 behavior.
- No CLI ships from this repo by design (see scope ruling below); the ddl
  registry checklist is out of scope.

## Deviations from the fleet standardization checklist

**Scope ruling (2026-10-15, closing `sunset-408`):** sunset is a **DSC
specification corpus** — specs, a frozen 0.2 executable truth, and 0.3
conformance machinery — not a shipped tool. The dulce-de-leche tool-registry
checklist (registry row, capability matrix, CI workflows, book pages,
`llms.txt`) assumes an installable CLI; building one for sunset would exist
only to satisfy the checklist. The items below are therefore **deliberately
out of scope**, not deferred work. Adoption happens via external consumers
implementing DSC and running the conformance suite against themselves.

Other recorded deviations:

- No CI workflow files (`just ci` arrives with an implementation; the spec
  gates run via `just spec-check` for now)
- No `book.toml`/theme or book pages
- No tool-registry `llm.txt`; [`llms.txt`](../../llms.txt) exists but serves
  documentation discovery only — it is not the tool-registration form the
  checklist assumes (same scope ruling as above)
- Not registered in ddl's registry, capability matrix, or dogfood matrix
- The research bundle's `specs/` were relocated to `openspec/` (single source
  of truth) — the recorded exception to "preserved as received" in the root
  [AGENTS.md](../../AGENTS.md)

## Acceptance gates for the 0.3 proposal

The bundle's [ACCEPTANCE.md](../../spec/document-model-specodelic-v3/ACCEPTANCE.md)
provides the original cases. The 0.3 requirements now live in the deployed
openspec specs (deployed from the archived add-dsc-03 change). The
[first-consumer demonstration](tracer-bullet.org) was executed 2026-10-15
(sunset-r68.13): 0 FP/FN against the reviewer oracle, R3/R5 correct only via
DSC — traceability benefit demonstrated; speed benefit not claimed.

## Tracer bullet (walking skeleton)

The 0.3 slice is implemented and green: descriptor → validate →
pinned profile resolve → evidence replay, plus adapters, coverage,
lineage/replay, reports, migration and honest conformance labels
(`dsc03/` package, full suite in `tests/tracer/`).
See [tracer-bullet.org](tracer-bullet.org) for the demo run and the
first-consumer workflow. The
frozen 0.2 validator stays untouched (PASS 11 descriptor fixtures).
