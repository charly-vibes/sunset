---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-c6i-identity-migration-assembly, pipeline-step:refactor]
---

REFACTOR: no behavior change — _declared_anchor returns the full (record_kind, locator_path, source_sha256) tuple (call site stores it verbatim, no re-wrap); compose sorts merged vocabularies before building the output dict instead of mutating after. command=.venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py tests/tracer/test_migrate.py -q; verified: 29 passed.
