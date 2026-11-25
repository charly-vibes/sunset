# Purpose: RED-first tests for gated export (add-agent-tool-surface task 4.1):
#   export excludes unaudited types and rejected claims; includes checks
#   passed, anchors, scope coverage and the run semantic digest.
# Responsibilities: Exercise sunset.tool_surface export over a real synthetic
#   run; the autonomy gate is evaluated through dsc03.audit_gate.gate_open
#   with human-labeled audit records only (G3).
"""Gated export honesty (task 4.1)."""
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


def page_scope(surface, page_index):
    return next(r["id"] for r in surface.descriptor["regions"]
                if r["kind"] == "page"
                and re.fullmatch(rf"page:{page_index}", r["anchor"]["locator_path"]))


def propose(surface, page_index, value, origin, extractive, claim_type="field:total"):
    spec = {"type": claim_type, "anchors": [page_scope(surface, page_index)],
            "value": value, "origin": origin, "extractive": extractive}
    env = surface.propose(spec=spec)
    assert env["status"] == "ok", env
    return env["data"]["claim_id"]


def exported_ids(env):
    return {r["id"] for r in env["data"]["claims"]}


# -- exclusions -------------------------------------------------------------------

def test_unaudited_type_without_human_acceptance_is_excluded(tmp_path):
    surface = opened(tmp_path)
    propose(surface, 2, "7.000,00", "model:g", extractive=False)
    env = surface.export()
    assert env["status"] == "ok", env
    assert exported_ids(env) == set()  # gate closed, no human acceptance
    assert env["data"]["excluded"]["ungated"] == 1


def test_verified_claim_stays_excluded_until_gate_opens(tmp_path):
    # native runs bind two divergent text observations per page, so
    # page-anchored extractive currency claims are refused typed; the gate
    # exclusion is exercised on the admissible generative claim
    surface = opened(tmp_path)
    propose(surface, 3, "1.234,56", "model:t", extractive=False)
    env = surface.export()
    assert exported_ids(env) == set()
    assert env["data"]["excluded"]["ungated"] == 1


def test_rejected_claims_are_never_exported(tmp_path):
    surface = opened(tmp_path)
    claim_id = propose(surface, 2, "7.000,00", "model:g", extractive=False)
    decide = surface.decide(claim_id=claim_id, action="reject")
    assert decide["status"] == "ok"
    env = surface.export()
    assert exported_ids(env) == set()
    assert env["data"]["excluded"]["rejected"] == 1
    assert all(r["status"] != "rejected" for r in env["data"]["claims"])


def test_ungated_audit_samples_never_open_the_gate(tmp_path):
    surface = opened(tmp_path)
    propose(surface, 2, "7.000,00", "model:g", extractive=False)
    agent = dict(fx.audit_record("field:total"), evidence_class="agent-executed")
    env = surface.export(audit_records=[agent])
    assert exported_ids(env) == set()  # Decision 7: agent audits never count


# -- inclusions -------------------------------------------------------------------

def test_human_acceptance_admits_the_claim(tmp_path):
    surface = opened(tmp_path)
    claim_id = propose(surface, 2, "7.000,00", "model:g", extractive=False)
    assert surface.decide(claim_id=claim_id, action="accept")["status"] == "ok"
    env = surface.export()
    ids = exported_ids(env)
    assert claim_id in ids
    assert len(ids) == 2  # model claim + its human accept claim
    record = next(r for r in env["data"]["claims"] if r["id"] == claim_id)
    assert record["anchors"] == [page_scope(surface, 2)]
    assert "checks_passed" in record and "checks" in record


def test_open_gate_admits_whole_audited_type(tmp_path):
    surface = opened(tmp_path)
    propose(surface, 2, "7.000,00", "model:g", extractive=False)
    propose(surface, 3, "1.234,56", "model:t", extractive=False)
    gate_record = fx.audit_record("field:total")  # human, n=400, 0 errors
    env = surface.export(audit_records=[gate_record])
    assert len(exported_ids(env)) == 2
    assert all(r["status"] == "unverified" for r in env["data"]["claims"])


def test_other_types_stay_excluded_when_only_one_gate_opens(tmp_path):
    surface = opened(tmp_path)
    propose(surface, 2, "7.000,00", "model:g", extractive=False)
    propose(surface, 1, "15/03/1991", "model:d", extractive=False,
            claim_type="field:date")
    env = surface.export(audit_records=[fx.audit_record("field:total")])
    records = env["data"]["claims"]
    assert records and {r["type"] for r in records} == {"field:total"}


# -- export payload -----------------------------------------------------------------

def test_export_carries_run_digest_and_coverage(tmp_path):
    surface = opened(tmp_path)
    claim_id = propose(surface, 3, "1.234,56", "model:t", extractive=False)
    surface.decide(claim_id=claim_id, action="accept")
    env = surface.export()
    data = env["data"]
    assert data["run_digest"] == surface.run_digest
    coverage = data["coverage"]
    assert coverage["declared"]  # descriptor-declared coverage summary
    assert coverage["regions_by_kind"]["word"] > 0
    assert coverage["exported_anchors"] == [page_scope(surface, 3)]
    assert data["checks_passed_total"] >= 0


def test_export_is_deterministic(tmp_path):
    surface = opened(tmp_path)
    claim_id = propose(surface, 2, "7.000,00", "model:g", extractive=False)
    surface.decide(claim_id=claim_id, action="accept")
    audits = [fx.audit_record("field:total")]
    assert fx.canonical(surface.export(audit_records=audits)) == \
        fx.canonical(surface.export(audit_records=audits))
