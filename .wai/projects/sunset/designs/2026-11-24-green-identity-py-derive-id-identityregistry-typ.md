---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-v0j-anchor-derived-identity, pipeline-step:green]
---

GREEN: identity.py derive_id/IdentityRegistry (typed outcomes ('derived',id)/('invalid_anchor',reason)/('collision',{id,witness})); canonical JSON matches canonical.py form; default digest sha256->bytes (py3.15 HASH lacks .hex()); profiles IMPLEMENTED_KINDS+='identity' with artifact grammar {kind:'identity',version,digest:{algorithm:'sha256',truncation_bits:128,prefix:'a:'}}; validator PROFILE_KINDS+='identity', FIELD_SPECS optional anchor on regions/contents/selectors/evidence, _is_text_content tolerates anchor key, rule after evidence-lineage: >1 identity profile -> invalid_profile; anchor absent -> identity_anchor_missing; malformed -> invalid_shape; id != derive_id(source_sha[, selector own] , section-singular record_kind, locator_path, profile id+version) -> identity_mismatch. Tests: 22 passed tests/tracer/test_identity.py; regression 12 passed test_tracer_validate + test_profile_resolution. Mid-run fixes: selector records must KEEP own source_sha256 (builder was popping it -> invalid_shape), collision test switched to birthday scan (fixed-target 16-bit search expected <1 hit in 1000 draws).

## Verification evidence

- RED (pre-implementation): `.venv/bin/python -B -m pytest tests/tracer/test_identity.py -q` -> `1 failed in 0.11s`, subprocess exit 1 `ModuleNotFoundError: No module named 'dsc03.identity'`.
- RED for 2.2b/2.4 (kind + rule not yet implemented): same command -> `8 failed, 13 passed` (unsupported_profile; invalid_profile/invalid_shape).
- GREEN narrow: `.venv/bin/python -B -m pytest tests/tracer/test_identity.py -q` -> `22 passed in 0.08s`.
- Regression: `.venv/bin/python -B -m pytest tests/tracer/test_tracer_validate.py tests/tracer/test_profile_resolution.py -q` -> `12 passed in 0.04s`.
Commands run (recorded in this artifact above):
