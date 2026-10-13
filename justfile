# sunset — spec-corpus checks
# The AGENTS.md-mandated gates, made executable. Run before committing.

# Run all spec-corpus gates (OpenSpec strict validation + frozen 0.2 validator)
spec-check:
    @echo "==> openspec strict validation (deployed specs)"
    openspec validate --specs --strict
    @echo "==> openspec strict validation (change add-dsc-03)"
    openspec validate add-dsc-03 --strict
    @echo "==> frozen 0.2 reference validator"
    python3 spec/document-model-specodelic-v3/validator.py test
    @echo "ALL GATES PASSED"

# Default: run every gate
default:
    @just spec-check
