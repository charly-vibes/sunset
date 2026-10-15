# Brief: sunset-7hs — Implement restore-document-substrate gates (purpose + categorical model)

## Why

Delegated to a subagent because it is a large, well-bounded implementation
block (Stage A mapping + Stage B fixtures/tests + Stage D docs from
`openspec/changes/restore-document-substrate/design.md`) whose inputs are
already committed: the grounded change proposal, the deployed 0.3 machinery
(`dsc03/`), and the real screened carriers under `fixtures/carriers/` and
`fixtures/demo/`. The lead session is orchestrating the sunset-9pf epic
loop; inline execution would chain past the ticket boundary (canon
Invariant 1). This ticket is the dependency root of the epic — sunset-905,
sunset-905.1, sunset-xx7, sunset-xx7.1 all block on it.

## Ticket

- **ID**: sunset-7hs (claimed, in_progress)
- **Epic**: sunset-9pf — implement the three grounded DSC proposal changes
  (substrate → composition → Lens)
- **Change**: `openspec/changes/restore-document-substrate/` (read
  `proposal.md`, `design.md`, `tasks.md` first — they are the authority)

## Desired outcome

The substrate change's implementable tasks are done and verified:
laws mapped onto deployed 0.3 entities, deterministic oracles + fixtures
exist and pass as tests, negative counterexamples prove rejection behavior,
README/status are amended, and a conformance matrix honestly separates
specified / implemented / tested / independently-reproduced.

## Work requirements (from tasks.md; authority = the change docs)

1. **Validate the change** — `openspec validate --changes restore-document-substrate --strict` (or repo equivalent) and `spk lint openspec/changes` clean; adjust naming/linking inside the change dir only if needed.
2. **Law mapping table** — map the six conceptual roles (Document, Region, Content, Relation, Annotation, Evidence) and the nine design §4 laws onto deployed 0.3 entities (`dsc03/*.py`, deployed specs under `openspec/specs/`). Publish as `openspec/changes/restore-document-substrate/mapping.md` with a **satisfied / partial / missing** table per role and per law, citing the entity or requirement that satisfies it. Never assert a bijection without proof (design §1).
3. **README + status amendments** — `README.md` and `docs/src/status.md`: normative purpose, consumers, honest current capabilities, documented non-goals. Do NOT upgrade any conformance claim language.
4. **Native PDF oracle** — deterministic structural oracle over an existing committed native-PDF carrier (`fixtures/carriers/`, e.g. the annotated business docs), no OCR; asserts declared page/coordinate basis, text runs, and unsupported-feature declarations.
5. **EPUB oracle** — deterministic spine/navigation/footnote oracle over `fixtures/carriers/sunset-carrier-sample.epub`; no invented pagination; footnote backlink is NOT a `precedes` edge.
6. **Scanned + hybrid fixtures** — use the committed scanned (`diario-de-poesia-excerpt.pdf`, `resumen-periodical-excerpt.pdf` p13) and hybrid carriers; alternate readings + evidence with provenance; OCR text is a derived observation with engine provenance; hybrid coexisting observations must not overwrite each other.
7. **Domain-independence fixture** — a financial/structured document (existing committed carrier, e.g. bank-statement / ABL constancia) described by the same core without adding a banking primitive to core.
8. **Law checks + negative counterexamples** — typed-edge endpoint rejection (structured, no crash), identity stability under canonical serialization, determinism (pinned inputs → identical canonical output), composition law where the machinery supports it, loss accounting, non-invention (mapping never asserts unobserved facts as direct observations), failure-of-factorization (sign-bearing geometry vs text-only flattening → declared loss). Each negative counterexample must be a real test asserting rejection/loss, not a prose claim.
9. **Raw gate report** — run `just spec-check`, `spk lint openspec/changes`, full pytest; report raw output in the final report.
10. **Second independent reader** — implement or evaluate a second independent reading path (e.g. an alternative adapter/reader in the new harness that does not reuse the first reader's grouping logic) over the same fixtures; measure agreement, descriptor overhead, and unrepresentable cases; record as a table. This is machinery-level independence (scripted), NOT a human-review claim — mark it as such wherever reported (recorded deviation: agent-executed; human pass supersedes).
11. **Conformance matrix** — in `docs/src/status.md` (or a new linked `docs/src/conformance-matrix.md`): per capability area, distinguish `specified` (deployed spec), `implemented` (dsc03 code), `tested` (tracer/gate tests), `independently reproduced` (second reader agreement). Real-carrier conformance stays UNCLAIMED.

## Hard constraints

- **Zero DSC core wire changes**: `git diff openspec/specs` must be EMPTY at all times. No edits to deployed specs, the frozen 0.2 validator, or `spec/document-model-specodelic-v3/` content.
- **No real-carrier conformance claims** — `dsc03/conformance.py` labels and `docs/src/status.md` stay honestly scoped.
- Stage C wire deltas are OUT OF SCOPE — if an expressivity gap is found, record it as a finding, do not submit wire deltas.
- New source files carry Purpose/Responsibilities/Rationale headers (file-headers criterion).
- No PII: reuse only already-committed screened carriers; never add new real documents.
- Do not modify `openspec/changes/define-document-composition-semantics/` or `add-document-structural-debugger/` (other tickets).
- `.beads/` is never staged (`git add .beads` is a hard error).

## Out of scope

- Composition-semantics and Lens changes (sunset-905, sunset-xx7).
- Human reader annotation (HITL noted as deviation only).
- mdBook/website tooling, docs/src/ consumer pages other than status.md.

## Red/green/refactor sequence

1. RED: create `tests/substrate/test_substrate_gates.py` (new harness dir, separate from `tests/tracer/` per design Stage B) with failing tests for the law checks + per-fixture oracles (4–8 above). Run: `python3 -B -m pytest tests/substrate -q` → fails.
2. GREEN: implement the harness modules (e.g. `dsc03/substrate/` or a separate `substrate/` harness package — your call, justify it) + `mapping.md` + README/status amendments until all tests pass.
3. REFACTOR: separate commit for tidy only (headers, dead code, naming).

## Exact files

- `tests/substrate/` (new test harness)
- harness package under `dsc03/` or repo root (new modules, your call — justify)
- `openspec/changes/restore-document-substrate/mapping.md` (new)
- `openspec/changes/restore-document-substrate/tasks.md` (tick completed tasks ONLY)
- `README.md`, `docs/src/status.md` (amendments; optional new `docs/src/conformance-matrix.md`)
- Do NOT touch: `openspec/specs/`, `spec/document-model-specodelic-v3/`, `dsc03/conformance.py` labels beyond honest wording, other change dirs.

## Exact test/review commands

```
python3 -B -m pytest tests -q        # full suite, exit 0, >154 passed
just spec-check                      # ALL GATES PASSED
spk lint openspec/changes            # ok: true, issues: []
git diff openspec/specs              # empty
git diff spec/document-model-specodelic-v3   # empty
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests -q` → exit 0 with ≥160 passed (154 baseline + new)
2. `just spec-check` → prints `ALL GATES PASSED`
3. `spk lint openspec/changes` → `"issues":[]`
4. `git diff openspec/specs spec/document-model-specodelic-v3` → empty output
5. `test -f openspec/changes/restore-document-substrate/mapping.md` → exit 0
6. `git log --oneline -5` shows atomic red/green/refactor commits for this ticket
7. `bd show sunset-7hs` still shows this ticket in_progress (lead closes it)

## Follow-up threshold

If a law cannot be tested without a wire delta, or a fixture requires a new
real carrier: STOP, commit what passes, and record the finding in the
report. Do not expand scope past this ticket.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read (mapping.md, new tests,
wai gate records) and include fresh test-run output (actual command +
result pasted) before recording CONFIRM; otherwise REVIEW_REQUIRED.

## Spawn model

- Model: current session's default model.
- Context ceiling: ≤ 40% of the actual model window at spawn time.
- Wall-clock budget for the spawn: `timeout 60m`.
