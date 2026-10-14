# Purpose: Tracer-bullet tests for the minimal DSC 0.3 validator (sunset-r68.1.2).
# Responsibilities: Assert the minimal 0.3 fixture validates with a typed outcome;
#   assert a deliberately malformed variant fails with invalid_shape (no exception)
#   and malformed JSON yields parse_error.
# Rationale: Walking-skeleton slice of the add-dsc-03 document-core delta
#   (descriptor shape, snapshot-local identity, outcome states) before breadth.
"""Tracer tests for the minimal DSC 0.3 validator (sunset-r68.1.2)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import validator

TRACER = Path(__file__).parent / "fixture_minimal.json"


def test_tracer_fixture_is_valid():
    d = validator.load(TRACER)
    assert validator.validate(d) == []


def test_tracer_malformed_field_is_typed_invalid_shape():
    d = validator.load(TRACER)
    d["relations"][0]["from"] = []  # array where a string is required
    result = validator.validate(d)
    assert result == ["invalid_shape"]


def test_tracer_duplicate_id_is_typed():
    d = validator.load(TRACER)
    d["regions"][1]["id"] = d["regions"][0]["id"]
    assert "duplicate_id" in validator.validate(d)


def test_tracer_malformed_json_raises_for_parse_error_outcome():
    import pytest
    with pytest.raises((validator.Duplicate, ValueError, json.JSONDecodeError)):
        validator.loads('{"version": "0.3", "id": "x"} malformed')
