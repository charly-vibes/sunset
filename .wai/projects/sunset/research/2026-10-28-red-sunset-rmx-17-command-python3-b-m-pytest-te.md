---
tags: [pipeline-run:tdd-ro5-2026-10-28-sunset-72d-digitization-review, pipeline-step:red]
---

RED sunset-rmx.17: command=python3 -B -m pytest tests/tracer/test_digitization_refinement.py -k selection_survives -q; three regressions fail because corrected fresh/explicit OCR reverts after unrelated revision. User authorized all review repairs; handle each ticket in separate red-green cycles within fix-review scope. No implementation changed before this evidence.
