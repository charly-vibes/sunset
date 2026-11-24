---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:quality-ledger]
---

GATE REPAIR: full-suite run under .venv (3.15) surfaced stale base_commit pin in fixtures/visual/verdicts-agent-sample.json (a52bf22, pre-wave-1 HEAD) tripping the by-design cross-commit refusal at test_visual_review_ingest positive path; fixed by re-pinning a tmp copy to live HEAD inside _ingest() - fixture left untouched. Also: .env pins SUNSET_PYTHON=/usr/bin/python3 whose user-site hypothesis crashes (PosixPath.endswith in scrutineer) - environmental, gate re-run with invocation-level venv override, .env (user config) untouched.
