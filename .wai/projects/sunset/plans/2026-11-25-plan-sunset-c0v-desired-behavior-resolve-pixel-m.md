---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-c0v-ceil-extent-binding, pipeline-step:plan]
---

PLAN sunset-c0v. Desired behavior: resolve_pixel_mapping computes expected px extent as ceil(source_pt*dpi/points_per_unit) matching poppler render surface; non-integral carriers bind; gross mismatches still refuse page-extent-mismatch. Test cases: variant-matrix helper synthesizes ceil extents; non-integral 432.063pt at 150dpi binds to 901x1351; integral 612x792 assertions unchanged. Out of scope: e2e dpi=72 pin, certificates, tolerance/document options. Narrow test command: .venv/bin/python -m pytest tests/tracer/test_visual_variant_matrix.py -q. Full verification command: just spec-check. Files likely touched: dsc03/visual/frames.py, openspec/changes/improve-geometry-render-binding/design.md, tests/tracer/test_visual_variant_matrix.py.
