---
tags: [pipeline-run:tdd-ro5-2026-11-25-sunset-14b-agent-tool-surface, pipeline-step:ship-close]
---

SHIP: sunset-14b tool surface shipped: original work committed earlier as c463330 (envelope, 6 read tools, idempotent propose/decide, gated export, CLI parity, packaging per G4 AGPL ruling); this round adds the ro5u review verdict pass + 6 boundary-hardening fixes (4 tests-first) on the parked run. bd has no open 14b ticket (closed previously); nothing committed yet for this round - orchestrator commits under standing instruction. Verified: command=SUNSET_PYTHON=.venv/bin/python just agent-surface-gate -> 15 passed (2026-11-25); full gate runs as the ship-close oracle next.
