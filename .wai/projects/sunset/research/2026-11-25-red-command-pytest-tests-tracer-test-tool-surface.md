---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-14b-agent-tool-surface, pipeline-step:red]
---

RED: command=pytest tests/tracer/test_tool_surface_*.py -q; expected failure=ModuleNotFoundError: No module named 'sunset' (8 collection errors) — observed before any sunset/ production code existed; failure is the missing behavior (no package), not setup breakage.
