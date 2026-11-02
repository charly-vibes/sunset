# Brief: sunset-xzy.1 — Pinned rendering infrastructure

**Ticket**: sunset-xzy.1 (beads, in_progress, lease held by orchestrator)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 3.1
**Base commit**: 5ee0e1d (post-approval `233d8f8` + issue-review fixes `eeac8b0`/`5ee0e1d`)
**Authority**: owner ruling 2026-11-02 recorded in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

The lead session orchestrates the sunset-xzy epic (claim → brief → spawn → verify → ship per
`epic-orchestrator` pipeline; canon Invariant 1 — inline execution is the historical failure
mode). This slice is a well-bounded TDD unit (one module, one test file, pinned spec text),
so it delegates cleanly to a fresh-context implementor while the lead conserves context for
verification and shipping.

## Desired outcome

A new `dsc03/visual/` package with a render-configuration module that:

1. Records every oracle render's **renderer name, version, DPI, page selection, binarization
   settings and source simplification** (design D2/D4) in an immutable config record
   (frozen dataclass or equivalent; expose it as an explicit record, not loose kwargs).
2. Renders a PDF page via **poppler `pdftoppm`** from that record; **identical configurations
   produce byte-identical renders** (same page, same DPI, same options ⇒ equal bytes).
3. A **missing renderer executable** yields a **typed `unavailable` outcome** — never
   `agree`, never a silent skip, never a bare exception leaking to callers. Model it as an
   explicit outcome type (e.g. dataclass/enum variants: render ok → bytes + config;
   unavailable → reason). Per design D5 the outcome vocabulary is `agree`/`differ`/`unknown`
   plus typed `unavailable`; this slice only needs the render-level outcome, not property
   verdicts.
4. Every result carries an **evidence class**: `correlated` when render and extraction share
   an implementation lineage (e.g. PyMuPDF render for PyMuPDF extraction), `independent`
   otherwise (poppler render vs PyMuPDF extraction). Provide it as data on the outcome/config
   (a lineage declaration in the config: extractor lineage + renderer lineage → label), since
   spec "Labeled evidence class" requires the label on results; correlated results support
   sensitivity demonstrations only, never accuracy claims — encode that rule as a docstring
   + a helper predicate, no need for property-verdict plumbing yet.
5. Each new module carries a **Purpose/Responsibilities/Rationale file header**
   (issue-review EXEC-004).

## Spec anchors (verbatim requirements)

- `specs/document-visual-oracles/spec.md` → "Pinned render configuration" (scenarios:
  Reproducible render, Renderer unavailable) and "Labeled evidence class" (scenarios:
  Shared library, Distinct renderer).
- `design.md` D2 (poppler pdftoppm as initial independent renderer; recording + byte-identical
  rule), D4 (source simplification recorded per config), D5 (outcome vocabulary).

## Out of scope

- Frame mapping / pixel↔descriptor coordinate resolution (that is sunset-xzy.2 / tasks 3.2).
- Ink-coverage and geometry-mask oracle properties (tasks 4.x), mutation fixtures (5.x),
  calibration (6.x), conformance integration (7.x), docs (8.x).
- No EPUB handling (unrenderable by pdftoppm → out of scope; may report `unavailable`/`unknown`
  naturally but no EPUB-specific work).
- No edits outside the exact files listed below. No changes to `dsc03/conformance.py` labels,
  no `spec/` bundle edits, no openspec spec-file edits (deltas already deployed for review),
  no `validator.py` (frozen 0.2) changes.
- **No `git push`. No commits outside the designated commit step.**

## Exact files

- CREATE `dsc03/visual/__init__.py` (package init; may re-export the public surface)
- CREATE `dsc03/visual/render.py` (config record + pdftoppm runner + outcome/evidence types)
- CREATE `tests/tracer/test_visual_render.py` (the failing-first test file)

## Test-first sequence (red → green → refactor)

1. **RED**: write `tests/tracer/test_visual_render.py` with tests that import
   `dsc03.visual.render` and pin: (a) two renders from one recorded config over a fixture PDF
   have identical bytes; (b) a config pointing at a nonexistent renderer executable returns
   the typed unavailable outcome (assert the type, assert it is not `agree`/bytes); (c) the
   config record serializes/round-trips its fields (renderer name, version, DPI, page
   selection, binarization, source simplification); (d) lineage → evidence-class labeling
   (PyMuPDF+PyMuPDF → correlated; PyMuPDF+poppler → independent). Run
   `python3 -m pytest tests/tracer/test_visual_render.py` → MUST FAIL (ImportError/missing API).
   Record the RED output.
2. **GREEN**: implement `dsc03/visual/render.py` minimally to make the tests pass. Run the
   test file → MUST PASS. Record the GREEN output.
3. **REFACTOR**: only if needed for clarity; behavior-neutral. Rerun the test file.
4. **Full suite**: `python3 -m pytest tests/tracer/ -q` — all existing tests must stay green
   (baseline: 455 passed, 18 subtests, 2 skips; small drift upward from your new tests is fine).
5. `pdftoppm` 26.01 is installed at `/usr/bin/pdftoppm` — use a real short fixture PDF for the
   byte-identical test (candidates already in repo: `fixtures/carriers/*.pdf`,
   `fixtures/demo/*.pdf` — pick the smallest; read bytes, render at low DPI e.g. 72 to keep it
   fast). Version detection may shell out to `pdftoppm -v` once per record creation.

## Exact commands

- RED/GREEN loop: `python3 -m pytest tests/tracer/test_visual_render.py -q`
- Full suite: `python3 -m pytest tests/tracer/ -q`
- Gate: `just spec-check` (expect ALL GATES PASSED; frozen validator must stay PASS 11)
- Syntax check: `python3 -m compileall dsc03/visual`

## Completion criteria (all must hold; exit 0 = done)

1. `python3 -m pytest tests/tracer/test_visual_render.py -q` exits 0
2. `python3 -m pytest tests/tracer/ -q` exits 0 (no regressions vs baseline 455+18)
3. `just spec-check` exits 0 with `ALL GATES PASSED` and frozen `PASS 11 descriptor fixtures`
4. `git status --short` shows ONLY: the three new files, plus allowed churn you must revert:
   `measurement.json` / fixture churn must be `git checkout --`-ed back before finishing
   (compare against `git status` at start; do NOT revert `.whisper/` or `.wai/` files).

## Verifier evidence contract (wai-px4g)

The lead-side verify session will cross-check your report against reality (`git status`,
`git diff`, fresh test runs). Your report artifact must cite the files you changed and paste
the actual RED and GREEN command outputs. Claims without pasted output will be treated as
unverified → REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` via `pi -p --provider openrouter --model z-ai/glm-5.3-flash`.
Context window: 1,000,000 tokens. Estimated session usage (brief + repo files + test runs):
well under 150K tokens → **context ceiling ≤ 15% of the model window**. If you exceed it,
stop and report rather than pushing on.

## Follow-up threshold

If you discover the slice cannot be completed as specified (e.g. pdftoppm output is not
deterministic at fixed DPI — it is expected to be, but verify), STOP, write findings into the
report, change nothing beyond the three files, and leave the tree clean. Do not widen scope,
do not fix unrelated bugs (record them as findings instead). Max ~20 minutes wall-clock.

## Report

Write your report to `.wai/projects/sunset/research/sunset-xzy.1-report.org` with:
RED output, GREEN output, full-suite tail, gate tail, files changed, deviations (should be
none), findings.
