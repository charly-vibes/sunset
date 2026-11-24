---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:fix-review]
---

RO5U REVIEW: wave-2/3 union (Ro5Review, repros executed). Critical: snap.py px/pt unit mix in top/bottom deltas (wrong at dpi!=72); run_ladder overwrites human rejected->verified; review_queue accept/reject collide on claim id; generative-claim accept raises unhandled Refusal in verdict ingestion. Medium: tier-1 sibling found[0] order-dependence; unparseable span mislabeled unregistered; edit bypasses normalization registry; region verdict maps only items[0]. Low: tautology assertions x2; render_cache double-read digest race. Fix round: three disjoint fixers dispatched.


Verified: commands run — `uv run pytest tests/tracer/test_review_queue.py -q` → reviewer repro run 8 passed; post-fix union 104 passed across seven suites (orchestrator re-run 2026-11-24).
