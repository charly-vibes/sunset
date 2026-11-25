# Purpose: RED-first tests for anchor-only addressing (add-agent-tool-surface
#   task 3.3): producer labels and positional indexes are refused with a
#   stable reason; only anchor-derived ids address scopes and claims.
# Responsibilities: Exercise sunset.tool_surface address validation; anchor
#   ids are the identity profile's `a:<32 hex>` form, claim ids `c:<32 hex>`.
"""Anchor-ids-only addressing; labels and indexes refused (task 3.3)."""
import sys
from pathlib import Path

import pytest

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


LABELS = ["page-1", "pw1-1", "TOTAL", "pg1", "r-total"]
INDEXES = [1, 0, -1, "1", 1.0]


@pytest.mark.parametrize("bad", LABELS)
def test_labels_are_refused_as_addresses(tmp_path, bad):
    surface = opened(tmp_path)
    for env in (surface.words(scope=bad),
                surface.zoom_in(scope=bad),
                surface.zoom_out(scope=bad),
                surface.crop(anchor=bad)):
        assert env["status"] == "refused", (bad, env)
        assert env["reason"] == "address.not-anchor", (bad, env)


@pytest.mark.parametrize("bad", INDEXES)
def test_positional_indexes_are_refused_as_addresses(tmp_path, bad):
    surface = opened(tmp_path)
    for env in (surface.words(scope=bad),
                surface.crop(anchor=bad)):
        assert env["status"] == "refused", (bad, env)
        assert env["reason"] == "address.not-anchor", (bad, env)


def test_well_formed_but_unknown_anchor_is_scope_unknown(tmp_path):
    surface = opened(tmp_path)
    env = surface.words(scope="a:" + "0" * 32)
    assert env["status"] == "refused"
    assert env["reason"] == "scope.unknown"


def test_claim_labels_are_refused_and_claim_indexes_unknown(tmp_path):
    surface = opened(tmp_path)
    env = surface.decide(claim_id="pw1-1", action="accept")
    assert env["status"] == "refused"
    assert env["reason"] == "address.not-anchor"
    env = surface.decide(claim_id="c:" + "9" * 32, action="accept")
    assert env["status"] == "refused"
    assert env["reason"] == "claim.unknown"


def test_propose_refuses_non_anchor_spec_addresses(tmp_path):
    surface = opened(tmp_path)
    for anchors in (["page-1"], ["pw1"], [1], "page:1"):
        spec = {"type": "field:total", "anchors": anchors, "value": "1",
                "origin": "model:x", "extractive": False}
        env = surface.propose(spec=spec)
        assert env["status"] == "refused", (anchors, env)
        assert env["reason"] == "address.not-anchor", (anchors, env)
    assert surface.claims == []


def test_real_anchor_ids_are_the_only_accepted_addresses(tmp_path):
    surface = opened(tmp_path)
    anchors = [r["id"] for r in surface.descriptor["regions"]
               if r["id"].startswith("a:")]
    assert anchors
    assert all(surface.words(scope=a)["status"] == "ok" for a in anchors[:3])
