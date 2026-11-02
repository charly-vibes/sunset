# Brief: sunset-xzy.2 — Declared frame mapping (pixel↔descriptor resolution)

**Ticket**: sunset-xzy.2 (beads, in_progress; complexity L — invariant-bearing)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 3.2
**Base commit**: 1f0b6b5 (sunset-xzy.1 shipped at `25eb25b`)
**Authority**: owner ruling 2026-11-02 in sunset-zo5 — tasks.md sections 3-7 ONLY.

## Why

Lead session orchestrates the sunset-xzy epic per the `epic-orchestrator` pipeline (canon
Invariant 1: the lead must not implement inline). This slice is a self-contained geometry
module with a hard invariant (wrong frames must never yield `agree`/`differ`), ideal for a
fresh-context implementor working test-first while the lead preserves context for
verification and shipping.

## Desired outcome

New module `dsc03/visual/frames.py` (plus its test file) that resolves pixel↔descriptor
coordinates **only through a declared geometry profile frame**, and produces `unknown`
outcomes for missing, incompatible, ambiguous or non-resolvable cases — never a guessed
coordinate convention.

Existing machinery you MUST build on (read these first):

- `dsc03/profiles.py` — `resolve_frame(artifact, frame_name)` →
  `('resolved', frame)` | `('invalid_geometry_frame', None)`; `resolve(decl, registry)` for
  profile artifacts. Do NOT modify this file — import from it.
- `tests/tracer/profiles/geometry-page-pt.json` — the frame record shape:
  `{"name", "unit": "pt", "origin": "bottom-left", "axes": "x-right-y-up", "scale": [1,1],
  "rotation": 0, "crop": null, "source_scope": "page:1"}`; artifact has `kind: "geometry"`,
  `version`, `subunit`.
- `dsc03/visual/render.py` (from sunset-xzy.1) — `Rendered(config, data)` /
  `RenderConfig(dpi, page, ...)`; render space is raster pixels at `config.dpi`, origin
  top-left, y-down (image convention). Do NOT modify — import.

Module contract:

1. `resolve_pixel_mapping(frame, render_config)` (or a similarly explicit API) returns a
   typed outcome: either a mapping object exposing forward/inverse coordinate transforms
   (descriptor point → pixel, pixel → descriptor point), or a typed `unknown` outcome
   carrying a reason. The mapping MUST be derived exclusively from the declared frame
   fields:
   - `unit` → scale factor to pixels (`pt` at DPI d ⇒ ×d/72; unknown/unsupported units ⇒
     `unknown`, never assume px);
   - `origin`/`axes` → axis flips (`bottom-left` + `x-right-y-up` is the canonical descriptor
     space; pixel space is top-left y-down ⇒ y must flip);
   - `scale` → additional declared scale factors;
   - `rotation` → 0/90/180/270 transforms of the pixel-space rectangle; other/missing values
     ⇒ `unknown` (no guessing "it's probably 0");
   - `crop` → declared offset when non-null;
   - `source_scope` (`page:N`) → binding check against `render_config.page`; mismatch ⇒
     `unknown` (ambiguous/wrong page).
2. Frame acquisition goes through `profiles.resolve_frame` (or the equivalent declared
   lookup): a region/descriptor referencing a frame name that does not resolve ⇒ `unknown`
   with reason `invalid_geometry_frame`-derived — never fall back to identity mapping.
3. Round-trip property: mapping(descriptor_pt) → pixel → mapping⁻¹(pixel) must recover the
   original descriptor point within a small epsilon (pin with an explicit tolerance constant;
   document it as the "pinned pixel tolerance").
4. Rotated-page case: a frame with `rotation: 90` (and one with 180 or 270 — pick per test
   taste, at least two rotation values total) must map the descriptor's region to the
   correctly transformed pixel coordinates using the declared rotation — verified against
   hand-computed expected pixels in the tests (tolerance-pinned), not by re-deriving with the
   same code under test.
5. Every result must be classifiable by the caller as resolved vs `unknown`; the string
   `"agree"`/`"differ"` MUST NOT appear as possible outcomes of this module (comparison
   verdicts belong to tasks 4.x — this module only resolves coordinates).
6. Each new module carries a **Purpose/Responsibilities/Rationale file header** (EXEC-004).

## Spec anchors

- `specs/document-visual-oracles/spec.md` → "Declared frame mapping": comparisons under
  incompatible, missing or ambiguous frames produce `unknown`, never `agree`/`differ`;
  scenarios "Rotated page" (declared rotated frame + pinned pixel tolerance) and
  "Missing frame" (region with no declared geometry frame ⇒ `unknown`).
- Deployed truth: `openspec/specs/document-adapters/spec.md` → "Declared coordinate frames"
  (frame semantics, `invalid_geometry_frame`, subunit integer precision).

## Out of scope

- No oracle property verdicts, no ink masks, no calibration (tasks 4.x+).
- No modifications to `dsc03/profiles.py`, `dsc03/visual/render.py`, any openspec file, the
  `spec/` bundle, or `validator.py` (frozen 0.2).
- No EPUB/unrenderable handling beyond what render.py already returns.
- **No `git push`. No commits.** (Ship step is the lead's.)

## Exact files

- CREATE `dsc03/visual/frames.py`
- CREATE `tests/tracer/test_visual_frames.py`
- (ALLOWED: a new test-fixture profile JSON under `tests/tracer/profiles/` if needed for a
  rotated/cropped frame — e.g. `geometry-rotated-page.json` — synthetic content is fine.)

## Test-first sequence (red → green → refactor)

1. **RED**: `tests/tracer/test_visual_frames.py` covering: (a) native carrier — identity-ish
   pt frame, rotation 0, page matches → mapping resolves; forward map of a known descriptor
   point equals hand-computed pixel; (b) rotated carrier — rotation 90/180 frame → mapped
   pixel equals hand-computed transformed coordinate within pinned tolerance; round-trip
   within epsilon; (c) scanned/cropped carrier — frame with `crop` → offset honored;
   (d) missing frame name → `unknown`, and result type is not a mapping; (e) unit
   `px`-unsupported/unknown unit → `unknown`; (f) page mismatch via `source_scope` →
   `unknown`; (g) invalid artifact (non-geometry kind) via `profiles.resolve_frame` path →
   `unknown`. Run with `/usr/bin/python3 -m pytest tests/tracer/test_visual_frames.py -q`
   → MUST FAIL first (ModuleNotFoundError). Record RED output.
2. **GREEN**: implement `dsc03/visual/frames.py` minimally; tests pass; record output.
3. **REFACTOR** only for clarity; rerun.
4. Full suite: `/usr/bin/python3 -m pytest tests -q` (baseline 459 passed + 18 subtests at
   1f0b6b5; your new tests add to it).
5. Gate: `just spec-check` → ALL GATES PASSED, frozen PASS 11.

## Exact commands

- `export SUNSET_PYTHON=/usr/bin/python3` is NOT needed if you call `/usr/bin/python3 -m
  pytest` directly (bare `python3` lacks pytest — justfile-documented gotcha).
- RED/GREEN: `/usr/bin/python3 -m pytest tests/tracer/test_visual_frames.py -q`
- Full: `/usr/bin/python3 -m pytest tests -q`
- Gate: `just spec-check`
- Syntax: `/usr/bin/python3 -m compileall dsc03/visual`

## Completion criteria (exit 0 = done)

1. `/usr/bin/python3 -m pytest tests/tracer/test_visual_frames.py -q` exits 0
2. `/usr/bin/python3 -m pytest tests -q` exits 0 (no regressions; ≥459+18 baseline + new)
3. `just spec-check` exits 0, ALL GATES PASSED, PASS 11
4. `git status --short` shows only the new files (+ pre-existing `.whisper`/`.wai`/
   `pba-judicial-2026-07-29.pdf` noise); revert any measurement/fixture churn you caused.

## Verifier evidence contract (wai-px4g)

Your report must cite files changed and paste actual RED and GREEN outputs; the verify
session cross-checks claims against reality (`git status`, fresh runs). Claims without pasted
output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` via `pi -p --provider openrouter --model z-ai/glm-5.3-flash`.
Window 1,000,000 tokens; estimated use ≪150K → **context ceiling ≤ 15%**; exceed ⇒ stop and
report.

## Follow-up threshold

Geometry math is fiddly: if a transform proves ambiguous at spec level (e.g. rotation
direction conventions irreconcilable with the declared `axes`), STOP, record the finding,
change nothing beyond the designated files, leave the tree clean. Max ~25 minutes wall-clock.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.2-report.org`: RED/GREEN outputs, full-suite
tail, gate tail, files changed, deviations, findings.
