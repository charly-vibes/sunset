# Brief: sunset-9pf.1 — Apply remaining rule-of-5 MEDIUM findings to the three changes

## Why

Delegated to a subagent because it is a self-contained spec-editing slice over
the three proposed (not deployed) openspec changes — no DSC code, no fixtures,
no wire changes. The lead session is orchestrating the sunset-9pf epic loop;
inline execution would chain past the ticket boundary (canon Invariant 1).
The CRITICAL/HIGH findings from the 2026-10-15 rule-of-5 pass were already
fixed in 9fecdf5; this ticket closes the four MEDIUM leftovers.

## Ticket

- **ID**: sunset-9pf.1 (claimed, in_progress)
- **Epic**: sunset-9pf — implement the three grounded DSC proposal changes
  (substrate → composition → Lens)
- **Authority**: the three change dirs under `openspec/changes/`:
  `restore-document-substrate/`, `define-document-composition-semantics/`,
  `add-document-structural-debugger/` — read the affected spec files in full
  before editing.

## The four findings (the entire scope)

1. **CLAR-001/002** — in
   `openspec/changes/define-document-composition-semantics/specs/`:
   scenarios whose **THEN** restates the GIVEN (`- **THEN** Given ...`,
   currently in document-assembly (6), document-context (3+), and check
   document-views/document-space too) must be rewritten so the THEN states
   only the observable outcome, and scenario names get descriptive titles
   (model: substrate's `A non-periodical consumer`; currently generic names
   like `Typed partial assembly fixture`). Keep WHEN/THEN structure valid
   per openspec scenario format.
2. **EDGE-002** — in
   `openspec/changes/restore-document-substrate/specs/document-purpose/spec.md`:
   the purpose state model has no declared path for `map_contract`/
   `test_fixtures` transition failure (lines ~37–38: purpose_declared →
   contract_mapped → fixtures_tested). Add refusal transitions or a
   state_limit-class outcome (model: the existing `state_limit` /
   `scope_limited` row at line ~40), with a rationale line.
3. **EDGE-004** — same file: `scope_limited` is terminal with no escalation
   transition. Declare the escalation semantics explicitly (a transition out,
   e.g. on new evidence or owner ruling) or document it as
   terminal-by-design with a stated rationale.

## Desired outcome

All four MEDIUM findings resolved in the change specs; spk lint stays 0
issues and `openspec validate --changes --strict` stays green; no behavioral
or wire changes anywhere.

## Work requirements

1. Read each affected spec file in full first; preserve every requirement's
   anchor tags ([[document.purpose.*]] etc.) and the scenario→requirement
   mapping.
2. Rewrite the flagged THENs: outcome-only assertions, no GIVEN restatement.
   Do NOT change what the scenario requires — prose clarity only. If a
   scenario name duplicates across requirement blocks in the same file
   (assembly currently repeats `Typed partial assembly fixture`), give each
   a distinct descriptive name.
3. For EDGE-002/004, keep the state-machine table format; add rows/notes in
   the file's established style. Note in the change's design.md (or a short
   section in tasks.md notes) that this closes rule-of-5 MEDIUM findings
   EDGE-002/EDGE-004.
4. Do not tick tasks.md items unless a listed task is fully completed by
   this work (likely none — this is findings hygiene, not a task-list item;
   if unsure, leave tasks.md untouched and say so in the report).

## Hard constraints

- **Zero DSC core wire changes**: `git diff openspec/specs` and
  `git diff spec/document-model-specodelic-v3` must stay EMPTY.
- Do not modify `dsc03/`, `tests/`, `fixtures/`, or the frozen bundle.
- Do not deploy/archive any change; all three changes remain proposed.
- Do not modify `add-document-structural-debugger/` unless a finding
  explicitly targets it (none do — leave it alone).
- No new Python code; no subprocess calls; no real-carrier claims.
- `.beads/` never staged.

## Out of scope

- CRITICAL/HIGH rule-of-5 findings (already fixed in 9fecdf5).
- sunset-905.3 (real-carrier conformance, HITL), sunset-xx7 (Lens MVP).
- Deployed specs and conformance labels.

## Exact files

- `openspec/changes/define-document-composition-semantics/specs/document-assembly/spec.md`
- `openspec/changes/define-document-composition-semantics/specs/document-views/spec.md`
- `openspec/changes/define-document-composition-semantics/specs/document-space/spec.md`
- `openspec/changes/define-document-composition-semantics/specs/document-context/spec.md`
- `openspec/changes/restore-document-substrate/specs/document-purpose/spec.md`
- possibly a one-line note in the respective design.md / tasks.md

## Exact test/review commands

```
spk lint openspec/changes            # ok: true, issues: []
openspec validate --changes --strict # exit 0, all changes valid
openspec validate --specs --strict   # exit 0 (unchanged, 7 pass)
git diff openspec/specs spec/document-model-specodelic-v3   # empty
python3 -B -m pytest tests -q        # 221 passed + 18 subtests (must be UNCHANGED)
```

## Completion criteria (runnable; exit 0 = done)

1. `spk lint openspec/changes` → JSON with `"ok":true` and `"issues":[]`
2. `openspec validate --changes --strict` → exit 0
3. `git diff openspec/specs spec/document-model-specodelic-v3` → empty output
4. `python3 -B -m pytest tests -q` → 221 passed, 18 subtests (unchanged)
5. `grep -rn "THEN.*Given" openspec/changes/define-document-composition-semantics/specs/` → no matches
6. `grep -n "scope_limited" openspec/changes/restore-document-substrate/specs/document-purpose/spec.md` → shows declared escalation semantics or terminal-by-design rationale
7. Atomic commits: prose edits and any table edits committed with clear
   messages referencing sunset-9pf.1

## Follow-up threshold

If resolving a finding would require changing a requirement's meaning,
deploying a spec, or touching the wire — STOP that item, record it as
deferred with the reason in the report, and commit only what stands.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read (edited spec files,
lint/validate output, wai gate records) and include fresh command output
(actual command + result pasted) before recording CONFIRM; otherwise
REVIEW_REQUIRED.

## Spawn model

- Model: current session's default model.
- Context ceiling: ≤ 40% of the actual model window at spawn time.
- Wall-clock budget for the spawn: `timeout 30m`.
