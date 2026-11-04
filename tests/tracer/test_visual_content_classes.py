"""Contract tests for the content-class-aware observation layer (sunset-pkj).

dsc03.visual.content_classes observes ONE source-PDF page through FOUR typed
classes tied to the source artifact and a declared frame:

- text   — native text spans (carrier observation),
- vector — vector drawing paths (carrier observation),
- raster — embedded image placements (carrier observation),
- graphic-hypothesis — pixel-morphology connected-component candidates over
  the pinned render (typed HYPOTHESES, never DSC observations: O-A01 says
  projections without provenance are not applied).

Every entry carries the source sha256, the declared frame name, the page and
its class; class-4 entries additionally carry ``interpretation_status`` and
full morphology provenance. Unknown frames keep canonical ``rect_pt`` and
null ``rect_px`` — nothing is dropped. Seeded defects on committed fixture
variants (a deleted text line, a shifted decorative band) must be detected
per class, and per-class geometric coverage must match hand-computed
expectations (fill-only synthetic fixture at 72 dpi, 1 pt = 1 px).

Fixture provenance (committed bytes, never rebuilt by tests): pymupdf
1.28.2-built BORA-like page — 4 native text lines + 1 stroked rule + 1
embedded 24x16 image + a decorative band placed via show_pdf_page (form
XObject; invisible to native TEXT extraction, its fills are vector-visible
on pymupdf 1.28.2). Hand-checkable because every painted rect is fill-only
black at integer-exact 72-dpi pixels.
"""

import hashlib
import json
from pathlib import Path

import pytest

from dsc03.visual.content_classes import observe_page

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/tracer/fixtures/visual"
PRISTINE = FIXTURES / "bora-like.pdf"
MINUS_LINE = FIXTURES / "bora-like-minus-line.pdf"
BAND_SHIFT = FIXTURES / "bora-like-band-shift.pdf"
GEOMETRY = json.loads((REPO / "tests/tracer/profiles/geometry-page-pt.json").read_text())

PAGE_AREA = 612.0 * 792.0  # 484704 pt^2

# Pinned from the committed pristine fixture (canonical descriptor pt,
# bottom-left y-up; pymupdf 1.28.2 + pdftoppm 26.01.0 measured).
TEXT_SPANS = [
    ("Primera linea de prueba", [72.0, 696.710999, 189.380966, 711.824997]),
    ("Segunda linea de prueba", [72.0, 676.710999, 194.913956, 691.824997]),
    ("Tercera linea de prueba", [72.0, 656.710999, 188.775970, 671.824997]),
    ("Cuarta linea de prueba", [72.0, 636.710999, 183.891968, 651.824997]),
]
TEXT_AREAS_SUM = 7087.903728  # sum of span bbox areas, pt^2
VECTOR_RECTS = [  # (draw_type, canonical rect) — stroke + band fills
    ("stroke", [72.0, 600.0, 540.0, 600.0]),  # hairline: rect area exactly 0
    ("fill", [72.0, 520.0, 272.0, 560.0]),    # band outer (form XObject fill)
    ("fill", [102.0, 528.0, 132.0, 552.0]),   # white cutout 1 (fill visible)
    ("fill", [162.0, 528.0, 192.0, 552.0]),   # white cutout 2
]
VECTOR_AREA = 9440.0  # 0 (hairline) + 200*40 + 30*24 + 30*24
RASTER_RECT = [72.0, 470.0, 96.0, 486.0]
RASTER_AREA = 384.0  # 24*16
# Class-4 morphology candidates: (rect_px, area_px) sorted top-left first;
# pinned render pdftoppm 26.01.0 @72dpi, threshold 128, dilation 2px, 8-conn.
COMPONENTS_PRISTINE = [
    ([71, 82, 153, 94], 860), ([154, 84, 191, 96], 374),
    ([71, 102, 117, 116], 502), ([118, 102, 196, 116], 804),
    ([70, 122, 111, 134], 403), ([114, 122, 190, 136], 777),
    ([71, 142, 106, 154], 370), ([107, 142, 185, 156], 804),
    ([70, 190, 542, 195], 2360),   # stroked rule ink band
    ([70, 230, 274, 274], 7936),   # decorative band (dilated frame)
    ([70, 304, 99, 325], 609),     # embedded image
]
BAND_COMPONENT_PX = [70, 230, 274, 274]
BAND_COMPONENT_AREA = 7936
BAND_SHIFTED_PX = [82, 230, 286, 274]  # +12 px in x, area unchanged
COMPONENTS_MINUS_LINE = 9
IMAGE_COMPONENT_PX = [70, 304, 99, 325]
STROKE_COMPONENT_PX = [70, 190, 542, 195]


@pytest.fixture(scope="module")
def pristine():
    return observe_page(PRISTINE, GEOMETRY)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_band_fill(entry):
    return (entry["draw_type"] == "fill"
            and entry["rect_pt"][2] - entry["rect_pt"][0] == 200.0)


def _band_fill(record):
    matches = [v for v in record["classes"]["vector"]["entries"]
               if _is_band_fill(v)]
    assert len(matches) == 1
    return matches[0]


def _hypothesis_at(record, rect_px):
    matches = [e for e in record["classes"]["graphic-hypothesis"]["entries"]
               if e["rect_px"] == rect_px]
    assert len(matches) == 1
    return matches[0]


def _assert_unmapped(entry):
    assert entry["mapping"] == "unknown"
    if entry["class"] == "graphic-hypothesis":
        assert entry["rect_px"] is not None
        assert entry["rect_pt"] is None
        assert entry["interpretation_status"] == "hypothesis"
        assert entry["attribution"] is None
        assert entry["attribution_status"] == "unknown-mapping"
    else:
        assert entry["rect_pt"] is not None      # canonical kept
        assert entry["rect_px"] is None          # no guessed mapping


def _all_entries(record):
    classes = record["classes"]
    entries = list(classes["text"]["entries"])
    entries += classes["vector"]["entries"] + classes["raster"]["entries"]
    entries += classes["graphic-hypothesis"]["entries"]
    return entries


def test_record_shape_and_four_typed_classes(pristine):
    assert pristine["kind"] == "content-class-observations"
    assert pristine["version"] == 1
    assert pristine["status"] == "observed"
    assert pristine["evidence_class"] == "independent"
    assert pristine["frame"] == {"name": "page-1", "status": "resolved", "reason": None}
    assert pristine["render"]["status"] == "rendered"
    assert pristine["source"]["extractor"]["id"] == "pymupdf"
    classes = pristine["classes"]
    assert set(classes) == {"text", "vector", "raster", "graphic-hypothesis"}
    assert classes["text"]["role"] == "carrier-observation"
    assert classes["vector"]["role"] == "carrier-observation"
    assert classes["raster"]["role"] == "carrier-observation"
    # O-A01 boundary: pixel-derived candidates are hypotheses, never observations
    assert classes["graphic-hypothesis"]["role"] == "hypothesis"
    assert classes["graphic-hypothesis"]["status"] == "derived"
    assert len(classes["text"]["entries"]) == 4
    assert len(classes["vector"]["entries"]) == 4
    assert len(classes["raster"]["entries"]) == 1
    assert len(classes["graphic-hypothesis"]["entries"]) == 11


def test_text_entries_pinned(pristine):
    entries = pristine["classes"]["text"]["entries"]
    assert [e["text"] for e in entries] == [t for t, _ in TEXT_SPANS]
    for entry, (_, rect) in zip(entries, TEXT_SPANS):
        assert entry["rect_pt"] == pytest.approx(rect, abs=1e-6)
        assert entry["mapping"] == "resolved"
        assert entry["font"] == "Helvetica"
        assert entry["size"] == 11.0
    # hand-computed px corners at 72 dpi (1 pt = 1 px, y-flipped, rounded)
    assert [e["rect_px"] for e in entries] == [
        [72, 80, 189, 95], [72, 100, 195, 115],
        [72, 120, 189, 135], [72, 140, 184, 155]]


def test_vector_and_raster_entries_pinned(pristine):
    vectors = pristine["classes"]["vector"]["entries"]
    assert [(v["draw_type"], v["rect_pt"]) for v in vectors] == VECTOR_RECTS
    assert vectors[0]["rect_px"] == [72, 192, 540, 192]
    assert vectors[1]["rect_px"] == [72, 232, 272, 272]
    rasters = pristine["classes"]["raster"]["entries"]
    assert rasters[0]["rect_pt"] == RASTER_RECT
    assert rasters[0]["rect_px"] == [72, 306, 96, 322]
    assert rasters[0]["image_size"] == [24, 16]


def test_class4_hypothesis_components_pinned(pristine):
    entries = pristine["classes"]["graphic-hypothesis"]["entries"]
    assert [(e["rect_px"], e["area_px"]) for e in entries] == COMPONENTS_PRISTINE
    for entry in entries:
        assert entry["class"] == "graphic-hypothesis"
        assert entry["interpretation_status"] == "hypothesis"
        assert entry["mapping"] == "resolved"
        assert entry["rect_pt"] is not None
        provenance = entry["provenance"]
        assert provenance["derived_from"] == "pinned-render-morphology"
        assert provenance["renderer"] == "pdftoppm"
        assert provenance["dpi"] == 72
        assert provenance["threshold"] == 128
        assert provenance["dilation_px"] == 2
        assert provenance["connectivity"] == 8
        assert provenance["min_area_px"] == 4
    by_rect = {tuple(e["rect_px"]): e for e in entries}
    band = by_rect[tuple(BAND_COMPONENT_PX)]
    assert band["area_px"] == BAND_COMPONENT_AREA
    assert band["fill_share"] == pytest.approx(7936 / (204 * 44), abs=1e-6)
    assert band["attribution"]["dominant"] == "vector"
    assert band["attribution"]["vector"] == pytest.approx(1.0, abs=1e-6)
    assert band["attribution"]["text"] == 0.0
    image = by_rect[tuple(IMAGE_COMPONENT_PX)]
    assert image["attribution"]["dominant"] == "raster"
    stroke = by_rect[tuple(STROKE_COMPONENT_PX)]
    assert stroke["attribution"]["dominant"] == "vector"
    text_comp = entries[0]
    assert text_comp["attribution"]["dominant"] == "text"


def test_every_entry_carries_source_frame_page_class(pristine):
    sha = _sha256(PRISTINE)
    for class_name, section in pristine["classes"].items():
        for entry in section["entries"]:
            assert entry["class"] == class_name
            assert entry["page"] == 1
            assert entry["source_sha256"] == sha
            assert entry["frame"] == "page-1"


def test_seeded_line_deletion_detected_per_class():
    pristine = observe_page(PRISTINE, GEOMETRY)
    defective = observe_page(MINUS_LINE, GEOMETRY)
    texts_p = [e["text"] for e in pristine["classes"]["text"]["entries"]]
    texts_d = [e["text"] for e in defective["classes"]["text"]["entries"]]
    assert texts_p == [t for t, _ in TEXT_SPANS]
    assert texts_d == [t for t, _ in TEXT_SPANS[:3]]
    # per-class detection: exactly the fourth line vanished from the text class
    assert set(texts_p) - set(texts_d) == {"Cuarta linea de prueba"}
    # vector and raster classes are untouched by the text defect
    assert len(defective["classes"]["vector"]["entries"]) == 4
    assert len(defective["classes"]["raster"]["entries"]) == 1
    # the deleted line's ink components vanish from the morphology class too
    assert len(defective["classes"]["graphic-hypothesis"]["entries"]) == \
        COMPONENTS_MINUS_LINE
    areas_d = sum(
        (e["rect_pt"][2] - e["rect_pt"][0]) * (e["rect_pt"][3] - e["rect_pt"][1])
        for e in defective["classes"]["text"]["entries"])
    assert areas_d == pytest.approx(5396.768747, abs=1e-6)


def test_seeded_band_shift_detected_per_class():
    pristine = observe_page(PRISTINE, GEOMETRY)
    shifted = observe_page(BAND_SHIFT, GEOMETRY)
    # vector class: the band outer fill moved exactly +12 pt in x
    assert _band_fill(pristine)["rect_pt"][0] == 72.0
    assert _band_fill(shifted)["rect_pt"][0] == 84.0
    # morphology class: the band candidate moved exactly +12 px, same area
    assert _hypothesis_at(pristine, BAND_COMPONENT_PX)["area_px"] == \
        BAND_COMPONENT_AREA
    assert _hypothesis_at(shifted, BAND_SHIFTED_PX)["area_px"] == \
        BAND_COMPONENT_AREA
    # text and raster classes unaffected
    assert len(shifted["classes"]["text"]["entries"]) == 4
    assert len(shifted["classes"]["raster"]["entries"]) == 1


def test_coverage_per_class_hand_computed(pristine):
    classes = pristine["classes"]

    def coverage(entries):
        return sum((e["rect_pt"][2] - e["rect_pt"][0]) *
                   (e["rect_pt"][3] - e["rect_pt"][1]) for e in entries)

    text_area = coverage(classes["text"]["entries"])
    assert text_area == pytest.approx(TEXT_AREAS_SUM, abs=1e-6)
    assert text_area / PAGE_AREA == pytest.approx(TEXT_AREAS_SUM / PAGE_AREA)
    assert coverage(classes["vector"]["entries"]) == VECTOR_AREA
    assert coverage(classes["vector"]["entries"]) / PAGE_AREA == \
        pytest.approx(VECTOR_AREA / PAGE_AREA, abs=1e-12)
    assert coverage(classes["raster"]["entries"]) == RASTER_AREA
    assert coverage(classes["raster"]["entries"]) / PAGE_AREA == \
        pytest.approx(RASTER_AREA / PAGE_AREA, abs=1e-12)


def test_unknown_frame_keeps_pt_nulls_px_nothing_dropped():
    empty_geometry = {"kind": "geometry", "version": "1", "frames": []}
    record = observe_page(PRISTINE, empty_geometry, frame_name="nope")
    assert record["frame"]["status"] == "unknown"
    assert record["frame"]["reason"]
    for entry in _all_entries(record):
        _assert_unmapped(entry)
    # pixel-derived candidates still exist (render is frame-independent),
    # but cannot be mapped back to pt or attributed without a frame
    assert len(record["classes"]["graphic-hypothesis"]["entries"]) == 11


def test_invalid_sources_typed_never_raised():
    for bad in (FIXTURES / "does-not-exist.pdf",
                FIXTURES / "geometry-rotated-strip.json"):
        record = observe_page(bad, GEOMETRY)
        assert record["status"] == "invalid-source"
        assert record["classes"]["text"]["entries"] == []
        assert record["classes"]["graphic-hypothesis"]["entries"] == []
    record = observe_page(PRISTINE, GEOMETRY, page_number=99)
    assert record["status"] == "invalid-page"
    record = observe_page(PRISTINE, GEOMETRY, page_number=0)
    assert record["status"] == "invalid-page"
