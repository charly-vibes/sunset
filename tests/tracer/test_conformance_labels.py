# Purpose: Conformance label tests — incomplete suites never claim 0.3 or
#   real-carrier conformance (sunset-r68.10, tasks.md 5.3).
# Responsibilities: dsc03.conformance.classify maps a description of what a test
#   suite actually exercised to honest labels: 0.2-fixture-only suites claim 0.2
#   coverage only; 0.3 contract suites without real carriers, two independent
#   readers, a declared extractor comparison, or the adversarial corpus report
#   "incomplete"; workflow benefit stays "unproven" without the first-consumer
#   demonstration and native-output baseline; a demonstration that passes
#   functional gates but slows review claims traceability, not speed.
# Rationale: add-dsc-03 document-conformance "No false claims", "Reader
#   independence", "First-consumer demonstration".
"""Conformance label classification tests (sunset-r68.10)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import conformance


def test_v02_only_suite_claims_v02_only():
    r = conformance.classify({"v02_fixtures": True})
    assert r["status"] == "incomplete"
    assert r["claims"] == ["0.2 fixture coverage"]
    assert "0.3 contract validation" not in r["claims"]
    assert r["real_carrier_conformance"] is False


def test_v03_contract_suite_without_carriers_is_not_real_carrier_conformance():
    r = conformance.classify({
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "migration": True,
    })
    assert r["status"] == "incomplete"
    assert r["real_carrier_conformance"] is False
    assert "0.3 contract validation" in r["claims"]


def test_missing_second_reader_is_incomplete():
    base = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "extractor_comparison": True,
    }
    r = conformance.classify({**base, "independent_readers": 1})
    assert r["status"] == "incomplete"
    assert "two independent readers" in r["missing"]


def test_missing_extractor_comparison_is_incomplete():
    base = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2,
    }
    r = conformance.classify(base)
    assert r["status"] == "incomplete"
    assert "declared extractor comparison" in r["missing"]


def test_missing_corpus_or_carriers_is_incomplete():
    base = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "independent_readers": 2, "extractor_comparison": True,
    }
    r = conformance.classify({**base, "adversarial_corpus": True, "real_carriers": False})
    assert r["status"] == "incomplete"
    r2 = conformance.classify({**base, "adversarial_corpus": False, "real_carriers": True})
    assert r2["status"] == "incomplete"


def test_full_conformance_requires_everything():
    r = conformance.classify({
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "migration": True, "adversarial_corpus": True,
        "real_carriers": True, "independent_readers": 2, "extractor_comparison": True,
    })
    assert r["status"] == "complete"
    assert r["real_carrier_conformance"] is True


def test_workflow_benefit_unproven_without_demo_and_baseline():
    full = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2, "extractor_comparison": True,
    }
    r = conformance.classify(full)
    assert r["workflow_benefit"] == "unproven"
    r2 = conformance.classify({
        **full, "first_consumer_demo": True, "native_output_baseline": True,
        "demo_result": {"functional_gates_passed": True, "review_time_delta": -0.1},
    })
    assert r2["workflow_benefit"] == {"traceability": "demonstrated", "speed": "demonstrated"}


def test_slower_review_claims_traceability_not_speed():
    full = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2, "extractor_comparison": True,
        "first_consumer_demo": True, "native_output_baseline": True,
        "demo_result": {"functional_gates_passed": True, "review_time_delta": 0.3},
    }
    r = conformance.classify(full)
    assert r["workflow_benefit"] == {"traceability": "demonstrated", "speed": "not claimed"}


def test_failed_functional_gates_fail_the_demo():
    full = {
        "v02_fixtures": True, "v03_schema": True, "v03_profiles": True,
        "v03_coverage": True, "adversarial_corpus": True, "real_carriers": True,
        "independent_readers": 2, "extractor_comparison": True,
        "first_consumer_demo": True, "native_output_baseline": True,
        "demo_result": {"functional_gates_passed": False, "review_time_delta": -1.0},
    }
    r = conformance.classify(full)
    assert r["workflow_benefit"]["traceability"] == "failed"
