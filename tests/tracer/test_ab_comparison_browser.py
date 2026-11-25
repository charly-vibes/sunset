"""Purpose: Real-browser acceptance for the attributed A/B comparison journey
(sunset-36n; document-debugger-comparison "Browser comparison and replay
journey" and "Independent-reader agreement").
Responsibilities: Build the minimal ab-comparison review bundle from the two
committed bank-statement observation sheets (sheet-import API stubbed at the
shared contract seam, comparison driven by dsc03.compare.scoped_compare), then
drive headless Chromium and assert both attributed readings render side by side
with the PDF source pane, per-page outcomes and witnesses are visible, and no
element, attribute, record key or counterexample encodes a winner or a
cross-reader region identity. Also pins the bundle-level rules: identical
claims compare equivalent and export nothing; a missing reading stays typed
unexamined, never agreement.
Rationale: the comparison layer's no-winner / no-identity invariants are data
invariants — the bundle must not carry them, so the browser can't invent them;
and the real_browser_gate — the journey fails, never skips, without the
browser runtime.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

from dsc03.compare import (
    RULE_TEXT_DIFFERENT,
    ComparatorSpec,
    ComparisonInput,
    scoped_compare,
)
from dsc03.visual import review

REPO = Path(__file__).resolve().parents[2]
OBSERVATIONS_A = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-a.observations.json"
OBSERVATIONS_B = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-b.observations.json"
CARRIER_PDF = REPO / "fixtures/carriers/bank-statement-ca-excerpt.pdf"
CARRIER = "bank-statement-ca-excerpt"
SHEET_A = CARRIER + "-a"
SHEET_B = CARRIER + "-b"

_IDENTITY_INFERENCE_KEYS = re.compile(
    r"winner|counterpart|cross_reader|crossreader|paired|matching|correspond",
    re.IGNORECASE)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fixture_regions(sheet_id, reader, path):
    """Region dicts in the shared sheet-import contract shape, derived from the
    committed observations fixture."""
    obs = json.loads(path.read_text(encoding="utf-8"))
    carrier_sha = _sha256(CARRIER_PDF)
    regions = []
    for index, entry in enumerate(obs["structure"], start=1):
        bbox = entry["bbox"]
        regions.append({
            "sheet_id": sheet_id,
            "region_id": f"{sheet_id}:{entry.get('label') or index}",
            "reader": reader,
            "page": int(entry["page"]),
            "bbox_px": [bbox["x"] * bbox["viewport_w"], bbox["y"] * bbox["viewport_h"],
                        bbox["w"] * bbox["viewport_w"], bbox["h"] * bbox["viewport_h"]],
            "bbox_relative": [bbox["x"], bbox["y"], bbox["w"], bbox["h"]],
            "viewport_w": bbox["viewport_w"], "viewport_h": bbox["viewport_h"],
            "carrier_sha256": carrier_sha,
            "type": entry.get("type") or "",
            "type_provenance": "human" if (entry.get("type") or "").strip() else "blank",
            "order_rank": entry.get("order_rank"),
            "order_alternatives": entry.get("order_alternatives") or [],
            "evidence": entry.get("evidence") or "",
        })
    return regions


def _regions_for_pages(regions, pages):
    """Keep only regions whose page is in `pages` (used to synthesize readings
    that disagree by omission)."""
    return [r for r in regions if r["page"] in pages]


def _stub_result(regions_by_sheet=None):
    """SheetImportResult per the shared producer contract. `regions_by_sheet`
    overrides the fixture-derived region sets (synthetic claims for the
    equivalent/unexamined cases)."""
    from dsc03.visual.sheet_import import SheetImportResult

    sheets = []
    all_regions = []
    carrier_sha = _sha256(CARRIER_PDF)
    defaults = {SHEET_A: ("reader-a", OBSERVATIONS_A), SHEET_B: ("reader-b", OBSERVATIONS_B)}
    for sheet_id, (default_reader, path) in defaults.items():
        reader = default_reader
        regions = None
        if regions_by_sheet and sheet_id in regions_by_sheet:
            reader, regions = regions_by_sheet[sheet_id]
        obs = json.loads(path.read_text(encoding="utf-8"))
        sheets.append({"sheet_id": sheet_id, "reader": reader, "carrier": CARRIER,
                       "source_sha256": carrier_sha,
                       "page_frames": obs["page_frames"]})
        if regions is None:
            regions = _fixture_regions(sheet_id, reader, path)
        all_regions.extend(regions)
    return SheetImportResult(sheets=sheets, regions=all_regions, refusals=[])


def _build(monkeypatch, tmp_path, result, spec=None):
    monkeypatch.setattr(review, "_import_sheets",
                        lambda sheet_paths, *, source_root: result)
    out = tmp_path / "compare.html"
    record = review.build_ab_comparison_bundle(
        [OBSERVATIONS_A, OBSERVATIONS_B], source_root=REPO, out_path=out,
        spec=spec)
    return record, out


@pytest.fixture
def compare_bundle(monkeypatch, tmp_path):
    return _build(monkeypatch, tmp_path, _stub_result())


@pytest.fixture
def browser_page(compare_bundle):
    """Headless Chromium over the built compare bundle (file://); the journey
    fails — never skips — when the browser runtime is unavailable."""
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError as exc:  # pragma: no cover - environment gate
        pytest.fail(f"playwright unavailable — the sunset-36n journey fails, "
                    f"never skips (canonical CI: pip install playwright + "
                    f"playwright install chromium): {exc}")
    with sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch(headless=True)
        except PlaywrightError as exc:  # pragma: no cover - environment gate
            pytest.fail(f"chromium unavailable for playwright — the sunset-36n "
                        f"journey fails, never skips (canonical CI: playwright "
                        f"install chromium): {exc}")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(compare_bundle[1].as_uri())
        yield page
        browser.close()


def _claims(regions):
    """The declared scoped observable, rebuilt independently from the fixture:
    one line per region (file order; the committed sheets' order_rank values
    are ascending in file order, asserted below) carrying the type claim."""
    ranks = [str(r.get("order_rank")) for r in regions]
    assert ranks == sorted(ranks), "fixture assumes file order == claimed order"
    return {"flattened_text": "\n".join(str(r.get("type") or "") for r in regions)}


def _expected_outcome():
    """The outcome the DOM must show, computed here straight through
    dsc03.compare.scoped_compare — not through the bundle builder."""
    obs_a = json.loads(OBSERVATIONS_A.read_text(encoding="utf-8"))
    obs_b = json.loads(OBSERVATIONS_B.read_text(encoding="utf-8"))
    spec = ComparatorSpec("reading-claims", "1",
                          ("reading-claims", "reading-claims"),
                          ("flattened_text",))
    left = ComparisonInput("reading-claims", _claims(obs_a["structure"]))
    right = ComparisonInput("reading-claims", _claims(obs_b["structure"]))
    return scoped_compare(spec, left, right)


# ---------------------------------------------------------------------------
# browser journeys
# ---------------------------------------------------------------------------


def test_both_attributed_readings_render_beside_the_pdf_source(browser_page,
                                                               compare_bundle):
    record, _ = compare_bundle
    page = browser_page
    assert page.locator("#wrap-compare-source img").count() == 1, \
        "the pinned PDF source pane must render"
    counts = {"reader-a": 1, "reader-b": 3}
    for pane, reader in (("a", "reader-a"), ("b", "reader-b")):
        title = page.locator(f"#reading-title-{pane}").inner_text()
        assert reader in title and f"{CARRIER}-{pane}" in title, \
            "each reading pane must carry its attribution (reader + sheet)"
        assert page.locator(f"#reading-list-{pane} .region-row").count() == \
            counts[reader]
        boxes = page.locator(f"#wrap-reading-{pane} .box")
        assert boxes.count() == counts[reader]
        for i in range(boxes.count()):
            assert boxes.nth(i).get_attribute("data-reader") == reader
        rows = page.locator(f"#reading-list-{pane} .region-row")
        for i in range(rows.count()):
            assert rows.nth(i).get_attribute("data-reader") == reader
            assert "provenance: blank" in rows.nth(i).inner_text()
    assert [r["reader"] for r in record["readings"]] == ["reader-a", "reader-b"]


def test_outcomes_and_witnesses_are_visible_from_scoped_compare(browser_page,
                                                                compare_bundle):
    expected = _expected_outcome()
    page = browser_page
    row = page.locator('.comparison-row[data-page="1"]')
    assert row.count() == 1
    assert row.get_attribute("data-outcome") == expected.outcome
    assert row.get_attribute("data-witness") == expected.witness
    assert row.get_attribute("data-rule-id") == RULE_TEXT_DIFFERENT
    text = row.inner_text()
    assert expected.outcome in text and expected.witness in text
    assert RULE_TEXT_DIFFERENT in text
    scope_line = page.locator("#compare-scope-line").inner_text()
    assert "flattened_text" in scope_line, "the declared scope must be visible"
    assert "reading-claims" in scope_line, "the comparator policy must be visible"


def test_no_element_or_attribute_encodes_a_winner(browser_page, compare_bundle):
    record, _ = compare_bundle
    page = browser_page
    hits = page.evaluate(
        """
        () => {
          const hits = [];
          /* the compare journey's rendered surface only: the hidden
             verdict-mode pane keeps its own review-rules copy and is not
             part of this journey */
          document.querySelectorAll('#mode-compare, #mode-compare *')
            .forEach(el => {
              el.getAttributeNames().forEach(a => {
                const v = a + '=' + (el.getAttribute(a) || '');
                if (/\bwinner\b|\belected\b|promoted side/i.test(v)) {
                  hits.push('attr:' + v.slice(0, 60));
                }
              });
              if (/\bwinner\b/i.test(el.id)) hits.push('id:' + el.id);
              if (/\bwinner\b/i.test(el.getAttribute('class') || '')) hits.push('class');
              if (/\bwinner\b/i.test(el.getAttribute('aria-label') || '')) hits.push('aria');
            });
          const surface = (document.getElementById('mode-compare').innerText || '');
          if (/\bwinner\b|\belected\b/i.test(surface)) hits.push('surface-text');
          const scan = o => {
            if (Array.isArray(o)) { o.forEach(scan); return; }
            if (o && typeof o === 'object') {
              Object.keys(o).forEach(k => {
                if (/\bwinner\b|\belected\b/i.test(k)) hits.push('key:' + k);
                scan(o[k]);
              });
            }
          };
          scan(DATA);
          return hits;
        }
        """
    )
    assert hits == [], f"winner-encoded UI found: {hits}"
    def _keys(node):
        out = set()
        if isinstance(node, dict):
            out.update(node.keys())
            for value in node.values():
                out |= _keys(value)
        elif isinstance(node, list):
            for value in node:
                out |= _keys(value)
        return out
    assert not any(_IDENTITY_INFERENCE_KEYS.search(k) for k in _keys(record)), \
        "bundle keys must not encode a winner or cross-reader identity"
    for region in (r for reading in record["readings"]
                   for pg in reading["pages"] for r in pg["regions"]):
        assert not any(_IDENTITY_INFERENCE_KEYS.search(k) for k in region), \
            "region entries must not pair readings by inferred identity"


# ---------------------------------------------------------------------------
# bundle-level rules (no browser needed)
# ---------------------------------------------------------------------------


def test_record_outcome_matches_scoped_compare(compare_bundle):
    record, _ = compare_bundle
    expected = _expected_outcome()
    assert record["mode"] == "ab-comparison"
    entry = next(c for c in record["comparisons"] if c["page"] == 1)
    assert entry["outcome"] == expected.outcome == "different"
    assert entry["witness"] == expected.witness
    assert entry["rule_id"] == expected.rule_id
    assert entry["scope"] == ["flattened_text"]
    assert entry["missing_reading"] is None
    assert record["counterexamples"], "a disagreement must export a counterexample"


def test_identical_claims_compare_equivalent_and_export_nothing(monkeypatch,
                                                                tmp_path):
    from dsc03.visual.sheet_import import SheetImportResult

    def _claim(sheet_id, reader, index, type_):
        return {"sheet_id": sheet_id, "region_id": f"{sheet_id}:{index}",
                "reader": reader, "page": 1,
                "bbox_px": [1.0, 1.0, 2.0, 2.0],
                "bbox_relative": [0.1, 0.1, 0.2, 0.2],
                "viewport_w": 966, "viewport_h": 1250,
                "carrier_sha256": _sha256(CARRIER_PDF),
                "type": type_, "type_provenance": "human",
                "order_rank": str(index), "order_alternatives": [],
                "evidence": "synthetic claim"}
    obs = json.loads(OBSERVATIONS_A.read_text(encoding="utf-8"))
    regions_a = [_claim(SHEET_A, "reader-a", 1, "heading")]
    regions_b = [_claim(SHEET_B, "reader-b", 1, "heading")]
    sheets = [
        {"sheet_id": SHEET_A, "reader": "reader-a", "carrier": CARRIER,
         "source_sha256": _sha256(CARRIER_PDF), "page_frames": obs["page_frames"]},
        {"sheet_id": SHEET_B, "reader": "reader-b", "carrier": CARRIER,
         "source_sha256": _sha256(CARRIER_PDF), "page_frames": obs["page_frames"]},
    ]
    result = SheetImportResult(sheets=sheets, regions=regions_a + regions_b,
                               refusals=[])
    record, _ = _build(monkeypatch, tmp_path, result)
    entry = record["comparisons"][0]
    assert entry["outcome"] == "equivalent"
    assert entry["rule_id"] == "dbg.compare.equivalent"
    assert record["counterexamples"] == [], \
        "an equivalent comparison must not export a counterexample"


def test_missing_reading_stays_unexamined_not_agreement(monkeypatch, tmp_path):
    """A reader with no recorded claims on a page is typed unexamined —
    absence is never converted into agreement (loss_visibility)."""
    stub = _stub_result()
    regions_a = [r for r in stub.regions if r["sheet_id"] == SHEET_A]
    regions_b = [dict(r, page=2)
                 for r in stub.regions if r["sheet_id"] == SHEET_B]
    from dsc03.visual.sheet_import import SheetImportResult
    result = SheetImportResult(sheets=stub.sheets,
                               regions=regions_a + regions_b, refusals=[])
    record, _ = _build(monkeypatch, tmp_path, result)
    by_page = {c["page"]: c for c in record["comparisons"]}
    assert by_page[1]["outcome"] == "unexamined"
    assert by_page[1]["missing_reading"] == "reader-b"
    assert by_page[1]["rule_id"] == "dbg.compare.unexamined"
    assert by_page[2]["outcome"] == "unexamined"
    assert by_page[2]["missing_reading"] == "reader-a"
    assert "absence is not agreement" in by_page[1]["message"]
    assert record["counterexamples"] == [], \
        "a builder-level unexamined page pins no replayable disagreement"
