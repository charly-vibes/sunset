---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:green]
---

GREEN (overcoverage/per-class slice): RED confirmed first — tests/tracer/test_visual_overcoverage.py: 11 failed, 4 baseline-control passes. Seeded giant region (572x520 claim over the 300x24 strip, agent-measured ratio ~34, fraction ~0.030 inside [0.01,1.0]) currently AGREEs: the defect demonstrated. Implementation: dsc03/visual/coverage.py gains shared per-class machinery — CONTENT_CLASSES=(text,vector,raster), content_classes-record validation -> typed unknowns class-observations-missing / class-observations-invalid, rect-union class masks painted from entries' rect_px, explained-by-<class> attribution on failing class-scoped ink claims whose claimed class is empty in-rect while another carrier class overlaps; masks.py gains oversized-region detection — pinned OVERSIZE_MAX_AREA_RATIO=20 (region-area : contained-ink-area measured on the primary comparison surface; legitimacy side validated: largest observed legitimate ratio ~13.3 = bank header band), region-oversized attribution on ink claims that PASS the primary window but overcover; no-ink claims exempt; primary failures keep plain differ. Calibration contract, recorded bounds and the agree/differ/unknown/unavailable vocabulary unchanged; claims without a class key evaluate identically (drift-pinned by test).

Verification evidence — commands run:
command=`uv run pytest tests/tracer/test_visual_overcoverage.py -x -q` -> collection SyntaxError in my own new test (malformed dict literal), fixed in the TEST file only, then:
command=`uv run pytest tests/tracer/test_visual_overcoverage.py -q` -> 11 failed, 4 passed (RED state confirmed before any production edit; failures = seeded giant region currently agrees + per-class TypeError on missing observations kwarg; the 4 passes are baseline controls, intended).
Non-production-code change in this step: none besides the new test file itself.
