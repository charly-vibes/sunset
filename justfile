# sunset — spec-corpus checks
# Purpose: Run the corpus gates and proposal composition regression.
# Responsibilities: Validate spec syntax, replacement semantics and frozen fixtures.
# Rationale: sunset-6pi found strict lint alone missed contradictory deltas.
#   Tracer-suite interpreter is overridable (sunset-5jo): machines without the
#   uv-managed venv pin their own via .env (SUNSET_PYTHON=...). The default is
#   the uv-managed .venv (sunset-olu): run `uv sync` once to populate it from
#   the committed uv.lock.

set dotenv-load

python := env_var_or_default("SUNSET_PYTHON", ".venv/bin/python")

# Python source for the page-key extraction shared by the digitization recipes
# below: print a recorded-config JSON's page keys as a numerically sorted,
# comma-separated list (argv[1] = config path). Each recipe wraps it in
# `-c '...'`; it holds no single quotes, so the shell quoting stays literal.
pages_py := 'import json,sys; print(",".join(sorted(json.load(open(sys.argv[1]))["pages"], key=int)))'

# Run all spec-corpus gates (OpenSpec strict validation + frozen 0.2 validator)
spec-check:
    @echo "==> spk lint (Specodelic layer of openspec/changes, incl. archive)"
    spk lint openspec/changes
    @echo "==> spk lint (Specodelic layer of deployed specs)"
    spk lint openspec/specs
    @echo "==> full test suite (pytest tests)"
    {{python}} -B -m pytest tests -q
    @echo "==> frozen 0.2 reference validator"
    python3 spec/document-model-specodelic-v3/validator.py test
    @echo "==> openspec 1.x strict validation (deployed specs + active changes, incl. deployed 0.3; validator pinned by versions.ddl.toml)"
    npx -y @fission-ai/openspec@1.14.2 validate --all --strict --no-interactive
    @echo "ALL GATES PASSED"

# Default: run every gate
default:
    @just spec-check

# Build + serve the human visual-review SPA over every recorded calibration
# example (sunset-e8t/sunset-fgg): side-by-side + overlay comparison of the
# claimed regions against pinned renders. Output is gitignored.
visual-review port="8123":
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .visual-review
    {{python}} -B -m dsc03.visual.review --out .visual-review/index.html --serve {{port}}

# Recorded digitization of a native-text PDF + its visual-review bundle
# (sunset-bv4): pymupdf text blocks become recorded detections/recognitions,
# the tested pipeline renders + exports the descriptor, and the review SPA
# presents the real extraction claims over pinned renders. Args:
# source output [pages] [port]. `pages` is an optional comma-separated 1-based
# list. `output` is the run directory (review lands at <output>/review.html);
# a trailing slash is stripped before deriving <output>-recorded.json. E.g.:
#   just digitization-review fixtures/carriers/cta-cte-propietario-redacted.pdf /tmp/cta-review
#   just digitization-review fixtures/carriers/cta-cte-propietario-redacted.pdf /tmp/cta-review 1,2 8124
digitization-review source output pages="" port="8124":
    #!/usr/bin/env bash
    set -euo pipefail
    src="{{source}}"; out="{{output}}"
    out="${out%/}"; cfg="${out}-recorded.json"
    page_flag=""
    [ -n "{{pages}}" ] && page_flag="--pages {{pages}}"
    {{python}} -B -m digitization.recorded_config --source "$src" --output "$cfg" $page_flag
    run_pages=$({{python}} -B -c '{{pages_py}}' "$cfg")
    {{python}} -B -m digitization run --source "$src" --pages "$run_pages" --config "$cfg" --output "$out"
    {{python}} -B -m dsc03.visual.review --descriptor "$out/descriptor.json" --out "$out/review.html" --serve {{port}}

# OCR ground-truth loop (sunset-9op): rasterize a text PDF to pixels, OCR the
# raster with pinned tesseract (spa), compare OCR regions against the native
# truth (IoU + text similarity measurement sheet), and serve the OCR claims
# in the review SPA over the rasterized render. Args: source output [pages]
# [port] [dpi]. `pages` is a comma-separated 1-based list (default: all).
# ocr_eval exit 2 = measured discrepancies (expected — that is the finding);
# any other nonzero exit aborts the recipe. E.g.:
#   just ocr-review fixtures/carriers/cta-cte-propietario-redacted.pdf /tmp/cta-ocr 1
ocr-review source output pages="" port="8125" dpi="200":
    #!/usr/bin/env bash
    set -euo pipefail
    src="{{source}}"; root="{{output}}"; dpi="{{dpi}}"
    page_flag=""; [ -n "{{pages}}" ] && page_flag="--pages {{pages}}"
    mkdir -p "$root"
    {{python}} -B -m digitization.rasterize --source "$src" --output-dir "$root/raster" --dpi "$dpi" $page_flag
    {{python}} -B -m digitization.recorded_config --source "$src" --output "$root/truth-config.json" --granularity lines $page_flag
    truth_pages=$({{python}} -B -c '{{pages_py}}' "$root/truth-config.json")
    {{python}} -B -m digitization run --source "$src" --pages "$truth_pages" --config "$root/truth-config.json" --output "$root/truth-run"
    {{python}} -B -m digitization.ocr_config --image-pdf "$root/raster/image.pdf" --pages-dir "$root/raster" --dpi "$dpi" $page_flag --output "$root/ocr-config.json"
    ocr_pages=$({{python}} -B -c '{{pages_py}}' "$root/ocr-config.json")
    {{python}} -B -m digitization run --source "$root/raster/image.pdf" --pages "$ocr_pages" --config "$root/ocr-config.json" --output "$root/ocr-run"
    set +e
    {{python}} -B -m digitization.ocr_eval --true "$root/truth-run/descriptor.json" --ocr "$root/ocr-run/descriptor.json" --output "$root/ocr-eval.json" --iou 0.5 >/dev/null
    eval_rc=$?
    set -e
    if [ "$eval_rc" -eq 2 ]; then
        echo "eval exit 2 (discrepancies measured — sheet at $root/ocr-eval.json)"
    elif [ "$eval_rc" -eq 0 ]; then
        echo "eval exit 0 (clean comparison — sheet at $root/ocr-eval.json)"
    else
        echo "ocr_eval failed with exit $eval_rc (expected 2 = discrepancies or 0 = clean; aborting)" >&2
        exit "$eval_rc"
    fi
    {{python}} -B -m dsc03.visual.review --descriptor "$root/ocr-run/descriptor.json" --out "$root/ocr-run/review.html" --serve {{port}}

# Typed agent tool surface gates (sunset-14b, add-agent-tool-surface task
# 5.3): parity + leakage + idempotence are the change's wired gates; the full
# suite target keeps the remaining surface suites one command away. These
# targets append to, and never reorder, the recipes above.
agent-surface-gate:
    @echo "==> agent tool surface: parity + leakage + idempotence"
    {{python}} -B -m pytest \
        tests/tracer/test_tool_surface_parity.py \
        tests/tracer/test_tool_surface_leakage.py \
        tests/tracer/test_tool_surface_idempotence.py -q

agent-surface-suite:
    @echo "==> agent tool surface: full suite"
    {{python}} -B -m pytest tests/tracer/test_tool_surface_envelope.py \
        tests/tracer/test_tool_surface_reads.py \
        tests/tracer/test_tool_surface_addressing.py \
        tests/tracer/test_tool_surface_idempotence.py \
        tests/tracer/test_tool_surface_leakage.py \
        tests/tracer/test_tool_surface_bounds.py \
        tests/tracer/test_tool_surface_export.py \
        tests/tracer/test_tool_surface_parity.py -q

# Prose gate (sunset-tur): sad flags in-code prose doing work the code should
# do. sad.toml excludes the preserved bundle (spec/) and tool-state dirs; the
# committed sad-baseline.json is shrink-only — new findings fail the gate.
sad-check:
    @echo "==> sad prose gate (baseline delta)"
    sad check --all
