# Brief: sunset-xzy.5 — Mutation validation: seeded shift/omission/duplication/wrong-frame fixtures

**Ticket**: sunset-xzy.5 (beads, in_progress)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 5.1
**Base commit**: 5a608b8 (xzy.1 `25eb25b`, .2 `cb9487e`, .3 `0492882`, .4 `c25f013` shipped)
**Authority**: owner ruling 2026-11-02 in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

The spec's "Mutation-validated sensitivity" requirement gates the whole epic: an oracle
property MAY gate decisions ONLY after a recorded demonstration that it detects each
defect class it claims, using seeded mutations (shift, omission, duplication, wrong
frame) on pinned carriers. Properties without a demonstration are `uncalibrated` and
cannot gate anything. This slice builds that demonstration corpus. It is a TEST-AND-
FIXTURE slice: the two oracles (`dsc03/visual/coverage.py`, `dsc03/visual/masks.py`)
already exist and MUST NOT be edited. If a seeded mutation exposes a real detection
gap, that is a STOP-and-record finding, not something you patch in the oracle.

## Desired outcome

Two deliverables, nothing else:

1. `tests/tracer/test_visual_mutations.py` — the mutation-validation suite.
2. `tests/tracer/fixtures/visual/` — COMMITTED, deterministic, tiny seeded-mutation
   fixtures (synthetic carriers built with `pymupdf` at creation time, committed as
   bytes, plus any descriptor/calibration JSON they pair with). Naming them
   `<carrier>-<mutation-class>.pdf` style is fine; document each file's provenance in
   a README.org or comment block (seed-free hand-computed geometry, which tool built
   it, what the mutation is).

### The four defect classes (spec vocabulary, not negotiable)

- **shift** — spec scenario: every region box shifted 12 pixels ⇒ alignment oracle
  outcome `differ` (region-attributed). Your shift fixtures MUST use ≥12 px so the
  demonstration matches the spec scenario exactly.
- **omission** — expected ink absent (ink block removed from the carrier, or an ink
  region omitted from the descriptor) ⇒ the claiming oracle reports `differ`.
- **duplication** — ink duplicated (the same ink block copied elsewhere on the page,
  or a region claimed twice) ⇒ the claiming oracle reports `differ`.
- **wrong frame** — the declared frame deliberately wrong (e.g. rot180 where rot90 is
  declared, or a 12 px offset baked into the frame) ⇒ alignment outcome `differ`.

### Claim discipline (the heart of the ticket)

Each oracle detects EXACTLY the defect classes it claims. Read both modules' docstrings
and outcome semantics FIRST, then pin the class→oracle mapping in the test module
docstring (state which oracle claims which class and why that follows from its
documented semantics). For every claimed class: a seeded fixture demonstration that
ends `differ` with region attribution. For any class an oracle does NOT claim: say so
explicitly in the docstring and pin the consequence — per the spec scenario
"Undemonstrated class", a property stays `uncalibrated` and cannot gate: assert the
no-gate path (missing calibration ⇒ `unknown` outcome and `aggregate()` NEVER reports
`pass` while a property/outcome is `unknown`/`uncalibrated`).

ANTI-GOALS (issue-review EXEC-003, hard):
- Do NOT weaken mutation magnitude/severity to ease detection.
- Do NOT count a class as demonstrated without its seeded fixture passing.
- Detection outcome is `differ` WITH region attribution per the spec scenario — not a
  loosened comparison, not `unknown`, not a softened aggregate.

### Red → green shape for a fixtures-only slice

- **RED**: with `tests/tracer/fixtures/visual/` absent, the suite fails (missing
  fixture files). Record the verbatim failure.
- **GREEN**: fixtures committed; every test passes. Every mutation test MUST carry an
  unmutated baseline control asserting the oracle `agree`s on the pristine fixture —
  detection is attributable to the mutation, never to baseline miscalibration.
- **REFACTOR** only for clarity inside your two deliverables.

### Geometry gotchas (from xzy.3/.4 reports — read both)

- pymupdf `draw_rect(color=..., fill=...)` strokes a +1px halo beyond the fill rect.
  12 px shifts dwarf it, but omission/duplication blocks ADJACENT to existing ink must
  budget the halo or draw fill-only: `draw_rect(rect, fill=(0,0,0), color=None, width=0)`.
- Landscape trick for rotated rasters: draw a plain 792x612 page with ink where the
  DECLARED frame maps the descriptor box; never use `pymupdf set_rotation`.
- Calibration entries keep the recorded shape
  `{"property", "carrier", "page", "min", "max"}` (coverage bounds ink fraction; masks
  bounds region ink fraction — read `_usable_calibration` / `_usable_region_calibration`
  for the exact pinned semantics and reuse a realistic `[min, max]` window).

### Render discipline

Use the pinned `RenderConfig`/`render_page` from `dsc03/visual/render.py` exactly as
`test_visual_render.py`/`test_visual_masks.py` do (pdftoppm is available). If a render
is unavailable in your environment, use the in-repo recorded pattern (`Rendered` vs
`RenderUnavailable`) — do not fake outcomes; a fixture that cannot render is a STOP.

## Spec anchors

- "Mutation-validated sensitivity" + scenarios "Seeded shift detected" (12 px ⇒
  `differ`, property eligible for calibration) and "Undemonstrated class" (claimed
  omission without demonstration ⇒ `uncalibrated`, cannot gate).
- "Calibrated thresholds with per-page outcomes" (aggregate never passes with
  unknown/uncalibrated pages) · "No silent resolution" (retain + region-attribute,
  never elect/smooth/mutate inputs) · "Scoped property claims".

## Out of scope

- Calibration sheet (5.2/.6), conformance integration (6.1/.7), docs (.8), final gate
  (.9). NO edits to `dsc03/**`, `openspec/**`, `justfile`, or any committed fixture
  outside `tests/tracer/fixtures/visual/`. **No `git push`. No commits.**

## Exact files

- CREATE `tests/tracer/test_visual_mutations.py`
- CREATE `tests/tracer/fixtures/visual/` (all fixture files + provenance note)
- CREATE `.wai/projects/sunset/research/sunset-xzy.5-report.org`

## Exact commands

- `/usr/bin/python3 -m pytest tests/tracer/test_visual_mutations.py -q` (bare
  `python3` lacks pytest; if pytest is missing entirely, STOP — do not pip-install)
- `/usr/bin/python3 -m pytest tests -q` (baseline 509 passed + 18 subtests)
- `just spec-check` → ALL GATES PASSED, PASS 11 descriptor fixtures
- `/usr/bin/python3 -m compileall tests/tracer/test_visual_mutations.py`

## Completion criteria (exit 0 = done)

1. Targeted pytest exits 0 (RED output recorded first, verbatim).
2. Full suite exits 0 (509+18 baseline + your new tests).
3. `just spec-check` exits 0, ALL GATES PASSED, PASS 11.
4. `git status --short` shows ONLY your two deliverable paths (+ pre-existing
   `.whisper`/`.wai`/`pba-judicial-2026-07-29.pdf` noise); revert any render churn
   (measurement.json, snapshots) you caused.

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste actual RED/GREEN outputs, suite tail, and
gate tail. Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK — zai usage billed to the owner's Z.ai
key). Window 1,000,000 tokens; **context ceiling ≤ 15%**; exceed ⇒ stop and report.

## Follow-up threshold

If a seeded mutation exposes a detection gap in an existing oracle, or calibration
semantics cannot express a mutation class, STOP: record the finding in the report,
touch nothing outside your deliverable paths, leave the tree clean. Max ~25 minutes
wall-clock.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.5-report.org`: RED/GREEN outputs,
suite tail, gate tail, files changed, the pinned class→oracle mapping, deviations,
findings (explicitly labeled AGENT-EXECUTED demonstration — human pass supersedes).
