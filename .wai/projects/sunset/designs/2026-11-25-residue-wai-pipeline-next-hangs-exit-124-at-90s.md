---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:ship-close]
---

RESIDUE: wai pipeline next hangs (exit 124 at 90s, repro x3) advancing ship-close of tdd-ro5-2026-11-24-ro5-review-fixes despite gate artifacts present; run substance complete (diff inspected, beads closed, pushed a52bf22..2e5d833). Next session: diagnose wai ship-close advance (strace/log), then wai close normally - do NOT close --force (run is shipped, not abandoned).
