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

# Run all spec-corpus gates (OpenSpec strict validation + frozen 0.2 validator)
spec-check:
    @echo "==> openspec strict validation (deployed specs + active changes, incl. deployed 0.3)"
    openspec validate --all --strict --no-interactive
    @echo "==> spk lint (Specodelic layer of openspec/changes, incl. archive)"
    spk lint openspec/changes
    @echo "==> tracer suite (0.3 machinery, not real-carrier conformance)"
    {{python}} -B -m pytest tests -q
    @echo "==> frozen 0.2 reference validator"
    python3 spec/document-model-specodelic-v3/validator.py test
    @echo "==> openspec 1.x strict (same corpus, validator pinned by versions.ddl.toml)"
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
# presents the real extraction claims over pinned renders. `pages` is an
# optional comma-separated 1-based list. `output` is the run directory
# (review lands at <output>/review.html). E.g.:
#   just digitization-review pba-judicial-2026-07-29.pdf /tmp/pba-review 8124
digitization-review source output port="8124" pages="":
    #!/usr/bin/env bash
    set -euo pipefail
    src="{{source}}"; out="{{output}}"; cfg="{{output}}-recorded.json"
    page_flag=""
    [ -n "{{pages}}" ] && page_flag="--pages {{pages}}"
    {{python}} -B -m digitization.recorded_config --source "$src" --output "$cfg" $page_flag
    run_pages=$({{python}} -B -c "import json,sys; print(','.join(sorted(json.load(open(sys.argv[1]))['pages'], key=int)))" "$cfg")
    {{python}} -B -m digitization run --source "$src" --pages "$run_pages" --config "$cfg" --output "$out"
    {{python}} -B -m dsc03.visual.review --descriptor "$out/descriptor.json" --out "$out/review.html" --serve {{port}}

# OCR ground-truth loop (sunset-9op): rasterize a text PDF to pixels, OCR the
# raster with pinned tesseract (spa), compare OCR regions against the native
# truth (IoU + text similarity measurement sheet), and serve the OCR claims
# in the review SPA over the rasterized render. Args: source output [port]
# [pages] [dpi]. `pages` is a comma-separated 1-based list (default: all).
# Eval exit 2 = measured discrepancies (expected — that is the finding).
# E.g.: just ocr-review pba-judicial-2026-07-29.pdf /tmp/pba-ocr 8126 1
ocr-review source output port="8125" pages="" dpi="200":
    #!/usr/bin/env bash
    set -euo pipefail
    src="{{source}}"; root="{{output}}"; dpi="{{dpi}}"
    page_flag=""; [ -n "{{pages}}" ] && page_flag="--pages {{pages}}"
    mkdir -p "$root"
    {{python}} -B -m digitization.rasterize --source "$src" --output-dir "$root/raster" --dpi "$dpi" $page_flag
    {{python}} -B -m digitization.recorded_config --source "$src" --output "$root/truth-config.json" --granularity lines $page_flag
    truth_pages=$({{python}} -B -c "import json,sys; print(','.join(sorted(json.load(open(sys.argv[1]))['pages'], key=int)))" "$root/truth-config.json")
    {{python}} -B -m digitization run --source "$src" --pages "$truth_pages" --config "$root/truth-config.json" --output "$root/truth-run"
    {{python}} -B -m digitization.ocr_config --image-pdf "$root/raster/image.pdf" --pages-dir "$root/raster" --dpi "$dpi" $page_flag --output "$root/ocr-config.json"
    ocr_pages=$({{python}} -B -c "import json,sys; print(','.join(sorted(json.load(open(sys.argv[1]))['pages'], key=int)))" "$root/ocr-config.json")
    {{python}} -B -m digitization run --source "$root/raster/image.pdf" --pages "$ocr_pages" --config "$root/ocr-config.json" --output "$root/ocr-run"
    set +e
    {{python}} -B -m digitization.ocr_eval --true "$root/truth-run/descriptor.json" --ocr "$root/ocr-run/descriptor.json" --output "$root/ocr-eval.json" --iou 0.5 >/dev/null
    echo "eval exit $? (2 = discrepancies measured — sheet at $root/ocr-eval.json)"
    set -e
    {{python}} -B -m dsc03.visual.review --descriptor "$root/ocr-run/descriptor.json" --out "$root/ocr-run/review.html" --serve {{port}}
