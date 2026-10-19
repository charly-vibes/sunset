# Purpose: Slice-2 tests for carrier locator adapters and synchronized selection
#   (sunset-xx7.2, add-document-structural-debugger).
# Responsibilities: Assert PDF fixed-coordinate resolution (intrinsic page/rect
#   loci via a describe_pdf descriptor, display coordinates only derived
#   explicitly); EPUB CFI stable-selector resolution where transient viewport
#   geometry is never persistent identity and anchors persist after reflow;
#   scan-image pixel-domain resolution with explicit dpi/scale and mixed-mode
#   pages keeping native/raster observations distinct; ambiguity reported with
#   neither target auto-selected; missing selectors reported as explicit missing
#   state; unsupported locators classified via the slice-1 unsupported diagnostic
#   category; and partial-order reading orders where two legal topological sorts
#   are both accepted and the display sort is never asserted as unique.
# Rationale: document-debugger spec deltas (carrier_locators,
#   bidirectional_navigation, scoped_structure; properties pdf_epub_no_ocr,
#   ambiguous_selector, partial_order). Slice 2 excludes comparators,
#   counterexamples, goldens, a11y (slices 3-4). The locators layer never
#   writes: real-only boundary re-checked against source fixture bytes.
"""Carrier locator adapter + synchronized selection tests (sunset-xx7.2)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import adapters
from dsc03 import inspect as dbg
from dsc03 import locators
from dsc03 import validator

CARRIERS = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
PDF = CARRIERS / "accounting-made-simple-excerpt.pdf"
EPUB = CARRIERS / "sunset-carrier-sample.epub"
EPUB_SIDECAR = CARRIERS / "sunset-carrier-sample-annotations.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selector_profile(desc, profile_id, uri):
    desc["profiles"].append(
        {"id": profile_id, "kind": "selector", "uri": uri, "version": "1",
         "sha256": sha(json.dumps({"uri": uri}, sort_keys=True).encode())}
    )


# -- (a) PDF: fixed-coordinate locator domain -------------------------------------
def test_pdf_region_resolves_to_declared_page_and_rect_loci(tmp_path):
    """A PDF region resolves to its declared page/rect loci via a
    describe_pdf-style descriptor; display coordinates only ever derived
    explicitly, never stored in the locus."""
    desc = adapters.describe_pdf(PDF, Path(tmp_path))
    selector_profile(desc, "p-sel", "pdf-selectors.json")
    desc["profiles"].append(
        {"id": "p-geo", "kind": "geometry", "uri": "geometry-page-pt.json",
         "version": "1", "sha256": sha(b"geometry-page-pt")}
    )
    # real page region from the adapter, pinned with an intrinsic rect
    for r in desc["regions"]:
        if r["id"] == "pg2":
            r["geometry"] = {"profile_id": "p-geo", "space": "page-pt",
                             "x": 36, "y": 72, "width": 180, "height": 40}
    desc["selectors"].append({
        "id": "sel-p1", "kind": "pdf-area", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "pg2",
        "locator": "page:2 rect:36,72,180,40",
    })
    assert validator.validate(desc) == []  # locator-domain declarations are schema-legal

    index = dbg.build_index(desc)
    sel = locators.resolve(index, "pg2")
    assert sel.status == "resolved"
    assert len(sel.loci) == 1
    locus = sel.loci[0]
    assert locus.domain == "pdf-fixed-coordinate"
    assert locus.page == 2
    assert locus.rect == (36, 72, 180, 40)
    # evidence flows with the selection (bidirectional_navigation)
    assert "ev-txt2" in sel.evidence_ids
    # intrinsic coordinates preserved; display coordinates never stored
    assert locus.display_rect is None
    display = locators.to_display(locus, zoom=2.0)
    assert display == (72, 144, 360, 80)  # derived explicitly, on demand
    assert all(l.display_rect is None for l in sel.loci)


# -- (b) EPUB: stable XHTML/CFI selectors; viewport never identity ------------------
def test_epub_cfi_resolves_and_viewport_geometry_is_never_identity(tmp_path):
    """EPUB CFI resolves from a real carrier via describe_epub + the committed
    sidecar; a simulated reflow (viewport geometry change) never changes the
    persistent identity, and viewport-style locators are not stored as loci."""
    sidecar = json.loads(EPUB_SIDECAR.read_bytes())
    cfi_a1 = next(a["target"] for a in sidecar["annotations"] if a["id"] == "a1")

    desc = adapters.describe_epub(EPUB, Path(tmp_path))
    selector_profile(desc, "p-sel", "epub-selectors.json")
    desc["regions"].append({"id": "r-ch1", "view_id": "v-main", "kind": "chapter"})
    desc["selectors"].append({
        "id": "sel-a1", "kind": "epub-fragment", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-ch1",
        "locator": cfi_a1,
    })
    index = dbg.build_index(desc)
    before = locators.resolve(index, "r-ch1")
    assert before.status == "resolved"
    assert [l.value for l in before.loci] == [cfi_a1]
    assert all(l.domain == "epub-stable-selector" for l in before.loci)

    # reflow: the reader reports new transient viewport geometry for the same region
    desc["selectors"].append({
        "id": "sel-a1-viewport", "kind": "epub-fragment", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-ch1",
        "locator": "viewport rect:0,0,600,800 zoom:1.25",
    })
    index = dbg.build_index(desc)
    after = locators.resolve(index, "r-ch1")
    # anchor persists: identity from the CFI only, unchanged after reflow
    assert [l.value for l in after.loci] == [cfi_a1]
    # viewport coordinates are transient: never a persistent locus
    assert all("viewport" not in l.value for l in after.loci)
    diags = locators.unsupported_diagnostics(index)
    assert any(d.category == "unsupported" and d.witness == "sel-a1-viewport"
               for d in diags)


# -- (c) Scan images: pixel domain, explicit dpi/scale, mixed mode ------------------
def _scan_descriptor():
    """Synthetic scan carrier descriptor: one raster page carrying a native
    text region and a raster region (mixed mode), pixel-domain selectors."""
    return {
        "version": "0.3", "id": "adapter-scan-sample",
        "source": {"format": "image/tiff", "sha256": sha(b"scan-bytes"),
                   "locator": "scan-sample.tiff"},
        "views": [{"id": "v-main", "kind": "physical", "root": "r-page1"}],
        "regions": [
            {"id": "r-page1", "view_id": "v-main", "kind": "page"},
            {"id": "r-native", "view_id": "v-main", "kind": "native-text"},
            {"id": "r-raster", "view_id": "v-main", "kind": "raster"},
        ],
        "contents": [
            {"id": "c-native", "kind": "text", "value": "rendered text layer"},
            {"id": "c-raster", "kind": "text", "value": "raster observation"},
        ],
        "relations": [
            {"id": "rel-cn", "kind": "contains", "from": "r-page1", "to": "r-native"},
            {"id": "rel-cr", "kind": "contains", "from": "r-page1", "to": "r-raster"},
            {"id": "rel-hn", "kind": "has-content", "from": "r-native", "to": "c-native"},
            {"id": "rel-hr", "kind": "has-content", "from": "r-raster", "to": "c-raster"},
        ],
        "annotations": [],
        "evidence": [
            {"id": "ev-native", "origin": "source", "source_ref": "sha256:x#page:1",
             "content_ids": ["c-native"], "selector_ids": []},
            {"id": "ev-raster", "origin": "source", "source_ref": "sha256:x#page:1",
             "content_ids": ["c-raster"], "selector_ids": []},
        ],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [
            {"id": "sel-native", "kind": "pdf-area", "profile_id": "p-sel",
             "source_sha256": sha(b"scan-bytes"), "target": "r-native",
             "locator": "pixels rect:10,20,300,120 dpi:300 scale:1.0"},
            {"id": "sel-raster", "kind": "pdf-area", "profile_id": "p-sel",
             "source_sha256": sha(b"scan-bytes"), "target": "r-raster",
             "locator": "pixels rect:0,0,2480,3508 dpi:300 scale:1.0"},
        ],
        "interpretations": [],
        "coverage": [],
        "profiles": [
            {"id": "p-sel", "kind": "selector", "uri": "scan-selectors.json",
             "version": "1", "sha256": sha(b"scan-selectors")},
        ],
    }


def test_scan_page_resolves_in_pixel_domain_with_explicit_dpi_scale():
    desc = _scan_descriptor()
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "r-raster")
    assert sel.status == "resolved"
    assert len(sel.loci) == 1
    locus = sel.loci[0]
    assert locus.domain == "scan-pixel-domain"
    assert locus.rect == (0, 0, 2480, 3508)
    assert locus.dpi == 300          # explicit, never implicit OCR-derived
    assert locus.scale == 1.0


def test_mixed_mode_scan_page_keeps_native_and_raster_distinct():
    desc = _scan_descriptor()
    index = dbg.build_index(desc)
    observations = locators.resolve_scan_page(index, "r-page1")
    assert len(observations) == 2
    origins = sorted(o.origin for o in observations)
    assert origins == ["native-text", "raster"]
    native = next(o for o in observations if o.origin == "native-text")
    raster = next(o for o in observations if o.origin == "raster")
    assert native.region_id != raster.region_id
    assert native.loci and raster.loci
    assert all(l.dpi == 300 for o in observations for l in o.loci)
    # independent evidence access: each observation carries only its own evidence
    assert set(native.evidence_ids) == {"ev-native"}
    assert set(raster.evidence_ids) == {"ev-raster"}


# -- (d) ambiguity and missing states ----------------------------------------------
def test_ambiguous_selector_reported_and_neither_target_auto_selected():
    """Two matching selector targets: ambiguity reported, no auto-selection."""
    desc = _scan_descriptor()
    # both regions share the same locator -> two matching targets
    desc["selectors"][1]["locator"] = desc["selectors"][0]["locator"]
    index = dbg.build_index(desc)
    sel = locators.resolve_locator(index, "pixels rect:10,20,300,120 dpi:300 scale:1.0")
    assert sel.status == "ambiguous"
    assert sorted(sel.candidates) == ["r-native", "r-raster"]
    assert sel.loci == ()          # neither target auto-selected
    assert "multiple" in sel.reason


def test_resolve_target_id_matching_region_and_content_is_ambiguous():
    """A target id matching both a region and a content is two matching
    targets -> ambiguity, neither auto-selected."""
    desc = _scan_descriptor()
    desc["regions"][2]["id"] = "dup-id"   # raster region
    desc["contents"][1]["id"] = "dup-id"  # raster content
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "dup-id")
    assert sel.status == "ambiguous"
    assert sorted(sel.candidates) == ["content", "region"]
    assert sel.loci == ()


def test_missing_selector_reported_as_explicit_missing_state():
    desc = _scan_descriptor()
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "r-nonexistent")
    assert sel.status == "missing"
    assert sel.loci == ()
    assert sel.reason          # explicit classified reason, no invention
    # a region with no declared selector is explicitly missing too
    desc["selectors"].clear()
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "r-native")
    assert sel.status == "missing"
    assert "no selector" in sel.reason


# -- (e) unsupported locator -> classified reason via slice-1 category --------------
def test_unsupported_locator_yields_classified_unsupported_diagnostic():
    desc = _scan_descriptor()
    desc["selectors"].append({
        "id": "sel-viewport", "kind": "epub-fragment", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-page1",
        "locator": "viewport rect:0,0,600,800 zoom:1.25",
    })
    desc["selectors"].append({
        "id": "sel-moon", "kind": "external", "profile_id": "p-sel",
        "source_sha256": desc["source"]["sha256"], "target": "r-page1",
        "locator": "moon:crater-42",
    })
    index = dbg.build_index(desc)
    diags = locators.unsupported_diagnostics(index)
    by_witness = {d.witness: d for d in diags}
    # slice-1 typed diagnostics model is reused, not rewritten
    assert all(isinstance(d, dbg.Diagnostic) for d in diags)
    assert all(d.category == "unsupported" for d in diags)
    vp = by_witness["sel-viewport"]
    assert vp.rule_id == "dbg.locator.unsupported"
    assert "viewport" in vp.message
    moon = by_witness["sel-moon"]
    assert "unknown locator scheme" in moon.message
    # resolving a target whose only locator is unsupported is explicit, not a guess
    desc["selectors"] = [s for s in desc["selectors"] if s["id"] == "sel-viewport"]
    index = dbg.build_index(desc)
    sel = locators.resolve(index, "r-page1")
    assert sel.status == "unsupported"
    assert sel.loci == ()


# -- (f) partial order: two legal topological sorts, display sort not unique --------
def test_two_legal_topological_sorts_both_accepted_display_sort_not_unique():
    desc = _scan_descriptor()
    desc["views"] = [{"id": "v-order", "kind": "logical", "root": "r-a"}]
    desc["regions"] = [
        {"id": "r-a", "view_id": "v-order", "kind": "paragraph"},
        {"id": "r-b", "view_id": "v-order", "kind": "paragraph"},
        {"id": "r-c", "view_id": "v-order", "kind": "paragraph"},
    ]
    desc["relations"] = [
        {"id": "rel-pre1", "kind": "precedes", "from": "r-a", "to": "r-c",
         "interpretation_id": "i-order"},
    ]
    desc["interpretations"] = [
        {"id": "i-order", "kind": "reading-order", "view_id": "v-order",
         "origin": "source", "status": "supported", "evidence": []},
    ]
    index = dbg.build_index(desc)
    view = locators.reading_orders(index, "v-order")
    # r-b is unconstrained: (a,b,c) and (b,a,c) are both legal — no total order invented
    assert len(view.orders) >= 2
    assert ("r-a", "r-b", "r-c") in view.orders
    assert ("r-b", "r-a", "r-c") in view.orders
    # every returned order satisfies the declared partial order
    for order in view.orders:
        assert order.index("r-a") < order.index("r-c")
    # the display sort is deterministic but explicitly NOT asserted as unique
    assert view.display_sort == ("r-a", "r-b", "r-c")
    assert view.display_is_unique is False


# -- read-only boundary (slice-1 unchanged_bytes must still hold) --------------------
def test_read_only_boundary_descriptor_and_source_bytes_unchanged(tmp_path):
    desc = adapters.describe_epub(EPUB, Path(tmp_path))
    before = copy.deepcopy(desc)
    source_before = sha(EPUB.read_bytes())
    index = dbg.build_index(desc)
    locators.resolve(index, "r-root")
    locators.resolve_locator(index, "epubcfi(/6/4[ch1]!/4/2/1:0,/4/2/1:40)")
    locators.unsupported_diagnostics(index)
    locators.reading_orders(index, "v-log")
    assert desc == before                       # no in-memory mutation
    assert sha(EPUB.read_bytes()) == source_before  # source fixture untouched
    assert not any(p.name.startswith("locators") for p in tmp_path.iterdir())
