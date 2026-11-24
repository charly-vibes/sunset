# Change: Derived review queue and audit-gated autonomy

## Why

For autonomy to be believable, human validation must be nearly instant and only for what verifiers cannot settle, and the decision to skip review must be backed by a measured false-accept rate, not by trust in the verifiers.

Sunset has the ingredients — verified at HEAD: the reader SPA and reader-agreement tooling (`hitl/visual-review/`, `tests/tracer/test_reader_agreement_*`, `test_second_reader_agreement`), pinned page rendering (`digitization/render.py`), coverage vocabulary, and human-vs-oracle agreement work already tracked as `sunset-12h` (review-verdicts.json ingest) — but no derived work queue and no mechanism to measure how often auto-accepted claims are wrong.

## What Changes

- A **review queue** derived as a pure function of descriptor, claims and policy: claims with status unverified or conflicted, grouped by type, ordered deterministically.
- Each item carries a pinned page crop reference, value, reason codes and retained alternatives. Actions: accept, reject, edit (creating a human claim).
- A **deterministic audit sampler** draws a seeded sample of auto-accepted claims for human check.
- An **autonomy gate**: a claim type is exported without review only if its audited false-accept upper bound is within a declared threshold over at least N audited claims; otherwise it is queued. No audit data means queued.
- Agent-executed audits are labeled and do not count as human audit.
- Existing HITL artifacts (`review-verdicts.json` and the reader sheets) feed the human-claim record rather than starting a parallel review path.

## Impact

- Affected specs: new capability `document-review` (all requirements ADDED).
- Depends on `add-claim-verification-ladder` and `add-scale-complete-regions` (crops, word anchors).
- Affected code: new `digitization/review.py`, queue and audit artifacts, reuse of `digitization/render.py` and the reader SPA assets.
- Dedupe task 1.1 reconciles with the in-flight `sunset-rmx` HITL work and `sunset-12h` before implementation.
- Success metrics are recorded per claim type: auto-accept rate, audited false-accept upper bound, human seconds per item. They are measurements, not normative targets, and are reported with their evidence class.
