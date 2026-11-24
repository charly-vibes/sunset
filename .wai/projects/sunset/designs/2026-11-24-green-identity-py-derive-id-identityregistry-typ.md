## Verification evidence

- RED (pre-implementation): `.venv/bin/python -B -m pytest tests/tracer/test_identity.py -q` -> `1 failed in 0.11s`, subprocess exit 1 `ModuleNotFoundError: No module named 'dsc03.identity'`.
- RED for 2.2b/2.4 (kind + rule not yet implemented): same command -> `8 failed, 13 passed` (unsupported_profile; invalid_profile/invalid_shape).
- GREEN narrow: `.venv/bin/python -B -m pytest tests/tracer/test_identity.py -q` -> `22 passed in 0.08s`.
- Regression: `.venv/bin/python -B -m pytest tests/tracer/test_tracer_validate.py tests/tracer/test_profile_resolution.py -q` -> `12 passed in 0.04s`.
Commands run (recorded in this artifact above):
