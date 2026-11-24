---
tags: [pipeline-run:tdd-ro5-2026-11-24-sunset-c6i-identity-migration-assembly, pipeline-step:red]
---

RED: command=.venv/bin/python -B -m pytest tests/tracer/test_identity_migration.py tests/substrate/test_assembly_laws.py -q. Expected failures confirmed: (1) migration tests error at collection — AttributeError dsc03.migrate has no attribute IDENTITY_PROFILE_ID (migrate_to_identity + identity constants unimplemented); (2) TestCanonicalOrderUnderIdentityProfile::test_compose_is_commutative_under_identity_profile fails — canonically_equal(compose(a,b), compose(b,a)) is False under identity profiles (no ordering regime in compose). Label-id left-first backstop test PASSES unchanged (10 passed).
