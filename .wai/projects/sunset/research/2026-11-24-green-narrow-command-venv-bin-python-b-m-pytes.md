---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-c6i-identity-migration-assembly, pipeline-step:green]
---

GREEN: narrow command .venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py -q = 18 passed. Existing suites untouched and green: test_migrate.py + test_views_space_context.py + test_identity.py + test_canonical_set_order.py = 57 passed. Implementation notes: (1) regime in _compose_nonempty also makes the assembled descriptor label order-independent (min of operand labels) and sorts merged vocabularies by namespace — compose takes the LEFT operand's label and vocab list order, so without these compose(a,b)/compose(b,a) could never be canonically equal whatever the sections; label regime keeps left label/order byte-identical. (2) detection reuses canonical._declares_identity_profile (one convention). Two test bugs fixed en route (anchors map keyed by (kind, locator); expected table order sorted).

command=.venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py -q; result=18 passed in 0.05s.
command=.venv/bin/python -B -m pytest tests/tracer/test_migrate.py tests/substrate/test_views_space_context.py tests/tracer/test_identity.py tests/tracer/test_canonical_set_order.py -q; result=57 passed in 0.15s.
verified: green confirmed; existing migrate/assembly behavior byte-identical (hard constraint held).
