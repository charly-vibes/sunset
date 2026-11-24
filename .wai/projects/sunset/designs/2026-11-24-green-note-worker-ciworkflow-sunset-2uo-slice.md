---
tags: [pipeline-run:tdd-ro5-2026-11-24-ro5-review-fixes, pipeline-step:green]
---

GREEN note (worker CiWorkflow, sunset-2uo slice): wrote tests/tracer/env_pins.py (shared pin detection + SUNSET_STRICT_ENV gate) for the CI+env-pins ticket; predicates verified on canonical (poppler 26.01.0, tesseract 5.5.4+spa -> ok).

commands run:
- command=uv run python (env_pins predicates): poppler_status -> (True, 'pdftoppm 26.01.0 on PATH (pin 26.01.x)'), tesseract_status -> (True, "tesseract 5.5.4 with 'spa' pack"), native_toolchain_status -> (True, 'all pinned native tools present'), strict_env() -> False.
- command=uv run --with pyyaml python: parsed .github/workflows/ci.yml -> name ci, on push(main)+pull_request, jobs ['spec-check'] runs-on ubuntu-24.04, 12 SUNSET_* pins, 9 steps ending 'uv sync && just spec-check'.
- command=uv run pytest tests/tracer/test_reader_workspace.py -q -ra -> 2 skipped (reasons name playwright missing + canonical install path).
- command=uv run pytest tests/tracer/test_first_consumer_demo.py -q -> 18 passed (66.4s).
- command=uv run pytest tests/tracer/test_visual_calibration.py -q -> 7 passed (6.5s).
- command=SUNSET_STRICT_ENV=1 uv run pytest tests/tracer/test_visual_calibration.py tests/tracer/test_first_consumer_demo.py -q -> 25 passed (strict parity).
- command=SUNSET_STRICT_ENV=1 uv run pytest tests/tracer/test_reader_workspace.py -q -> 2 setup errors 'Failed: SUNSET_STRICT_ENV=1 (canonical CI): playwright is not installed...' (strict flip demonstrated).
- command=env PATH=<empty> uv run pytest tests/tracer/test_first_consumer_demo.py::TestExtractors -q -ra -> 3 skipped 'pinned native toolchain unavailable: poppler... tesseract not on PATH'; same under SUNSET_STRICT_ENV=1 -> 3 setup errors with strict prefix (both gate branches demonstrated).

verified: env gates skip-with-reason on stock/mismatched env and flip to failures under SUNSET_STRICT_ENV=1; the three touched suites are green on the canonical machine (18+7 passed, 2 reasoned skips); workflow YAML parses with the pinned poppler 26.01 / tesseract 5.3.4+spa / node 26.13.1 pins and runs spec-check via the justfile recipe. Poppler source-build step not compiled locally (no cmake; CI verify step asserts pins and fails loudly). Tests-pass oracle: the run-level gate for this step is owned by the orchestrator; my slice evidence is the targeted pytest above (validation run, non-code config for the workflow).

