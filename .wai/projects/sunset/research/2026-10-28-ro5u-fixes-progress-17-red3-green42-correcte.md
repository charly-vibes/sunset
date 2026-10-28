---
tags: [pipeline-run:tdd-ro5-2026-10-28-sunset-72d-digitization-review, pipeline-step:fix-review]
---

RO5U-FIXES progress: .17 RED3 -> GREEN42 (corrected earlier fixture-collision verification record); .18 RED cached-mismatch refusal and cached-match acceptance -> GREEN25 with retained candidate artifacts and usage; .19 RED4 malformed-envelope variants -> GREEN29 refinement tests; .20 RED3 manifest amount/type/unbound-ledger variants -> GREEN85 digitization tests. .0y1 RED2 stock ship configuration/missing oracle -> GREEN2 real isolated frozen-fixture checks, including broken-fixture refusal. New executable spec-corpus oracle invokes actual just spec-check, full gate now running. No tidy/refactor bundled; docs updated to precise realized-output/ledger behavior.

Verified: command=python3 -B -m pytest tests/tracer/test_digitization_first_page.py tests/tracer/test_digitization_cache.py tests/tracer/test_digitization_structure.py tests/tracer/test_digitization_refinement.py -q; 85 passed in16.99s before final typed-key test. Isolated oracle2 passed. Final refinement30 passed after typed-key correction; final full corpus oracle is running.
