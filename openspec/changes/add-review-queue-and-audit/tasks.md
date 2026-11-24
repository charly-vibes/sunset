## 1. Dedupe

- [ ] 1.1 Reconcile with the `sunset-rmx` HITL work and `sunset-12h` (review-verdicts.json ingest): map existing verdict artifacts to human claims, or extend them; record the mapping in design.md before implementation

## 2. Queue

- [ ] 2.1 RED: identical inputs and policy yield identical queues in two processes
- [ ] 2.2 Implement derived queue (unverified + conflicted, scope/type/id order)
- [ ] 2.3 Item content: crop reference, value, reason codes, alternatives with origins

## 3. Decisions

- [ ] 3.1 RED: accept/reject/edit create human claims; model claims never mutated
- [ ] 3.2 Wire the reader SPA to the queue (existing templates; no parallel review path)

## 4. Audit and gate

- [ ] 4.1 RED: seeded sampler deterministic; seed and rate recorded
- [ ] 4.2 Wilson upper bound with recorded confidence; zero errors still nonzero bound
- [ ] 4.3 RED: gate queues a type with no audit data; agent-executed audits never open the gate
- [ ] 4.4 Decide Open Question 1 (threshold and minimum N) with the owner

## 5. Metrics

- [ ] 5.1 Record auto-accept rate, audited false-accept upper bound, human seconds per item per claim type; evidence-class labeled
- [ ] 5.2 Report human-rejected count separately (false rejects are not measured by the audit)
