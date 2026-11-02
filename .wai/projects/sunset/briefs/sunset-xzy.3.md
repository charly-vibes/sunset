# Brief: sunset-xzy.3 — Binarized ink-coverage oracle (representation level B)

**Ticket**: sunset-xzy.3 (beads, in_progress)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 4.1
**Base commit**: ec2b298 (xzy.1 `25eb25b`, xzy.2 `cb9487e` shipped)
**Authority**: owner ruling 2026-11-02 in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

Lead orchestrates the sunset-xzy epic per the `epic-orchestrator` pipeline (canon Invariant 1
— no inline implementation). This slice is a single oracle module over the existing render +
frame surfaces, well-bounded for a fresh-context TDD implementor while the lead preserves
context for verification and shipping.

## Desired outcome

`dsc03/visual/coverage.py`: the level-B (D3) **binarized ink-coverage oracle**. It evaluates
exactly one property — `"ink-coverage"` — for pinned carrier pages, comparing claimed region
coverage against the pinned render's binarized ink, and reports typed per-page/per-property
outcomes with evidence class. Build on (import, never modify):

- `dsc03/visual/render.py` — `Rendered(config, data)` PNG bytes / `RenderUnavailable`;
  `RenderConfig` with `binarization` (`Binarization.enabled/method/threshold`) and
  `source_simplification` (string, e.g. `"ink-dilation-2px"`); `evidence_class` property.
- `dsc03/visual/frames.py` — `frame_mapping(artifact, frame_name, render_config, page_px)`
  → `PixelMapping` (with `descriptor_to_pixel` / `pixel_to_descriptor`) or
  `UnknownMapping(reason)`. Region rects are in descriptor points; convert through the
  declared frame — an unknown mapping makes the outcome `unknown`, never a guessed
  conversion.

Module contract:

1. **Binarize** the rendered PNG (decode pixels with `pymupdf`/`fitz` Pixmap — decoding
   rendered bytes is NOT a lineage-bearing step; the evidence label comes solely from
   `config.evidence_class`). Grayscale → ink mask via `config.binarization` (method
   `fixed-threshold` + `threshold`); if `binarization.enabled` is false ⇒ per-page outcome
   `unknown` (reason `binarization-not-configured`) — config drives everything, no defaults.
2. **Like-with-like source simplification (D4)**: apply the recorded `source_simplification`
   (ink dilation, e.g. parse `"ink-dilation-<N>px"` → dilate the ink mask by N px, 4-
   or 8-connected, your pick — pin it in the module docstring) as tolerance. If
   `source_simplification` is `"none"` ⇒ `unknown` (reason `source-simplification-missing`).
3. **Evaluate**: input = page's claimed region rects (descriptor coords, `{"id", "x", "y",
   "w", "h", "expected": "ink"|"no-ink"}` dicts) + one **recorded calibration entry** for
   the carrier+page (dict `{"property": "ink-coverage", "carrier": ..., "page": ...,
   "min": float, "max": float}` — the numeric calibration SHEET itself is sunset-xzy.6; tests
   record their own entries as the pinned calibration for their synthetic carriers).
   Per region: measured ink fraction (after dilation) within the mapped pixel rect vs
   `expected` and calibration bounds ⇒ region outcome `agree`/`differ`. Out-of-bounds or
   `expected` claims contradicting calibration ⇒ `differ` with the region `id` retained.
   Aggregation to page outcome follows the same bounds over the whole page.
4. **Outcome object** carries ALL of: `status` (`agree`/`differ`/`unknown`/`unavailable`),
   `property: "ink-coverage"`, `page`, `evidence_class` (from config), `carrier`,
   `regions` (list of `{id, status}` for region-level attribution — retain, never elect,
   never smooth, never mutate inputs), and `reason` when not agree/differ.
5. **Typed unavailability**: a `RenderUnavailable` input ⇒ outcome `unavailable` (reason
   carried). An `UnknownMapping` ⇒ `unknown` with that reason. A missing calibration entry
   ⇒ `unknown` with reason `uncalibrated`.
6. **Aggregate rule**: an `aggregate(outcomes)` helper returns `"pass"` ONLY if every page
   outcome is `agree` with calibration recorded (no `unknown`/`unavailable`/uncalibrated
   anywhere); otherwise `"blocked"` with the blocking reasons listed. One blank/degraded
   page must never yield an aggregate pass.
7. **Scoped property claims**: module docstring + a `SCOPED_CLAIM` constant state that a
   coverage pass establishes NOTHING about text correctness, reading order, semantic
   grouping or visual completeness. Every outcome carries the `property` field.
8. **Evidence class**: `correlated` results flow through unchanged but a helper
   `supports_accuracy_claim(outcome)` (reuse semantics from render.py) makes the
   sensitivity-only restriction explicit at the oracle level.
9. **EXEC-004**: Purpose/Responsibilities/Rationale header on the new module AND the test
   file.

## Spec anchors (openspec/changes/add-raster-visual-oracles/specs/document-visual-oracles/spec.md)

- "Scoped property claims" (+ scenario "Coverage pass with wrong order")
- "Calibrated thresholds with per-page outcomes" (+ scenario "Faint scan": degraded page ⇒
  page `unknown`, aggregate does not pass)
- "No silent resolution" (retain region-attributed disagreements)
- "Labeled evidence class"; "Pinned render configuration"; D3/D4 in design.md

## Out of scope

- Geometry-mask alignment (level C = sunset-xzy.4 / tasks 4.2), mutation fixtures (5.x),
  the actual calibration sheet (6.x), conformance integration (7.x), docs (8.x).
- No modifications to `dsc03/visual/render.py`, `frames.py`, `profiles.py`, any openspec
  file, `spec/` bundle, `validator.py` (frozen 0.2).
- **No `git push`. No commits.** (Ship step is the lead's.)

## Exact files

- CREATE `dsc03/visual/coverage.py`
- CREATE `tests/tracer/test_visual_coverage.py`
- (Optional, ALLOWED: a small fixture profile JSON under `tests/tracer/profiles/` if the
  rotated-carrier test needs a declared rotated frame — reuse
  `tests/tracer/profiles/geometry-rotated-page.json` from xzy.2 if suitable.)

## Test-first sequence (red → green → refactor)

1. **RED**: `tests/tracer/test_visual_coverage.py`. Build deterministic synthetic pinned
   carriers IN-TEST with `pymupdf` (`import pymupdf`; white page + drawn black rectangles =
   known ink; save to tmp_path) — pin the exact bytes via a fixed seed-free construction.
   Tests: (a) ink-region agree: region over drawn box, calibration bounds satisfied ⇒
   region+page `agree`; (b) differ: region over blank area claiming ink (bounds unsatisfied)
   ⇒ `differ` with region id retained; (c) rotated carrier: 90° declared frame maps the
   region; verdict computed on the correctly mapped rect; (d) `unavailable` from
   `RenderUnavailable`; (e) `unknown` matrix: missing frame / uncalibrated / binarization
   disabled / `source_simplification == "none"`; (f) aggregate: single `unknown` page blocks
   pass ("faint scan" scenario); (g) every outcome carries `property="ink-coverage"` +
   evidence class; correlated config ⇒ `supports_accuracy_claim` False. One test renders a
   REAL pinned carrier (`fixtures/carriers/bank-statement-ca-excerpt.pdf`, page 1) and
   asserts the oracle RUNS with wide recorded bounds (status is agree/differ — not
   unknown/unavailable). Run `/usr/bin/python3 -m pytest tests/tracer/test_visual_coverage.py
   -q` → MUST FAIL first (ModuleNotFoundError). Record RED output.
2. **GREEN**: implement `dsc03/visual/coverage.py` minimally; record GREEN output.
3. **REFACTOR** only for clarity; rerun.
4. Full suite: `/usr/bin/python3 -m pytest tests -q` (baseline 477 passed + 18 subtests).
5. Gate: `just spec-check` → ALL GATES PASSED, frozen PASS 11.

## Exact commands

- Bare `python3` lacks pytest — always `/usr/bin/python3 -m pytest ...` (justfile-documented).
- RED/GREEN: `/usr/bin/python3 -m pytest tests/tracer/test_visual_coverage.py -q`
- Full: `/usr/bin/python3 -m pytest tests -q` · Gate: `just spec-check` ·
  Syntax: `/usr/bin/python3 -m compileall dsc03/visual`

## Completion criteria (exit 0 = done)

1. `/usr/bin/python3 -m pytest tests/tracer/test_visual_coverage.py -q` exits 0
2. `/usr/bin/python3 -m pytest tests -q` exits 0 (≥ 477+18 baseline + new)
3. `just spec-check` exits 0, ALL GATES PASSED, PASS 11
4. `git status --short` shows only the new files (+ pre-existing `.whisper`/`.wai`/
   `pba-judicial-2026-07-29.pdf` noise); revert any measurement/fixture churn you caused.

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste actual RED and GREEN outputs; the verify session
cross-checks against reality. Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK — zai usage billed to the owner's Z.ai key,
not OpenRouter credits). Window 1,000,000 tokens; estimated use ≪150K → **context ceiling
≤ 15%**; exceed ⇒ stop and report.

## Follow-up threshold

If binarization/dilation on real carrier pixels proves nondeterministic or a spec-level
ambiguity surfaces (e.g. dilation semantics irreconcilable with D4), STOP, record findings,
change nothing beyond the designated files, leave the tree clean. Max ~25 minutes wall-clock.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.3-report.org`: RED/GREEN outputs, full-suite
tail, gate tail, files changed, deviations, findings.
