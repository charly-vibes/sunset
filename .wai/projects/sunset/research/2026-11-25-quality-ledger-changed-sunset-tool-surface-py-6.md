---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-14b-agent-tool-surface, pipeline-step:quality-ledger]
---

QUALITY LEDGER: Changed: sunset/tool_surface.py (6 guard/clarify edits: crop fallback guard, extract completeness re-extract, claims shape validation, evidence_class type check, _anchor signature), sunset/cli.py (dead store removed), tests/tracer/test_tool_surface_reads.py (+3 tests), tests/tracer/test_tool_surface_export.py (+1 test). Verified: commands recorded in RO5U-FIXES: narrow suites 24 passed, remaining suites 45 passed, just agent-surface-gate 15 passed; full gate to run at ship-close oracle. Review: RO5U pass 0 critical 0 high; 2 MEDIUM + 4 LOW all fixed this round; no open findings. Risks: none known — boundary hardening only, no contract changes (envelope/vocabulary unchanged; parity suite green). Next: ship-close — approve ship evidence, then final oracle run.
