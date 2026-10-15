# Brief: sunset-msj.4 — Reference index: specs, dsc03 surface, labels, fixtures

## Why

Delegated: bounded reference-writing task with a well-defined inventory (7
specs, 11 modules, label taxonomy, fixture dirs). Lead orchestrates the
loop. This is the lookup page every other doc links to, and its completion
unblocks sunset-msj.5 (AI-facing layer indexes it).

## Ticket

- **ID**: sunset-msj.4 (claimed, in_progress)
- **Epic**: sunset-msj — consumer documentation suite
- **Diátaxis quadrant**: REFERENCE only (information-oriented, no narrative)

## Desired outcome

`docs/src/reference.md` — four lookup tables/lists:

1. **Capability specs** — the 7 deployed specs under `openspec/specs/`
   (document-core, document-structure, document-semantics, document-evidence,
   document-adapters, document-conformance, document-ontology-boundaries)
   with a one-line scope each (read each spec's Purpose section) and a
   0.2-baseline vs 0.3-updated marker where it matters (all deployed specs
   carry the 0.3 updates; the frozen 0.2 executable tests only the 0.2
   core — say this once, precisely).
2. **`dsc03` module surface** — validator, profiles, adapters, coverage,
   evidence, report, migrate, boundaries, canonical, projection,
   conformance, corpus, demo. One line each, sourced from the module
   docstring (read them; do not paraphrase loosely). Mark which modules
   are consumer-facing (validator/adapters/report/conformance/evidence/
   migrate/boundaries) vs reviewer/developer machinery
   (canonical/projection/corpus/demo/profiles).
3. **Conformance label taxonomy** — read `dsc03/conformance.py` classify()
   fully; produce the label list with the suite-key conditions that produce
   each, plus the honest-claim boundaries (what can never be claimed).
4. **Fixture catalog** — `tests/tracer/` (fixture_minimal.json + profiles),
   `fixtures/carriers/` (list actual files from MANIFEST.org; state the
   PII-screening rule and that the bundle under
   `spec/document-model-specodelic-v3/` is preserved provenance, not test
   input), `fixtures/demo/` (demo issue + reviewer layers +
   measurement.json). Note the redaction/provenance rules per MANIFEST.org
   — do not duplicate its contents, link it.

## Content rules

- Table/list format, scannable, one topic per section; no how-to steps, no
  tutorial voice, no explanation paragraphs longer than two sentences.
- Terminology identical to specs and docstrings.
- Front matter not required (plain markdown), but unique semantic headings.

## Out of scope

- Any change to specs, modules, tests, fixtures, or MANIFEST.org.
- llms.txt / for-agents.md (sunset-msj.5 consumes this page).

## Exact files

- `docs/src/reference.md` (new)
- `tests/docs/test_docs_links.py` — only if the in-progress expectation
  for reference.md needs updating (minimal change, permitted)

## Exact test/review commands

```
python3 -B -m pytest tests/docs -q      # all pass
just spec-check                         # ALL GATES PASSED
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests/docs -q` → exit 0
2. `just spec-check` → prints `ALL GATES PASSED`
3. `test -f docs/src/reference.md` → exit 0
4. `git log --oneline -1` shows the atomic commit

## Follow-up threshold

If a docstring/spec contradicts another (terminology drift), record it as a
finding in the report — do not fix the source in this ticket.

## Verifier evidence contract (wai-px4g)

Cite artifacts read + fresh test-run output before CONFIRM; otherwise
REVIEW_REQUIRED.

## Spawn model

- Model: current session default.
- Context ceiling: ≤ 40% at spawn.
- Wall-clock budget: `timeout 45m`.
