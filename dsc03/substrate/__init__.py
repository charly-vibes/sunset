# Purpose: Substrate gate harness package for restore-document-substrate
#   (sunset-7hs, Stage B consumer harness).
# Responsibilities: Host the carrier oracles (oracles.py), the categorical law
#   checks and typed transformation algebra (laws.py), the second
#   independent reading path (reader_b.py), the assembly composition
#   (assembly.py), and the views/space/context law modules of the
#   composition slices (views.py, space.py, context.py — sunset-905.2);
#   tests live separately under tests/substrate/. Machinery-only: no
#   real-carrier or human-review conformance claims are made anywhere in
#   this package.
# Rationale: restore-document-substrate design Stage B calls for a separate
#   consumer harness maintaining the existing first-consumer tests; placing
#   the modules under dsc03 keeps the deployed-machinery imports (validator,
#   canonical, profiles, coverage, adapters, evidence, report) in one package
#   while the GATE layer stays a distinct tests/substrate/ suite.
"""Substrate gates: deterministic oracles + law checks + second reader."""
