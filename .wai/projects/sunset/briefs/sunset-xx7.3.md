# Brief — sunset-xx7.3 · Lens slice 3: scoped comparators + counterexample export + goldens

Ticket: `sunset-xx7.3` (P2) · Parent: `sunset-xx7` · Depends on: `sunset-xx7.2` ✓ (8dd5256; current green HEAD `7a4cd89`)

## Why

Delegation rationale: epic-orchestrator canon — subagents implement, lead orchestrates/verifies/ships. Slice 3 has a crisp executable contract (each negative fixture fails with its expected diagnostic code + witness; export replay round-trip deterministic; gates green).

## Design decisions (Jev-typed, recorded)

- **Module layout**: NEW `dsc03/compare.py` (Jev 0.98) — comparators + counterexample export; imports `Diagnostic` from `dsc03.inspect` and locator/loci types from `dsc03.locators`; do not rewrite shipped modules.
- **Golden storage**: `fixtures/debugger-goldens/` (Jev 1.0 after archival fact supplied) — runtime tests and the future second implementation both consume a stable path that survives openspec change archival. The specifying README (`openspec/changes/add-document-structural-debugger/fixtures/README.md`) stays where it is as the spec artifact.

## Desired outcome

Per `openspec/changes/add-document-structural-debugger/specs/document-debugger-comparison/spec.md` (constraints `scoped_comparison`, `typed_outcome`, `composition_checks`, `no_edition_guess`, `counterexample_replay`, `loss_visibility`; NOT `independent_agreement` — that is slice 4/HITL):

1. **Versioned scoped observable comparators**: every comparison declares inputs, endpoint types, a versioned observable scope and the comparator; outcomes are exactly `equivalent / different / disputed / unsupported / unexamined` (note: comparison outcomes, distinct from slice-1 diagnostic categories but lossless-adjacent). Loss, unresolved evidence and unexamined coverage can NEVER be converted into `equivalent`/pass by normalization (`loss_visibility`).
2. **Composition/identity/associativity probes** on compatible typed mappings, including loss/error effects — declared identity and associativity are checked and mismatches produce witnesses; unsupported mapping/comparator → classified `unsupported`, no equivalence claim.
3. **No edition guessing**: titles/filenames alone never establish equivalent editions or semantic equality (`no_edition_guess` — the `same-title-editions` fixture case).
4. **Deterministic minimized counterexample export**: witness records rule id, input hashes (sha256), exact scope, versions, expected/observed, and replay limitations; redaction state + `replayable=false` when secret source bytes are omitted (`private-redaction` case). Export → reload → re-compare round-trip is byte-deterministic.
5. **Goldens + negative fixtures** under `fixtures/debugger-goldens/` (JSON, deterministic, no timestamps): implement the specified-but-unrealized cases from the README that are in slice scope — wrong reading order (oracle mismatch + witness), containment cycle (structural violation + cycle witness), dangling target, selector ambiguity, edition mismatch, sign loss (`cannot certify sign preservation` → typed non-equivalent/disputed outcome, never pass). At least one golden built from a real committed carrier (fixtures/carriers/).

## Out of scope

- Second-implementation agreement / a11y / keyboard (slice 4, HITL — do not claim `independent_agreement`).
- Changes to `dsc03/inspect.py` / `dsc03/locators.py` beyond minimal additive integration; `dsc03/validator.py`, `dsc03/substrate/`, deployed openspec specs, frozen 0.2 validator. No OCR/network/writes to sources. No DSC core wire changes. Do not edit the fixtures README (spec artifact).

## Exact files

- NEW `dsc03/compare.py` (Purpose/Responsibilities/Rationale header).
- NEW `tests/tracer/test_compare.py`.
- NEW `fixtures/debugger-goldens/**` (JSON + a README.org manifest noting provenance + redaction states).
- May READ: `dsc03/inspect.py`, `dsc03/locators.py`, `dsc03/adapters.py`, `fixtures/carriers/*`, spec deltas, fixtures README.

## Exact commands

- Slice: `python3 -B -m pytest tests/tracer/test_compare.py -q`
- Full gates: `python3 -B -m pytest tests -q && just spec-check` → ALL GATES PASSED, frozen 0.2 PASS 11.

## Red/green/refactor sequence (TDD — mandatory)

1. RED: ≥6 failing tests first, covering: (a) scoped comparator emits all five outcomes incl. loss-visibility non-conversion; (b) identity + associativity probes pass on a declared-compatible mapping and fail with witness on a broken one; (c) title-only edition match is refused; (d) each negative fixture yields its expected diagnostic code + minimal witness; (e) export→reload→re-compare byte-determinism incl. replayable=false redaction path; (f) unsupported comparator → classified unsupported, no equivalence claim.
2. GREEN: implement minimally. 3. REFACTOR: tidy, stay green. 4. Full gates; fix only your own breakage.

## Completion criteria (exit 0 = done)

- Slice tests + full suite + `just spec-check` ALL GATES PASSED.
- Each negative fixture fails with its expected diagnostic code + witness (test asserts the exact code).
- Export replay round-trip deterministic (test asserts byte equality).
- Single atomic commit on `main`: `feat(debugger): sunset-xx7.3 scoped comparators, counterexample export, goldens`.
- No push; do not close the beads ticket.

## Spawn model

- Model: provider default (`z-ai/glm-5.3-flash`), pi non-interactive, named session `subagent:sunset-xx7.3:impl`.
- Context ceiling: ≤ 60% of model window.
- Wall-clock budget: `timeout 1200` (20 min), nohup detached, poll every 5 min. Zero commits at kill → clean `-retry`; partial commits → manual resume via `pi -c`.

## Follow-up threshold

Out-of-scope conflict or spec contradiction → stop, commit nothing, final output `BLOCKED: <reason>`.

## Verifier evidence contract (wai-px4g)

CONFIRM only with cited artifacts + fresh test-run output; otherwise REVIEW_REQUIRED.
