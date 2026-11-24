## Context

`digitization/render.py` renders pinned page frames in-process (PyMuPDF, correlated lineage — labeled per `improve-geometry-render-binding`); the HITL tooling already records reader sheets and an agreement matrix (agent-run and human-run kept distinct). This change reuses both ideas: derive, don't hand-curate, and keep evidence classes separate.

## Goals / Non-Goals

Goals: queue as a function; decisions as evidence; audit that bounds false-accepts; autonomy gated on evidence.

Non-goals: UI polish; multi-reviewer adjudication workflows; model selection; replacing the existing reader SPA — the queue feeds it.

## Decisions

1. **Queue is derived.** Items are claims with status unverified or conflicted. Order: scope order, then claim type, then claim id. Same inputs, same queue.
2. **Item content.** Crop reference (render profile digest, page frame, box), canonical value, verifier reason codes, alternatives with origins.
3. **Actions.** Accept and reject record a human claim. Edit records a new human claim with adjusted value or anchors; the model claim is never mutated.
4. **Audit sample.** Seeded draw, per claim type, from auto-accepted claims at a declared rate with a minimum count per type. Seed and rate are recorded.
5. **Interval.** False-accept upper bound uses the Wilson score interval at a declared confidence; with zero errors it still reports a nonzero bound.
6. **Gate.** Type is autonomous only if upper bound is at most the declared threshold and audited count is at least N. Otherwise queued. Policy changes are themselves recorded configuration.
7. **Evidence class.** Each audit result is labeled `human` or `agent-executed`; only `human` counts toward the gate.
8. **False rejects are reported, not ignored.** Auditing only auto-accepted claims does not measure false rejects; rejected-by-human claims are reported as a separate count per type.

## Risks / Trade-offs

- Reviewer fatigue biases audits. Mitigation: sample size and per-item timing are recorded as non-semantic metadata for later analysis.
- Small N gives wide intervals and keeps types in review for long. That is the honest outcome; threshold and N are configuration.
- Duplicating the HITL review path would fork the human-evidence record. Mitigation: task 1.1 dedupe — the queue derives items and the existing SPA renders them; `review-verdicts.json` maps to human claims.

## Open Questions

1. Default threshold and minimum N per claim type; needs owner ruling.
   **Ruled (owner, 2026-11-24, via sunset-gpd gate G3): a type opens the autonomy gate when its Wilson false-accept upper bound at 95% confidence is ≤ 1% and the audited sample is ≥ 30 per claim type (human-labeled audits only, Decision 7).** Task 4.4 unblocked.
2. Should audits sample across documents or within each document?
