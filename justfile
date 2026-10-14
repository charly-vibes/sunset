# sunset — spec-corpus checks
# Purpose: Run the corpus gates and proposal composition regression.
# Responsibilities: Validate spec syntax, replacement semantics and frozen fixtures.
# Rationale: sunset-6pi found strict lint alone missed contradictory deltas.

# Run all spec-corpus gates (OpenSpec strict validation + frozen 0.2 validator)
spec-check:
    @echo "==> openspec strict validation (deployed specs, incl. deployed 0.3)"
    openspec validate --specs --strict
    @echo "==> tracer suite (0.3 machinery, not real-carrier conformance)"
    python3 -B -m pytest tests -q
    @echo "==> frozen 0.2 reference validator"
    python3 spec/document-model-specodelic-v3/validator.py test
    @echo "ALL GATES PASSED"

# Default: run every gate
default:
    @just spec-check
