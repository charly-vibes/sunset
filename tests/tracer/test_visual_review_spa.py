"""Contract tests for the human visual-review SPA (sunset-e8t).

The SPA (hitl/visual-review/templates/visual-review-spa.html) is the human
counterpart of the raster visual oracles: it presents a pinned page render
beside the claimed descriptor regions and collects per-region verdicts.
It must:

- be a single self-contained file (works offline over file://),
- never phone home or reference external resources,
- present both a side-by-side view and an overlay view,
- collect tri-state verdicts (agree / differ / unknown) per region plus
  human-drawn missed-ink boxes, serializing unknown as null,
- serialize verdicts in a pinned key order that mirrors the oracle
  outcome vocabulary, with no winner election and no smoothing,
- be producible by dsc03.visual.review.build_review_bundle, which embeds
  the pinned render, pixel-mapped regions, render configuration and
  evidence class; missing renderers and unknown frames stay typed
  (unavailable / unknown), never silently dropped,
- walk every recorded calibration example through
  build_calibration_review_bundle (all carriers, all unique render
  targets incl. both rotated-strip frames), and
- be buildable and servable via `python -m dsc03.visual.review` and
  `just visual-review`.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dsc03.visual import Binarization, RenderConfig, render
from dsc03.visual.review import build_descriptor_review_bundle, build_review_bundle

REPO = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO / "hitl" / "visual-review" / "templates" / "visual-review-spa.html"
GEOMETRY = json.loads((REPO / "tests/tracer/profiles/geometry-page-pt.json").read_text())
CARRIER_PDF = REPO / "fixtures/carriers/bank-statement-ca-excerpt.pdf"
CALIBRATION = json.loads((REPO / "fixtures/visual/calibration.json").read_text())
DESCRIPTOR_FIXTURE = REPO / "tests/tracer/fixtures/descriptor-review/cta-cte-descriptor.json"


def _regions_for(carrier_id):
    matches = [c for c in CALIBRATION["carriers"] if c["id"] == carrier_id]
    assert len(matches) == 1, f"carrier {carrier_id!r} not uniquely recorded"
    return [dict(r) for r in matches[0]["regions"]]


def _pinned_config(page=1, executable=None):
    exe = executable or shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=exe,
        renderer_version=render.detect_renderer_version(exe),
        dpi=72,
        page=page,
        binarization=Binarization(enabled=True, method="fixed-threshold", threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


# ---------------------------------------------------------------------------
# template contract
# ---------------------------------------------------------------------------


def test_review_spa_template_exists():
    assert TEMPLATE_PATH.is_file(), TEMPLATE_PATH
    html = TEMPLATE_PATH.read_text()
    assert len(html) > 4000, "template suspiciously small"


def test_review_spa_is_offline_only():
    html = TEMPLATE_PATH.read_text()
    assert "http://" not in html and "https://" not in html
    for banned in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "import("):
        assert banned not in html, banned
    for tag in re.findall(r"<(?:script|img|link)[^>]*>", html):
        src = re.search(r'(?:src|href)="([^"]*)"', tag)
        if src:
            assert src.group(1).startswith("data:") or src.group(1).startswith("#"), tag
    assert "application/json" in html, "embedded data island missing"


def test_review_spa_pins_interaction_affordances():
    html = TEMPLATE_PATH.read_text()
    for token in (
        "side-by-side",           # dual-pane comparison view
        "overlay",                # regions drawn over the render
        "agree", "differ", "unknown",   # tri-state oracle vocabulary
        "missed-ink",             # human-attributed ink outside claimed regions
        "Download",               # verdict export
        "localStorage",           # autosave + resume
        "no winner election",     # review rules, verbatim
        "no smoothing",
    ):
        assert token in html, token


def test_review_spa_embeds_the_data_island():
    html = TEMPLATE_PATH.read_text()
    assert 'id="review-data"' in html
    assert "data:image/png;base64" in html


# ---------------------------------------------------------------------------
# serialization contract (pure JS, extracted and run under node)
# ---------------------------------------------------------------------------


def _review_core_js():
    html = TEMPLATE_PATH.read_text()
    match = re.search(
        r"/\* REVIEW-CORE-START \*/(.*?)/\* REVIEW-CORE-END \*/", html, re.S
    )
    assert match, "REVIEW-CORE markers missing from template"
    return match.group(1)


def _run_node(script: str) -> str:
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node failed:\n{r.stderr}"
    return r.stdout


def _bundle():
    """A v2 review record: the SPA's data-island contract."""
    return {
        "kind": "visual-review-bundle",
        "version": 2,
        "rules": "no winner election, no smoothing; unknown is an answer",
        "carriers": [
            {
                "carrier": "bank-statement-ca-excerpt",
                "frame": "page-1",
                "evidence_class": "independent",
                "render_config": {"renderer_name": "pdftoppm", "dpi": 72},
                "pages": [
                    {
                        "page": 1,
                        "unavailable": None,
                        "regions": [
                            {"id": "ledger-block", "rect_px": [110, 75, 140, 50]},
                            {"id": "margin-lower", "rect_px": [102, 400, 150, 60]},
                        ],
                    },
                    {
                        "page": 2,
                        "unavailable": "pdftoppm not found: /nonexistent/pdftoppm",
                        "regions": [],
                    },
                ],
            },
        ],
    }


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_verdict_serialization_key_order_and_tri_state_null():
    script = _review_core_js() + r'''
const assert = require("assert");
const data = BUNDLE_FIXTURE;
const answers = { "bank-statement-ca-excerpt":
                    { "1": { "ledger-block": {verdict: "agree", note: "box matches"},
                            "margin-lower": {verdict: "differ", note: "ink bleeds"} },
                      "2": {} } };
const missed = { "bank-statement-ca-excerpt":
                   { "1": [{rect_px: [300, 500, 40, 20]}], "2": [] } };
const out = JSON.parse(buildVerdictJson(data, answers, missed));
assert.deepEqual(Object.keys(out), ["reviewer", "carriers", "rules"]);
assert.equal(out.reviewer, null);
assert.deepEqual(Object.keys(out.carriers[0]), ["carrier", "pages"]);
assert.deepEqual(Object.keys(out.carriers[0].pages[0]),
                 ["page", "unavailable", "regions", "missed_ink"]);
assert.deepEqual(Object.keys(out.carriers[0].pages[0].regions[0]),
                 ["id", "rect_px", "verdict", "note"]);
assert.equal(out.carriers[0].pages[0].regions[0].verdict, "agree");
assert.equal(out.carriers[0].pages[0].missed_ink.length, 1);
// page 2: typed unavailable carries the reason, no regions, no verdicts
assert.deepEqual(Object.keys(out.carriers[0].pages[1]),
                 ["page", "unavailable", "regions", "missed_ink"]);
assert.equal(out.carriers[0].pages[1].unavailable,
             "pdftoppm not found: /nonexistent/pdftoppm");
assert.deepEqual(out.carriers[0].pages[1].regions, []);
assert.deepEqual(out.carriers[0].pages[1].missed_ink, []);
// untouched verdicts serialize as null, notes as empty strings
const untouched = JSON.parse(
  buildVerdictJson(data, {"bank-statement-ca-excerpt": {"1": {}, "2": {}}},
                      {"bank-statement-ca-excerpt": {"1": [], "2": []}}));
assert.equal(untouched.carriers[0].pages[0].regions[0].verdict, null);
assert.equal(untouched.carriers[0].pages[0].regions[0].note, "");
console.log("ok");
'''.replace("BUNDLE_FIXTURE", json.dumps(_bundle(), ensure_ascii=False))
    assert "ok" in _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_verdict_serialization_covers_every_carrier_in_a_multi_bundle():
    data = _bundle()
    second = json.loads(json.dumps(data["carriers"][0]))
    second["carrier"] = "visual-strip"
    second["pages"] = [dict(second["pages"][0], page=1)]
    data["carriers"].append(second)
    script = _review_core_js() + r'''
const assert = require("assert");
const data = BUNDLE_FIXTURE;
const answers = { "bank-statement-ca-excerpt": { "1": { "ledger-block": {verdict: "differ", note: ""} } },
                  "visual-strip": { "1": { "ledger-block": {verdict: "unknown", note: "faint"} } } };
const missed = { "bank-statement-ca-excerpt": { "1": [{rect_px: [1,2,3,4]}] } };
const out = JSON.parse(buildVerdictJson(data, answers, missed));
assert.deepEqual(out.carriers.map(c => c.carrier),
                 ["bank-statement-ca-excerpt", "visual-strip"]);
assert.equal(out.carriers[0].pages[0].regions[0].verdict, "differ");
assert.equal(out.carriers[0].pages[0].missed_ink.length, 1);
assert.equal(out.carriers[1].pages[0].regions[0].verdict, "unknown");
assert.equal(out.carriers[1].pages[0].missed_ink.length, 0);
console.log("ok");
'''.replace("BUNDLE_FIXTURE", json.dumps(data, ensure_ascii=False))
    assert "ok" in _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_missed_ink_wiring_is_idempotent_across_re_renders():
    """Regression (owner report): renderPanes() re-wires the drag handlers on
    every re-render, so after N interactions one drag committed N stacked
    copies of the same box. The attach helper must be idempotent per element,
    and commit must fire exactly once per completed drag."""
    script = _review_core_js() + r'''
const assert = require("assert");
function stubAnn() {
  return { listeners: {},
           addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
           fire(t, ev) { (this.listeners[t] || []).forEach(f => f(ev)); } };
}
const ann = stubAnn();
let committed = [];
let pos = [10, 10];
const env = {
  active: () => true,
  point: () => pos,
  ghost: () => {},
  commit: box => committed.push(box)
};
// simulate many re-renders wiring the same persistent element
for (let i = 0; i < 5; i++) attachMissedInkHandlers(ann, env);
ann.fire("mousedown", {});
ann.fire("mousemove", {});
pos = [60, 40];
ann.fire("mouseup", {});
assert.equal(committed.length, 1, "one drag after 5 re-wires must commit exactly once, got " + committed.length);
// tiny drags are rejected, not committed
const ann2 = stubAnn();
const tiny = [];
attachMissedInkHandlers(ann2, { active: () => true, point: () => [3, 3], ghost: () => {}, commit: b => tiny.push(b) });
ann2.fire("mousedown", {});
ann2.fire("mouseup", {});
assert.deepEqual(tiny, []);
console.log("ok");
'''
    assert "ok" in _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_push_missed_box_dedupes_identical_rects():
    script = _review_core_js() + r'''
const assert = require("assert");
const list = [];
pushMissedBox(list, [100, 200, 50, 30]);
pushMissedBox(list, [100, 200, 50, 30]);  // same drag recorded twice — one layer only
pushMissedBox(list, [100, 200, 51, 30]);  // genuinely different box
assert.equal(list.length, 2, JSON.stringify(list));
assert.deepEqual(list[0].rect_px, [100, 200, 50, 30]);
console.log("ok");
'''
    assert "ok" in _run_node(script)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_verdict_serialization_rejects_off_vocabulary_verdicts():
    script = _review_core_js() + r'''
const assert = require("assert");
const data = BUNDLE_FIXTURE;
const bad = { "bank-statement-ca-excerpt":
                { "1": { "ledger-block": {verdict: "winner", note: ""} } } };
assert.throws(() => buildVerdictJson(data, bad, {}), /verdict/);
console.log("ok");
'''.replace("BUNDLE_FIXTURE", json.dumps(_bundle(), ensure_ascii=False))
    assert "ok" in _run_node(script)


# ---------------------------------------------------------------------------
# generator contract
# ---------------------------------------------------------------------------


def test_build_review_bundle_embeds_image_and_pixel_mapped_regions(tmp_path):
    out = tmp_path / "review.html"
    record = build_review_bundle(
        CARRIER_PDF,
        regions=_regions_for("bank-statement-ca-excerpt"),
        geometry=GEOMETRY,
        frame_name="page-1",
        carrier="bank-statement-ca-excerpt",
        out_path=out,
        config=_pinned_config(),
    )
    html = out.read_text()
    assert "data:image/png;base64," in html, "pinned render not embedded"
    assert "ledger-block" in html and "margin-lower" in html
    assert "independent" in html, "evidence class not embedded"
    assert "page-1" in html, "frame name not embedded"
    # pixel rect derived through the declared frame (pt bottom-left y-up)
    page = record["carriers"][0]["pages"][0]
    assert page["unavailable"] is None
    ledger = next(r for r in page["regions"] if r["id"] == "ledger-block")
    x, y, w, h = ledger["rect_px"]
    assert (x, y, w, h) == (110, 75, 140, 50), ledger["rect_px"]


def test_missing_renderer_is_typed_unavailable(tmp_path):
    out = tmp_path / "review.html"
    record = build_review_bundle(
        CARRIER_PDF,
        regions=_regions_for("bank-statement-ca-excerpt"),
        geometry=GEOMETRY,
        frame_name="page-1",
        carrier="bank-statement-ca-excerpt",
        out_path=out,
        config=_pinned_config(executable="/nonexistent/pdftoppm"),
    )
    page = record["carriers"][0]["pages"][0]
    assert "pdftoppm" in page["unavailable"] and "nonexistent" in page["unavailable"]
    assert page["regions"] == []
    html = out.read_text()
    assert "data:image/png;base64," not in html


def test_unknown_frame_is_flagged_not_dropped(tmp_path):
    out = tmp_path / "review.html"
    record = build_review_bundle(
        CARRIER_PDF,
        regions=_regions_for("bank-statement-ca-excerpt"),
        geometry=GEOMETRY,
        frame_name="no-such-frame",
        carrier="bank-statement-ca-excerpt",
        out_path=out,
        config=_pinned_config(),
    )
    page = record["carriers"][0]["pages"][0]
    assert page["unavailable"] is not None and "frame" in page["unavailable"]
    assert [r["id"] for r in page["regions"]] == ["ledger-block", "margin-lower"]
    assert all(r["rect_px"] is None for r in page["regions"])


# ---------------------------------------------------------------------------
# all-examples bundle (calibration walk) and CLI/serve contract
# ---------------------------------------------------------------------------


def test_calibration_bundle_walks_every_recorded_example(tmp_path):
    from dsc03.visual.review import build_calibration_review_bundle

    out = tmp_path / "index.html"
    record = build_calibration_review_bundle(out_path=out)
    html = out.read_text()

    recorded_ids = [c["id"] for c in CALIBRATION["carriers"]]
    assert [c["carrier"] for c in record["carriers"]] == recorded_ids

    # 8 unique render targets in the record (incl. both rotated-strip frames)
    targets = [(p["file"], p["page"], p.get("frame"))
               for c in record["carriers"] for p in c["pages"]]
    assert len(targets) == 8, targets
    rot = next(c for c in record["carriers"] if c["carrier"] == "visual-strip-rot")
    assert [p["frame"] for p in rot["pages"]] == ["page-1-rot90", "page-1-rot180"]

    for carrier in record["carriers"]:
        assert carrier["evidence_class"] == "independent"
        for page in carrier["pages"]:
            assert page["unavailable"] is None, (carrier["carrier"], page)
            assert page["image"].startswith("data:image/png;base64,")
            assert page["regions"], carrier["carrier"]
            assert all(r["rect_px"] is not None for r in page["regions"])
            assert carrier["carrier"] in html
    assert "page-1-rot180" in html


def test_cli_builds_the_all_examples_bundle_without_serving(tmp_path):
    r = subprocess.run(
        [sys.executable, "-B", "-m", "dsc03.visual.review",
         "--out", str(tmp_path / "index.html")],
        capture_output=True, text=True, timeout=120, cwd=REPO,
        env={**os.environ, "PATH": "/usr/bin:" + os.environ["PATH"]},
    )
    assert r.returncode == 0, r.stderr
    html = (tmp_path / "index.html").read_text()
    assert "visual-review-bundle" in html and "ledger-block" in html


# ---------------------------------------------------------------------------
# descriptor-sourced bundles (sunset-ayj)
# ---------------------------------------------------------------------------


def test_descriptor_fixture_is_validator_passing():
    from dsc03 import validator

    descriptor = json.loads(DESCRIPTOR_FIXTURE.read_text())
    assert validator.validate(descriptor) == []


def test_descriptor_bundle_has_one_entry_per_page_with_verbatim_ids(tmp_path):
    """A multi-page descriptor walks EVERY page target — no silent truncation.

    Pins the descriptor→targets adapter on a committed multi-page fixture:
    pages come from the descriptor's ``kind: page`` regions, claimed regions
    attach through ``contains`` relations, ids are preserved verbatim, and
    page 1's rect is hand-computed through the declared frame (595x842 pt
    page at dpi 72, frame page-1-pt: box (54, 700, 200, 40) pt bottom-left
    y-up → px [54, 842-740, 200, 40]).
    """
    out = tmp_path / "descriptor-review.html"
    record = build_descriptor_review_bundle(DESCRIPTOR_FIXTURE, out)
    assert record["kind"] == "visual-review-bundle" and record["version"] == 2
    (carrier,) = record["carriers"]
    assert carrier["carrier"] == "fixture-cta-cte-review"
    assert carrier["evidence_class"] == "independent"
    pages = carrier["pages"]
    assert [p["page"] for p in pages] == [1, 2]  # no silent truncation
    assert all(p["file"] == "../../../../fixtures/carriers/cta-cte-propietario-redacted.pdf"
               for p in pages)
    page1, _page2 = pages
    assert page1["image"].startswith("data:image/png;base64,")
    assert page1["width"] == 595 and page1["height"] == 842
    assert [r["id"] for r in page1["regions"]] == ["claim-1"]
    # hand-computed through the declared frame (see docstring)
    assert page1["regions"][0]["rect_px"] == [54, 102, 200, 40]
    assert out.is_file() and "fixture-cta-cte-review" in out.read_text()


def test_descriptor_bundle_missing_declared_profile_stays_typed(tmp_path):
    """An unreadable declared geometry profile maps nothing — typed unknown.

    The generator must not crash and must not guess a coordinate
    convention: every page keeps its regions with rect_px null.
    """
    descriptor = json.loads(DESCRIPTOR_FIXTURE.read_text())
    carrier = REPO / "fixtures/carriers/cta-cte-propietario-redacted.pdf"
    descriptor["source"]["locator"] = str(carrier)  # absolute: resolvable from tmp
    descriptor["profiles"][0]["uri"] = "absent-profile.json"  # declared but unreadable
    broken = tmp_path / "descriptor.json"
    broken.write_text(json.dumps(descriptor), encoding="utf-8")

    record = build_descriptor_review_bundle(broken, tmp_path / "out.html")
    for page in record["carriers"][0]["pages"]:
        assert page["unavailable"], page["page"]
        assert page["unavailable"].startswith("frame unknown:")
        assert page["regions"], page["page"]
        assert all(r["rect_px"] is None for r in page["regions"])


def test_descriptor_bundle_unknown_frame_page_keeps_regions(tmp_path):
    out = tmp_path / "descriptor-review.html"
    record = build_descriptor_review_bundle(DESCRIPTOR_FIXTURE, out)
    page2 = record["carriers"][0]["pages"][1]
    assert page2["unavailable"] and page2["unavailable"].startswith("frame unknown:")
    assert [r["id"] for r in page2["regions"]] == ["claim-2"]
    assert page2["regions"][0]["rect_px"] is None
