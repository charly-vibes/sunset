# sunset-jbb.4 — Reproduce and replay native extraction and document the usable journey

## Why
The owner requested Codex gpt-6-luna implementation subagents and wai orchestration.
This vertical slice builds on the verified preceding child, not a separate layer.
Read bd show sunset-jbb.4 and openspec/changes/add-native-pdf-extraction/design.md.

## Outcome and files
## Traceability
add-native-pdf-extraction:1.4; parent sunset-jbb. Owner approved completing all slices with codex gpt-6-luna. Native-only local processing; independent of sunset-rmx OCR approvals.

## Outcome and acceptance
Two fresh public native runs over identical PDF bytes under pinned settings/dependencies produce byte-identical declared semantic artifacts (DSC, raw/search text, source maps, pinned profiles/config), independent of source filename/location and output path; run IDs/timestamps/timing stay only in execution envelopes. Add native support to existing public replay/resume routes as needed; offline replay verifies digests and reconstructs selected artifacts with zero extraction/OCR/network calls. Tamper/missing-artifact refusal and read-only inspect. Document actual native/inspect/replay commands with expected output and exit codes, update README/status/explanation to distinguish implemented baseline from remaining OCR work. Run local owner PDF smoke without publishing it.

## Must and Meter
Must: 1 complete fresh-process public CLI extraction/inspection journey passes; all listed boundary fixtures pass; 0 OCR/model/network calls; 0 source mutations or existing-file overwrites; descriptor validation and inspection integrity pass. Meter: `/tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_replay.py -q`. The proposed test file is created by this ticket; it is expected absent at base_commit. Regression: `PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 npm_config_cache=/tmp/sunset-native-pdf-npm-cache just spec-check`.

## Files and coordination
Intended paths: digitization/native.py, digitization/replay.py, digitization/__main__.py, digitization/inspection.py, tests/tracer/test_digitization_native_replay.py, README.md, docs/src/digitization.org, docs/src/status.md, docs/src/what-is-dsc.md. Shared native/CLI/inspection files are intentionally sequentially owned across children; re-read previous slice and reanchor base_commit/digests before claiming. Update ownership metadata if implementation requires existing helpers.

## TDD and handoff
Define known-input expected-output fixtures first; run RED and capture actual failure, implement minimal GREEN, and capture fresh passing test output. New source/test files require Purpose/Responsibilities/Rationale headers; update headers where contracts change. Any optional refactor is a separate ticket. No weakening prior assertions or manufacturing provenance. Runtime work only after baseline gate understood. No commits, pushes, remote services, packaging, core wire changes, frozen validator/bundle edits or publishing pba-judicial-2026-07-29.pdf. Synthetic/generated or redistributable test PDFs only. Report exact files, RED/GREEN commands/output and limitations to the lead; lead verifies before closing.


## Completion criteria
PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 /tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_replay.py -q
PATH=/tmp/sunset-native-venv/bin:$PATH OMP_THREAD_LIMIT=1 /tmp/sunset-native-venv/bin/python -B -m pytest tests/tracer/test_digitization_native_basic.py tests/tracer/test_digitization_first_page.py -q
git diff --check

## Spawn model
gpt-6-luna through Codex collaboration, fork_turns none. Context ceiling ≤35%
of actual model window (do not invent fixed window size). Budget 20 minutes.

## Evidence contract
Start with failing behavioral tests; append actual RED/GREEN outputs and progress
to .wai/projects/sunset/logs/sunset-jbb.4.log. Write final report with read artifact
paths, files, commands/output and limitations to
.wai/projects/sunset/research/sunset-jbb.4-report.org. Reports are claims; lead reads
code and reruns tests. Stop after two unresolved fix attempts for same failure.
Do not close issues, advance wai, commit, push or spawn agents. Do not touch
whisper files, owner PDF or frozen bundle. Existing source work is shared and
must be preserved. Use PATH prefix on all test/CLI runs so child python3 gets the
pinned environment. PyMuPDF1.28.2 and pytest installed only in /tmp env.
Lead owns full just spec-check after all focused slices; do not repeatedly run
expensive OCR suites unless a new relevant regression justifies it.

## Lead review points carried from earlier slices
Native integrity currently loops over declared artifacts; require the full named
artifact set so removing word-map.json/raw.txt/etc from the manifest cannot evade
hash verification. Bind mode/version/source/config/descriptor/selected pages and
semantic artifact digest consistently. Reject path traversal, symlink escapes,
malformed manifest top-level types and malformed mappings with typed failures.
Check every word/line source_sha256 against retained source, nonnegative bounded
raw/search spans and matching frames; no zip truncation for short box arrays.
Treat these as integrity behavior tests in the replay/inspection journey, not
speculative security framework work. Existing recorded behavior must still pass.
