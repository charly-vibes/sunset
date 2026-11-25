---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-14b-agent-tool-surface, pipeline-step:plan]
---

sunset-14b tool surface: core sunset/tool_surface.py (envelope {status,reason,data,cursor?,provider_calls}, STATUSES=(ok,refused,error), stable REASONS, anchor-ids-only addressing, idempotent propose/decide via claim ids, untrusted data.text, deterministic cursors+bounds, gated export, pure reads) + sunset/cli.py phase-1 adapter; tests already RED in tests/tracer/test_tool_surface_{envelope,reads,idempotence,addressing,leakage,bounds,export,parity}.py + tool_surface_fixtures.py. Narrow test cmd: pytest tests/tracer/test_tool_surface_envelope.py -q. Full: pytest tests/tracer/test_tool_surface_*.py -q + the three just gate targets. Files: sunset/*, pyproject.toml, justfile (append), openspec change docs.
