---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:plan]
---

PLAN: ro5-review-fixes (TDD)
Desired behavior: (a) correlated review refusal carried structurally as page["refusal"]={code, reason}; "unavailable" keeps the prefixed display string (SPA unchanged); (b) quantize_scalar refuses non-finite coordinates with ValueError; digitization.native.extract converts that to NativeInputError('malformed-pdf', 'extraction produced non-finite word geometry'); (c) behavior-preserving refactors pinned by the existing suite: dsc03/visual/_pixels.py shared gate (done pre-start), _maybe_render helper in review.py, shared test fixtures to tests/tracer/conftest.py.
Out of scope: resolving owner flags G3/G5/G6 (owner-only), SPA template changes, git commit/push (conservative profile).
Tests to write FIRST (RED): extend test_visual_lineage_gate.py::test_evaluation_entry_refuses_correlated_render to assert refusal.code=="correlated-render-refused" and refusal.reason nonempty; new test_space_quantization.py::test_non_finite_coordinates_are_refused (nan/inf/-inf raise ValueError); new test_native_quantization.py::test_non_finite_word_geometry_is_typed_refused (monkeypatched _map_box returning NaN; extract raises NativeInputError match 'non-finite').
Narrow command: .venv/bin/python -B -m pytest tests/tracer/test_visual_lineage_gate.py tests/tracer/test_space_quantization.py tests/tracer/test_native_quantization.py -q
Full verification: just spec-check (openspec strict + spk lint + tracer suite + frozen 0.2 validator + openspec 1.x).
Files likely touched: dsc03/visual/review.py, dsc03/substrate/space.py, digitization/native.py, dsc03/visual/_pixels.py, dsc03/visual/coverage.py, dsc03/visual/masks.py, dsc03/visual/content_classes.py, tests/tracer/test_visual_lineage_gate.py, tests/tracer/test_space_quantization.py, tests/tracer/test_native_quantization.py, tests/tracer/conftest.py, tests/tracer/test_coverage.py, tests/tracer/test_reports.py, docs/src/status.md, openspec/changes/add-scale-complete-regions/design.md.

