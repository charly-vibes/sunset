---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-c0v-ceil-extent-binding, pipeline-step:quality-ledger]
---

QUALITY LEDGER sunset-c0v ceil extent binding. Changed: dsc03/visual/frames.py (round->math.ceil in resolve_pixel_mapping + convention comments), openspec/changes/improve-geometry-render-binding/design.md:14 (ceil wording), tests/tracer/test_visual_variant_matrix.py (ground-truth helper mirrors ceil). Verified: command=pytest tests/tracer/test_visual_variant_matrix.py -q -> 3 passed; full gate just spec-check scheduled at ship-close. Review: RO5U pass, 0/0/0/0 findings (.wai/projects/sunset/reviews/2026-11-25-ro5u-sunset-c0v-ceil-binding-pass.md). Risks: PyMuPDF pixmap convention unverified (out of scope, poppler-bound path unaffected). Next: ship-close after the debugger milestone slices land and the full gate runs green; bd sunset-c0v close with ruling note.
