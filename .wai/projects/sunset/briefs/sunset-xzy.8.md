# Brief: sunset-xzy.8 — Docs: oracle contract, evidence-class rules and calibrated limits

**Ticket**: sunset-xzy.8 (beads, in_progress, complexity s)
**Change**: `openspec/changes/add-raster-visual-oracles/` — tasks.md 6.2
**Base commit**: 04d7b7b (xzy.1–.7 shipped; `.7` landed `dsc03/visual/reports.py` + its tests)
**Gates baseline (recorded at claim)**: `just spec-check` ALL GATES PASSED; pytest 533 passed + 18 subtests (verified lead-side at e701227; the only later commit adds research notes).

## Why

The oracles exist and are tested, but no user-facing page says what they may and
may not claim. Spec requirement set (all eight): "Pinned render configuration",
"Declared frame mapping", "Labeled evidence class", "Scoped property claims",
"Mutation-validated sensitivity", "Calibrated thresholds with per-page outcomes",
"No silent resolution", "Distinct evidence class in demonstrations". Docs slice:
describe the contract honestly — especially the LIMITS — and cross-link the
change + approval provenance. NO accuracy, completeness or semantic claims
anywhere.

## Desired outcome

1. **NEW page `docs/src/visual-oracles.md`** (CLRT-001: this is the planned new
   page; adjust the filename only if a clearly better home exists, and say so in
   the report). Content, Diátaxis-flavored reference/how-to, house doc style
   (match `docs/src/conformance-matrix.md` tone and `reference.md` honesty
   boundaries):
   - The oracle contract, one section per requirement above — what each
     guarantees in one or two plain sentences.
   - **Evidence-class rules**: `correlated` (render shares the extractor's
     lineage) demonstrates sensitivity only and SHALL NOT support accuracy
     claims; `independent` (pdftoppm poppler render vs PyMuPDF extraction) may
     support scoped claims per the spec; outcomes carry the label per page.
   - **Calibrated limits, stated honestly**: thresholds exist ONLY for the
     recorded calibration carriers (`fixtures/visual/calibration.json`, six
     D6 fields); pages outside the recorded set are `uncalibrated` → outcome
     `unknown` → the aggregate blocks; the committed faint fixture is honestly
     uncalibrated by design — that is the documented behavior, not a gap.
   - **Conformance inertness**: visual results are recorded as a SEPARATE
     evidence class (`dsc03.visual.reports.record` — the `visual_oracles`
     section with its `non_substitution` note) and provably do not move
     conformance labels; oracles cannot complete a suite (passing oracles +
     no independent readers → label stays `incomplete`).
   - **Provenance**: implemented under the active change
     `openspec/changes/add-raster-visual-oracles/` (relative repo link);
     owner approval recorded 2026-11-02 in decision ticket `sunset-zo5`
     (beads; APPROVED with all 9 rule-of-5 findings applied as amendments in
     `eeac8b0`; authorization scope = tasks.md sections 3-7 only). State the
     AGENT-EXECUTED caveat for all measurements/thresholds/fixtures — human
     pass supersedes.
   - NO claims of accuracy, completeness, semantic understanding, or OCR;
     NO suggestion the change's specs are deployed (they are a proposal under
     implementation; deployed truth remains `openspec/specs/`).
2. **`docs/src/reference.md`**: add `dsc03.visual` to "## `dsc03` module
   surface" (consumer-facing vs reviewer/developer machinery split as the file
   already uses: render/frame/oracle/report functions; keep one line each) and
   list the new fixture locations in "## Fixture catalog"
   (`tests/tracer/fixtures/visual/` — mutation + calibration fixtures;
   `fixtures/visual/calibration.json` — the calibration record).
3. **`docs/src/integrate.md`**: extend "Recipe 3: Read the four reports" with a
   short paragraph + minimal example: `dsc03.visual.reports.record(...)` adds a
   separate `visual_oracles` evidence-class section; it never changes
   conformance labels. Keep the existing four-reports framing intact.
4. **`docs/src/status.md`**: update the machinery status honestly — raster
   visual oracles implemented as scoped machinery under the active change
   (sections 3–6 of its tasks.md done; docs + final gate remaining), evidence
   classes labeled, calibration bounded to recorded carriers, labels inert.
   Where the page currently says OCR/visual things are "not part of" the core,
   adjust ONLY the wording made stale by this change — keep every other
   limitation claim verbatim.

## House rules

- House doc voice: short declarative sentences, honest-boundary framing like
  `reference.md` § "Honest-claim boundaries". No marketing.
- Relative repo links only for repo files (openspec paths, docs pages);
  links must resolve on disk. The link gate (`tests/docs/test_docs_links.py`)
  only checks `what-is-dsc.md`, but ALL docs links you touch must resolve.
- Do NOT add a link to `what-is-dsc.md` navigation unless natural — if you do,
  the new page must exist in the same change (it does) so the gate stays green.
- AGENT-EXECUTED labeling for measurements/thresholds/fixtures; human pass
  supersedes. No human-evidence phrasing anywhere.
- `/usr/bin/python3 -m pytest ...` (bare `python3` lacks pytest).

## Red → green shape

Docs slice: RED = `just spec-check` + full pytest run BEFORE edits (baseline
green recorded), plus a failing link check if you add navigation (optional).
GREEN = all gates green after edits. Record both verbatim.

## Anti-goals (hard)

- NO accuracy/completeness/semantic claims; NO OCR claims; no "validates
  documents" phrasing.
- Do NOT describe the change's specs as deployed; do not touch
  `openspec/specs/` or `validator.py` framing (frozen 0.2 stays 0.2).
- Do NOT edit code, fixtures, tests (except none), justfile, or
  `tests/docs/` expectations.

## Out of scope

Final gate (7.1/.9), tickets.md updates (lead does those at ship), any code.

## Exact files

- CREATE `docs/src/visual-oracles.md`
- EDIT `docs/src/reference.md`, `docs/src/integrate.md`, `docs/src/status.md`
- CREATE `.wai/projects/sunset/research/sunset-xzy.8-report.org`

## Exact commands

- `/usr/bin/python3 -m pytest tests -q` (baseline 533 passed + 18 subtests)
- `/usr/bin/python3 -m pytest tests/docs -q` (link + tutorial gates green)
- `just spec-check` → ALL GATES PASSED, PASS 11 descriptor fixtures

## Completion criteria (exit 0 = done)

1. Pre-edit baseline recorded (533+18, ALL GATES PASSED).
2. Post-edit: full pytest exits 0 (533+18 unchanged — docs only, no test
   churn), `tests/docs` green, `just spec-check` ALL GATES PASSED, PASS 11.
3. Every repo-relative link you introduced resolves on disk (`ls` each target).
4. `git status --short` shows ONLY the three docs pages + your report (+ the
   pre-existing `.whisper`/`.wai`/`pba-judicial-2026-07-29.pdf` noise).

## Verifier evidence contract (wai-px4g)

Report must cite files changed and paste baseline + post-edit gate/suite tails.
Claims without pasted output ⇒ REVIEW_REQUIRED.

## Spawn model

`openrouter/z-ai/glm-5.3-flash` (owner BYOK, maxTokens 48000 cap). Window
1,000,000 tokens; **context ceiling ≤ 15%**; exceed ⇒ stop and report.
Complexity s: ~15 minutes wall-clock budget (timeout 1500).

## Follow-up threshold

If honest wording seems impossible without overclaiming (e.g. status.md's
existing limitation sentences contradict the change's existence), STOP: record
the conflicting sentences verbatim in the report, touch nothing, leave the tree
clean.

## Report

Write `.wai/projects/sunset/research/sunset-xzy.8-report.org`: baseline +
post-edit outputs, files changed, link-resolution evidence, deviations,
findings (labeled AGENT-EXECUTED — human pass supersedes).
