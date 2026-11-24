---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:red]
---

RED: command=.venv/bin/python -B -m pytest tests/tracer/test_visual_lineage_gate.py tests/tracer/test_space_quantization.py tests/tracer/test_native_quantization.py -q
Expected failures confirmed: (1) test_evaluation_entry_refuses_correlated_render -> KeyError 'refusal' (structured refusal field absent in _page_record); (2) test_non_finite_coordinates_are_refused -> ValueError raised but with Fraction's message, not the typed guard ('cannot convert NaN to integer ratio'); (3) test_non_finite_word_geometry_is_typed_refused -> raw ValueError escapes extract() untyped (expected NativeInputError 'malformed-pdf').
Side validation: 11 pre-existing oracle/quantization tests pass with the _pixels.py extraction in place — refactor is behavior-preserving.

