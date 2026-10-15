# Brief: sunset-msj.5 — AI-facing layer: llms.txt + agent integration brief

## Why

Delegated: well-scoped authoring of two machine-first artifacts consuming
four finished pages. Lead orchestrates the loop. This layer is the entry
point for agentic consumers (coding agents implementing DSC, agents running
the conformance suite) — docs-as-runtime-input.

## Ticket

- **ID**: sunset-msj.5 (claimed, in_progress)
- **Epic**: sunset-msj — consumer documentation suite
- **Audience**: AI/agent consumers (second audience); humans may read it too

## Desired outcome

Two artifacts:

1. **`llms.txt` at repo root.** Format: H1 title line, blockquote one-line
   value proposition, then `## ` sections grouping links with one-line
   summaries. Include: what-is-dsc (explanation), first-descriptor
   (tutorial), integrate (how-tos), reference (reference), the 7 normative
   specs (link each spec.md), status.md (corpus status + scope ruling +
   deviations), and baseline-limitations.md. Every link must resolve (the
   link-integrity test only covers docs/src/*.md — ALSO extend it, see
   gate below). Keep summaries current with deployed 0.3 state (no
   "proposal" language).
2. **`docs/src/for-agents.md` — agent integration brief.** Precise,
   ambiguity-free, machine-consumable prose:
   - Integration contract: input (descriptor JSON shape — link
     document-core spec + tracer fixture), validation API surface
     (`dsc03.validator.load/validate/run` — verify exact names in source),
     output (typed outcome lists, the four reports via
     `dsc03.report.assess`), error conditions (typed outcomes, never
     exceptions — verify).
   - Conformance boundary: what an implementation may and may never claim
     (classify keys, scoped labels, scripted-machinery limit, recorded
     deviations — human pass supersedes; link status.md).
   - Runnable examples: reuse the tutorial's tagged descriptor block as
     the canonical example (link, don't duplicate — or embed identically
     ONLY if the gate test makes single-source explicit); include the
     exact validation command transcript verified from a fresh clone.
   - RAG-ready structure: one topic per section, unique semantic headings,
     explicit version scope ("applies to DSC 0.3 deployed specs,
     2026-10-15").

## Scope-ruling consistency (mandatory)

`llms.txt` must carry a one-line note distinguishing it from the ddl
registry checklist ruled out of scope in sunset-408 (see status.md): this
file serves documentation discovery, not tool registration.

## Hard constraints

- No changes to `dsc03/`, `openspec/`, tests/tracer, fixtures, or the four
  finished pages (read-only consumption). Exception: the link-integrity
  test may be EXTENDED (new test function for llms.txt resolution) —
  never weaken existing assertions.
- No duplication drift: summaries must not contradict the pages they
  summarize.

## Gate (TDD red first)

Extend `tests/docs/test_docs_links.py` with a new test:
`test_llms_txt_links_resolve` — parse llms.txt markdown-style links, assert
every relative target resolves to an existing repo file. RED: fails (no
llms.txt). Commit RED. Then GREEN with both artifacts. Commit GREEN.

## Exact files

- `llms.txt` (new, repo root)
- `docs/src/for-agents.md` (new)
- `tests/docs/test_docs_links.py` (new test function only)

## Exact test/review commands

```
python3 -B -m pytest tests/docs -q      # RED first, then all pass
just spec-check                         # ALL GATES PASSED
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests/docs -q` → exit 0
2. `just spec-check` → prints `ALL GATES PASSED`
3. `test -f llms.txt && test -f docs/src/for-agents.md` → exit 0
4. `git log --oneline -2` shows RED then GREEN commits

## Follow-up threshold

If an API name/behavior in the contract section contradicts source — STOP,
record the finding (source wins; docs change in a follow-up).

## Verifier evidence contract (wai-px4g)

Cite artifacts read + fresh test-run output before CONFIRM; otherwise
REVIEW_REQUIRED.

## Spawn model

- Model: current session default.
- Context ceiling: ≤ 40% at spawn.
- Wall-clock budget: `timeout 45m`.
