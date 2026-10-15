# Brief: sunset-905.1 — Composition slice 1: canonical equality + ID namespace + assembly law fixtures

## Why

Delegated to a subagent because it is a self-contained red→green slice with
clear authority documents (the `document-assembly` spec delta and the
just-completed substrate harness from sunset-7hs). The lead session is
orchestrating the sunset-9pf epic loop; inline execution would chain past
the ticket boundary (canon Invariant 1). This slice blocks sunset-905.2
(views/space/context) and sunset-905.3.

## Ticket

- **ID**: sunset-905.1 (claimed, in_progress)
- **Epic**: sunset-9pf — implement the three grounded DSC proposal changes
  (substrate → composition → Lens)
- **Authority**: `openspec/changes/define-document-composition-semantics/specs/document-assembly/spec.md` (read it in full first) + `openspec/changes/restore-document-substrate/mapping.md` (what substrate already provides)

## Desired outcome

(a) A DESIGN decision recorded in the change dir for **stable canonical
equality + explicit ID namespace collision behavior**; (b) assembly law
fixtures implemented red→green: at least 6 new law fixtures covering
left/right identity, associativity on grouping-independent triples,
incompatible shared-ID refusal, shared-ID merge (same_id_identical_claims),
and non-invented order (no_invented_order) — each mapping to a named
property in the spec delta's Properties table.

## Work requirements

1. **DESIGN decision artifact** — write
   `openspec/changes/define-document-composition-semantics/design-decisions-assembly.md`
   (or extend the existing `design.md` with a dated section): decide (i)
   canonical equality — what counts as canonically equivalent for assembly
   results (reference the substrate canonical serialization from
   `dsc03/substrate/` and the deployed `dsc03/canonical.py`); (ii) ID
   namespace collision behavior — collision = refuse with classified
   witness vs merge under identical-claims precondition; justify against
   the spec delta's `assembly_compatible` and `boundaries_preserved`
   invariants. Keep it a decision record, not new normative scope.
2. **Assembly law fixtures** — implement the assembly composition rules
   described by the delta as a consumer-side module (e.g.
   `dsc03/substrate/assembly.py` — reuse the substrate harness; justify
   placement), with tests under `tests/substrate/test_assembly_laws.py`:
   - `left_right_identity`: canonical(compose(A,empty)) == canonical(A) == canonical(compose(empty,A))
   - `associate_three`: canonical(compose(compose(A,B),C)) == canonical(compose(A,compose(B,C))) for jointly compatible triples whose constraints don't depend on grouping
   - `duplicate_conflict`: same ID, conflicting intrinsic origin → structured refusal with the smallest known witness (classified, no crash)
   - `shared_id_merges`: same ID, identical claims → single identity, original edges + provenance retained
   - `no_invented_order`: composing two unrelated regions adds NO precedes edge or semantic ordering
   - `compatible_pair`: compose succeeds, preserves nodes and edges
   Follow the existing patterns in `dsc03/substrate/laws.py`
   (`typed_check`, `Mapping`, classified results) — do not reinvent.
3. **Tick tasks** — tick the corresponding tasks in
   `openspec/changes/define-document-composition-semantics/tasks.md`
   ONLY if this slice completes them; leave others untouched.

## Hard constraints

- **Zero DSC core wire changes**: `git diff openspec/specs` and
  `git diff spec/document-model-specodelic-v3` must stay EMPTY.
- No real-carrier conformance claims; honest labels everywhere.
- Synthetic fixtures only (reuse `dsc03/substrate/laws.py::synthetic_instance` patterns); do NOT add new real documents.
- New files carry Purpose/Responsibilities/Rationale headers.
- Do not modify `restore-document-substrate/` (done) or `add-document-structural-debugger/` (other ticket); do not touch `tests/tracer/` existing tests.
- All subprocess calls (if any) carry explicit `timeout=` — recorded finding from sunset-7hs: a wedged pdftotext blocked a gate run; this slice is synthetic-only so avoid subprocesses entirely.
- `.beads/` never staged.

## Out of scope

- Views/space/context deltas (sunset-905.2), cross-page projection and
  refinement diagnostics, PDF frame/rotation and EPUB anchor fixtures —
  later slices.
- Any change to deployed specs, frozen bundle, `dsc03/conformance.py` labels.

## Red/green/refactor sequence

1. RED: create `tests/substrate/test_assembly_laws.py` with the ≥6 law
   fixtures above (failing — no assembly module yet). Run
   `python3 -B -m pytest tests/substrate -q` → fails.
2. GREEN: implement the assembly module + DESIGN decision artifact until
   tests pass.
3. REFACTOR: separate commit for tidy only.

## Exact files

- `tests/substrate/test_assembly_laws.py` (new)
- `dsc03/substrate/assembly.py` (new; justify placement in the report)
- `openspec/changes/define-document-composition-semantics/design-decisions-assembly.md` (new) or a dated section in its `design.md`
- `openspec/changes/define-document-composition-semantics/tasks.md` (tick only completed slice tasks)
- Do NOT touch: `openspec/specs/`, `spec/document-model-specodelic-v3/`, other change dirs.

## Exact test/review commands

```
python3 -B -m pytest tests -q        # full suite, exit 0, >=199 passed (193 baseline + 6)
just spec-check                      # ALL GATES PASSED
spk lint openspec/changes            # ok: true, issues: []
git diff openspec/specs spec/document-model-specodelic-v3   # empty
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests -q` → exit 0 with ≥199 passed
2. `just spec-check` → prints `ALL GATES PASSED`
3. `spk lint openspec/changes` → `"issues":[]`
4. `git diff openspec/specs spec/document-model-specodelic-v3` → empty output
5. `test -f tests/substrate/test_assembly_laws.py` → exit 0
6. `git log --oneline -4` shows atomic red/green/refactor commits
7. `bd show sunset-905.1` still shows this ticket in_progress (lead closes it)

## Follow-up threshold

If an assembly law cannot be implemented without a wire delta, STOP,
commit what passes, and record the finding in the report.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read (assembly module, tests,
design decision, wai gate records) and include fresh test-run output
(actual command + result pasted) before recording CONFIRM; otherwise
REVIEW_REQUIRED.

## Spawn model

- Model: current session's default model.
- Context ceiling: ≤ 40% of the actual model window at spawn time.
- Wall-clock budget for the spawn: `timeout 60m`.
