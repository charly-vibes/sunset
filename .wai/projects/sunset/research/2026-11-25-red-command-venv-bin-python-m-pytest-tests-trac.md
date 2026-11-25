---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-c0v-ceil-extent-binding, pipeline-step:red]
---

RED: command=.venv/bin/python -m pytest tests/tracer/test_visual_variant_matrix.py -q against pre-change round() binder (frames.py stashed) -> test_every_native_frame_resolves FAILED 156/240 frames unresolved with page-extent-mismatch at (901,1351)/(1351,901) - the expected missing ceil behavior, non-integral budgeting-basics carrier refused at every dpi. Restored impl: 3 passed. Expected failure confirmed for the right reason.
