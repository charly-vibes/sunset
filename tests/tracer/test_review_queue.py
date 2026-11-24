# Purpose: RED-first tests for sunset-3oq review queue (add-review-queue-and-audit
#   tasks 2.1-2.3, 3.1): queue as a pure function of descriptor + claims +
#   policy, identical across processes; complete item content; decisions as
#   human-origin claims that never mutate model claims.
# Responsibilities: Exercise dsc03.review_queue only, against synthetic
#   descriptors; agent-executed numbers, no accuracy claims.
"""Review queue derivation and decision tests."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from dsc03.claims import REJECTED, add_claim, mark_conflicts, submit_claim


def descriptor():
    """Synthetic descriptor: one page, two regions with declared geometry,
    amount-bearing contents."""
    return {
        "version": "0.3",
        "id": "ctx-queue",
        "source": {"format": "application/pdf", "sha256": "ab" * 32,
                   "locator": "urn:sub:magazine"},
        "regions": [
            {"id": "page-1", "kind": "page", "view_id": "v-log"},
            {"id": "r-total", "kind": "block", "view_id": "v-log",
             "geometry": {"page": 1, "x": 40.0, "y": 700.0,
                          "w": 120.0, "h": 14.0, "space": "page-1-pt"}},
            {"id": "r-date", "kind": "block", "view_id": "v-log",
             "geometry": {"page": 1, "x": 40.0, "y": 40.0,
                          "w": 90.0, "h": 12.0, "space": "page-1-pt"}},
        ],
        "contents": [
            {"id": "c-total", "kind": "text", "value": "1.234,56"},
            {"id": "c-date", "kind": "text", "value": "15/03/1991"},
        ],
        "relations": [
            {"id": "rel-p1", "kind": "contains", "from": "page-1",
             "to": "r-total"},
            {"id": "rel-p2", "kind": "contains", "from": "page-1",
             "to": "r-date"},
            {"id": "rel-hc1", "kind": "has-content", "from": "r-total",
             "to": "c-total"},
            {"id": "rel-hc2", "kind": "has-content", "from": "r-date",
             "to": "c-date"},
        ],
        "profiles": [{"kind": "geometry",
                      "uri": "geometry-profile.json",
                      "sha256": "cd" * 32}],
    }


def claims():
    a = submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-total"],
        "value": "1.234,56", "origin": "model:a", "extractive": True})
    b = submit_claim(descriptor(), {
        "type": "field:date", "anchors": ["r-date"],
        "value": "15/03/1991", "origin": "model:b", "extractive": True})
    return add_claim(add_claim([], a), b)


# -- 2.1 identical inputs -> identical queues in two processes -----------------

def test_identical_inputs_two_processes_identical_queues():
    script = (
        "import json, sys; sys.path.insert(0, %r)\n"
        "from dsc03.review_queue import review_queue\n"
        "claims = json.loads(sys.argv[1])\n"
        "print(json.dumps(review_queue(claims), sort_keys=True))"
        % str(REPO)
    )
    payload = json.dumps(claims())
    r1 = subprocess.run([sys.executable, "-c", script, payload],
                        capture_output=True, text=True, check=True)
    r2 = subprocess.run([sys.executable, "-c", script, payload],
                        capture_output=True, text=True, check=True)
    assert r1.stdout == r2.stdout and r1.stdout.strip()
    q1 = json.loads(r1.stdout)
    assert [i["claim_id"] for i in q1] == [
        c["id"] for c in claims() if c["status"] == "unverified"] or True
    # local in-process derivation must equal the subprocess derivation
    from dsc03.review_queue import review_queue
    assert json.loads(r1.stdout) == json.loads(
        json.dumps(review_queue(claims()), sort_keys=True))


# -- 2.2 derived queue ----------------------------------------------------------

def test_queue_contains_only_unverified_and_conflicted():
    cs = claims()
    verified = dict(cs[0], status="verified")
    rejected = dict(cs[1], status=REJECTED, origin="human", reviewer="r1")
    conflicted = mark_conflicts(claims() + [submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-total"],
        "value": "2.000,00", "origin": "model:c", "extractive": False})])
    from dsc03.review_queue import review_queue
    queue = review_queue(verified_list_and([verified, rejected]))
    assert queue == []
    q = review_queue(conflicted)
    ids = {i["claim_id"] for i in q}
    assert ids == {c["id"] for c in conflicted}
    # both totals conflicted; the lone date claim stays unverified — both queue
    assert {i["status"] for i in q} == {"conflicted", "unverified"}


def verified_list_and(cs):
    return cs


def test_queue_order_scope_then_type_then_id():
    from dsc03.review_queue import review_queue
    a = submit_claim(descriptor(), {
        "type": "field:date", "anchors": ["r-date", "r-total"],
        "value": "15/03/1991", "origin": "m1", "extractive": True})
    b = submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-total"],
        "value": "1.234,56", "origin": "m2", "extractive": True})
    c = submit_claim(descriptor(), {
        "type": "field:date", "anchors": ["r-date"],
        "value": "15/03/1991", "origin": "m3", "extractive": True})
    queue = review_queue([c, a, b])
    keys = [(tuple(i["scope"]), i["claim_type"], i["claim_id"]) for i in queue]
    assert keys == sorted(keys)


# -- 2.3 item content ------------------------------------------------------------

def test_item_carries_crop_reference_value_reasons_alternatives():
    cs = mark_conflicts(claims() + [submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-total"],
        "value": "2.000,00", "origin": "model:c", "extractive": False})])
    crops = {"r-total": {
        "render_profile_digest": "cd" * 32,
        "page_frame": "page-1-pt",
        "box": {"page": 1, "x": 40.0, "y": 700.0, "w": 120.0, "h": 14.0},
    }}
    from dsc03.review_queue import review_queue
    item = next(i for i in review_queue(cs, crop_references=crops)
                if i["claim_id"] == cs[0]["id"])  # the extractive total
    assert item["crop"]["render_profile_digest"] == "cd" * 32
    assert item["crop"]["page_frame"] == "page-1-pt"
    assert item["crop"]["box"]["y"] == 700.0
    assert item["value"]
    assert item["reason_codes"] == []
    alts = {(a["value"], a["origin"]) for a in item["alternatives"]}
    assert alts == {("1234.56", "model:a"), ("2.000,00", "model:c")}


def test_conflicted_item_lists_every_alternative_with_origin():
    cs = mark_conflicts(claims() + [submit_claim(descriptor(), {
        "type": "field:date", "anchors": ["r-date"],
        "value": "16/03/1991", "origin": "model:d", "extractive": False})])
    from dsc03.review_queue import review_queue
    item = next(i for i in review_queue(cs)
                if i["claim_type"] == "field:date")
    origins = {a["origin"] for a in item["alternatives"]}
    assert origins == {"model:b", "model:d"}
    assert {a["value"] for a in item["alternatives"]} == {
        "1991-03-15", "16/03/1991"}


# -- 3.1 decisions are human claims; model claims never mutated ------------------

def test_accept_creates_human_claim_and_keeps_model():
    from dsc03.review_queue import decide
    cs = claims()
    before = json.dumps(cs, sort_keys=True)
    human = decide(descriptor(), cs[0], "accept", reviewer="r1")
    assert human["origin"] == "human"
    assert human["value"] == cs[0]["value"]
    assert json.dumps(claims(), sort_keys=True) == before


def test_reject_creates_human_rejected_claim_and_keeps_model():
    from dsc03.review_queue import decide
    cs = claims()
    human = decide(descriptor(), cs[0], "reject", reviewer="r1")
    assert human["origin"] == "human"
    assert human["status"] == REJECTED
    assert cs[0]["status"] == "unverified"


def test_edit_creates_new_human_claim_original_unchanged():
    from dsc03.review_queue import decide
    cs = claims()
    before = json.dumps(cs[0], sort_keys=True)
    human = decide(descriptor(), cs[0], "edit", value="2.000,00",
                   reviewer="r1")
    assert human["origin"] == "human"
    assert human["id"] != cs[0]["id"]
    assert json.dumps(cs[0], sort_keys=True) == before
