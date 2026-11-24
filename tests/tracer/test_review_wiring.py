# Purpose: RED-first tests for sunset-3oq review wiring (tasks 2.3 crop
#   reference, 3.2 SPA wiring, 5.1-5.2 metrics reporting): queue review
#   bundles built with the EXISTING visual-review SPA template (no parallel
#   review path), pinned crop references through digitization.render, and
#   verdicts-to-human-claim mapping feeding dsc03.claims (model claims
#   never mutated).
# Responsibilities: Exercise digitization.review + digitization.render
#   crop support against a synthetic carrier; agent-executed numbers.
"""Review queue SPA wiring and crop-reference tests."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import make_carrier
from dsc03.claims import REJECTED, add_claim, submit_claim

TEMPLATE_PATH = (REPO / "hitl" / "visual-review" / "templates"
                 / "visual-review-spa.html")


def descriptor():
    return {
        "version": "0.3",
        "id": "ctx-wire",
        "source": {"format": "application/pdf", "sha256": "ab" * 32,
                   "locator": "urn:sub:magazine"},
        "regions": [
            {"id": "page-1", "kind": "page", "view_id": "v-log"},
            {"id": "r-total", "kind": "block", "view_id": "v-log",
             "geometry": {"page": 1, "x": 40.0, "y": 700.0,
                          "w": 120.0, "h": 14.0, "space": "page-1-pt"}},
        ],
        "contents": [
            {"id": "c-total", "kind": "text", "value": "1.234,56"},
        ],
        "relations": [
            {"id": "rel-p1", "kind": "contains", "from": "page-1",
             "to": "r-total"},
            {"id": "rel-hc1", "kind": "has-content", "from": "r-total",
             "to": "c-total"},
        ],
        "profiles": [{"kind": "geometry", "uri": "geometry-profile.json",
                      "sha256": "cd" * 32}],
    }


def claims():
    claim = submit_claim(descriptor(), {
        "type": "field:total", "anchors": ["r-total"],
        "value": "1.234,56", "origin": "model:a", "extractive": True})
    return add_claim([], claim)


def carrier(tmp_path):
    return make_carrier(tmp_path, "wire.pdf", [(30, 690, 150, 30)])


# -- crop reference (2.3, digitization/render.py) --------------------------------

def test_crop_reference_pins_profile_frame_and_box(tmp_path):
    import digitization.render as render
    source = carrier(tmp_path).read_bytes()
    png, record = render.render_crop(
        source, 1, 144, {"page": 1, "x": 40.0, "y": 700.0,
                         "w": 120.0, "h": 14.0})
    assert png[:4] == b"\x89PNG"
    assert record["pixel_box"][2] == 240  # 120pt at 144dpi
    assert record["page_frame"] == "page-1-pt"
    ref = render.crop_reference("cd" * 32, record,
                                {"page": 1, "x": 40.0, "y": 700.0,
                                 "w": 120.0, "h": 14.0})
    assert ref["render_profile_digest"] == "cd" * 32
    assert ref["page_frame"] == "page-1-pt"
    assert ref["box"]["y"] == 700.0
    assert ref["digest"].startswith("crop:")


# -- 3.2 queue -> existing SPA, verdicts -> human claims --------------------------

def test_queue_bundle_uses_existing_template(tmp_path):
    from digitization.review import build_queue_bundle
    out = tmp_path / "queue-bundle.html"
    record = build_queue_bundle(descriptor(), claims(),
                                carrier(tmp_path).read_bytes(), out, dpi=72)
    html = out.read_text()
    template = TEMPLATE_PATH.read_text()
    assert "__REVIEW_DATA_ISLAND__" not in html
    assert html.startswith(template.split("__REVIEW_DATA_ISLAND__")[0][:200])
    # queue items embedded in the SPA's own carriers/pages/regions shape
    page0 = record["carriers"][0]["pages"][0]
    ids = {r["id"] for r in page0["regions"]}
    assert ids == {"r-total"}
    assert page0["regions"][0]["rect_px"] == [40, 700, 120, 14]  # 72dpi = pt
    assert page0["image"].startswith("data:image/png;base64,")
    # queue itself recorded with crop reference
    item = record["queue"][0]
    assert item["crop"]["render_profile_digest"] == "cd" * 32


def test_verdicts_map_to_human_claims_without_touching_model(tmp_path):
    from digitization.review import verdicts_to_decisions
    cs = claims()
    verdicts = {
        "reviewer": "r1",
        "carriers": [{"carrier": "ctx-wire", "pages": [
            {"page": 1, "regions": [
                {"id": "r-total", "verdict": "agree"},
                {"id": "r-date", "verdict": "differ"},
                {"id": "r-other", "verdict": "unknown"},
            ]}]}],
    }
    human = verdicts_to_decisions(verdicts, descriptor(), cs)
    # agree -> human claim repeating the canonical value; r-date/r-other
    # anchor no queued claim here, so only the agree produces a claim
    assert len(human) == 1
    assert human[0]["origin"] == "human"
    assert human[0]["value"] == cs[0]["value"]
    assert human[0]["reviewer"] == "r1"


def test_differ_verdict_rejects_queued_claim(tmp_path):
    from digitization.review import verdicts_to_decisions
    cs = claims()
    verdicts = {
        "reviewer": "r1",
        "carriers": [{"carrier": "ctx-wire", "pages": [
            {"page": 1, "regions": [{"id": "r-total",
                                     "verdict": "differ"}]}]}],
    }
    human = verdicts_to_decisions(verdicts, descriptor(), cs)
    assert len(human) == 1
    assert human[0]["status"] == REJECTED
    assert cs[0]["status"] == "unverified"
