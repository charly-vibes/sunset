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
