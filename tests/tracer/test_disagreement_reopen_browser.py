"""Purpose: Real-browser acceptance for the export/reopen disagreement journey
(sunset-j1c; document-debugger-comparison "Export a replayable counterexample"
and "Reopen an exported disagreement" / "Reopen without matching source").
Responsibilities: Build the ab-comparison bundle for the committed fixture
sheets, export the pinned counterexample bundle through the SPA export button
(product of dsc03.compare.export_counterexample + serialize_bundle, pinned at
bundle-build time), reopen it in the browser against the matching local PDF and
assert the outcome and locus are reproduced, reopen against a wrong local PDF
and assert the explicit typed source-digest-mismatch state, and reopen a
redacted bundle into the typed not-replayable state. Cross-checks the browser
replay against the canonical Python reopen path (dsc03.compare.load_bundle +
replay, refusing per NotReplayable).
Rationale: replay must re-derive the disagreement from pinned inputs after the
local source digest is verified — never claim a successful source replay on a
mismatch, never fabricate a reproducible source; and the real_browser_gate —
the journey fails, never skips, without the browser runtime.
"""

import hashlib
import json
from pathlib import Path

import pytest

from dsc03.compare import RULE_TEXT_DIFFERENT, load_bundle, serialize_bundle
from dsc03.visual import review

REPO = Path(__file__).resolve().parents[2]
OBSERVATIONS_A = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-a.observations.json"
OBSERVATIONS_B = REPO / "hitl/sunset-905.3/bank-statement-ca-excerpt-b.observations.json"
CARRIER_PDF = REPO / "fixtures/carriers/bank-statement-ca-excerpt.pdf"
CARRIER = "bank-statement-ca-excerpt"
SHEET_A = CARRIER + "-a"
SHEET_B = CARRIER + "-b"

# reader-a claims one blank-typed region; reader-b claims three — the
# flattened claim texts therefore differ and scoped_compare must disagree.
CLAIMS_A = {"flattened_text": ""}
CLAIMS_B = {"flattened_text": "\n\n"}


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _stub_result():
    """SheetImportResult per the shared producer contract from the committed
    fixture sheets (sibling-owned dsc03/visual/sheet_import.py: only its
    contract shape is used)."""
    from dsc03.visual.sheet_import import SheetImportResult

    sheets, regions = [], []
    carrier_sha = _sha256(CARRIER_PDF)
    for sheet_id, reader, path in ((SHEET_A, "reader-a", OBSERVATIONS_A),
                                   (SHEET_B, "reader-b", OBSERVATIONS_B)):
        obs = json.loads(path.read_text(encoding="utf-8"))
        sheets.append({"sheet_id": sheet_id, "reader": reader, "carrier": CARRIER,
                       "source_sha256": carrier_sha,
                       "page_frames": obs["page_frames"]})
        for index, entry in enumerate(obs["structure"], start=1):
            bbox = entry["bbox"]
            regions.append({
                "sheet_id": sheet_id,
                "region_id": f"{sheet_id}:{entry.get('label') or index}",
                "reader": reader,
                "page": int(entry["page"]),
                "bbox_px": [bbox["x"] * bbox["viewport_w"],
                            bbox["y"] * bbox["viewport_h"],
                            bbox["w"] * bbox["viewport_w"],
                            bbox["h"] * bbox["viewport_h"]],
                "bbox_relative": [bbox["x"], bbox["y"], bbox["w"], bbox["h"]],
                "viewport_w": bbox["viewport_w"],
                "viewport_h": bbox["viewport_h"],
                "carrier_sha256": carrier_sha,
                "type": entry.get("type") or "",
                "type_provenance": "blank",
                "order_rank": entry.get("order_rank"),
                "order_alternatives": entry.get("order_alternatives") or [],
                "evidence": entry.get("evidence") or "",
            })
    return SheetImportResult(sheets=sheets, regions=regions, refusals=[])


@pytest.fixture
def compare_bundle(monkeypatch, tmp_path):
    result = _stub_result()
    monkeypatch.setattr(review, "_import_sheets",
                        lambda sheet_paths, *, source_root: result)
    out = tmp_path / "compare.html"
    record = review.build_ab_comparison_bundle(
        [OBSERVATIONS_A, OBSERVATIONS_B], source_root=REPO, out_path=out)
    return record, out


@pytest.fixture
def browser_page(compare_bundle):
    """Headless Chromium over the built compare bundle (file://); the journey
    fails — never skips — when the browser runtime is unavailable."""
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError as exc:  # pragma: no cover - environment gate
        pytest.fail(f"playwright unavailable — the sunset-j1c journey fails, "
                    f"never skips (canonical CI: pip install playwright + "
                    f"playwright install chromium): {exc}")
    with sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch(headless=True)
        except PlaywrightError as exc:  # pragma: no cover - environment gate
            pytest.fail(f"chromium unavailable for playwright — the sunset-j1c "
                        f"journey fails, never skips (canonical CI: playwright "
                        f"install chromium): {exc}")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(compare_bundle[1].as_uri())
        yield page
        browser.close()


def _export_counterexample(browser_page):
    """Drive the export button and return (raw bytes, temp file path)."""
    page = browser_page
    with page.expect_download() as saved:
        page.locator("#export-counterexample").click()
    path = Path(saved.value.path())
    return path.read_bytes(), path


def _reopen(browser_page, bundle_path, pdf_path, state):
    page = browser_page
    page.locator("#reopen-bundle").set_input_files(str(bundle_path))
    page.locator("#reopen-pdf").set_input_files(str(pdf_path))
    page.locator("#reopen-run").click()
    page.wait_for_function(
        'document.querySelector("#reopen-status") && '
        'document.querySelector("#reopen-status").dataset.state === ' + json.dumps(state))
    return page.locator("#reopen-status").inner_text()


# ---------------------------------------------------------------------------
# browser journeys
# ---------------------------------------------------------------------------


def test_export_button_downloads_the_pinned_counterexample_bundle(
        browser_page, compare_bundle):
    raw, _ = _export_counterexample(browser_page)
    assert raw == serialize_bundle(load_bundle(raw)), \
        "the export must be the byte-deterministic serialize_bundle product"
    bundle = load_bundle(raw)
    witness = bundle["witness"]
    assert witness["rule_id"] == RULE_TEXT_DIFFERENT
    assert witness["outcome"] == "different"
    assert witness["replayable"] is True
    assert witness["observable_scope"] == ["flattened_text"]
    assert witness["comparator"] == {"id": "reading-claims", "version": "1"}
    assert bundle["inputs"]["left"]["payload"] == CLAIMS_A
    assert bundle["inputs"]["right"]["payload"] == CLAIMS_B
    for side, claims in (("left", CLAIMS_A), ("right", CLAIMS_B)):
        assert bundle["inputs"][side]["source_sha256"] == _sha256(CARRIER_PDF)
        expected_hash = hashlib.sha256(
            json.dumps(claims, sort_keys=True).encode("utf-8")).hexdigest()
        assert witness["input_hashes"][side] == expected_hash


def test_reopen_with_matching_source_reproduces_outcome_and_locus(
        browser_page, compare_bundle):
    record, _ = compare_bundle
    raw, path = _export_counterexample(browser_page)
    digest = _sha256(CARRIER_PDF)
    text = _reopen(browser_page, path, CARRIER_PDF, "replayed")
    assert "different" in text and "char:0" in text, \
        "the replayed outcome and witness must be visible"
    assert "matches the exported" in text
    assert digest[:12] in text, "the locus must name the verified source digest"
    canonical = review.reopen_counterexample(raw, CARRIER_PDF)
    assert canonical["status"] == "replayed"
    assert canonical["outcome"] == "different"
    assert canonical["rule_id"] == RULE_TEXT_DIFFERENT
    assert canonical["witness"] == "char:0"
    assert canonical["matches_exported"] is True
    assert canonical["locus"]["source_digest"] == digest
    entry = next(c for c in record["comparisons"] if c["page"] == 1)
    assert canonical["outcome"] == entry["outcome"]
    assert canonical["witness"] == entry["witness"]


def test_reopen_with_wrong_source_shows_the_mismatch_state(browser_page,
                                                           compare_bundle,
                                                           tmp_path):
    raw, path = _export_counterexample(browser_page)
    wrong = tmp_path / "wrong-source.pdf"
    wrong.write_bytes(CARRIER_PDF.read_bytes() + b"\n")
    actual = hashlib.sha256(wrong.read_bytes()).hexdigest()
    text = _reopen(browser_page, path, wrong, "source-digest-mismatch")
    assert "replay refused" in text.lower()
    assert _sha256(CARRIER_PDF) in text and actual in text, \
        "both the pinned and the actual digest must be shown"
    canonical = review.reopen_counterexample(raw, wrong)
    assert canonical["status"] == "source-digest-mismatch"
    assert canonical["expected"] == [_sha256(CARRIER_PDF), _sha256(CARRIER_PDF)]
    assert canonical["actual"] == actual


def test_redacted_bundle_reopens_not_replayable(browser_page, compare_bundle,
                                                tmp_path):
    _export_counterexample(browser_page)
    redacted = tmp_path / "redacted.json"
    redacted.write_text(json.dumps({
        "witness": {"replayable": False, "rule_id": RULE_TEXT_DIFFERENT,
                    "outcome": "different",
                    "replay_limitations": ["source bytes omitted (redacted)"]}}))
    text = _reopen(browser_page, redacted, CARRIER_PDF, "not-replayable")
    assert "redacted" in text.lower()


# ---------------------------------------------------------------------------
# canonical Python reopen path (typed at every refusal; no browser needed)
# ---------------------------------------------------------------------------


def test_reopen_path_is_typed_at_every_refusal(tmp_path):
    from dsc03.compare import (
        ComparatorSpec,
        ComparisonInput,
        ComparisonOutcome,
        export_counterexample,
    )

    spec = ComparatorSpec("reading-claims", "1",
                          ("reading-claims", "reading-claims"),
                          ("flattened_text",))
    left = ComparisonInput("reading-claims", CLAIMS_A,
                           source_sha256=_sha256(CARRIER_PDF))
    right = ComparisonInput("reading-claims", CLAIMS_B,
                            source_sha256=_sha256(CARRIER_PDF))
    outcome = ComparisonOutcome("different", RULE_TEXT_DIFFERENT, "char:0",
                                "flattened text differs")

    redacted = serialize_bundle(export_counterexample(
        outcome, spec, left, right, redact=True))
    refused = review.reopen_counterexample(redacted, CARRIER_PDF)
    assert refused["status"] == "not-replayable", \
        "NotReplayable is the existing typed signal for withheld sources"

    unverified = serialize_bundle({
        "witness": {"replayable": True, "outcome": "different",
                    "rule_id": RULE_TEXT_DIFFERENT,
                    "comparator": {"id": "reading-claims", "version": "1"},
                    "endpoint_types": ["reading-claims", "reading-claims"],
                    "observable_scope": ["flattened_text"]},
        "inputs": {"left": {"endpoint_type": "reading-claims", "payload": CLAIMS_A},
                   "right": {"endpoint_type": "reading-claims", "payload": CLAIMS_B}}})
    assert review.reopen_counterexample(unverified, CARRIER_PDF)["status"] == \
        "source-digest-unavailable", \
        "no source digest pinned: replay must be refused, never guessed"

    assert review.reopen_counterexample(b"{not json", CARRIER_PDF)["status"] == \
        "invalid-bundle"
