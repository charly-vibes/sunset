# Brief — sunset-xx7.2 · Lens slice 2: carrier locator adapters + synchronized selection

Ticket: `sunset-xx7.2` (P2) · Parent: `sunset-xx7` · Depends on: `sunset-xx7.1` ✓ (d6edc1b — `dsc03/inspect.py` shipped, 232 tests + gates green at `162edf7`)

## Why

Delegation rationale: epic-orchestrator canon — the lead orchestrates, subagents implement. Slice 2 is a self-contained vertical (locators + synchronized selection) with runnable completion criteria, building on the shipped slice-1 surface without touching shipped scope.

## Design decisions (Jev-typed, recorded)

- **Module layout**: NEW `dsc03/locators.py` (Jev 0.97 vs extend-inspect 0.03) — keep `inspect.py` focused on index/diagnostics; `locators.py` imports from it.
- **Scan-image carriers**: pixel coordinate domain over the raster page (Jev 0.92 vs reject-scans 0.01) — regions carry intrinsic pixel rects + explicit dpi/scale so intrinsic↔display conversion is always explicit. OCR stays forbidden as implicit; if a declared, attributed extraction profile exists, its text may be resolved as attributed evidence only (never semantic truth — `evidence_truth_boundary`).

## Desired outcome

Per `openspec/changes/add-document-structural-debugger/specs/document-debugger/spec.md` (constraints `carrier_locators`, `bidirectional_navigation`, `scoped_structure`, transition guards `inspect`/`unsupported_source`, properties `pdf_epub_no_ocr`, `ambiguous_selector`, `partial_order`):

1. **Carrier locator adapters** in `dsc03/locators.py`:
   - PDF: fixed-coordinate locator domain over the page/rect geometry already present in descriptors built by `dsc03/adapters.describe_pdf` — intrinsic coordinates preserved; display coordinates only ever derived explicitly.
   - EPUB: stable XHTML/CFI selectors (the sidecar style used by `fixtures/carriers/sunset-carrier-sample-annotations.json` and `dsc03/adapters.describe_epub`); **transient viewport coordinates are never persistent EPUB identity**; anchors persist after reflow.
   - Scan-image: pixel-domain locator (see decision above); explicit mixed-mode observations when one page carries both native text regions and raster regions — both remain distinct with independent evidence access.
   - Unsupported carrier/locator → classified reason (`unsupported` diagnostic category from slice 1), never a guess.
2. **Synchronized selection**: resolving a selected region/view returns ALL available source loci AND evidence records (`bidirectional_navigation`):
   - missing selector → explicit missing state, no invention;
   - multiple matching targets → ambiguity reported, neither auto-selected;
   - scoped alternative reading orders: no total order invented; display sort not asserted as unique (`partial_order` — two legal topological sorts both accepted).
3. Read-only boundary holds (slice-1 `unchanged_bytes` must still pass against locators in use).

## Out of scope

- Comparators, counterexample export, goldens, negative fixtures (slice 3), a11y/keyboard + second implementation (slice 4/HITL).
- Changes to `dsc03/inspect.py`'s shipped diagnostics model beyond consuming it (additive integration is allowed if required — keep it minimal), `dsc03/validator.py`, `dsc03/substrate/`, deployed openspec specs, frozen 0.2 validator. No OCR/network/no writes to sources. No DSC core wire changes.

## Exact files

- NEW `dsc03/locators.py` (Purpose/Responsibilities/Rationale header).
- NEW `tests/tracer/test_locators.py`.
- May READ: `dsc03/inspect.py`, `dsc03/adapters.py`, `fixtures/carriers/*` (real carriers + EPUB CFI sidecars), spec deltas under `openspec/changes/add-document-structural-debugger/specs/`.

## Exact commands

- Slice: `python3 -B -m pytest tests/tracer/test_locators.py -q`
- Full gates: `python3 -B -m pytest tests -q && just spec-check` → ALL GATES PASSED, frozen 0.2 PASS 11.

## Red/green/refactor sequence (TDD — mandatory)

1. RED: ≥5 failing tests first: (a) PDF region resolves to its declared page/rect loci via `describe_pdf`-style descriptor; (b) EPUB CFI resolves and viewport geometry is never stored as identity; (c) scan page resolves in pixel domain with explicit dpi/scale and mixed-mode page keeps native/raster observations distinct; (d) ambiguous selector (two matching targets) reported, no auto-selection; missing selector reported as missing; (e) unsupported locator → `unsupported` classified reason; two legal topological sorts of the same scoped reading order both accepted (no unique-order assertion).
2. GREEN: implement minimally.
3. REFACTOR: tidy, tests stay green.
4. Full gates; fix only your own breakage.

## Completion criteria (exit 0 = done)

- Slice tests + full suite + `just spec-check` all green (ALL GATES PASSED).
- At least one test exercises a real committed carrier fixture via `dsc03/adapters` (e.g. the EPUB sample or one PDF).
- Single atomic commit on `main`: `feat(debugger): sunset-xx7.2 carrier locator adapters + synchronized selection`.
- No push; do not close the beads ticket (orchestrator ships).

## Spawn model

- Model: provider default (`z-ai/glm-5.3-flash`), pi non-interactive, named resumable session `subagent:sunset-xx7.2:impl`.
- Context ceiling: ≤ 60% of model window.
- Wall-clock budget: `timeout 1200` (20 min), nohup detached, orchestrator polls every 5 min. Zero commits at kill → clean `-retry`; partial commits → manual resume via `pi -c`.

## Follow-up threshold

Out-of-scope conflict or spec contradiction → stop, commit nothing, final output `BLOCKED: <reason>`.

## Verifier evidence contract (wai-px4g)

CONFIRM only with cited artifacts + fresh test-run output in the review artifact; otherwise REVIEW_REQUIRED.
