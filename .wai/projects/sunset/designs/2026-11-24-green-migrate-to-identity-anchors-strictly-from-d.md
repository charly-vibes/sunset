---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-c6i-identity-migration-assembly, pipeline-step:green]
---

GREEN: migrate_to_identity anchors strictly from declared data: selector=own locator+own source_sha256, evidence=own source_ref, region/content=exactly-one targeting selector's locator (text content -> raw:<locator> per Decision 1); duplicate anchor tuples refuse BOTH records via report['unanchored']; relabel evidence = one record, origin manual, source_ref 'sha256:<sha>#relabel-table=<canonical json sorted [old,new]>' (evidence schema closed, referential lists would dangle, transform would claim content lineage), anchored at RELABEL_LOCATOR 'relabel-table'; every reference rebound; identity profile decl id 'identity' v1 pins test_identity IDENTITY_ARTIFACT bytes.

commands run: .venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py -q (18 passed); verified: existing suites test_migrate.py/test_views_space_context.py/test_identity.py/test_canonical_set_order.py 57 passed.
