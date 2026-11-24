# Purpose: RED-first tests for sunset-1x7 verifier ladder (add-claim-verification-ladder):
#   pinned pure verifiers, registry digest, tier 0 anchor/value checks, tier 1
#   Argentine domain pack with a negative fixture per rule, tier 3 adapter over
#   dsc03.visual oracles, cross-process determinism.
# Responsibilities: Exercise dsc03.verify only; agent-executed; no accuracy
#   claims; tier 2 absent by design (deferred, `agreed` reserved).
"""Verifier ladder tests: contract, tiers, determinism, negative fixtures."""
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tests" / "tracer"))

from conftest import make_carrier, render_config
from dsc03.visual import render
from dsc03.claims import STATUS_ORDER, submit_claim, meet_status, add_claim
from dsc03.substrate.context import issue_fixture
from dsc03.verify import REGISTRY_DIGEST, VERIFIERS, verifier, run_ladder


def descriptor():
    desc = issue_fixture()
    desc["contents"].extend([
        {"id": "c-total", "kind": "text", "value": "1.234,56"},
        {"id": "c-subtotal", "kind": "text", "value": "1.000,00"},
        {"id": "c-tax", "kind": "text", "value": "234,56"},
        {"id": "c-cuit", "kind": "text", "value": "20-30587115-9"},
        {"id": "c-date", "kind": "text", "value": "29/07/2026"},
        {"id": "c-balance", "kind": "text", "value": "2.000,00"},
        {"id": "c-amount", "kind": "text", "value": "500,00"},
        {"id": "c-prior", "kind": "text", "value": "1.500,00"},
    ])
    for cid in ("c-total", "c-subtotal", "c-tax", "c-cuit", "c-date",
                "c-balance", "c-amount", "c-prior"):
        desc["relations"].append(
            {"id": f"rel-{cid}", "kind": "has-content", "from": "r-issue",
             "to": cid})
    return desc


def make_claim(d, type_, content_id, type_map):
    """Submit an extractive claim for one content's text (valid values)."""
    return submit_claim(d, {
        "type": type_, "anchors": [content_id],
        "value": next(c["value"] for c in d["contents"] if c["id"] == content_id),
        "origin": "model", "extractive": True,
    })


def invoice_claims():
    d = descriptor()
    claims = [
        make_claim(d, "field:total", "c-total", {}),
        make_claim(d, "field:subtotal", "c-subtotal", {}),
        make_claim(d, "field:tax", "c-tax", {}),
        make_claim(d, "field:cuit", "c-cuit", {}),
        make_claim(d, "field:date", "c-date", {}),
    ]
    return d, claims


def bank_claims():
    d = descriptor()
    claims = [
        make_claim(d, "field:balance", "c-balance", {}),
        make_claim(d, "field:amount", "c-amount", {}),
        make_claim(d, "field:prior-balance", "c-prior", {}),
    ]
    return d, claims


# -- 4.1 contract, registry pinning -------------------------------------------

def test_registry_digest_stable_and_verifiers_declare_identity():
    digest = REGISTRY_DIGEST
    again = __import__("dsc03.verify", fromlist=["REGISTRY_DIGEST"]).REGISTRY_DIGEST
    assert digest == again and len(digest) == 64
    for v in VERIFIERS:
        assert v.id and v.version and len(v.digest) == 64
        assert callable(v.check) and v.applies_to


def test_no_tier2_producer_and_agreed_reserved():
    tiers = {v.tier for v in __import__("dsc03.verify", fromlist=["VERIFIERS"]).VERIFIERS}
    assert 2 not in tiers
    assert "agreed" in STATUS_ORDER


def test_verifier_pure_no_io():
    d, claims = invoice_claims()
    total = claims[0]
    r1 = verifier("ar.invoice.total-sum").check(total, descriptor_claims=claims)
    r2 = verifier("ar.invoice.total-sum").check(total, descriptor_claims=claims)
    assert r1 == r2
    assert json.loads(json.dumps(r1)) == r1


# -- 4.2 tier 0 -----------------------------------------------------------------

def test_tier0_pass_then_domain_rule_yields_verified():
    d, claims = invoice_claims()
    results = run_ladder(claims, descriptor=d)
    total = [c for c in results if c["type"] == "field:total"][0]
    assert total["status"] == "verified"
    assert "ar.invoice.total-sum" in [c["id"] for c in total["checks"]]


def test_no_applicable_rule_stays_unverified():
    d, claims = invoice_claims()
    notes = make_claim(d, "field:notes", "c-poem-text", {})
    results = run_ladder(claims + [notes], descriptor=d)
    notes_out = [c for c in results if c["type"] == "field:notes"][0]
    assert notes_out["status"] == "unverified"
    assert [c for c in notes_out["checks"] if c["tier"] == 1] == []


def test_ladder_passes_human_rejection_through_unchanged():
    # a human `rejected` claim must never be promoted to `verified` (or
    # demoted) by the ladder: rejection is final human evidence
    from dsc03.claims import REJECTED, claim_id
    d, claims = invoice_claims()
    total = claims[0]
    rejected = dict(total, origin="human", reviewer="r1", status=REJECTED)
    rejected["id"] = claim_id("field:total", total["anchors"],
                              total["value"], "human")
    out = run_ladder([total, rejected], descriptor=d)
    human = [c for c in out if c["origin"] == "human"][0]
    assert human["status"] == REJECTED
    model = [c for c in out if c["origin"] == "model"][0]
    assert model["status"] == "verified"


# -- 4.3 tier 1 domain pack: positive + negative fixture per rule ---------------

def test_cuit_valid_and_negative():
    d, claims = invoice_claims()
    results = run_ladder(claims, descriptor=d)
    cuit = [c for c in results if c["type"] == "field:cuit"][0]
    assert "ar.cuit.check-digit" in [c["id"] for c in cuit["checks"]]
    # negative fixture: wrong check digit refused by the rule, never passing
    bad = dict(cuit, value="20-30587115-8")
    outcome = verifier("ar.cuit.check-digit").check(bad)
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.cuit.check-digit.invalid"


def test_total_sum_negative():
    d, claims = invoice_claims()
    lying_total = dict(claims[0], value="9999.00")
    outcome = verifier("ar.invoice.total-sum").check(
        lying_total, descriptor_claims=claims)
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.total-sum.mismatch"


def test_conflicted_sibling_is_unsupported_not_order_dependent():
    # two retained tax claims (a conflict): the tier-1 rule must return the
    # typed unknown — never silently elect found[0], which flips the exported
    # check attribution with claim order
    d, claims = invoice_claims()
    alt_tax = submit_claim(d, {"type": "field:tax", "anchors": ["c-tax"],
                               "value": "999.00", "origin": "model-b",
                               "extractive": False})
    total = claims[0]
    out1 = run_ladder(claims + [alt_tax], descriptor=d)
    out2 = run_ladder(list(reversed(claims + [alt_tax])), descriptor=d)
    for out in (out1, out2):
        total_out = [c for c in out if c["type"] == "field:total"][0]
        check = next(c for c in total_out["checks"]
                     if c["id"] == "ar.invoice.total-sum")
        assert check["outcome"] == "unsupported"
        assert check["reason_code"] == "verify.total-sum.siblings-conflicted"


def test_running_balance_positive_and_negative():
    d, claims = bank_claims()
    results = run_ladder(claims, descriptor=d)
    balance = [c for c in results if c["type"] == "field:balance"][0]
    assert "ar.bank.running-balance" in [c["id"] for c in balance["checks"]]
    bad = dict(balance, value="2.000,01")
    bad = dict(bad, value="2000.01")
    outcome = verifier("ar.bank.running-balance").check(
        bad, descriptor_claims=claims)
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.running-balance.broken"


def test_date_parse_negative():
    bad = {"type": "field:date", "value": "31/02/2026", "anchors": ["c-date"],
           "origin": "model"}
    outcome = verifier("ar.date.parse").check(bad)
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.date.parse.invalid"


def test_currency_parse_negative():
    bad = {"type": "field:total", "value": "1.234.56", "anchors": ["c-total"],
           "origin": "model"}
    outcome = verifier("ar.currency.parse").check(bad)
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.currency.parse.invalid"


# -- 4.5 tier 3 adapter over dsc03.visual ---------------------------------------

# Synthetic carrier geometry (hand-computed, seed-free; snap-test
# discipline): 612x792 pt white page, fill-only black rect via the conftest
# carrier builder. pymupdf draws with a TOP-LEFT y-down origin, so the
# fitz Rect(200, 392, 300, 492) ink rect is the descriptor (y-up,
# bottom-left) box x 200..300, y 300..400 pt.
INK_FITZ_RECT = pymupdf.Rect(200, 392, 300, 492)
INK_BOX = [200, 300, 300, 400]
INK_BOX_OVERHANG = [198, 298, 302, 402]  # +2 pt overhang on every side
BLANK_BOX = [40, 40, 120, 80]            # white region, far from the ink rect
# Pinned tier-3 contract literals: the declared ink fraction (must never
# drift silently) and the descriptor-fact type carrying the pinned render.
INK_FRACTION_THRESHOLD = 0.01
RENDER_FACT_TYPE = "visual:render:page"


def _boxed_claim(boxes):
    anchors = [{"id": f"a-{i}", "box": list(box)}
               for i, box in enumerate(boxes)]
    return {"type": "field:total", "anchors": anchors, "value": "1.234,56",
            "origin": "model", "extractive": True}


def _tier3_render(tmp_path):
    config = render_config(dpi=72, simplification="ink-dilation-2px")
    pdf = make_carrier(tmp_path, "ink-agreement-carrier.pdf", [INK_FITZ_RECT])
    result = render.render_page(config, pdf)
    assert isinstance(result, render.Rendered), getattr(result, "reason",
                                                        result)
    return config, result


def _render_fact(config, rendered):
    return {"type": RENDER_FACT_TYPE, "rendered": rendered, "config": config}


def test_tier3_adapter_unsupported_is_typed():
    outcome = verifier("visual.ink-agreement").check(
        {"type": "field:total", "anchors": ["c-total"]})
    # no render fact supplied: the pinned typed unknown — never a pass/fail
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.render-result-missing"}


def test_tier3_inked_box_passes_and_overhang_accepted(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    fact = _render_fact(config, rendered)
    outcome = verifier("visual.ink-agreement").check(
        _boxed_claim([INK_BOX]), descriptor_claims=[fact])
    assert outcome == {"outcome": "pass",
                       "reason_code": "verify.visual.ink-present"}
    # sub-tolerance overhang on the declared box is accepted, never refused
    over = verifier("visual.ink-agreement").check(
        _boxed_claim([INK_BOX_OVERHANG]), descriptor_claims=[fact])
    assert over["outcome"] == "pass"


def test_tier3_empty_box_fails_with_witness(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    fact = _render_fact(config, rendered)
    outcome = verifier("visual.ink-agreement").check(
        _boxed_claim([BLANK_BOX]), descriptor_claims=[fact])
    assert outcome["outcome"] == "fail"
    assert outcome["reason_code"] == "verify.visual.ink-absent"
    witness = outcome["witness"]
    assert witness["anchor"] == "a-0"
    assert witness["box"] == BLANK_BOX
    assert witness["fraction"] == 0.0
    assert witness["threshold"] == INK_FRACTION_THRESHOLD


def test_tier3_missing_render_fact_is_typed(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    outcome = verifier("visual.ink-agreement").check(_boxed_claim([INK_BOX]))
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.render-result-missing"}


def test_tier3_unboxed_anchor_is_typed(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    fact = _render_fact(config, rendered)
    outcome = verifier("visual.ink-agreement").check(
        {"type": "field:total", "anchors": ["c-total"]},
        descriptor_claims=[fact])
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.anchor-box-missing"}


def test_tier3_invalid_box_is_typed(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    fact = _render_fact(config, rendered)
    for bad in ([200, 300, 300, 200],         # negative extent
                [200, 300],                   # wrong arity
                [200, "300", 300, 400]):      # non-numeric coordinate
        outcome = verifier("visual.ink-agreement").check(
            _boxed_claim([bad]), descriptor_claims=[fact])
        assert outcome == {"outcome": "unsupported",
                           "reason_code": "verify.visual.anchor-box-invalid"}


def test_tier3_box_outside_render_is_typed(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    fact = _render_fact(config, rendered)
    outcome = verifier("visual.ink-agreement").check(
        _boxed_claim([[1000, 1000, 1100, 1040]]), descriptor_claims=[fact])
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.box-outside-render"}


def test_tier3_mask_unavailable_is_typed_unknown(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    disabled = render_config(dpi=72, enabled=False,
                             simplification="ink-dilation-2px")
    fact = _render_fact(disabled, rendered)
    outcome = verifier("visual.ink-agreement").check(
        _boxed_claim([INK_BOX]), descriptor_claims=[fact])
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.binarization-not-configured"}


def test_tier3_malformed_render_fact_is_typed(tmp_path):
    config, rendered = _tier3_render(tmp_path)
    outcome = verifier("visual.ink-agreement").check(
        _boxed_claim([INK_BOX]),
        descriptor_claims=[{"type": RENDER_FACT_TYPE}])
    assert outcome == {"outcome": "unsupported",
                       "reason_code": "verify.visual.render-fact-invalid"}


def test_tier3_byte_identical_across_processes(tmp_path):
    import os
    config, rendered = _tier3_render(tmp_path)
    png = tmp_path / "ink-agreement-carrier.pdf.png"
    png.write_bytes(rendered.data)
    script = (
        "import json,sys;"
        "sys.path.insert(0, %r);"
        "from conftest import render_config;"
        "from dsc03.visual.render import Rendered;"
        "from dsc03.verify import verifier;"
        "config = render_config(dpi=72, simplification='ink-dilation-2px');"
        "rendered = Rendered(config=config, data=open(%r,'rb').read());"
        "fact = {'type': 'visual:render:page', 'rendered': rendered,"
        "        'config': config};"
        "ink = {'type': 'field:total', 'anchors': [{'id': 'a-0',"
        "        'box': [200, 300, 300, 400]}], 'value': '1.234,56',"
        "        'origin': 'model'};"
        "blank = {'type': 'field:total', 'anchors': [{'id': 'a-0',"
        "         'box': [40, 40, 120, 80]}], 'value': '1.234,56',"
        "         'origin': 'model'};"
        "check = verifier('visual.ink-agreement').check;"
        "out = [check(ink, descriptor_claims=[fact]),"
        "       check(blank, descriptor_claims=[fact])];"
        "sys.stdout.write(json.dumps(out, sort_keys=True,"
        "                            separators=(',',':')))"
    ) % (str(_REPO_ROOT / "tests" / "tracer"), str(png))
    env = dict(os.environ,
               PYTHONPATH=str(_REPO_ROOT) + os.pathsep
               + str(_REPO_ROOT / "tests" / "tracer"))
    outs = []
    for _ in range(2):
        r = subprocess.run([sys.executable, "-c", script],
                           capture_output=True, text=True, env=env,
                           cwd=str(_REPO_ROOT))
        assert r.returncode == 0, r.stderr
        outs.append(r.stdout.encode())
    assert outs[0] == outs[1]
    # the in-process computation over identical inputs agrees byte for byte
    fact = _render_fact(config, rendered)
    local = json.dumps(
        [verifier("visual.ink-agreement").check(_boxed_claim([INK_BOX]),
                                                descriptor_claims=[fact]),
         verifier("visual.ink-agreement").check(_boxed_claim([BLANK_BOX]),
                                                descriptor_claims=[fact])],
        sort_keys=True, separators=(",", ":")).encode()
    assert outs[0] == local
    assert b'"reason_code":"verify.visual.ink-present"' in outs[0]
    assert b'"reason_code":"verify.visual.ink-absent"' in outs[0]


# -- determinism across processes ------------------------------------------------

def test_verifier_output_byte_identical_across_processes():
    import os
    script = (
        "import json,sys;"
        "sys.path.insert(0, %r);"
        "from tests.tracer.test_verify_ladder import invoice_claims;"
        "from dsc03.verify import run_ladder;"
        "d, claims = invoice_claims();"
        "out = run_ladder(claims, descriptor=d);"
        "sys.stdout.write(json.dumps(out, sort_keys=True, separators=(',',':')))"
    ) % (str(_REPO_ROOT),)
    env = dict(os.environ, PYTHONPATH=str(_REPO_ROOT))
    outs = []
    for _ in range(2):
        r = subprocess.run([sys.executable, "-c", script],
                           capture_output=True, text=True, env=env,
                           cwd=str(_REPO_ROOT))
        assert r.returncode == 0, r.stderr
        outs.append(r.stdout.encode())
    assert outs[0] == outs[1]
    assert len(outs[0]) > 10
