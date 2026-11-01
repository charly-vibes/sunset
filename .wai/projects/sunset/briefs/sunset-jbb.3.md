# sunset-jbb.3 — Retain partial native results and refuse invalid PDF inputs safely

## Why
The owner requested Codex gpt-6-luna implementation subagents and wai orchestration.
This vertical slice builds on the verified preceding child, not a separate layer.
Read bd show sunset-jbb.3 and openspec/changes/add-native-pdf-extraction/design.md.

## Outcome and files
## Traceability
add-native-pdf-extraction:1.3; parent sunset-jbb. Owner approved completing all slices with codex gpt-6-luna. Native-only local processing; independent of sunset-rmx OCR approvals.

## Outcome and acceptance
Through native/inspect, retain usable text while declaring scanned/textless pages and unsupported raster features. A native text layer does not prove full visual coverage; even empty text is unexamined, not proof of blankness. Selected pages exclude other pages explicitly. Test malformed/encrypted input, missing file, out-of-range/duplicate/invalid page selections and existing output (including empty directories); refuse before output creation or overwrite. Stable status/reason and nonzero exit; no tracebacks for expected failures. Support partial zero-text results and read-only inspection with no OCR fallback.

## Must and Meter
Must: 1 complete fresh-process public CLI extraction/inspection journey passes; all listed boundary fixtures pass; 0 OCR/model/network calls; 0 source mutations or existing-file overwrites; descriptor validation and inspection integrity pass. Meter: `/tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_partial.py -q`. The proposed test file is created by this ticket; it is expected absent at base_commit. Regression: `PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 npm_config_cache=/tmp/sunset-native-pdf-npm-cache just spec-check`.

## Files and coordination
Intended paths: digitization/native.py, digitization/__main__.py, digitization/inspection.py, tests/tracer/test_digitization_native_partial.py. Shared native/CLI/inspection files are intentionally sequentially owned across children; re-read previous slice and reanchor base_commit/digests before claiming. Update ownership metadata if implementation requires existing helpers.

## TDD and handoff
Define known-input expected-output fixtures first; run RED and capture actual failure, implement minimal GREEN, and capture fresh passing test output. New source/test files require Purpose/Responsibilities/Rationale headers; update headers where contracts change. Any optional refactor is a separate ticket. No weakening prior assertions or manufacturing provenance. Runtime work only after baseline gate understood. No commits, pushes, remote services, packaging, core wire changes, frozen validator/bundle edits or publishing pba-judicial-2026-07-29.pdf. Synthetic/generated or redistributable test PDFs only. Report exact files, RED/GREEN commands/output and limitations to the lead; lead verifies before closing.


## Completion criteria
PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 /tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_partial.py -q
PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 /tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_basic.py tests/tracer/test_digitization_first_page.py -q
git diff --check

## Spawn model
gpt-6-luna through Codex collaboration, fork_turns none. Context ceiling ≤35%
of actual model window (do not invent fixed window size). Budget 20 minutes.

## Evidence contract
Start with failing behavioral tests; append actual RED/GREEN outputs and progress
to .wai/projects/sunset/logs/sunset-jbb.3.log. Write final report with read artifact
paths, files, commands/output and limitations to
.wai/projects/sunset/research/sunset-jbb.3-report.org. Reports are claims; lead reads
code and reruns tests. Stop after two unresolved fix attempts for same failure.
Do not close issues, advance wai, commit, push or spawn agents. Do not touch
whisper files, owner PDF or frozen bundle. Existing source work is shared and
must be preserved. Use PATH prefix on all test/CLI runs so child python3 gets the
pinned environment. PyMuPDF1.28.2 and pytest installed only in /tmp env.
Lead owns full just spec-check after all focused slices; do not repeatedly run
expensive OCR suites unless a new relevant regression justifies it.
