# Brief: sunset-msj.1 — Explanation page "What is DSC and why"

## Why

Delegated to a subagent because it is a self-contained single-file writing
task with well-bounded source material (bundle README, archived proposal,
status.md scope ruling). The lead session is orchestrating the sunset-msj
epic loop; inline execution would chain past the ticket boundary (canon
Invariant 1). The page is the orientation root of the whole docs suite —
later tickets (tutorial, how-tos, reference, for-agents) link to it.

## Ticket

- **ID**: sunset-msj.1 (claimed, in_progress)
- **Epic**: sunset-msj — consumer documentation suite (human + AI)
- **Diátaxis quadrant**: EXPLANATION only

## Desired outcome

`docs/src/what-is-dsc.md` — a newcomer-oriented explanation of the DSC
(Document Structural Core) model and the sunset corpus. After reading it,
an implementer who has never seen sunset can answer: what problem does DSC
solve, what is a descriptor, which version applies to me, what does sunset
provide, and where do I go next (the tutorial).

## Content requirements

1. **The problem DSC solves** — multiple structural views, incompatible
   reading orders, source-addressable text/layout, silent normalization,
   dishonest extraction coverage claims. (Source:
   `spec/document-model-specodelic-v3/README.md` TL;DR +
   `RESEARCH-DECISIONS.md`, archived proposal
   `openspec/changes/archive/2026-10-14-add-dsc-03/proposal.md`.)
2. **What a DSC descriptor is** — conceptual, non-normative: structural
   views, selectors, evidence/provenance, coverage inventories.
3. **0.2 vs 0.3 orientation** — 0.2 is the executable baseline (frozen
   validator, PASS 11); 0.3 is implemented machinery (`dsc03/`, tests in
   `tests/tracer/`) deployed to the openspec specs from the archived
   change. Newcomers target 0.3.
4. **What sunset is** — a DSC *specification corpus* (specs + frozen 0.2
   executable truth + conformance equipment), **not a tool**; no CLI by
   design. Link the scope ruling section in `docs/src/status.md` and note
   the recorded agent-executed review deviations (human pass supersedes).
5. **Where next** — link forward to `docs/src/first-descriptor.md`
   (tutorial, being built in sunset-msj.2) and `docs/src/reference.md`.
   If the linked file does not exist yet, link anyway with "(in
   progress)" wording so the forward path stays stable.

## Hard constraints

- Single quadrant: NO how-to steps, NO normative SHALL statements, no
  copy of spec text (link to `openspec/specs/` instead).
- EPPO: the page establishes its own context; no "as mentioned above"
  dependencies on files the reader hasn't read.
- PII/provenance rules respected; do not quote PII-screened fixture
  contents.
- Do not modify anything outside `docs/src/what-is-dsc.md` and the
  forward-link anchor in `docs/src/status.md` (one line, only if needed
  to link the new page).
- Anti-slop: concrete claims, no vague marketing prose.

## Out of scope

- Tutorial, how-tos, reference index, llms.txt/for-agents (other tickets).
- Any change to `openspec/`, `dsc03/`, tests, or the preserved bundle.
- mdBook/website tooling (deliberately none — scope ruling).

## Red/green/refactor sequence

This is a docs ticket; the "red" is the missing acceptance check:
1. RED: create `tests/docs/test_docs_links.py` — asserts every markdown
   link target in `docs/src/what-is-dsc.md` resolves to an existing repo
   file (and that the file exists). Run it; it fails (page missing).
2. GREEN: write `docs/src/what-is-dsc.md`; test passes.
3. REFACTOR: separate commit for any tidy (none expected).

## Exact files

- `docs/src/what-is-dsc.md` (new)
- `tests/docs/test_docs_links.py` (new)
- `docs/src/status.md` (at most: one link line, optional)

## Exact test/review commands

```
python3 -B -m pytest tests/docs -q          # new link test passes
just spec-check                             # ALL GATES PASSED, 146+ tests
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests/docs -q` → exit 0
2. `just spec-check` → prints `ALL GATES PASSED`
3. `test -f docs/src/what-is-dsc.md` → exit 0
4. `git log --oneline -2` shows the atomic commit(s) for this ticket

## Follow-up threshold

If content requires touching openspec specs, dsc03 code, or turns out to
need a second page — STOP, commit what is done, and record the finding in
the report instead of expanding scope.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read (at minimum: the new
page, the link test, `wai search research` gate records) and include fresh
test-run output (actual command + result pasted) before recording CONFIRM;
otherwise REVIEW_REQUIRED.

## Spawn model

- Model: current session's default model.
- Context ceiling: ≤ 40% of the actual model window, computed at spawn
  time from the brief + repo orientation only.
- Wall-clock budget for the spawn: `timeout 45m`.
