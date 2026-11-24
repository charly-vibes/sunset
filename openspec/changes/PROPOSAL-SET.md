# Adoption of the reviewed proposal set (2026-11-24)

Six changes adopted from the corpus proposal set (chat `e505b9ec`, reviewed via
Rule-of-5 against HEAD), plus two additive extensions to in-flight changes.
Grounded claims were re-verified against HEAD on 2026-11-24; stale premises were
rewritten (notably: `word-map.json` no longer exists — word data is absent from
native output entirely).

## Dependency order

```
add-anchor-derived-identity ──► add-scale-complete-regions ──┬─► add-claim-verification-ladder ──► add-review-queue-and-audit ──► add-agent-tool-surface
        │                                                    │
        └──► define-document-composition-semantics           └──► improve-geometry-render-binding (§ frame record;
             (join-law + harness tasks, extended in place)        crop-box/extent fixes start immediately)
```

| Change | Capability | Status |
|---|---|---|
| improve-geometry-render-binding | document-visual-oracles (ADDED reqs) | start now; fixes the verified crop-box false-disagreement bug |
| add-anchor-derived-identity | document-identity | start now; owner Q: additive in 0.3 vs 0.4 |
| add-scale-complete-regions | document-zoom | after identity; reconciled with document-views scoped projection |
| add-claim-verification-ladder | document-claims, document-verification | after identity+zoom; reconciled with document-context |
| add-review-queue-and-audit | document-review | after claims+zoom; dedupe with sunset-rmx HITL / sunset-12h |
| add-agent-tool-surface | document-agent-interface | last; AGPL gate blocks packaging |
| define-document-composition-semantics (extended) | document-assembly +3 reqs, tasks +2 | join laws (commutativity/idempotence/absorption) + law catalogue absorbed here |
| add-iterative-document-digitization (extended) | document-digitization +5 reqs, tasks §4 | model-call determinism absorbed here (no separate capability) |

## Review findings carried into the artifacts

- CORR-001: proposal 2 motivation rewritten from a fresh HEAD native run.
- CORR-004: replay-variation attribution corrected (rmx.11 measurement; Fresh inference variability requirement).
- CORR-005: collisions resolved by merging into in-flight changes instead of ADDED-only duplicates.
- EDGE-002/EDGE-005: deferred geometry statistics carry the design tensions in improve-geometry-render-binding Non-goals.
- EDGE-001: normalization registry added to the claim ladder.

## Owner gates (all block approval of the named change)

- [ ] G1 — Identity profile additive in DSC 0.3, or 0.4? Blocks add-anchor-derived-identity tasks 2.2+.
- [ ] G2 — Claims as annotations-with-profile vs new `claims` section? Blocks add-claim-verification-ladder task 2.3.
- [ ] G3 — Autonomy gate defaults: false-accept threshold and minimum audited N. Blocks add-review-queue-and-audit task 4.4.
- [ ] G4 — PyMuPDF AGPL vs commercial. Blocks add-agent-tool-surface packaging only (task 5.2); repo-internal use unaffected.
- [ ] G5 — Retention policy for recorded model I/O containing document text. Blocks add-iterative-document-digitization §4 rollout.
- [ ] G6 — Block scale in the ladder. Blocks add-scale-complete-regions task 2.3.

## Necessity cuts (over-engineering audit, 2026-11-24)

Deferred features with re-entry triggers — not deleted needs:

- **Dense region table** (was a document-zoom requirement): words ship as expanded records first. Trigger: measured descriptor size makes gate runs or review crops slow.
- **zoom_out aggregation** (was a document-zoom requirement): page-level meet already exists (`classify_outcome`); claim-status meet lives in document-verification. Trigger: a consumer needs retention-status meet below page level.
- **Tier 2 independent agreement** (was a document-verification requirement): `agreed` stays defined in the status order as reserved; autonomy v1 runs on tier-1 rules + human audit. Trigger: a claim type needs autonomy but has no applicable domain rule.
- **MCP adapter** (agent surface): CLI-first; the parity requirement now covers every exposed adapter. Trigger: a model harness needs MCP.
