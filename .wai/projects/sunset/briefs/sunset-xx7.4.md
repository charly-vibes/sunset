# Brief — sunset-xx7.4 · Lens slice 4: a11y/interaction + second-implementation agreement (HITL)

Ticket: `sunset-xx7.4` (P3, lane:hitl) · Parent: `sunset-xx7` · Depends on: `sunset-xx7.3` ✓ (136d99a; green HEAD `c9b6d98`, 254 tests + 18 subtests)

## Why

Delegation rationale: canon — subagents implement. Slice 4's part A (a11y/keyboard/interaction tests) is pure test work over shipped machinery; part B (second-implementation agreement) is executed here as a **separate fresh subagent** to maximize independence, but is **labeled AGENT-EXECUTED** — the owner gate on agreement results stays OPEN (Jev 1.0 for this shape; 0.92 that closing the gate now would overclaim `independent_agreement`).

## Desired outcome

**Part A — interaction/a11y tests** (task 3.3) over the shipped `dsc03.inspect` / `dsc03.locators` / `dsc03.compare` surfaces:
- `tests/tracer/test_debugger_a11y.py` with tests for:
  - **Keyboard-only path**: a modeled keyboard-only selection flow (`keyboard_only_selection_flow()` per spec property `keyboard_navigation`) reaches every inspectable detail (region → loci → evidence → diagnostic) without pointer interaction; non-color status labels (text status tokens, not color codes).
  - **Offline operation**: inspection runs with no network (assert no socket usage — e.g. inspect module surface makes no network calls; deterministic outputs).
  - **Rotation/reflow**: PDF region loci survive a modeled rotation (fixed-coordinate domain remap is explicit, not silently mutated); EPUB anchors persist after a modeled viewport reflow (`pdf_epub_no_ocr` property shape — identity stays CFI-based).
  - **Malformed input**: malformed descriptors/locators produce classified diagnostics (never crashes, never silent pass).
  - **Performance** (honest measurement only): record inspection wall-time for the pinned demo/carrier fixtures in the test output WITHOUT claiming performance wins (no unmeasured claims — repo anti-goal).

**Part B — second-reader agreement harness** (task 3.4, AGENT-EXECUTED):
- `tests/tracer/test_second_reader_agreement.py` + a minimal second reader implemented as a FRESH, INDEPENDENT session (spawned separately — do not read the first implementor's test internals; consume only the public shipped surface and the frozen goldens in `fixtures/debugger-goldens/`).
- The second reader recomputes canonical diagnostic codes + comparison outcomes for the golden inputs; assert byte-identical after the declared canonicalization (sorted-key JSON, no timestamps) — or classify each disagreement explicitly (no silent winner election).
- Everything labeled AGENT-EXECUTED: a `fixtures/debugger-goldens/second-reader-agreement.org` record with provenance (agent/model, date, session names), stating the owner gate on agreement results remains OPEN and a human pass supersedes.

## Out of scope

- Closing the owner HITL gate or claiming human-equivalent independence. No performance-win claims. No changes to `dsc03/inspect.py`/`locators.py`/`compare.py` beyond minimal additive fixes if a11y tests expose a genuine shipped-code defect (record any such change in the report). No OCR/network; no DSC core wire changes; no edits to openspec/ trees.

## Exact files

- Part A: NEW `tests/tracer/test_debugger_a11y.py`.
- Part B: NEW `tests/tracer/test_second_reader_agreement.py`, NEW `fixtures/debugger-goldens/second-reader-agreement.org` (+ optional small second-reader module `dsc03/compare.py` additive or NEW `dsc03/second_reader.py` — prefer NEW file).
- May READ: shipped dsc03 modules, fixtures/debugger-goldens/, spec deltas.

## Exact commands

- Slice: `python3 -B -m pytest tests/tracer/test_debugger_a11y.py tests/tracer/test_second_reader_agreement.py -q`
- Full gates: `python3 -B -m pytest tests -q && just spec-check` → ALL GATES PASSED, frozen 0.2 PASS 11.

## Red/green/refactor (TDD — mandatory)

Part A: write ≥5 failing tests first (keyboard flow, offline, rotation, reflow, malformed) → minimal fixes/additive code → green. Part B (separate spawn): write failing agreement tests → implement second reader → green or classified disagreement record.

## Completion criteria (exit 0 = done)

- Both new test files pass; full suite + `just spec-check` ALL GATES PASSED.
- Keyboard-only path reaches every inspected detail (test asserts the full chain).
- Agreement record exists with AGENT-EXECUTED labeling + OPEN owner gate statement.
- Single atomic commits per part on `main`: `feat(debugger): sunset-xx7.4 a11y/keyboard/interaction tests` and `feat(debugger): sunset-xx7.4 agent-executed second-reader agreement (labeled, owner gate open)`.
- No push; do not close the beads ticket.

## Spawn model

- Two sequential spawns, each provider default (`z-ai/glm-5.3-flash`), fresh `pi -p -n` sessions (NEVER `--continue` — it attaches to the orchestrator's session), nohup + `timeout 1200` (20 min), poll every 5 min.
- Part B spawn must not read Part A's test file (independence); give it the goldens + public module surface only.

## Follow-up threshold

Blocked/out-of-scope conflict → stop, commit nothing, `BLOCKED: <reason>`.

## Verifier evidence contract (wai-px4g)

CONFIRM only with cited artifacts + fresh test-run output; otherwise REVIEW_REQUIRED. Final verdict for the slice is REVIEW_REQUIRED by design (HITL gate open).
