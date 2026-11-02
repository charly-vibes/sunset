# Brief: sunset-xzy.4 — Geometry-mask alignment oracle (representation level C)

**Ticket**: sunset-xzy.4 (beads, in_progress)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 4.2
**Base commit**: d615125 (xzy.1 `25eb25b`, .2 `cb9487e`, .3 `0492882` shipped)
**Authority**: owner ruling 2026-11-02 in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

Lead orchestrates the sunset-xzy epic per the `epic-orchestrator` pipeline (canon Invariant 1
— no inline implementation). Single oracle module over the existing render/frame/coverage
surfaces — bounded TDD work for a fresh-context implementor while the lead preserves context.

## Desired outcome

`dsc03/visual/masks.py`: the level-C (D3) **geometry-mask alignment oracle**. It evaluates
exactly one property — `"region-alignment"` — comparing **descriptor region masks** (declared
rects mapped through frames) against the **simplified source render**, with every
disagreement retained and region-attributed. Import, never modify:
`dsc03/visual/render.py` (Rendered/RenderUnavailable/RenderConfig/Binarization),
`dsc03/visual/frames.py` (frame_mapping → PixelMapping.descriptor_to_pixel /
UnknownMapping), `dsc03/visual/coverage.py` — **read it first**: its binarization guard,
dilation parser (`ink-dilation-<N>px`), unknown/outcome patterns, aggregate rule and
EXEC-004 header style are the house pattern for this slice. Reuse its helpers where sensible
(import, don't duplicate: `_decode_grayscale`, `_parse_dilation`, `_dilate` are private — if
reused, import them explicitly or re-implement thin wrappers; do NOT edit coverage.py).

Module contract:

1. **No naive mask-vs-pixels (D4, hard invariant)**: rectangles cover whitespace between
   glyphs. Region-mask alignment is measured against the SIMPLIFIED source: binarized ink
   mask dilated by the recorded `source_simplification` (`ink-dilation-<N>px`, same parser
   semantics as coverage.py). `source_simplification == "none"` ⇒ outcome `unknown`
   (reason `source-simplification-missing`); missing/unmapped frame ⇒ `unknown` with the
   frame reason; binarization not configured ⇒ `unknown` (`binarization-not-configured`);
   `RenderUnavailable` ⇒ `unavailable`. No defaults, config drives everything.
2. **Alignment test per region**: a claimed region rect (descriptor points, `{"id", "x",
   "y", "w", "h", "expected": "ink"|"no-ink"}`) is mapped to pixel coords through the
   declared frame; `agree` iff the simplified-source ink fraction inside the mapped rect
   satisfies the region's expectation against the ONE recorded calibration entry for
   carrier+page (same entry shape as coverage.py: `{"property", "carrier", "page", "min",
   "max"}` — region `expected:"ink"` requires measured ≥ min; `expected:"no-ink"` requires
   measured ≤ min's complement bound ≤ max… pin the exact rule in the docstring, mirroring
   coverage.py's pinned semantics); otherwise `differ`. Additional refinement allowed: a
   region whose ink lies substantially OUTSIDE its rect while the rect itself is empty ⇒
   `differ` with reason `ink-outside-rect` (detect via dilation bleed: ink within N px
   outside the rect boundary counts as misplaced, not missing — pin the rule). Keep it
   simple and deterministic; document every threshold.
3. **Outcome object**: `status` (`agree`/`differ`/`unknown`/`unavailable`), `property:
   "region-alignment"`, `page`, `carrier`, `evidence_class` (from config), `regions` (list
   of `{"id", "status"}` + optional `reason` — retained, never elected, never smoothed,
   never mutating inputs), `reason` when not agree/differ.
4. **Aggregate**: `aggregate(outcomes)` → `pass` ONLY if every page outcome is `agree` with
   calibration recorded; else `blocked` + reasons (one blank/degraded page never passes).
5. **Scoped claims**: `PROPERTY = "region-alignment"`; `SCOPED_CLAIM` constant + docstring:
   alignment pass establishes nothing about text correctness, reading order, semantic
   grouping or visual completeness. Missing calibration ⇒ `unknown`/`uncalibrated`.
6. **Evidence class**: from config; `supports_accuracy_claim(outcome)` delegating to
   render.py semantics (correlated ⇒ sensitivity only).
7. **EXEC-004** header on both new files.

## Spec anchors

- "No silent resolution" (+ scenario "Mask disagreement": retained region ids, neither
  reading replaced) · "Scoped property claims" · "Calibrated thresholds with per-page
  outcomes" · "Labeled evidence class" · design D3 (level C = geometry-only masks), D4.

## Out of scope

- Mutation fixtures (5.x), calibration sheet (6.x), conformance integration (7.x), docs
  (8.x). No edits to render.py/frames.py/coverage.py/profiles.py/openspec/spec bundle/
  validator.py. No EPUB. **No `git push`. No commits.**

## Exact files

- CREATE `dsc03/visual/masks.py`
- CREATE `tests/tracer/test_visual_masks.py`

## Test-first sequence (red → green → refactor)

1. **RED**: `tests/tracer/test_visual_masks.py` — deterministic synthetic carriers built
   in-test with `pymupdf` (white page + black rects at hand-computed pixel positions; use
   the landscape-raster trick from sunset-xzy.3's report for the rotated carrier — see
   `.wai/projects/sunset/research/sunset-xzy.3-report.org` finding 1). Tests: (a) aligned
   ink region ⇒ agree; (b) ink-outside-rect ⇒ differ with region id + reason retained;
   (c) no-ink region over blank area ⇒ agree; over ink ⇒ differ; (d) rotated carrier via
   declared 90° frame + wrong-frame flip control (rot180 frame flips verdict — proves the
   declared frame drives comparison); (e) unavailable from RenderUnavailable; (f) unknown
   matrix: missing frame / uncalibrated / binarization disabled / simplification none;
   (g) aggregate blocking; (h) property + evidence-class fields everywhere; correlated ⇒
   not supports_accuracy_claim. One real-carrier smoke:
   `fixtures/carriers/bank-statement-ca-excerpt.pdf` page 1, wide bounds, status
   agree/differ (not unknown/unavailable). Run
   `/usr/bin/python3 -m pytest tests/tracer/test_visual_masks.py -q` → MUST FAIL
   (ModuleNotFoundError). Record RED output.
2. **GREEN**: implement `dsc03/visual/masks.py` minimally; record GREEN output.
3. **REFACTOR** only for clarity. 4. Full: `/usr/bin/python3 -m pytest tests -q` (baseline
   494+18). 5. Gate: `just spec-check` → ALL GATES PASSED, PASS 11.

## Exact commands

- `/usr/bin/python3 -m pytest tests/tracer/test_visual_masks.py -q` (bare `python3` lacks
  pytest) · `/usr/bin/python3 -m pytest tests -q` · `just spec-check` ·
  `/usr/bin/python3 -m compileall dsc03/visual`

## Completion criteria (exit 0 = done)

1. Targeted pytest exits 0. 2. Full suite exits 0 (≥ 494+18 + new). 3. `just spec-check`
   exits 0, ALL GATES PASSED, PASS 11. 4. `git status --short` shows only the two new files
   (+ pre-existing `.whisper`/`.wai`/`pba-judicial-2026-07-29.pdf` noise); revert any
   measurement/fixture churn you caused.

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste actual RED/GREEN outputs; verify session
cross-checks against reality. Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK — zai usage billed to the owner's Z.ai key).
Window 1,000,000 tokens; **context ceiling ≤ 15%**; exceed ⇒ stop and report.

## Follow-up threshold

If alignment semantics prove ambiguous at spec level (e.g. the ink-outside-rect rule
irreconcilable with D4), STOP, record findings, touch nothing beyond the designated files,
leave the tree clean. Max ~25 minutes wall-clock.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.4-report.org`: RED/GREEN outputs, suite
tail, gate tail, files changed, deviations, findings.
