# Purpose: RED-first tests for the typed agent tool surface envelope
#   (add-agent-tool-surface tasks 2.1-2.2): closed status vocabulary, stable
#   reason codes, unknown scope refused as a typed outcome — never an
#   exception.
# Responsibilities: Exercise sunset.tool_surface only, against real synthetic
#   carriers digitized through `digitization native`; agent-executed numbers.
"""Envelope vocabulary and typed-refusal tests (tasks 2.1, 2.2)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.tool_surface import REASONS, STATUSES, ToolSurface


ENVELOPE_KEYS = {"status", "reason", "data", "cursor", "provider_calls"}


def opened_workspace(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    surface = ToolSurface(ws)
    env = surface.open(run=str(run))
    assert env["status"] == "ok", env
    return surface, env


# -- 2.1 closed envelope ---------------------------------------------------------

def test_status_vocabulary_is_exactly_the_closed_set():
    assert tuple(STATUSES) == ("ok", "refused", "error")


def test_reason_vocabulary_is_closed_and_stable():
    assert tuple(REASONS) == tuple(sorted(REASONS))
    assert len(set(REASONS)) == len(REASONS)


def test_every_tool_returns_a_closed_envelope(tmp_path):
    surface, _ = opened_workspace(tmp_path)
    run = fx.plain_run(tmp_path)
    page = next(r["id"] for r in surface.descriptor["regions"]
                if r["kind"] == "page")
    calls = [
        ("open", {"run": str(run)}),
        ("words", {"scope": page}),
        ("crop", {"anchor": page}),
        ("zoom_in", {"scope": page}),
        ("zoom_out", {"scope": page}),
        ("queue", {}),
        ("export", {}),
    ]
    for tool, args in calls:
        env = getattr(surface, tool)(**args)
        assert set(env) - ENVELOPE_KEYS == set(), (tool, sorted(env))
        assert {"status", "reason", "data", "provider_calls"} <= set(env)
        assert env["status"] in STATUSES, (tool, env["status"])
        assert env["reason"] in REASONS, (tool, env["reason"])
        assert env["provider_calls"] == 0, tool
        json.dumps(env)  # envelope must be JSON-serializable


def test_envelope_has_no_message_field_even_on_refusals(tmp_path):
    surface, _ = opened_workspace(tmp_path)
    for env in (surface.words(scope="nope"),
                surface.decide(claim_id="c:" + "0" * 32, action="accept")):
        assert "message" not in env and "detail" not in env


# -- 2.2 unknown scope: typed refusal, never an exception -------------------------

def test_unknown_scope_returns_typed_refusal_on_every_addressed_tool(tmp_path):
    surface, _ = opened_workspace(tmp_path)
    ghost = "a:" + "0" * 32
    for env in (surface.words(scope=ghost),
                surface.zoom_in(scope=ghost),
                surface.zoom_out(scope=ghost),
                surface.crop(anchor=ghost)):
        assert env["status"] == "refused", env
        assert env["reason"] == "scope.unknown", env


def test_hostile_garbage_arguments_never_raise(tmp_path):
    surface, _ = opened_workspace(tmp_path)
    for bad in (None, 3, "", "page-1", "a:ZZZZ", "a:" + "g" * 32, []):
        for call in (lambda: surface.words(scope=bad),
                     lambda: surface.zoom_in(scope=bad),
                     lambda: surface.crop(anchor=bad)):
            env = call()  # must not raise
            assert env["status"] == "refused", (bad, env)


# -- session bounds ---------------------------------------------------------------

def test_tool_before_open_is_a_typed_refusal(tmp_path):
    surface = ToolSurface(tmp_path / "fresh-ws")
    env = surface.words(scope="a:" + "0" * 32)
    assert env["status"] == "refused"
    assert env["reason"] == "session.unopened"


def test_unreadable_run_and_source_are_typed_refusals(tmp_path):
    surface = ToolSurface(tmp_path / "ws")
    env = surface.open(run=str(tmp_path / "missing-run"))
    assert env == dict(env, status="refused", reason="source.unreadable")
    garbage = tmp_path / "garbage.pdf"
    garbage.write_bytes(b"not a pdf")
    env = surface.open(source=str(garbage))
    assert env["status"] == "refused"
    assert env["reason"] == "source.unreadable"


def test_open_reports_run_digest_and_scope_counts(tmp_path):
    surface, env = opened_workspace(tmp_path)
    data = env["data"]
    assert len(data["run_digest"]) == 64
    int(data["run_digest"], 16)  # hex digest
    assert data["pages"] == 3
    assert data["regions_by_kind"]["word"] > 0
    assert data["source_sha256"] == surface.manifest["source"]["sha256"]
