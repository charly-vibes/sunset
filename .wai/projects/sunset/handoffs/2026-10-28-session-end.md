---
date: 2026-10-28
project: sunset
phase: research
---

# Session Handoff

## What Was Done

Committed recorded digitization .2-.5 and all review repairs as 0e50cf4; committed the corpus-specific TDD/RO5U workflow as 43485e1. Four code findings and oracle adaptation are fixed; .17-.20, sunset-0y1 and .5 are closed, OpenSpec2.1 checked. The user explicitly authorized commit and push. The TDD/RO5U run completed after its approved ship gate; wai close succeeded. The older Lens run is preserved.

## Key Decisions

Use canonical operation keys to retain explicit/fresh attempt selections across unchanged requests. Validate structural replacements against actual selected recognition before admitting a revision. Preserve refused candidate artifacts and usage; explicitly refuse malformed prior envelopes. Inspection requires canonical agreement with the hash-bound ledger. Keep all pipeline metadata outside the unchanged DSC wire contract.

## Gotchas & Surprises

Earlier .2-.5 work was outside wai TDD/RO5U; the omission and original review remain preserved. An incorrect GREEN artifact from a test-output path collision has an explicit correction and fresh verification. The built-in workflow is named tdd-ro5; its Cargo oracle was replaced with real spec-corpus checks. Original TypeSafe confidence was below0.8; no measured convergence or independent closure verification is claimed. SSH uses GIT_SSH_COMMAND="ssh -F /var/home/sasha/.ssh/config".

## What Took Longer Than Expected

The final request-type edge case required canonical-key rather than Python dict equality (0 and False must differ). Final full just spec-check passed393 tests +18 subtests, both OpenSpec validators11/11, lint and frozen PASS11. The approved pipeline reran the executable corpus oracle successfully before completion. Generated benchmark/recall usage churn was restored. Five-pass repair review: no remaining findings in the authorized scope.

## Open Questions

Real-engine settings, numeric budgets/thresholds and reviewed pilot references remain gated by .10/.16. No paid inference, remote source uploads, real digitization quality/economy claims or broader conformance were authorized by shipment. Canonical-label permutation performance remains a documented limitation. Old Lens epic-orchestrator run is still preserved at1/7; do not abandon it silently.

## Next Steps

Resume sunset-rmx.6 (semantic equality and cycle/fixed-point stopping), currently open and unclaimed. Run wai status and bd show, check conflicts, claim, then use a new tdd-ro5 run with failing semantic-state regressions first. No implementation of .6 was started. Full review/repair ledger: ../research/2026-10-28-digitization-review-fixes.org. Shipment includes the following session-context commit; verify origin/main if delivery state is needed.

## Context

### git_status

```
 M .wai/resources/pipelines/.last-run
 M .whisper/branches/main/notes.md
?? .wai/pipeline-runs/tdd-ro5-2026-10-28-sunset-72d-digitization-review.yml
?? .wai/projects/sunset/designs/2026-10-28-green-sunset-rmx-17-command-python3-b-m-pytest.md
?? .wai/projects/sunset/designs/2026-10-28-refactor-no-tidy-changes-required-for-sunset-rmx.md
?? .wai/projects/sunset/handoffs/
?? .wai/projects/sunset/plans/
?? .wai/projects/sunset/research/2026-10-27-digitization-first-page.org
?? .wai/projects/sunset/research/2026-10-28-correction-to-prior-green-refactor-evidence-earli.md
?? .wai/projects/sunset/research/2026-10-28-digitization-cache.org
?? .wai/projects/sunset/research/2026-10-28-digitization-refinement.org
?? .wai/projects/sunset/research/2026-10-28-digitization-review-fixes.org
?? .wai/projects/sunset/research/2026-10-28-digitization-review-repros.py
?? .wai/projects/sunset/research/2026-10-28-digitization-ro5u-review.org
?? .wai/projects/sunset/research/2026-10-28-digitization-structure.org
?? .wai/projects/sunset/research/2026-10-28-orient-sunset-72d-reviews-the-existing-uncommitte.md
?? .wai/projects/sunset/research/2026-10-28-quality-ledger-changed-request-key-attempt-inher.md
?? .wai/projects/sunset/research/2026-10-28-red-sunset-rmx-17-command-python3-b-m-pytest-te.md
?? .wai/projects/sunset/research/2026-10-28-ro5u-fixes-complete-verified-command-npm-config.md
?? .wai/projects/sunset/research/2026-10-28-ro5u-fixes-progress-17-red3-green42-correcte.md
?? .wai/projects/sunset/research/2026-10-28-ship-evidence-all-authorized-review-repairs-and-p.md
?? .wai/projects/sunset/research/2026-10-28-ship-owner-explicitly-authorized-commit-and-push.md
?? .wai/projects/sunset/reviews/
```

### open_issues

```
○ sunset-36n P1 Compare two attributed readings beside their PDF source
○ sunset-5ay P1 Approve the source-linked PDF review milestone
○ sunset-5bu P1 Inspect a human-marked region on its PDF source
○ sunset-9pf P1 [epic] Implement the three grounded DSC proposal changes (substrate → composition → Lens)
└── ○ sunset-905 P1 Implement define-document-composition-semantics fixtures and law witnesses
○ sunset-j1c P1 Export and reopen a source-linked disagreement
○ sunset-rmx P1 [epic] Digitize Diario pages with bounded refinement and recorded replay
├── ○ sunset-rmx.6 P1 Stop oscillating refinements despite newly allocated revision IDs
├── ○ sunset-rmx.7 P1 Resume interrupted extraction without resetting or duplicating spend
├── ○ sunset-rmx.8 P1 Reconstruct selected extraction results offline with integrity checks
├── ○ sunset-rmx.9 P1 Compute reproducible pilot metrics and reject unsupported conclusions
├── ○ sunset-rmx.10 P1 Approve difficult-page references and bounded local configuration
├── ○ sunset-rmx.11 P1 Measure difficult-page quality and fresh-run variation against baseline
├── ○ sunset-rmx.12 P1 Measure six-page Diario extraction including continuation errors
├── ○ sunset-rmx.13 P1 Verify the complete digitization pilot without broadening conformance
├── ○ sunset-rmx.14 P1 Decide whether measured Diario results justify full-issue scaling
├── ○ sunset-rmx.15 P1 Exercise real local crop OCR through run and inspect
└── ○ sunset-rmx.16 P1 Approve six-page references and bounded stage configuration

--------------------------------------------------------------------------------
Total: 18 issues (18 open, 0 in progress)

Status: ○ open  ◐ in_progress  ● blocked  ✓ closed  ❄ deferred
Priority: P0–P4 (label only; not a status icon)

```
