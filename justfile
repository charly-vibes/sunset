# sunset — spec-corpus checks
# Purpose: Run the corpus gates and proposal composition regression.
# Responsibilities: Validate spec syntax, replacement semantics and frozen fixtures.
# Rationale: sunset-6pi found strict lint alone missed contradictory deltas.

# Run all spec-corpus gates (OpenSpec strict validation + frozen 0.2 validator)
spec-check:
    @echo "==> openspec strict validation (deployed specs, incl. deployed 0.3)"
    openspec validate --specs --strict --no-interactive
    @echo "==> spk lint (Specodelic layer of openspec/changes, incl. archive)"
    spk lint openspec/changes
    @echo "==> tracer suite (0.3 machinery, not real-carrier conformance)"
    python3 -B -m pytest tests -q
    @echo "==> frozen 0.2 reference validator"
    python3 spec/document-model-specodelic-v3/validator.py test
    @echo "ALL GATES PASSED"

# Pinned openspec 1.x check (sunset-rtl): deployed specs must also pass under
# @fission-ai/openspec@1.14.2. Change deltas are structurally blocked on the
# spk dual-format <-> openspec 1.x conflict (see docs/src/status.md) — specs
# only until spk accommodates 1.x delta rules.
spec-1x:
    npx -y @fission-ai/openspec@1.14.2 validate --specs --strict --no-interactive

# Default: run every gate
default:
    @just spec-check
