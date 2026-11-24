---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:fix-review]
---

RO5U-FIXES GREEN: claims.py — claim.value.unparseable for registered-type parse failure; decision in claim_id/digest_input; verify/registry.py — rejected passthrough in run_ladder, siblings-conflicted typed unknown; review_queue.py — decision in decide specs, generative accept/reject, edit normalization; digitization/review.py — multi-claim region typed skip + bundle report. RED confirmed 13 failing first.


Verified: commands run — `uv run pytest tests/tracer/test_claims_ladder.py -q` → 17 passed (orchestrator re-run 2026-11-24).
