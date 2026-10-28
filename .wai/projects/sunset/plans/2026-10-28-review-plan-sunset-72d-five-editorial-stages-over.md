---
tags: [pipeline-run:tdd-ro5-2026-10-28-sunset-72d-digitization-review, pipeline-step:plan]
---

Review plan sunset-72d: five editorial stages over digitization .2-.5, reproduce multi-step selection rollback, cached-output admission, malformed envelope replacement, and manifest/ledger mismatch with synthetic sources. No production fixes. Remediation must write regression tests first, then minimal fixes, focused suite python3 -B -m pytest tests/tracer/test_digitization_*.py -q and full OMP_THREAD_LIMIT=1 npm_config_cache=/tmp/sunset-905-3-npm-cache just spec-check. Files: refinement.py, inspection.py, structure.py, pipeline.py, focused tests. Prior implementations were outside the pipeline; do not backfill RED/GREEN gates. Await regression-test implementation after this review.
