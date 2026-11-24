---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:green]
---

GREEN: typed BudgetExhausted(ValueError) on attempt-limit-exceeded; run_local catches it pre-I/O and emits budget-exhausted stopped outcome preserving stage ledger (exit 2, no traceback, no manifest).

## Verification evidence

Agent-executed, 2026-11-24:
- RED first: `uv run pytest tests/tracer/test_digitization_local_route.py::test_budget_exhaustion_stops_without_manifest_and_preserves_ledger tests/tracer/test_digitization_budget.py::test_budget_ledger_types_attempt_limit_refusal -x -q` -> failed before implementation (ImportError: cannot import name 'BudgetExhausted').
- GREEN: `uv run pytest tests/tracer/test_digitization_local_route.py tests/tracer/test_digitization_budget.py -q` -> 21 passed, 0 failed.
- CLI: `python -m digitization run` (local provider, max_provider_attempts=1, 2 detected regions) -> exit 2; stdout JSON `{"status":"stopped-with-unresolved-work","reason":"budget-exhausted","attempts_dispatched":1,...}`; stderr empty (no raw traceback); run/ retained with budget-state.json; no manifest.json.
Commands run (recorded in this artifact above):
- `uv run pytest tests/tracer/test_digitization_local_route.py tests/tracer/test_digitization_budget.py -x -q` (RED) -> `1 failed` (ImportError: BudgetExhausted).
- `uv run pytest tests/tracer/test_digitization_local_route.py tests/tracer/test_digitization_budget.py -q` (GREEN) -> `21 passed, 1 warning in 1.40s`.
