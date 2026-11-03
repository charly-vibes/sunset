# Brief: sunset-xzy.7 — Integration: visual results as a separate evidence class; conformance labels unchanged

**Ticket**: sunset-xzy.7 (beads, in_progress, complexity s)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 6.1
**Base commit**: 0a00c35 (xzy.1–.6 shipped; calibration record + mutation fixtures are in place)
**Gates baseline (recorded at claim)**: `just spec-check` ALL GATES PASSED; pytest 526 passed + 18 subtests; frozen 0.2 validator PASS 11.

## Why

Spec requirement "Distinct evidence class in demonstrations": visual oracle results
SHALL be recorded separately from reader agreement, extractor comparison and
reviewed anchor mapping, and SHALL NOT substitute for any of them in conformance
labels or demonstration suites. Scenario "Oracles cannot complete a suite": a
demonstration suite with passing visual oracles but no independent readers keeps
its label (`incomplete`), unchanged by oracle results. This slice is the wiring +
the proof that the wiring is inert with respect to labels. PLUMBING slice: no
oracle semantics change, no threshold change, no label change.

## Desired outcome

Two deliverables, nothing else:

1. `dsc03/visual/reports.py` — records visual oracle results into demo/evaluation
   report dicts as a SEPARATE evidence-class section. Suggested shape (you may
   refine names, not semantics):
   - `record(report, visual_results)` → returns the report dict with a new
     `visual_oracles` section. It MUST carry, per property/page: outcome status
     (`agree`/`differ`/`unknown`/`unavailable` per the existing `CoverageOutcome`
     /`AlignmentOutcome`/`AggregateOutcome` vocabulary), reasons (e.g.
     `uncalibrated`), the evidence-class label (`correlated`/`independent` via
     `dsc03.visual.render.evidence_class`), the aggregate status (`agree`/`blocked`…)
     and blocker reasons, and an explicit non-substitution note (which conformance
     inputs this section does NOT provide).
   - Honest statuses only: `unknown`/`unavailable`/uncalibrated pass through
     verbatim (SCOPE-002) — never upgraded, never dropped, never masked by an
     aggregate.
   - Pure-function style matching the dsc03 house pattern; dict-in/dict-out;
     NEVER mutates or fills the other report sections (schema/profiles/coverage/
     interpretation from `report.assess`, or any reader-agreement / extractor-
     comparison / anchor-mapping fields).
   - Module file header: `# Purpose / # Responsibilities / # Rationale` (EXEC-004).
2. `tests/tracer/test_visual_integration.py` — TDD, red first:
   - RED: with `dsc03/visual/reports.py` absent, the import/collection fails.
     Record verbatim.
   - GREEN must assert, at minimum:
     a. Recording adds the `visual_oracles` section with per-page statuses,
        reasons, evidence class, aggregate status + blockers — and leaves every
        pre-existing section byte-for-byte unchanged (distinctness).
     b. Unknown/uncalibrated outcomes are recorded verbatim (feed a real
        uncalibrated page outcome — `fixtures/visual/calibration.json` documents
        the faint page as honestly uncalibrated → unknown; reuse that shape).
     c. **Label inertness** (the spec scenario): `dsc03.conformance.classify`
        output is IDENTICAL with and without visual-oracle data present —
        including a suite with passing visual oracles but no independent readers:
        the label/missing-items stay exactly the same (`incomplete`, readers
        still listed missing). Assert by passing a suite dict that includes a
        visual-oracles key vs the same dict without it, and by a full passing-
        oracles/no-readers suite. `classify` must need NO edits — if you find
        yourself editing `dsc03/conformance.py` to make a test pass, STOP (that
        would contradict the requirement; record it as a finding instead).
     d. No substitution: the recorded section cannot toggle `real_carrier_
        conformance`, `workflow_benefit`, or any claim string, whatever the
        oracle outcomes (agree, blocked, unknown — all identical labels).

## House rules (on record — obey)

- `/usr/bin/python3 -m pytest ...` (bare `python3` lacks pytest; if pytest is
  missing entirely, STOP — do not pip-install).
- Touch ONLY `dsc03/visual/reports.py` and `tests/tracer/test_visual_integration.py`.
  NO edits to `dsc03/conformance.py`, `dsc03/report.py`, `dsc03/demo.py`,
  `dsc03/visual/__init__.py` (import via `from dsc03.visual import reports` or
  `import dsc03.visual.reports` — both work), other dsc03 modules, fixtures,
  openspec, justfile.
- Existing vocabulary: `CoverageOutcome`/`AlignmentOutcome` (`status`,
  `evidence_class`, `page`), `AggregateOutcome` (`status`, `reasons`),
  `aggregate()` NEVER reports pass while a page is `unknown`/`unavailable` or
  the property uncalibrated. Build outcome objects for tests from these real
  classes (import from `dsc03.visual.coverage` / `dsc03.visual.masks`) — no
  synthetic stubs where the real type exists.
- AGENT-EXECUTED labeling: nothing here produces human evidence; the report says
  so; human pass supersedes.

## Red → green shape

- **RED**: `ModuleNotFoundError`/collection error on the absent module. Verbatim.
- **GREEN**: module exists; every new test passes.
- **REFACTOR** only inside your two deliverable paths.

## Spec anchors

"Distinct evidence class in demonstrations" · scenario "Oracles cannot complete
a suite" · "Labeled evidence class" (correlated demonstrates sensitivity, never
accuracy) · "No silent resolution" · "Scoped property claims".

## Anti-goals (hard)

- Do NOT let visual results substitute for readers, extractor comparison, or
  reviewed anchor mapping — in data shape or in labels.
- Do NOT edit `conformance.py` (see 2c/2d: inertness is the deliverable).
- Do NOT drop or upgrade unknown/unavailable/uncalibrated statuses.
- No accuracy, completeness or semantic claims anywhere in code or docstrings.

## Out of scope

Docs (6.2/.8), final gate (7.1/.9), any oracle/render/frame change, fixtures,
openspec. **No commits. No push.**

## Exact files

- CREATE `dsc03/visual/reports.py`
- CREATE `tests/tracer/test_visual_integration.py`
- CREATE `.wai/projects/sunset/research/sunset-xzy.7-report.org`

## Exact commands

- `/usr/bin/python3 -m pytest tests/tracer/test_visual_integration.py -q`
- `/usr/bin/python3 -m pytest tests -q` (baseline 526 passed + 18 subtests)
- `just spec-check` → ALL GATES PASSED, PASS 11 descriptor fixtures
- `/usr/bin/python3 -m compileall dsc03/visual/reports.py tests/tracer/test_visual_integration.py`

## Completion criteria (exit 0 = done)

1. Targeted pytest exits 0 (RED output recorded first, verbatim).
2. Full suite exits 0 (526+18 baseline + your new tests).
3. `just spec-check` exits 0, ALL GATES PASSED, PASS 11.
4. `git status --short` shows ONLY your deliverable paths (+ pre-existing
   `.whisper`/`.wai`/`pba-judicial-2026-07-29.pdf` noise); no churn anywhere else.

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste actual RED/GREEN outputs, suite tail,
and gate tail. Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK, maxTokens already capped 48000).
Window 1,000,000 tokens; **context ceiling ≤ 15%**; exceed ⇒ stop and report.
Complexity s: ~15 minutes wall-clock budget (timeout 1500 to be safe).

## Follow-up threshold

If honest recording seems impossible without touching forbidden files (e.g.
labels DO move when visual data is added), STOP: record the finding + the exact
label diff in the report, touch nothing outside your deliverable paths, leave
the tree clean.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.7-report.org`: RED/GREEN outputs,
suite tail, gate tail, files changed, deviations, findings (labeled
AGENT-EXECUTED — human pass supersedes).
