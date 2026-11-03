# Brief: sunset-xzy.6 — Calibration sheet: thresholds over varied pages with per-page outcomes

**Ticket**: sunset-xzy.6 (beads, in_progress, complexity L)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 5.2
**Base commit**: 5f05edb (xzy.1–.5 shipped; mutation fixtures from .5 are reusable)
**Authority**: owner ruling 2026-11-02 in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

Spec "Calibrated thresholds with per-page outcomes": thresholds SHALL come from
recorded calibration over varied pinned carriers; outcomes reported per page and per
property; no aggregate SHALL report pass while any page is `unknown`/`unavailable` or
its property `uncalibrated`. Design D6 pins the calibration-record fields — task 5.2
asserts against them. This slice produces THE calibration record the later integration
slice (.7) and final gate (.9) consume. TEST-AND-RECORD slice: the oracles
(`dsc03/visual/coverage.py`, `dsc03/visual/masks.py`) and render/frame machinery MUST
NOT be edited. A measurement that contradicts oracle semantics is a STOP-and-record
finding.

## Desired outcome

Three deliverables, nothing else:

1. `fixtures/visual/calibration.json` — the committed calibration record. MUST carry
   ALL SIX design.md D6 fields, with these key names (or a documented mapping to them):
   `property`, `defect_classes_exercised`, `carriers`, `per_page_outcomes`,
   `thresholds`, `render_configuration`. Threshold entries keep the oracle-consumed
   shape `{"property", "carrier", "page", "min", "max"}` so
   `_usable_calibration`/`_usable_region_calibration` consume them directly. Record
   which entries were derived from the threshold set vs reused from xzy.3/.4/.5
   fixtures; record any overlap between derivation and detection sets explicitly
   (ALIGN-001).
2. `tests/tracer/test_visual_calibration.py` — the test asserting (a) the record
   carries the six fields; (b) re-running BOTH oracles with the recorded calibration
   over the recorded carriers reproduces the recorded per-page outcomes; (c) the
   aggregate rule: `aggregate()` NEVER reports pass while any page outcome is
   `unknown`/`unavailable` or the property is uncalibrated — assert with a real faint
   page, not just a synthetic stub; (d) detection assertions on pages OUTSIDE the
   threshold-derivation set (reuse the committed xzy.5 mutation fixtures
   `tests/tracer/fixtures/visual/`); (e) unknown cases surfaced in the record, never
   masked by a corpus-wide aggregate.
3. IF needed for the faint category: one new committed deterministic faint fixture
   under `tests/tracer/fixtures/visual/` (same house pattern as xzy.5: pymupdf-built,
   fill-only rects, README provenance updated). Anything else under
   `tests/tracer/fixtures/visual/` is already committed — reuse, don't regenerate.

### The five page varieties (spec/design vocabulary)

Derive thresholds from recorded runs over: **native text**, **image-only scan**,
**mixed**, **rotated**, **faint**. Committed real carriers under `fixtures/carriers/`
— suggested mapping, verify by rendering before committing to it (record your final
mapping in the record):
- native text: `bank-statement-ca-excerpt.pdf` (the xzy.3/.4 smoke carrier)
- image-only scan: `diario-de-poesia-excerpt.pdf`
- mixed (text + image content): `budgeting-basics-excerpt.pdf` or
  `invoice-arca-redacted.pdf` — pick after measuring, record why
- rotated: reuse committed `tests/tracer/fixtures/visual/visual-strip-rot90.pdf`
  (landscape-raster trick; NO pymupdf `set_rotation`) with its true `page-1-rot90`
  frame from `geometry-rotated-strip.json`; the wrong-frame flip control
  (`page-1-rot180`) is the detection demonstration for this category
- faint: no committed carrier exists — create the deterministic fixture (very light
  gray ink near the binarization threshold) and pin its honest outcome: per the spec
  scenario "Faint scan", a degraded page below render-confidence limits yields
  `unknown` and blocks the aggregate. An oracle outcome object has no
  "confidence" field — `unknown` must come through the existing typed reasons
  (e.g. binarization/threshold path) or the recorded calibration legitimately cannot
  bound it; pin WHICH mechanism you used and never fake an outcome.

### House rules for measurement (from xzy.2–.5 findings — all on record)

- Calibration entries `[min, max]` MUST admit region- AND page-scale fractions
  (xzy.2 finding). Measure first, then set the window with deterministic margin.
- `ink-dilation-<N>px` simplification is part of the render configuration field —
  record the exact dilation per carrier entry; dilation margins are deterministic
  (xzy.4 finding).
- pymupdf `draw_rect(color=..., fill=...)` strokes a +1px halo — draw fill-only
  (`color=None, width=0`) in any new fixture.
- Render through the pinned `RenderConfig`/`render_page` exactly as
  `test_visual_render.py` does; pdftoppm is available and renders are byte-identical
  (xzy.1). Region descriptors for real carriers: pick claimed rects by rendering and
  measuring — recorded, never guessed; include at least one `expected:"ink"` and one
  `expected:"no-ink"` region per calibrated page where the oracle's vocabulary allows.
- AGENT-EXECUTED labeling: thresholds and timings are agent-measured; the record and
  report say so; human pass supersedes.

### Red → green shape

- **RED**: with `fixtures/visual/calibration.json` absent, the suite fails. Record
  verbatim.
- **GREEN**: record committed; every test passes against re-run reality.
- **REFACTOR** only inside your deliverables.

## Spec anchors

- "Calibrated thresholds with per-page outcomes" + scenario "Faint scan" ·
  "Mutation-validated sensitivity" (detection set) · "No silent resolution" ·
  "Scoped property claims" · design D6 (six record fields) · D4 (simplification is
  the tolerance).

## Anti-goals (issue-review, hard)

- Do NOT mark a property calibrated from the same run that demonstrates detection
  without recording the derivation/detection split explicitly.
- Do NOT aggregate across pages in any way that masks unknown or unavailable.
- No weakened windows to ease passing; no faked outcomes for the faint page.

## Out of scope

- Integration into demo/evaluation reports (6.1/.7), docs (.8), final gate (.9).
  NO edits to `dsc03/**`, `openspec/**`, `justfile`, existing fixtures, or anything
  under `fixtures/` outside `fixtures/visual/calibration.json`. **No commits.
  No push.**

## Exact files

- CREATE `fixtures/visual/calibration.json`
- CREATE `tests/tracer/test_visual_calibration.py`
- CREATE `tests/tracer/fixtures/visual/<faint-fixture>.pdf` (+ README.org line) — only if needed
- CREATE `.wai/projects/sunset/research/sunset-xzy.6-report.org`

## Exact commands

- `/usr/bin/python3 -m pytest tests/tracer/test_visual_calibration.py -q` (bare
  `python3` lacks pytest; if pytest is missing entirely, STOP — do not pip-install)
- `/usr/bin/python3 -m pytest tests -q` (baseline 519 passed + 18 subtests)
- `just spec-check` → ALL GATES PASSED, PASS 11 descriptor fixtures
- `/usr/bin/python3 -m compileall tests/tracer/test_visual_calibration.py`

## Completion criteria (exit 0 = done)

1. Targeted pytest exits 0 (RED output recorded first, verbatim).
2. Full suite exits 0 (519+18 baseline + your new tests).
3. `just spec-check` exits 0, ALL GATES PASSED, PASS 11.
4. `git status --short` shows ONLY your deliverable paths (+ pre-existing
   `.whisper`/`.wai`/`pba-judicial-2026-07-29.pdf` noise); revert any render churn
   (measurement.json, snapshots) you caused.

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste actual RED/GREEN outputs, suite tail, and
gate tail. Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK). Window 1,000,000 tokens; **context
ceiling ≤ 15%**; exceed ⇒ stop and report. Complexity L: ~30 minutes wall-clock
budget.

## Follow-up threshold

If real-carrier measurements contradict oracle semantics (e.g. a native-text page
cannot produce a stable `[min,max]` under the pinned render), STOP: record the
finding + measured data in the report, touch nothing outside your deliverable paths,
leave the tree clean.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.6-report.org`: RED/GREEN outputs,
suite tail, gate tail, files changed, the final carrier→variety mapping, the
derivation-vs-detection set split (ALIGN-001), deviations, findings (labeled
AGENT-EXECUTED — human pass supersedes).
