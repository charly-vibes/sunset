"""Purpose: Real-browser acceptance for the source-linked inspection journey
(sunset-5bu; document-debugger "Executable PDF inspection journey" and
"Accessible inspection", document-adapters total_accounting/declared_frames).
Responsibilities: Build the minimal import-inspection review bundle from
committed fixtures (the smallest human observation sheets plus the matching
carrier PDF) with the sibling sheet-import API stubbed at the shared contract
seam, then drive headless Chromium through pointer selection and keyboard
navigation, asserting that the source-pane highlight is exactly the recorded
page-frame transform of the imported region (bbox_px -> source px), that
regions carry their type_provenance visibly, and that every import refusal
renders as a typed unresolved entry instead of a silent drop.
Rationale: the layer contract's real_browser_gate — acceptance SHALL execute
an actual browser and SHALL fail, never skip, when the browser runtime is
unavailable; modeled interaction alone does not satisfy it.
"""

import hashlib
import json
from pathlib import Path

import pytest

from dsc03.visual import review

REPO = Path(__file__).resolve().parents[2]
OBSERVATIONS_A = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-a.observations.json"
OBSERVATIONS_B = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-b.observations.json"
CARRIER_PDF = REPO / "fixtures/carriers/bank-statement-ca-excerpt.pdf"
CARRIER = "bank-statement-ca-excerpt"
SHEET_A = CARRIER + "-a"
SHEET_B = CARRIER + "-b"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fixture_region(sheet_id, reader, index, entry, carrier_sha):
    """One region dict in the shared sheet-import contract shape, derived from
    the committed observations fixture (never invented geometry)."""
    bbox = entry["bbox"]
    return {
        "sheet_id": sheet_id,
        "region_id": f"{sheet_id}:{entry.get('label') or index}",
        "reader": reader,
        "page": int(entry["page"]),
        "bbox_px": [bbox["x"] * bbox["viewport_w"], bbox["y"] * bbox["viewport_h"],
                    bbox["w"] * bbox["viewport_w"], bbox["h"] * bbox["viewport_h"]],
        "bbox_relative": [bbox["x"], bbox["y"], bbox["w"], bbox["h"]],
        "viewport_w": bbox["viewport_w"],
        "viewport_h": bbox["viewport_h"],
        "carrier_sha256": carrier_sha,
        "type": entry.get("type") or "",
        "type_provenance": "human" if (entry.get("type") or "").strip() else "blank",
        "order_rank": entry.get("order_rank"),
        "order_alternatives": entry.get("order_alternatives") or [],
        "evidence": entry.get("evidence") or "",
    }


def _stub_result(wrong_digest_for=None, drop_frames_for=None, extra_region=None,
                 refusal=None):
    """SheetImportResult per the shared producer contract, built from the
    committed fixture sheets (dsc03/visual/sheet_import.py is sibling-owned;
    only its contract shape is used here)."""
    from dsc03.visual.sheet_import import ImportRefusal, SheetImportResult

    sheets, regions = [], []
    carrier_sha = _sha256(CARRIER_PDF)
    for sheet_id, reader, path in ((SHEET_A, "reader-a", OBSERVATIONS_A),
                                   (SHEET_B, "reader-b", OBSERVATIONS_B)):
        obs = json.loads(path.read_text(encoding="utf-8"))
        pinned = "0" * 64 if wrong_digest_for == sheet_id else carrier_sha
        page_frames = {} if drop_frames_for == sheet_id else obs["page_frames"]
        sheets.append({"sheet_id": sheet_id, "reader": reader, "carrier": CARRIER,
                       "source_sha256": pinned, "page_frames": page_frames})
        for i, entry in enumerate(obs["structure"], start=1):
            regions.append(_fixture_region(sheet_id, reader, i, entry, carrier_sha))
    if extra_region is not None:
        regions.append(extra_region)
    refusals = []
    if refusal is not None:
        refusals.append(ImportRefusal(region_key=refusal["region_key"],
                                      reason=refusal["reason"],
                                      detail=refusal["detail"]))
    return SheetImportResult(sheets=sheets, regions=regions, refusals=refusals)


def _build(monkeypatch, tmp_path, result, source_pdf=None):
    monkeypatch.setattr(review, "_import_sheets",
                        lambda sheet_paths, *, source_root: result)
    out = tmp_path / "inspect.html"
    record = review.build_import_review_bundle(
        [OBSERVATIONS_A, OBSERVATIONS_B], source_root=REPO, out_path=out,
        source_pdf=source_pdf)
    return record, out


@pytest.fixture
def inspect_bundle(monkeypatch, tmp_path):
    """The journey bundle: both committed fixture sheets for the carrier plus
    one typed import refusal that must stay visible."""
    result = _stub_result(refusal={"region_key": f"{SHEET_B}:9",
                                   "reason": "missing-frame",
                                   "detail": "no page frame recorded for page 2"})
    return _build(monkeypatch, tmp_path, result)


@pytest.fixture
def browser_page(inspect_bundle):
    """Headless Chromium over the built bundle (file://), failing — never
    skipping — when the browser runtime is unavailable (real_browser_gate)."""
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError as exc:  # pragma: no cover - environment gate
        pytest.fail(f"playwright unavailable — the sunset-5bu journey fails, "
                    f"never skips (canonical CI: pip install playwright + "
                    f"playwright install chromium): {exc}")
    with sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch(headless=True)
        except PlaywrightError as exc:  # pragma: no cover - environment gate
            pytest.fail(f"chromium unavailable for playwright — the sunset-5bu "
                        f"journey fails, never skips (canonical CI: playwright "
                        f"install chromium): {exc}")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(inspect_bundle[1].as_uri())
        yield page
        browser.close()


def _committed_frames_are_full_page(record):
    """Guard: the committed page_frames are full-page frames (x=0, y=0, w=1,
    h=1), so bbox_relative maps 1:1 onto the rendered source extent and the
    expected highlight is hand-computable from the fixture alone."""
    for sheet in record["carriers"][0]["sheets"]:
        frame = sheet["page_frames"]["1"]
        assert (frame["x"], frame["y"], frame["w"], frame["h"]) == (0, 0, 1, 1)


def _expected_rects(record):
    """region_id -> expected source-page rect, recomputed here from the
    committed fixture values and the record's rendered extent (independent of
    the builder's frame math)."""
    _committed_frames_are_full_page(record)
    page = record["carriers"][0]["pages"][0]
    return {r["region_id"]: [round(r["bbox_relative"][0] * page["width"]),
                             round(r["bbox_relative"][1] * page["height"]),
                             round(r["bbox_relative"][2] * page["width"]),
                             round(r["bbox_relative"][3] * page["height"])]
            for r in page["regions"]}


# ---------------------------------------------------------------------------
# browser journeys
# ---------------------------------------------------------------------------


def test_click_moves_source_highlight_to_the_frame_mapped_rect(browser_page,
                                                               inspect_bundle):
    record, _ = inspect_bundle
    page = browser_page
    expected = _expected_rects(record)
    rows = page.locator("#inspect-region-list .region-row")
    assert rows.count() == 4, "all four imported fixture regions must render"
    for rid in expected:
        page.locator(f'.region-row[data-rid="{rid}"]').click()
        box = page.locator("#wrap-inspect .box.selected")
        assert box.get_attribute("data-rid") == rid
        assert json.loads(box.get_attribute("data-rect")) == expected[rid], (
            f"highlight for {rid} must be the recorded page-frame transform "
            f"of bbox_px onto the pinned source render")


def test_overlapping_region_is_selectable_from_the_clickable_row_surface(
        browser_page, inspect_bundle):
    """Region boxes overlap on real sheets, so the overlays render as pure
    visual highlights (pointer-events: none) and the region rows are the
    pointer activation surface: clicking a row must select its region
    exactly — including a region whose box overlaps other boxes on the
    source pane — and overlay hit-testing can never intercept it."""
    record, _ = inspect_bundle
    page = browser_page
    expected = _expected_rects(record)
    rid = f"{SHEET_B}:3"   # overlapping/adjacent strip (h=14px) on the sheet
    assert rid in expected
    row = page.locator(f'.region-row[data-rid="{rid}"]')
    assert row.count() == 1
    row.click()   # real pointer activation on the clickable row surface
    box = page.locator("#wrap-inspect .box.selected")
    assert box.get_attribute("data-rid") == rid
    assert json.loads(box.get_attribute("data-rect")) == expected[rid]
    # regression guard for this journey: overlays stay click-transparent so
    # overlapping boxes can never intercept region activation
    overlay = page.locator(f'#wrap-inspect .box[data-rid="{rid}"]')
    assert overlay.evaluate("el => getComputedStyle(el).pointerEvents") == "none"


def test_keyboard_navigation_traverses_regions_and_moves_the_highlight(
        browser_page, inspect_bundle):
    record, _ = inspect_bundle
    page = browser_page
    expected = _expected_rects(record)
    ids = list(expected)  # DOM order: claimed-order sort of the fixture regions
    rows = page.locator("#inspect-region-list .region-row")

    rows.first.focus()
    box = page.locator("#wrap-inspect .box.selected")
    assert box.get_attribute("data-rid") == ids[0]
    assert json.loads(box.get_attribute("data-rect")) == expected[ids[0]]

    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.dataset.rid") == ids[1]
    assert page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rid") == ids[1]
    assert json.loads(page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rect")) == expected[ids[1]]

    page.keyboard.press("ArrowUp")
    assert page.evaluate("document.activeElement.dataset.rid") == ids[0]
    assert json.loads(page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rect")) == expected[ids[0]]

    page.keyboard.press("Enter")
    assert page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rid") == ids[0]
    assert json.loads(page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rect")) == expected[ids[0]]

    rows.first.focus()
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.dataset.rid") == ids[1]
    assert page.locator("#wrap-inspect .box.selected").get_attribute(
        "data-rid") == ids[1]


def test_import_refusal_renders_as_typed_unresolved_entry(browser_page,
                                                          inspect_bundle):
    page = browser_page
    refusals = page.locator('.refusal-row[data-refusal-reason="missing-frame"]')
    assert refusals.count() == 1, "the typed import refusal must stay visible"
    ref = refusals.first
    assert ref.get_attribute("data-region-key") == f"{SHEET_B}:9"
    text = ref.inner_text()
    assert "REFUSAL" in text and "unresolved" in text.lower()
    assert "page 2" in text, "the refusal detail must be shown, not summarized away"
    progress = page.locator("#inspect-progress").inner_text()
    assert "1 unresolved import refusal" in progress


def test_regions_carry_visible_type_provenance(browser_page, inspect_bundle):
    page = browser_page
    rows = page.locator("#inspect-region-list .region-row")
    for i in range(rows.count()):
        row = rows.nth(i)
        assert row.get_attribute("data-provenance") == "blank", (
            "blank fixture types must be labeled blank, never human")
        assert "provenance: blank" in row.inner_text()


# ---------------------------------------------------------------------------
# typed unmapped / mismatch states (bundle level; no browser needed)
# ---------------------------------------------------------------------------


def test_region_with_missing_frame_gets_no_invented_highlight(monkeypatch,
                                                              tmp_path):
    result = _stub_result(drop_frames_for=SHEET_B)
    record, _ = _build(monkeypatch, tmp_path, result)
    page1 = record["carriers"][0]["pages"][0]
    by_id = {r["region_id"]: r for r in page1["regions"]}
    assert by_id[f"{SHEET_A}:1"]["rect_px"] is not None
    lost = by_id[f"{SHEET_B}:1"]
    assert lost["rect_px"] is None
    assert lost["unmapped_reason"].startswith("missing-frame")


def test_source_digest_mismatch_refuses_the_highlight(monkeypatch, tmp_path):
    result = _stub_result(wrong_digest_for=SHEET_A)
    record, _ = _build(monkeypatch, tmp_path, result)
    carrier = record["carriers"][0]
    assert carrier["source_digest_mismatch"] == [
        {"sheet_id": SHEET_A, "expected": "0" * 64, "actual": _sha256(CARRIER_PDF)}]
    page1 = carrier["pages"][0]
    by_id = {r["region_id"]: r for r in page1["regions"]}
    refused = by_id[f"{SHEET_A}:1"]
    assert refused["rect_px"] is None
    assert refused["unmapped_reason"].startswith("source-digest-mismatch")
    kept = by_id[f"{SHEET_B}:1"]
    assert kept["rect_px"] is not None


def test_every_input_region_and_refusal_is_accounted_for(monkeypatch, tmp_path):
    result = _stub_result(refusal={"region_key": f"{SHEET_B}:9",
                                   "reason": "missing-frame",
                                   "detail": "no page frame recorded for page 2"})
    record, _ = _build(monkeypatch, tmp_path, result)
    carrier = record["carriers"][0]
    rendered = [r for page in carrier["pages"] for r in page["regions"]]
    assert len(rendered) == len(result.regions), "regions are never dropped"
    assert sorted(r["region_id"] for r in rendered) == sorted(
        r.region_id if hasattr(r, "region_id") else r["region_id"]
        for r in result.regions)
    assert carrier["refusals"] == [{
        "region_key": f"{SHEET_B}:9", "reason": "missing-frame",
        "detail": "no page frame recorded for page 2"}]
    assert record["mode"] == "import-inspection"
