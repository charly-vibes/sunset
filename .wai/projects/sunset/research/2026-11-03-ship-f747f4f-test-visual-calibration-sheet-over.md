---
tags: [pipeline-run:epic-orchestrator-2026-11-03-sunset-xzy-6-calibration-sheet, pipeline-step:ship]
---

SHIP: f747f4f test(visual): calibration sheet over varied pages, six D6 record fields (sunset-xzy.6) + 0a00c35 docs(beads): close sunset-xzy.6. tasks.md 5.2 ticked. Ticket CLOSED, beads exported (.beads/issues.jsonl, git add -f). NOT pushed — awaiting explicit owner authorization per conservative profile.

## Verification evidence (commands run, fresh at ship)

$ PATH=/usr/bin:$PATH /usr/bin/python3 -m pytest tests/tracer/test_visual_calibration.py -q
.......                                                                  [100%]
7 passed in 6.44s

$ PATH=/usr/bin:$PATH /usr/bin/python3 -m pytest tests -q
526 passed, 1 warning, 18 subtests passed in 223.57s (0:03:43)

$ PATH=/usr/bin:$PATH just spec-check
Totals: 13 passed, 0 failed (13 items)
ALL GATES PASSED

All three commands executed fresh by the lead after the ship commit; frozen 0.2 validator PASS 11 inside spec-check. Working tree clean apart from by-design noise.
