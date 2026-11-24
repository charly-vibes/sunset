---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-c6i-identity-migration-assembly, pipeline-step:fix-review]
---

RO5U-FIXES: both findings were Low. (1) targeting-lookup micro-dedup in _unanchored_reason: left as-is deliberately — the reason text needs the pin list with different framing than the anchor derivation; merging would couple report wording to derivation internals. (2) min-label + identity-regime vocabulary sort: kept, already documented in the compose comment; ratification belongs to define-document-composition-semantics, not this slice. No behavior-impacting fixes, so no new tests. commands run: .venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py tests/tracer/test_migrate.py -q; verified: 27 passed (unchanged).
