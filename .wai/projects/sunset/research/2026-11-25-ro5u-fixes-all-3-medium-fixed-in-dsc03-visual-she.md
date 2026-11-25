---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-5bu-36n-j1c-debugger-slices, pipeline-step:fix-review]
---

RO5U-FIXES: all 3 Medium fixed in dsc03/visual/sheet_import.py — (1) pinned _ASPECT_TOLERANCE=0.01 aspect guard -> UnknownMapping page-extent-mismatch (rotated/swapped recording refuses, corpus deviates <0.1%); (2) _CarrierPages opens carrier once per sheet, closed in finally; (3) non-dict structure entry -> typed invalid-box refusal. Lows: (4) label key only for non-empty str labels + uniqueness assertion in test 1; (5) pt_dims out-param folded into _CarrierPages. Tests added first (RED confirmed): test_swapped_viewport_frame_is_refused_not_silently_mismapped, test_non_dict_structure_entry_is_refused_not_fatal. commands run: uv run pytest tests/tracer/test_sheet_import.py tests/tracer/test_visual_frames.py tests/tracer/test_adapters.py -q -> 49 passed.
