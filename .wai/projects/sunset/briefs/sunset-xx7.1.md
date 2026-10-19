# Brief — sunset-xx7.1 · Lens slice 1: read-only loader + inspection index + typed diagnostics model

Ticket: `sunset-xx7.1` (P2, lane:afk, complexity:m) · Parent: `sunset-xx7` (add-document-structural-debugger MVP) · base_commit `9fecdf5` (history base; work from current `main` HEAD)

## Why

Delegation rationale: the lead session is orchestrating the sunset-xx7 epic (claim → brief → spawn → verify → ship per `.wai/resources/pipelines/epic-orchestrator.toml`); implementation is subagent work so the lead stays free to verify and ship. Slice 1 is well-bounded (loader + index + diagnostics model, no carriers/comparators yet — those are slices 2–3) and has an executable completion contract, making it safe for an unattended subagent.

## Desired outcome

A read-only DSC descriptor inspection layer per `openspec/changes/add-document-structural-debugger/specs/document-debugger/spec.md`:

1. **Read-only descriptor loader** — loads a 0.3 descriptor via the existing `dsc03.validator` (two-phase lexical/type validation already exists in `dsc03/validator.py`), then builds a **validated inspection index** over the loaded descriptor: regions/containment, reading-order edges, evidence records, provenance/annotations — indexed for O(1)-ish lookup by id. **No implicit OCR, no network access.**
2. **Read-only enforcement** — bytes/sha256 of the input descriptor file and any referenced source artifacts must be identical before and after inspection (`unchanged_bytes` property). The loader/index never writes.
3. **Typed diagnostics model** — result categories exactly per spec constraint `typed_diagnostics`: `pass`, `violated`, `disputed` (review/dispute), `unsupported`, `unexamined` — with a stable rule ID and a link to the **smallest available witness** (minimal fixture/element/edge ids). `unexamined` content must never masquerade as `pass` (constraint `evidence_truth_boundary`: attributed claims are not automatically true).
4. New files carry Purpose/Responsibilities/Rationale file headers.

## Out of scope (later slices — do NOT build)

- Carrier locator adapters (PDF/scan/EPUB CFI) — slice 2 (`sunset-xx7.2`).
- Comparators, counterexample export, goldens, negative fixtures — slice 3 (`sunset-xx7.3`).
- a11y/keyboard/second-implementation agreement — slice 4 (`sunset-xx7.4`, HITL).
- Any change to `dsc03/validator.py`, `dsc03/substrate/`, deployed openspec specs, or the frozen 0.2 `spec/document-model-specodelic-v3/validator.py`. **No DSC core wire changes.**

## Exact files

- NEW `dsc03/inspect.py` — loader + inspection index + typed diagnostics model (single module keeps slice cohesive; split into `dsc03/inspect/` only if it exceeds ~600 lines).
- NEW `tests/tracer/test_inspect.py` — all slice-1 tests.
- May READ anything; must not modify anything else.

## Exact commands

- Test: `python3 -B -m pytest tests/tracer/test_inspect.py -q`
- Full gates: `python3 -B -m pytest tests -q && just spec-check` (must end ALL GATES PASSED; frozen 0.2 fixtures still `PASS 11 descriptor fixtures`)
- Byte-identity check is part of the tests: hash file before load, run full inspection, hash after, assert equal.

## Red/green/refactor sequence (TDD — mandatory)

1. RED: write ≥4 failing unit tests first, covering: (a) loader round-trip byte-identity on a frozen 0.3 fixture (`fixtures/` has 0.3 descriptors; `tests/tracer/fixture_minimal.json` is one), (b) inspection index resolves region/reading-order/evidence ids, (c) typed diagnostics emits all five categories with rule ID + minimal witness, (d) unexamined content never reported as pass.
2. GREEN: implement `dsc03/inspect.py` minimally to pass.
3. REFACTOR: tidy only if needed; keep tests green.
4. Run full gates; fix only your own breakage.

## Completion criteria (exit 0 = done)

- `python3 -B -m pytest tests/tracer/test_inspect.py -q` — all pass
- `python3 -B -m pytest tests -q` — all pass, no new failures
- `just spec-check` — ends `ALL GATES PASSED`
- `sha256` before/after assertion exists as a test and passes
- Work committed atomically on `main` with a conventional message (`feat(debugger): ...`); no push (orchestrator ships).

## Spawn model

- Model: provider default (`z-ai/glm-5.3-flash` via pi non-interactive).
- Context ceiling: ≤ 60% of the model window. The brief + spec + tasks + ticket are small; if the subagent finds itself reading more than the files listed above plus `dsc03/validator.py`/`openspec/changes/add-document-structural-debugger/`, it is off-track.
- Wall-clock budget: `timeout 1200` (20 minutes) wrapped around the spawn. If killed at budget: zero commits → clean `-retry` spawn; partial commits → manual resume via `pi -c`.

## Follow-up threshold

If you discover the slice cannot be completed without touching out-of-scope files, or the deployed spec contradicts this brief, STOP writing code, commit nothing, and record the blocker as your final output (the orchestrator files follow-up tickets).

## Verifier evidence contract (wai-px4g)

The verify session records CONFIRM only if its artifact cites artifacts actually read (brief, commits via `git log`, test output) **and** includes fresh test-run output (command + result pasted). Otherwise: REVIEW_REQUIRED.
