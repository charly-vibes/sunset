---
tags: [pipeline-run:epic-orchestrator-2026-11-02-sunset-xzy-2-declared-frame-mapping, pipeline-step:ship]
---

SHIP sunset-xzy.2 (step-6 record): feature commit cb9487e (frames.py + 18 tests + rotated/cropped frame fixtures + tasks.md 3.2 ticked); tracker commit ec2b298 (beads sunset-xzy.2 closed, exported no-db tracked JSONL). Full verification command: command=just spec-check → exit 0 ALL GATES PASSED (477 tests + 18 subtests, frozen 0.2 PASS 11, strict 13/13) run fresh before commit; command=/usr/bin/python3 -m pytest tests/tracer/test_visual_frames.py -q → 18 passed exit 0. Tests pass verified. Nothing pushed — owner authorization required.
