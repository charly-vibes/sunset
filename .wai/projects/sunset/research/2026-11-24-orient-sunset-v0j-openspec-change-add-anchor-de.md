---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-v0j-anchor-derived-identity, pipeline-step:orient]
---

ORIENT: sunset-v0j = openspec change add-anchor-derived-identity tasks 2.1-2.4 (anchor tuple (source_sha256, record_kind, locator_path, profile_id, profile_version), id 'a:'+128-bit sha256 prefix of canonical JSON, IdentityRegistry collision refusal with witness naming both tuples, profiles 'identity' kind, validator identity_mismatch/identity_anchor_missing rule gated on declared identity profile, hard no-profile behavior unchanged). RED captured: tests/tracer/test_identity.py::test_two_independent_processes_derive_identical_ids fails, ModuleNotFoundError: dsc03.identity. Scope: dsc03/identity.py new, dsc03/profiles.py additive kind, dsc03/validator.py additive rule, tests/tracer/test_identity.py, tasks.md ticks.
