# Brief: sunset-msj.3 — How-tos: integrate an implementation with DSC

## Why

Delegated to a subagent: bounded writing task over a known module surface
(adapters, report, conformance). The lead orchestrates the epic loop; inline
execution would chain past the ticket boundary. This page is the
implementation-facing bridge: after the tutorial, a reader needs the actual
recipes to adopt DSC with their own extractor.

## Ticket

- **ID**: sunset-msj.3 (claimed, in_progress)
- **Epic**: sunset-msj — consumer documentation suite
- **Diátaxis quadrant**: HOW-TO only (task-oriented, assumes tutorial done)

## Desired outcome

`docs/src/integrate.md` — four how-to recipes for an implementer who already
did `first-descriptor.md`:

1. **Adapt a real carrier into a 0.3 descriptor.** Recipe around
   `dsc03.adapters.describe_pdf(source_path, out_dir, page_texts=None,
   desc_suffix="")` and `dsc03.adapters.describe_epub(source_path,
   out_dir)`: what they require (real carrier bytes — synthetic descriptors
   do NOT count, per the module docstring), what they write
   (inventory.json/manifest.json artifacts under out_dir, pinned in the
   descriptor's profile declarations with kind/version/sha256), what
   page_texts means (extractor-snapshot provenance for the first-consumer
   demo pattern), and what "preserving source observations" means
   (per-page regions + text evidence + annotation bindings, coverage
   computed from actual bytes). Include a complete runnable example using a
   committed fixture from `fixtures/carriers/` (check the PII screening
   note in `fixtures/carriers/MANIFEST.org` and respect it: do not suggest
   running adapters on files outside the committed fixtures without the
   screening step).
2. **Run the conformance suite against your implementation.** Recipe around
   the tests under `tests/tracer/`: which test files cover which capability
   area, how to run them (`python3 -B -m pytest tests/tracer -q`), and what
   a passing run does and does NOT entitle you to claim.
3. **Read the four reports.** Recipe around `dsc03.report.assess(descriptor,
   resolved_profiles, registry, enumerator=None)` +
   `validator_reasons`/`interpret`: the four separate report kinds
   (schema / profile / source-coverage / interpretation), what each answers,
   and how to read a failure.
4. **Classify honestly.** Recipe around `dsc03.conformance.classify(suite)`:
   the suite keys (from the docstring: v02_fixtures, v03_schema,
   v03_profiles, v03_coverage, migration, adversarial_corpus,
   real_carriers, independent_readers, extractor_comparison,
   first_consumer_demo, native_output_baseline, demo_result), what labels
   come out, and the honest-claiming rules: labels are scoped; never claim
   real-carrier conformance from scripted machinery alone; recorded
   agent-executed deviations exist and a human pass supersedes (link
   status.md deviations section).

## Content rules

- Every code block complete and runnable from a fresh clone; commands must
  work — verify each one before committing.
- How-to voice: "To do X, do Y" — problem-oriented, minimal explanation
  (link back to `what-is-dsc.md` and forward to `reference.md` when the
  reader needs why or what).
- Terminology matches the specs and module docstrings exactly.
- Link the historical evidence pages (tracer-bullet.org,
  first-consumer-demo.org) only as "background" pointers, not required
  reading.

## Out of scope

- No changes to `dsc03/`, `openspec/`, `tests/tracer/`, fixtures.
- Reference index, llms.txt, for-agents (other tickets).
- No new machinery, no new fixtures.

## Exact files

- `docs/src/integrate.md` (new)
- `tests/docs/test_docs_links.py` — ONLY if the link-integrity test's
  in-progress expectations need updating (its scope permits this; keep the
  change minimal)

## Exact test/review commands

```
python3 -B -m pytest tests/docs -q      # link integrity + tutorial gate still pass
just spec-check                         # ALL GATES PASSED
```

## Completion criteria (runnable; exit 0 = done)

1. `python3 -B -m pytest tests/docs -q` → exit 0
2. `just spec-check` → prints `ALL GATES PASSED`
3. `test -f docs/src/integrate.md` → exit 0
4. `git log --oneline -1` shows the atomic commit for this ticket

## Follow-up threshold

If a recipe cannot be made runnable without code changes, or a documented
API turns out to be broken — STOP, commit progress, record the finding.

## Verifier evidence contract (wai-px4g)

Cite artifacts read + fresh test-run output before CONFIRM; otherwise
REVIEW_REQUIRED.

## Spawn model

- Model: current session default.
- Context ceiling: ≤ 40% at spawn.
- Wall-clock budget: `timeout 45m`.
