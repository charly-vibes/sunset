# Purpose: Separate outcome reports for one descriptor run (sunset-r68.8, tasks.md 3.3).
# Responsibilities: dsc03.report.assess produces four independent outcomes — schema
#   validity, per-profile resolution, source coverage, and interpretive assessment
#   (annotation statuses; assessment "unverifiable" is an external report outcome,
#   never a descriptor status); asserts valid-schema/failed-coverage stays
#   separated and supported/disputed claims are not promoted by schema validity.
# Rationale: add-dsc-03 document-adapters "Partial results carry loss accounting"
#   and document-semantics "Source observations vs claims".
"""Separate schema/profile/coverage/interpretation reports (sunset-r68.8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import profiles, report, validator
from test_coverage import full_pages, pdf_descriptor, PROFILES, TRACER, enumerated, resolve

REGISTRY = profiles.Registry(PROFILES.parent)  # fixture URIs are relative to tests/tracer


def assess(d, enum=enumerated):
    return report.assess(d, resolve(d), REGISTRY, enum)


def test_schema_and_coverage_are_separate_outcomes():
    d = pdf_descriptor(full_pages(glyph_status="omitted"))
    r = assess(d)
    assert r["schema"] == {"status": "valid", "reasons": []}
    assert r["profiles"] == {"status": "resolved", "unresolved": []}
    assert r["coverage"]["summaries"]["pdf:glyphs"] == "omitted"
    assert r["interpretation"]["counts"]["supported"] == 0  # nothing auto-promoted


def test_valid_schema_with_failed_coverage_stays_invalid_only_in_coverage():
    # manifest version drift: schema-clean, coverage-invalid
    d = pdf_descriptor(full_pages())
    resolved = resolve(d)
    resolved["p-man"][1]["version"] = "2"
    r = report.assess(d, resolved, REGISTRY, enumerated)
    assert r["schema"]["status"] == "valid"
    assert "invalid_coverage" in r["coverage"]["reasons"]
    assert r["coverage"]["status"] == "invalid"


def test_schema_failure_does_not_run_coverage():
    d = pdf_descriptor(full_pages())
    d["relations"][0]["from"] = []  # malformed field type
    r = report.assess(d, {}, REGISTRY, enumerated)
    assert r["schema"]["status"] == "invalid"
    assert "invalid_shape" in r["schema"]["reasons"]
    assert r["coverage"]["status"] == "skipped"


def test_unresolved_profile_is_reported_independently():
    d = pdf_descriptor(full_pages())
    r = assess(d)
    # tamper: point the selector profile at missing bytes
    resolved = resolve(d)
    resolved["p-sel"] = ("unsupported_profile", None)
    r2 = report.assess(d, resolved, REGISTRY, enumerated)
    assert r2["profiles"]["unresolved"] == ["p-sel"]
    assert r2["coverage"]["status"] == "skipped"  # cannot verify without inventory


def test_annotation_statuses_are_reported_not_promoted():
    d = pdf_descriptor(full_pages())
    r = assess(d)
    # the tracer's annotation is asserted_without_evidence -> unverifiable
    assert r["interpretation"]["by_annotation"] == {"a-note": "unverifiable"}
    assert r["interpretation"]["counts"]["supported"] == 0
    assert r["interpretation"]["counts"]["disputed"] == 0
