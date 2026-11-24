command=.venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py -q; result=18 passed in 0.05s.
command=.venv/bin/python -B -m pytest tests/tracer/test_migrate.py tests/substrate/test_views_space_context.py tests/tracer/test_identity.py tests/tracer/test_canonical_set_order.py -q; result=57 passed in 0.15s.
verified: green confirmed; existing migrate/assembly behavior byte-identical (hard constraint held).
