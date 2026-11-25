---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-14b-agent-tool-surface, pipeline-step:green]
---

GREEN: command=pytest tests/tracer/test_tool_surface_*.py -q -> 65 passed. Smallest change: new sunset/ package (tool_surface core + cli adapter) consuming landed dsc03/digitization read-only; no landed module edited. Cascade pre-pass in _restrict because landed views.project does not cascade selectors/evidence (validator dangling_reference) — counted in envelope data.dropped_refs.
