# Purpose: Honest conformance label classification (sunset-r68.10, tasks.md 5.3).
# Responsibilities: Map what a test suite actually exercised to report labels —
#   0.2-fixture-only suites claim 0.2 coverage only; 0.3 contract suites without
#   real carriers, the adversarial corpus, two independent readers, or a declared
#   extractor comparison are "incomplete" and never claim real-carrier
#   conformance; workflow benefit stays "unproven" without the first-consumer
#   demonstration and native-output baseline; a demonstration that passes all
#   functional gates claims traceability, and claims speed only when review time
#   did not increase.
# Rationale: add-dsc-03 document-conformance "No false claims", "Reader
#   independence", "First-consumer demonstration". Label logic only — the
#   underlying checks live in the other dsc03 modules and future suites.
"""Conformance labels: classify a suite; never overclaim."""


def classify(suite):
    """Classify a suite description into honest report labels.

    suite keys (all optional, defaulting to False/0): v02_fixtures, v03_schema,
    v03_profiles, v03_coverage, migration, adversarial_corpus, real_carriers,
    independent_readers (int), extractor_comparison, first_consumer_demo,
    native_output_baseline, demo_result ({functional_gates_passed, review_time_delta}).
    """
    suite = dict(suite)
    claims = []
    if suite.get("v02_fixtures"):
        claims.append("0.2 fixture coverage")
    contract = all([
        suite.get("v03_schema"), suite.get("v03_profiles"), suite.get("v03_coverage"),
    ])
    if contract:
        claims.append("0.3 contract validation")
    if suite.get("migration"):
        claims.append("0.2-to-0.3 migration")

    missing = []
    if suite.get("real_carriers"):
        if not suite.get("adversarial_corpus"):
            missing.append("adversarial corpus")
        if suite.get("independent_readers", 0) < 2:
            missing.append("two independent readers")
        if not suite.get("extractor_comparison"):
            missing.append("declared extractor comparison")
    elif contract or suite.get("adversarial_corpus"):
        missing.append("real PDF/EPUB carrier fixtures")

    real_carrier_conformance = not missing and bool(
        suite.get("real_carriers") and suite.get("adversarial_corpus")
        and suite.get("independent_readers", 0) >= 2 and suite.get("extractor_comparison")
    )
    if real_carrier_conformance:
        claims.append("real-carrier conformance")

    workflow_benefit = "unproven"
    if suite.get("first_consumer_demo") and suite.get("native_output_baseline"):
        result = suite.get("demo_result") or {}
        if result.get("functional_gates_passed"):
            slower = (result.get("review_time_delta") or 0) > 0
            workflow_benefit = {
                "traceability": "demonstrated",
                "speed": "not claimed" if slower else "demonstrated",
            }
        else:
            workflow_benefit = {"traceability": "failed", "speed": "not claimed"}

    status = "complete" if real_carrier_conformance and not missing else "incomplete"
    return {
        "status": status,
        "claims": claims,
        "missing": missing,
        "real_carrier_conformance": real_carrier_conformance,
        "workflow_benefit": workflow_benefit,
    }
