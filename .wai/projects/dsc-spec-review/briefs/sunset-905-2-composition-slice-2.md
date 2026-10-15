# Brief: sunset-905.2 — Composition slice 2: views/space/context law fixtures

## Why

Delegated to a subagent because it is a self-contained red→green slice over
three already-grounded spec deltas (document-views, document-space,
document-context), with the substrate harness and assembly module from
sunset-7hs/905.1 committed and available as building blocks. The lead
session is orchestrating the sunset-9pf epic loop; inline execution would
chain past the ticket boundary (canon Invariant 1). This slice blocks
sunset-905.3 (real-carrier conformance slice).

## Ticket

- **ID**: sunset-905.2 (claimed, in_progress)
- **Epic**: sunset-9pf — implement the three grounded DSC proposal changes
  (substrate → composition → Lens)
- **Authority**: the three spec deltas, read in full first:
  `openspec/changes/define-document-composition-semantics/specs/document-views/spec.md`
  `openspec/changes/define-document-composition-semantics/specs/document-space/spec.md`
  `openspec/changes/define-document-composition-semantics/specs/document-context/spec.md`
  Each has a **Properties** table naming every fixture — implement at least
  one fixture per named property (16 named properties total across the
  three deltas; the ticket requires ≥9 new fixtures red→green — cover ALL
  named properties where implementable without a wire delta, and record a
  per-property satisfied/partial/missing line for any that are not).

## Desired outcome

Consumer-side law fixtures proving views/space/context behavior:
cycle rejection with a path witness, incomparable regions preserved,
projection loss reported, refinement supersession/conflict reported,
cross-frame spatial predicates returning typed unknown, EPUB stable
selectors across reflow, context inheritance vs direct observation,
conflicting claims retained, deterministic replay (same_pinned_input) —
all classified, deterministic, no exceptions, no subprocesses.

## Work requirements

1. **Implement the named fixtures** (from the deltas' Properties tables —
   the fixture list below is the ticket's minimum):
   - views: `view_overlap`, `cycle_refused` (refusal must include the cycle
     path witness), `partial_order_ok`, `projection` (excluded link reported
     in coverage), `refinement_conflict`, `links_not_containment`
   - space: `pdf_rotation`, `cross_page_unknown` (typed unknown, not null/
     exception), `epub_reflow`, `native_ocr_coexist`, `spatial_not_order`,
     `roundtrip_transform`, `no_spatial_reading_order`
   - context: `publication_date`, `quoted_author`, `context_dispute`,
     `same_pinned_input`, `uncertain_ocr`, `no_union_on_assembly`
2. **Module placement** — new consumer-side modules under
   `dsc03/substrate/` (e.g. `views.py`, `space.py`, `context.py` — or one
   `composition.py`; your call, justify). Reuse `dsc03/substrate/laws.py`
   (`typed_check`, classified results), `assembly.py`, and the synthetic
   instance patterns. Subprocesses are FORBIDDEN (synthetic fixtures only;
   sunset-7hs finding).
3. **Per-property status table** — extend
   `openspec/changes/define-document-composition-semantics/design-decisions-assembly.md`
   or a sibling `design-decisions-views-space-context.md`: one line per
   named property — satisfied (fixture + module), partial (what's missing),
   or missing (why; wire-delta need → record, do NOT submit).
4. **Tick tasks** — tick only the tasks in
   `openspec/changes/define-document-composition-semantics/tasks.md` that
   this slice fully completes, with attribution like slice 1 did.

## Hard constraints

- **Zero DSC core wire changes**: `git diff openspec/specs` and
  `git diff spec/document-model-specodelic-v3` must stay EMPTY.
- No real-carrier conformance claims; honest labels everywhere.
- Synthetic fixtures only; NO subprocess calls; no OCR runs.
- New files carry Purpose/Responsibilities/Rationale headers.
- Do not modify `restore-document-substrate/`, `add-document-structural-debugger/`,
  or existing tests in `tests/tracer/`.
- `.beads/` never staged.

## Out of scope

- Real-carrier conformance + two independent readers (sunset-905.3, HITL).
- Deployed specs, frozen bundle, `dsc03/conformance.py` labels.
- The Lens/debugger change (sunset-xx7).

## Red/green/refactor sequence

1. RED: create `tests/substrate/test_views_space_context.py` with the
   fixtures above (failing). Run `python3 -B -m pytest tests/substrate -q`
   → fails.
2. GREEN: implement the modules + status table until tests pass.
3. REFACTOR: separate commit for tidy only.

## Exact files

- `tests/substrate/test_views_space_context.py` (new)
- new modules under `dsc03/substrate/` (placement justified in report)
- `openspec/changes/define-document-composition-semantics/design-decisions-views-space-context.md` (new or extended)
- `openspec/changes/define-document-composition-semantics/tasks.md` (tick only completed tasks)
- Do NOT touch: `openspec/specs/`, `spec/document-model-specodelic-v3/`, other change dirs.

## Exact test/review commands

```
python3 -B -m pytest tests -q        # full suite, exit 0, >=211 passed (202 baseline + 9)
just spec-check                      # ALL GATES PASSED
spk lint openspec/changes            # ok: true, issues: []
git diff openspec/specs spec/document-model-specodelic-v3   # empty
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests -q` → exit 0 with ≥211 passed
2. `just spec-check` → prints `ALL GATES PASSED`
3. `spk lint openspec/changes` → `"issues":[]`
4. `git diff openspec/specs spec/document-model-specodelic-v3` → empty output
5. `test -f tests/substrate/test_views_space_context.py` → exit 0
6. `git log --oneline -4` shows atomic red/green/refactor commits
7. `bd show sunset-905.2` still shows this ticket in_progress (lead closes it)

## Follow-up threshold

If a named property cannot be implemented without a wire delta or a
subprocess, record it partial/missing with the reason and move on — do not
expand scope. Commit what passes.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read (modules, tests, status
table, wai gate records) and include fresh test-run output (actual command
+ result pasted) before recording CONFIRM; otherwise REVIEW_REQUIRED.

## Spawn model

- Model: current session's default model.
- Context ceiling: ≤ 40% of the actual model window at spawn time.
- Wall-clock budget for the spawn: `timeout 60m`.
