# sunset-jbb.1 — Native PDF baseline

## Why
The owner requested gpt-6-luna subagents implementing each vertical slice while
the lead runs wai orchestration and fresh verification. Read bd show sunset-jbb.1
and openspec/changes/add-native-pdf-extraction/{proposal,design}.md first.

## Outcome
Implement public `python3 -m digitization native --source PDF --output NEW_DIR`
with optional `--pages 2,3` (defaults all) and existing inspect command. Generated
simple two-page PDF → raw/search text, valid DSC, word and line mappings with
source hash/page/frame/box and exact raw offsets. Retain extractor provenance
and config pinning, 0 OCR/network/model calls. Record adapter/helper reuse decision.
Do not disguise extracted text as recorded OCR/provider observations. Native run
artifacts may use a dedicated mode/schema if existing recorded invariants require
it; integrate inspection routing safely. Existing recorded tests must still pass.

## Files
Own digitization/native.py, digitization/__main__.py,
digitization/inspection.py, tests/tracer/test_digitization_native_basic.py.
Update metadata through lead if scope needs to expand. Reuse dsc03 adapters,
profiles/locators and artifact helpers where correct. Avoid speculative frameworks.
The next child owns complex layout and Unicode; next partiality; last replay and
repeatability. Basic implementation must permit later strengthening.

## TDD
Write meaningful fresh-process behavioral tests first; capture actual RED output
in .wai/projects/sunset/logs/sunset-jbb.1.log, then implement minimal GREEN.
New/contract-changed sources/tests need Purpose/Responsibilities/Rationale headers.
Optional tidy refactors require separate tickets. No commits, pushes, fixture
publication, remote service, frozen-validator/core-wire/bundle edits or subagents.
Do not edit the unrelated whisper files or owner PDF. Do not close tracker issues
or advance wai; lead owns orchestration. User approved all slices; no routine
confirmation needed. If baseline environment fails, report instead of weakening tests.

## Completion criteria
/tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_basic.py -q
/tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_first_page.py -q
git diff --check

## Spawn model
gpt-6-luna through Codex collaboration; fresh context (fork_turns none).
Context ceiling ≤ 35% of the actual model window; report before reaching it,
without inventing an absolute window size. Wall-clock budget 20 minutes.

## Evidence contract
Write .wai/projects/sunset/research/sunset-jbb.1-report.org with exact RED/GREEN
commands/output, files changed, reuse rationale and known limitations. Append
progress/evidence to .wai/projects/sunset/logs/sunset-jbb.1.log. Final report
must cite actual artifacts; lead reruns tests and inspects code before closure.
