---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:green]
---

GREEN evidence: test_refusal_absorption RED pre-fix (compose dropped the left refusal, returned raw operand 'part-id-review'); re-applied absorption branch; tests/substrate/test_assembly_laws.py now 14 passed (11 baseline + join_commutativity, join_idempotence, refusal_absorption).

Verification commands run (agent-executed):
- `uv run pytest tests/substrate/test_assembly_laws.py::TestIdentityProfileJoinLaws::test_refusal_absorption -q` on pre-fix compose → `1 failed` (AssertionError: raw part descriptor != {'status': 'refused', ...}, label 'left-part').
- `uv run pytest tests/substrate/test_assembly_laws.py -q` after re-applying the absorption branch → `14 passed in 0.02s`.
