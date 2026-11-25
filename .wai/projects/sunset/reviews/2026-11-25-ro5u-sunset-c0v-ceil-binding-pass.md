# RO5U review: sunset-c0v ceil extent binding (2026-11-25)

Scope: diff of dsc03/visual/frames.py, openspec/changes/improve-geometry-render-binding/design.md, tests/tracer/test_visual_variant_matrix.py @ main (post 83ddf93 worktree).

## Findings

- Critical: none.
- High: none.
- Medium: none.
- Low: none blocking.

## Review notes (evidence)

1. Comparison swap order: `expected` computes ceil per axis, rotation 90/270 swaps the tuple afterwards — matches poppler (pdftoppm applies ceil to the rendered page, rotation transposes output dims). Confirmed empirically: with the old round() binder stashed, `test_every_native_frame_resolves` failed 156/240 frames at exactly (901,1351)/(1351,901); with ceil, all pass.
2. Exactness preserved: no tolerance added; gross mismatch (wrong page/crop/dpi) still refuses via page-extent-mismatch — the D2 silent-false-bind class stays closed.
3. Comments at frames.py:32/:215 state the poppler convention; design.md:14 wording synced; matrix ground-truth helper mirrors ceil so the synthetic matrix cannot mask a future convention drift. Integral 612x792 assertions untouched (ceil==round there).
4. Certificates/render-cache contain no extent pins (grep clean) — blast radius confined to the binder and its helper.
5. Residual known-unknown (out of scope, recorded in ticket): PyMuPDF pixmap sizing convention unverified; irrelevant to the poppler-bound path this ruling covers.

## Verdict

pass — ship-ready.
