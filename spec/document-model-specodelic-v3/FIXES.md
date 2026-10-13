# Rule of 5 — 20 finding dispositions

These are specification/design fixes, not a claim of full implementation validation.

- **DRAFT-001:** CONTRACT.md defines fields, cardinalities, namespaces, exact canonicalization and reference validator.
- **DRAFT-002:** JSON is mandatory structured baseline; other adapter conformance is individually optional and coverage missing is explicit.
- **DRAFT-003:** Region.view physical/logical; realizes relates them.
- **CORR-001:** Core guards now any_core_check_fails vs all_core_checks_pass.
- **CORR-002:** Carrier dispatcher selects applicable adapter; outcome guards reflect conditions.
- **CORR-003:** Evidence states reflect actual support/conflict/replay predicates.
- **CORR-004:** Interpretation no longer requires edition equivalence; suite status separate from per-instance.
- **CORR-005:** Concrete fixture paths and validator predicates replace English tautologies, subject to coverage limitations.
- **CORR-006:** Unique root, exactly one parent, DAG generator ordering defined.
- **CLAR-001:** IDs snapshot-scoped and canonical UTF-8 JSON precisely restricted.
- **CLAR-002:** Source digest, adapter/version/config/dependencies and preservation profiles required.
- **CLAR-003:** No implicit cross-edition equivalence; explicit projection/comparator required.
- **EDGE-001:** Hybrid per-observation source/evidence permitted; mixed PDF fixture.
- **EDGE-002:** EPUB spine-linear/nonlinear, navigation/visual order separated; full adapter pending.
- **EDGE-003:** Human assertion without evidence explicit; conflicting claims coexist.
- **EDGE-004:** Content shared with has-content; physical/logical realizations.
- **EDGE-005:** Negative fixtures for graph errors; additional real carrier fault fixtures pending.
- **EXCL-001:** Instance result and suite completeness separated.
- **EXCL-002:** Valid two-region descriptor, invalid dangling descriptor and canonical roundtrip checks.
- **EXCL-003:** Category theoretic motivation explicitly non-normative.

## Remaining validation debt
Real native PDF/EPUB/scanned inputs, malformed input/geometry/bidi fixtures, second independent implementation, formal equivalence comparators, and Specodelic CLI lint remain unverified or unimplemented. These are explicit scope limitations rather than concealed successes.
