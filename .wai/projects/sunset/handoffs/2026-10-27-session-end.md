---
date: 2026-10-27
project: sunset
phase: research
---

# Session Handoff

## What Was Done

Owner explicitly approved digitization proposal; sunset-rmx.1 closed with wording/digests. Implemented and closed sunset-rmx.2: recorded first-page run, valid DSC/source-linked searchable output, human/JSON inspection and explicit unsupported resume/replay. OpenSpec 1.1 checked. Changes are uncommitted.

## Key Decisions

Use recorded observations only until budget and stage configuration approval. Reuse existing DSC validation/index/locator/profile machinery. Keep raw/layout text apart from region-level normalized search mappings. Real OCR remains sunset-rmx.15.

## Gotchas & Surprises

wai close --project sunset refused because the older Lens epic-orchestrator pipeline remains at step 1/7. Preserved that run unchanged; direct handoff generation attempted to link this unrelated handoff into it, and that link-only mutation was restored. Do not force-abandon it without deciding its disposition.

## What Took Longer Than Expected

Initial 12 tests RED due absent package, then GREEN after satisfying DSC required logical view. Malformed-PDF regression RED then GREEN. Final focused 15/15 and full just spec-check ALL GATES PASSED: 320 tests +18 subtests, frozen PASS11, both strict OpenSpec validators11/11 and lint. Restored generated demo timing/memory churn.

## Open Questions

Pilot engine, numeric limits/thresholds and reviewed references remain stage-gated (.10/.16). No real OCR quality or economy measured; no remote inference, upload, commit or push performed.

## Next Steps

Resume sunset-rmx.3 (verified operation cache and selective reuse) using TDD; reanchor shared pipeline ownership before claiming. Full quality ledger: ../research/2026-10-27-digitization-first-page.org. Docs: docs/src/digitization.org. Manual image-only example: /tmp/sunset-rmx-2-example-th8iuqpd (temporary).

## Context

### git_status

```
 M openspec/changes/add-iterative-document-digitization/tasks.md
?? .wai/projects/sunset/research/2026-10-27-digitization-first-page.org
?? digitization/
?? docs/src/digitization.org
?? tests/tracer/test_digitization_first_page.py
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
├── ○ sunset-rmx.3 P1 Reuse verified region results while retaining fresh attempts
├── ○ sunset-rmx.4 P1 Inspect poems and competing structural readings without layout loss
├── ○ sunset-rmx.5 P1 Refine mixed columns without reprocessing unaffected regions
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
Total: 21 issues (21 open, 0 in progress)

Status: ○ open  ◐ in_progress  ● blocked  ✓ closed  ❄ deferred
Priority: P0–P4 (label only; not a status icon)
```


## Cache continuation completed (2026-10-28)

Closed sunset-rmx.3 and checked OpenSpec1.2. Public --cache/--fresh/--select now
provide verified region reuse and immutable per-run output selection. A changed
prompt or crop reuses unrelated regions; fresh outputs coexist without replacing
the first cache default. Corrupt request/attempt/output evidence refuses reuse.
Recorded-only; no actual inference or new remote authorization.

Verified: 35 focused tests, manual public CLI sequence, full just spec-check
ALL GATES PASSED (340 tests +18 subtests, OpenSpec11/11 twice, spk lint, frozen
PASS11). Restored generated benchmark timing/memory churn. No commits/push.
Ledger: ../research/2026-10-28-digitization-cache.org.
Next ready slice: sunset-rmx.4 (attributed structure/poetic layout). Reanchor shared
files against uncommitted .2/.3 code before claiming. The older Lens pipeline
remains unmodified; wai close still needs its disposition.

## Next-session entry: attributed structure (.4)

Owner requested continuation. Ticket sunset-rmx.4 reviewed, not claimed; no .4
implementation/tests written. Reanchor against current uncommitted .2/.3 files,
check conflicts, claim .4, then write failing poem line/stanza/indentation and
search-token source mapping fixtures; cover attributed OCR/model/manual readings,
competing caption/continuation alternatives, invalid model schema and out-of-frame
proposal refusal preserving the last valid result. Keep frozen core and research
bundle untouched. AGENTS.md context-limit stop; resume after fresh context.

## Attributed structure completed (2026-10-28)

Closed sunset-rmx.4; OpenSpec1.3 checked. Added structure.py, structure tests,
pipeline manifest-bound structure sidecar, inspection and documentation. Exact
poem text/line geometry/stanzas/indentation and token derivations retained; OCR,
model and manual observations remain separate. Caption/continuation candidates
stay unresolved. Malformed schema/frames/targets/envelopes retain valid output
with diagnostics. Structure-only edits reuse OCR cache; no inference calls.

Focused18, literal documented JSON public run/inspect smoke, full just spec-check
ALL GATES PASSED358 tests +18 subtests, OpenSpec11/11 twice, lint, frozen PASS11.
Restored generated measurement timing/memory churn. All .2/.3/.4 code/tests/docs
and ledgers remain uncommitted; no push or sync. Ledger:
../research/2026-10-28-digitization-structure.org.
Next ready slice: sunset-rmx.5 (region refinement). Reanchor shared files and
claim before RED fixtures. Preserve old Lens pipeline; do not abandon it silently.

## Immutable recorded refinement completed (2026-10-28)

Closed sunset-rmx.5; OpenSpec2.1 checked. Added refinement.py and refinement
tests, pipeline dispatcher/single-state integration, inspection and docs.
Versioned rules drive split/merge/expand/rerecognize/restructure. Rules are
considered once here; .6 owns full state equality/cycle stops. Each valid state
is retained as an independently inspectable revisions/state-N run. Root manifest
binds every snapshot and original configuration. Transforms and mappings retain
parent/child IDs; geometric equality does not merge identities.

Checks consume selected cached responses. Ordering uses priority/page/canonical
semantic region labels/rule ID/action digest; exact equal-attribute permutations
may be expensive at scale. Invalid candidates retain the previous valid state.
Changed regions invalidate structure transitively, including neighboring links;
accepted replacements clear their recheck requirement, unresolved ones stay
visible. Unrelated OCR retains verified keys/output/selected attempts.

Focused19 and literal documented JSON/public run/inspect smoke pass. Full gate
ALL GATES PASSED377 tests +18 subtests, strict OpenSpec11/11 twice, lint, frozen
PASS11. Restored demo timing/memory churn. Ledger:
../research/2026-10-28-digitization-refinement.org.
All implementation remains uncommitted, no push/sync. wai close refused due the
older Lens epic-orchestrator at1/7; no force-abandon.
Next ready slice: sunset-rmx.6. Reanchor .6 against all uncommitted .2-.5 code,
check conflicts and claim before RED semantic equality/stable/repeated-state tests.
Preserve existing accepted partial human results and stage approval boundaries.

## Rule-of-5 implementation review supersedes .5 acceptance (2026-10-28)

Owner requested RO5U review and asked whether wai tdd-ro5u was used. Answer:
NO, prior .2-.5 implementation did empirical TDD/full gates outside the pipeline.
Actual wai built-in template is tdd-ro5 with ro5u-review step. Initialized it and
started tdd-ro5-2026-10-28-sunset-72d-digitization-review; orientation/plan newly
recorded, current RED3/9. No retrospective RED/GREEN/refactor/ship compliance.
Old Lens run preserved. wai close now refuses the new unfinished run; no force.

Review sunset-72d CLOSED; five stages, NEEDS_REVISION. Reopened sunset-rmx.5,
OpenSpec2.1 UNCHECKED; .6 blocked again. HIGH followups .17 fresh selection rollback
after unrelated action; .18 replacement layout prevalidated against unselected
recording before cached output resolves; .19 malformed structure envelope plus
replacement crashes, no output. MEDIUM .20 inspection returns manifest usage
inconsistent with intact hashed ledger. No production fixes.

Four local reproductions preserved in research/2026-10-28-digitization-review-repros.py.
Full report research/2026-10-28-digitization-ro5u-review.org. Existing72 tests pass
(14.42s), demonstrating missing combination coverage. TypeSafe single batch
returned verified choices but confidence0.57/0.67/0.27 below0.8: HIGH findings
REVIEW_REQUIRED, route ESCALATE_TO_HUMAN per skill. Medium UNVERIFIED; measured
FP rate undefined, convergence not established. No production edits/commit/push.
Next: claim sunset-rmx.17, write true failing regression tests and use actual
pipeline RED/GREEN gates for bounded repair; separate tickets for other fixes.

Pipeline applicability note: generated release-docs-fresh oracle requires Cargo.toml; template ship gate needs corpus adaptation before it is usable. Do not mistake initialized RED3/9 run for completed/configured end-to-end compliance.

## All implementation review repairs completed (2026-10-28)

Owner authorized fix all. Closed sunset-rmx.17/.18/.19/.20 and sunset-0y1,
then reclosed sunset-rmx.5 and restored OpenSpec2.1. No production findings
remain from sunset-72d; initial review/reproductions remain historical artifacts.

Canonical request-key inheritance preserves fresh/explicit/corrected attempts
across unrelated revisions, including numeric0 versus booleanFalse key changes.
Actual resolved candidate output is validated before state admission. Refused
candidates remain inspectable under candidates/candidate-N and hash-bound with
usage retained. Malformed prior envelopes explicitly refuse replacement without
losing the valid state. Inspection enforces bound ledger/manifest agreement.

Corpus ship oracle spec-corpus.sh now runs actual just spec-check; positive and
broken-fixture negative isolated tests pass. Generated Cargo-specific oracle
removed. Ship prompt respects conservative commit authority; explicit human
approval gate preserved. All source/test headers remain self-describing.

Real tdd-ro5 run tdd-ro5-2026-10-28-sunset-72d-digitization-review advanced from
RED3/9 through green/refactor-review/fix-review/quality ledger and is now at
ship-close9/9, pending explicit HUMAN APPROVAL. No approval or bypass recorded.
Initial GREEN command incorrectly continued after a test fixture path collision;
a correction artifact and fresh42 passing tests were recorded before review
advanced. Corrected fresh/select tests also fail when inheritance is removed in
an isolated copied module. All subsequent gate commands stopped on failure.

Full final oracle ALL GATES PASSED393 tests +18 subtests, both strict OpenSpec
validators11/11, lint, frozen PASS11; final typed-key refinement30 passes.
Generated benchmark timing/memory churn restored. Final five-pass resolution
review READY for these recorded repairs; no new HIGH/CRITICAL finding, no new
API or measured convergence claim. Initial TypeSafe low-confidence record retained.
Report/ledger: ../research/2026-10-28-digitization-review-fixes.org.
All implementation remains UNCOMMITTED; no push, sync or pilot inference.
Older Lens run remains at1/7 and preserved. Next: user can approve the concrete
ship checkpoint via wai pipeline approve with explicit run selector, without
implying commit/push authority. Then .6 is the next implementation slice.
