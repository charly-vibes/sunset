# Brief: sunset-msj.2 — Tutorial "emit and validate your first 0.3 descriptor"

## Why

Delegated to a subagent: self-contained writing + one small test file, with
clearly bounded machinery surface (dsc03.validator, one fixture). The lead
session is orchestrating the epic loop; inline execution would chain past
the ticket boundary. The tutorial is the main adoption on-ramp — it must
have a CI gate so its example can never silently rot.

## Ticket

- **ID**: sunset-msj.2 (claimed, in_progress)
- **Epic**: sunset-msj — consumer documentation suite
- **Diátaxis quadrant**: TUTORIAL only

## Desired outcome

`docs/src/first-descriptor.md` — a tutorial that takes a newcomer from zero
to a validated DSC 0.3 descriptor, using only what exists in this repo.
After it, the reader has: a descriptor file they created (or copied and
modified), knowledge of how to validate it, and a mental model of
views/regions/contents/evidence — sufficient to start `integrate.md`.

## Content requirements

1. **Prerequisites**: Python 3, clone of this repo. No installs (dsc03 is
   stdlib-only; state this).
2. **Walkthrough steps**, each with a verifiable outcome:
   - Look at the reference fixture `tests/tracer/fixture_minimal.json`
     (link it) — explain each top-level array briefly: version/id/source,
     views, regions, contents, relations, evidence (verify against the
     actual fixture fields; do not invent field names — read the fixture
     and `dsc03/validator.py`).
   - Create a minimal descriptor of your own (complete JSON the reader can
     copy-paste; model it on the tracer fixture — keep it SMALL and valid;
     you MUST verify it validates before committing, see gate below).
   - Validate it with the documented command, e.g.
     `python3 -c "from dsc03 import validator; import sys; d=validator.load('my-descriptor.json'); print(validator.validate(d))"`
     — adapt to the real API after reading `dsc03/validator.py` and
     `tests/tracer/test_tracer_validate.py`; the printed outcome must be
     explained (empty list = valid; typed outcomes like `invalid_shape`,
     `parse_error` for failures — show one deliberate failure and its
     typed outcome, then fix it).
   - Point to what comes next: adapting real carriers (`integrate.md`,
     in progress) and the reference index.
3. **Terminology**: match the specs exactly (view, region, content,
   relation, evidence, selector); no synonyms.
4. Link back to `what-is-dsc.md` for orientation (it already links here).

## Hard constraints

- Single quadrant: tutorial voice, imperative steps, no explanation
  digressions longer than a sentence or two (link to explanation page).
- Complete runnable code only — every command must work from a fresh clone.
- No modification outside: `docs/src/first-descriptor.md`,
  `tests/docs/test_tutorial_example.py` (new), and at most one link line in
  `docs/src/reference.md`/`docs/src/what-is-dsc.md` if needed (prefer NOT
  touching them; the existing "(in progress)" links already point here).
- The example descriptor embedded in the page MUST be the same one the
  gate test validates (single source of truth — see test shape).

## Gate test shape (write the test FIRST — TDD red)

`tests/docs/test_tutorial_example.py`:
- Parse `docs/src/first-descriptor.md` and extract fenced ```json blocks.
- Assert exactly one is tagged/identifiable as the tutorial descriptor
  (e.g. the block containing `"version": "0.3"` — pick a robust rule and
  document it in the test docstring).
- Assert `dsc03.validator.validate(validator.load(<parsed dict>)) == []`
  using the real API (import via the same sys.path trick as
  `tests/tracer/test_tracer_validate.py`).
- RED: write test, run `python3 -B -m pytest tests/docs -q` → fails
  (page missing or descriptor invalid). Commit RED.
- GREEN: write the page with a valid descriptor; test passes. Commit GREEN.

## Out of scope

- The link-integrity test in `tests/docs/test_docs_links.py` may need its
  forward-link expectation updated (it currently expects
  `first-descriptor.md` to be linked as "(in progress)") — updating that
  expectation is ALLOWED and expected; that is its only permitted change.
- adapters/coverage/evidence deep-dives, reference index, for-agents,
  llms.txt (other tickets).
- Any change to `dsc03/`, `openspec/`, or the preserved bundle.

## Exact files

- `tests/docs/test_tutorial_example.py` (new, committed first — RED)
- `docs/src/first-descriptor.md` (new, second — GREEN)
- `tests/docs/test_docs_links.py` (only the forward-link expectation)

## Exact test/review commands

```
python3 -B -m pytest tests/docs -q      # all pass (RED first, then GREEN)
just spec-check                         # ALL GATES PASSED
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests/docs -q` → exit 0
2. `just spec-check` → prints `ALL GATES PASSED`
3. `test -f docs/src/first-descriptor.md` → exit 0
4. `git log --oneline -2` shows the RED commit then the GREEN commit

## Follow-up threshold

If the real validator API cannot express the tutorial flow without code
changes, or the embedded descriptor needs fixture files that don't exist —
STOP, commit progress, record the finding in the report.

## Verifier evidence contract (wai-px4g)

The verify session must cite the artifacts it read and include fresh
test-run output before recording CONFIRM; otherwise REVIEW_REQUIRED.

## Spawn model

- Model: current session default.
- Context ceiling: ≤ 40% of the actual model window at spawn.
- Wall-clock budget: `timeout 45m`.
