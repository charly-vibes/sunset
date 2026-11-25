# Purpose: RED-first gate tests for write-tool idempotence through claim ids
#   (add-agent-tool-surface task 3.2): repeating propose or decide leaves the
#   stored claim set unchanged and reports the claim as already present.
# Responsibilities: Exercise sunset.tool_surface propose/decide only;
#   assertions compare canonical claim-set snapshots across calls and across
#   separate ToolSurface instances bound to the same workspace.
"""Write-tool idempotence through claim ids (task 3.2, gate)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.tool_surface import ToolSurface


def opened(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    surface = ToolSurface(ws)
    assert surface.open(run=str(run))["status"] == "ok"
    return surface


def amount_spec(surface, value="9.999,00", origin="model:g"):
    p1 = next(r["id"] for r in surface.descriptor["regions"]
              if r["kind"] == "page"
              and re.fullmatch(r"page:1", r["anchor"]["locator_path"]))
    return {"type": "field:total", "anchors": [p1], "value": value,
            "origin": origin, "extractive": False}


def test_propose_admits_once_then_reports_already_present(tmp_path):
    surface = opened(tmp_path)
    spec = amount_spec(surface)
    first = surface.propose(spec=spec)
    assert first["status"] == "ok", first
    assert first["data"]["already_present"] is False
    claim_id = first["data"]["claim_id"]
    assert claim_id.startswith("c:")
    snapshot = fx.canonical(surface.claims)
    second = surface.propose(spec=dict(spec))
    assert second["status"] == "ok", second
    assert second["data"]["already_present"] is True
    assert second["data"]["claim_id"] == claim_id
    assert fx.canonical(surface.claims) == snapshot


def test_propose_distinct_values_admit_distinct_claims(tmp_path):
    surface = opened(tmp_path)
    a = surface.propose(spec=amount_spec(surface, value="9.999,00"))
    b = surface.propose(spec=amount_spec(surface, value="8.888,00"))
    assert a["data"]["claim_id"] != b["data"]["claim_id"]
    assert len(surface.claims) == 2


def test_decide_is_idempotent_through_claim_ids(tmp_path):
    surface = opened(tmp_path)
    proposed = surface.propose(spec=amount_spec(surface))
    claim_id = proposed["data"]["claim_id"]
    first = surface.decide(claim_id=claim_id, action="accept", reviewer="r1")
    assert first["status"] == "ok", first
    assert first["data"]["already_present"] is False
    snapshot = fx.canonical(surface.claims)
    second = surface.decide(claim_id=claim_id, action="accept", reviewer="r1")
    assert second["status"] == "ok", second
    assert second["data"]["already_present"] is True
    assert fx.canonical(surface.claims) == snapshot


def test_accept_and_reject_are_distinct_idempotent_claims(tmp_path):
    surface = opened(tmp_path)
    claim_id = surface.propose(
        spec=amount_spec(surface))["data"]["claim_id"]
    accept = surface.decide(claim_id=claim_id, action="accept")
    reject = surface.decide(claim_id=claim_id, action="reject")
    assert accept["data"]["claim_id"] != reject["data"]["claim_id"]
    again = surface.decide(claim_id=claim_id, action="reject")
    assert again["data"]["already_present"] is True
    assert again["data"]["claim_id"] == reject["data"]["claim_id"]
    assert len(surface.claims) == 3  # model + accept + reject


def test_decide_unknown_claim_and_action_are_typed_refusals(tmp_path):
    surface = opened(tmp_path)
    env = surface.decide(claim_id="c:" + "0" * 32, action="accept")
    assert env["status"] == "refused"
    assert env["reason"] == "claim.unknown"
    claim_id = surface.propose(
        spec=amount_spec(surface))["data"]["claim_id"]
    env = surface.decide(claim_id=claim_id, action="negate")
    assert env["status"] == "refused"
    assert env["reason"] == "action.unknown"


def test_claims_persist_across_surface_instances(tmp_path):
    ws = tmp_path / "ws"
    run = fx.plain_run(tmp_path)
    first = ToolSurface(ws)
    first.open(run=str(run))
    claim_id = first.propose(spec=amount_spec(first))["data"]["claim_id"]
    second = ToolSurface(ws)
    second.open(run=str(run))
    assert [c["id"] for c in second.claims] == [claim_id]
    repeat = second.propose(spec=amount_spec(second))
    assert repeat["data"]["already_present"] is True


def test_propose_refusal_admits_nothing(tmp_path):
    surface = opened(tmp_path)
    ghost = "a:" + "0" * 32
    spec = {"type": "field:total", "anchors": [ghost], "value": "1",
            "origin": "model:x", "extractive": True}
    env = surface.propose(spec=spec)
    assert env["status"] == "refused"
    assert env["reason"] == "claim.anchor.unresolved"
    assert surface.claims == []
