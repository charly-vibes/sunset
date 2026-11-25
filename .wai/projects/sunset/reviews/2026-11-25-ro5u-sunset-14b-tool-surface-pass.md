# RO5U review: sunset-14b typed agent tool surface (2026-11-25)

**Work reviewed:** code — `sunset/tool_surface.py` (779 ln), `sunset/cli.py` (54 ln), `sunset/__init__.py`, 8 tracer suites + fixtures, justfile gate, packaging (commit c463330; files unchanged since ship, verified `git diff c463330..HEAD` empty for the scope).

**Convergence:** Stage 4 (no new critical after Stage 2; new-issue rate < 10% per stage; findings below are verified against the source, not speculative — no TYPESAFE_API_KEY set, so findings carry self-reported validation only).

## Stage 1 — DRAFT

Assessment: coherent single-core design — one envelope, closed status/reason vocabularies asserted exhaustively, decorator-guarded tools that never raise, thin CLI adapter, workspace session store separated from immutable run state.

Shape Quality: EXCELLENT

## Stage 2 — CORRECTNESS

Issues Found:

[CORR-001] LOW — tool_surface.py:234,303 (`_load_session` / `open()` claim restore)
Description: session `claims` payload shape is trusted (`list(session.get("claims", []))`); a corrupt claims value (e.g. a string) iterates into junk entries and surfaces later as `internal.error` TypeErrors in read/write tools instead of a clean session reset.
Evidence: no isinstance/element checks on the restored list; everything downstream indexes `claim["id"]`.
Recommendation: guard both restore sites with a shape check (`isinstance(claims, list)` and all-dict elements), else reset to `[]`.

[CORR-002] LOW — tool_surface.py:738-741 (`export()` audit record check)
Description: audit-record validation type-checks `claim_type`, `n`, `errors` but not `evidence_class`; a non-string passes validation and reaches `gate_open` — observed in the fix round: `gate_open` silently tolerates it, so a malformed audit record is accepted as valid input rather than refused.
Evidence: the key-presence set includes `evidence_class`, the type checks omit it; narrow test showed status ok for `evidence_class: 7`.
Recommendation: add `isinstance(record["evidence_class"], str)` to the spec.invalid branch.

Correctness Quality: GOOD

## Stage 3 — CLARITY

Issues Found:

[CLAR-001] LOW — cli.py:42
Description: `kwargs = {}` is a dead store: the invalid-args branch builds the spec.invalid envelope and returns immediately; `kwargs` is never used.
Impact: reader pauses on whether `{}` kwargs flow onward.
Recommendation: drop the assignment; return directly.

[CLAR-002] LOW — tool_surface.py:306 (`_anchor(self, value, field)`)
Description: `field` parameter is unused at all three call sites.
Impact: implies per-field messaging that the envelope deliberately does not have.
Recommendation: drop the parameter.

Clarity Quality: EXCELLENT

## Stage 4 — EDGE CASES

Issues Found:

[EDGE-001] MEDIUM — tool_surface.py:575-578 (`_crop_box` page-frame fallback)
Description: the whole-page fallback indexes `cropbox[2]`/`[3]` after `frame.get("cropbox") or frame.get("source_dimensions") or [0, 0]`; a frame record carrying neither key yields the `[0,0]` default and `cropbox[2]` raises IndexError → `internal.error` envelope for what is a descriptor-shape issue.
Scenario: a recorded/third-party descriptor whose carrier/geometry.json frame lacks both keys (the surface explicitly supports recorded runs without word maps, so shape-lean frames are plausible).
Impact: misclassified outcome — the envelope contract reserves `error` for genuine internal faults; the typed refusal `crop.geometry-missing` exists for exactly this.
Recommendation: guard the fallback (`if len(cropbox) < 4: continue/fall through to None`) so the region resolves to the `crop.geometry-missing` refusal; add a bounds/reads test with a stubbed lean frame.

[EDGE-002] MEDIUM — tool_surface.py:364-370 (`_extract_source` completeness)
Description: any existing `workspace/runs/<digest16>` directory is accepted as a finished extraction (`if not target.is_dir()`); an `extract()` interrupted midway leaves a partial dir that then permanently refuses `source.unreadable` — `open()` binds nothing and nothing self-heals; only manual deletion recovers.
Scenario: process killed mid-extract (long carrier, Ctrl-C); retry hits the poisoned dir.
Impact: silent permanent refusal with no diagnostic distinguishing "unreadable source" from "interrupted extract".
Recommendation: treat a dir without `manifest.json` as incomplete — remove it and re-extract (`shutil.rmtree` + existing call, both inside the guarded try); test via a stubbed `digitization.native.extract` recording re-extraction.

Correctness note verified, no issue: cursor stale/invalid handling, ceil-consistent crop pixel estimate (`-(-w*dpi//72)`, matching the c0v poppler convention), digest pinning of descriptor/artifacts, atomic session persist via `os.replace`, idempotent propose/decide keyed by claim id, export never emitting rejected claims.

Edge Case Coverage: GOOD

## Stage 5 — EXCELLENCE

Final Polish Issues:

[EXCL-001] LOW — tool_surface.py `_word_entries` primary branch
Description: a word region whose locator no longer parses is dropped silently from `words` output when a word map exists.
Recommendation: acceptable as-is (total/count remain self-consistent and the descriptor is immutable); consider a `dropped_unlocatable` count in data for parity with zoom's `dropped_refs` honesty.

Excellence Assessment:
- Structure: EXCELLENT
- Correctness: GOOD
- Clarity: EXCELLENT
- Edge Cases: GOOD
- Overall: GOOD

Production Ready: WITH_NOTES (fix EDGE-001/EDGE-002 before relying on raw-source extraction and lean descriptors; the rest are cheap hardening)

## What's Working Well

1. Closed vocabulary assertion + no-message envelope by construction (`envelope()` docstring, tool_surface.py:117) — makes text-leakage structurally impossible, not just tested.
2. Untrusted-text confinement proven by a hostile-fixture suite (`tool_surface_fixtures.HOSTILE_TEXT` colliding with envelope field names) — defence-in-depth the design doc names explicitly.
3. Parity requirement implemented as a suite (`test_tool_surface_parity.py`), keeping the CLI adapter from drifting from the core.

## Top Findings

1. EDGE-001 (MEDIUM) — lean page-frame IndexError → `internal.error` instead of `crop.geometry-missing`.
   Fix: length-guard the fallback box.
2. EDGE-002 (MEDIUM) — partial extract dir poisons `open(source=...)` permanently.
   Fix: manifest-presence check + re-extract.
3. CORR-001 (LOW) — unvalidated session claims restore.
   Fix: shape guard at both restore sites.

## Verdict

**READY** (pass) — 0 critical, 0 high; 2 medium + 4 low, all concrete and cheap to fix in the fix-review step.

**Rationale:** the surface's contract mechanics (envelope, vocabulary, confinement, idempotence, parity) are sound and well-tested; findings are boundary hardening, none affect claims integrity or text confinement.
