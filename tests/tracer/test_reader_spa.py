"""Contract tests for the sunset-905.3 reader observation SPA.

The SPA (hitl/sunset-905.3/templates/observations-spa.html) is the reader-
facing form that replaces hand-edited JSON observation sheets. It must:

- exist in both the repo templates/ and the bundle templates/ copies,
- be fully self-contained (works offline over file://),
- never phone home or reference external resources,
- emit the exact observations-template.json schema (same keys, same
  context kinds, same rotation/column vocabularies),
- record reader identity and elapsed time per carrier.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPO_SPA = REPO / "hitl" / "sunset-905.3" / "templates" / "observations-spa.html"
BUNDLE_SPA = REPO / "hitl" / "sunset-905.3" / "bundle" / "templates" / "observations-spa.html"

TEMPLATE = json.loads(
    (REPO / "hitl" / "sunset-905.3" / "templates" / "observations-template.json").read_text()
)

CONTEXT_KINDS = {
    "publication_date",
    "publisher_or_source",
    "author_or_attribution",
    "quoted_material",
}
ROTATIONS = {"0", "90", "180", "270", "unknown"}
COLUMN_VALUES = {"single", "two", "multi", "unknown"}
ANNOTATION_TYPES = {
    "Highlight",
    "Text",
    "StrikeOut",
    "FreeText",
    "Underline",
    "Square",
    "Ink",
    "other",
}
CONTEXT_STATUSES = {"observed", "observed_absent", "unknown"}
REGION_TYPES = {
    "text",
    "title",
    "heading",
    "image",
    "table",
    "caption",
    "header",
    "footer",
    "list",
    "other",
}
CARRIERS = [
    "diario-de-poesia-excerpt",
    "agentic-patterns-excerpt",
    "sunset-carrier-sample",
    "bank-statement-ca-excerpt",
]


def _spa() -> str:
    return REPO_SPA.read_text()


def test_spa_exists_in_repo_and_bundle() -> None:
    assert REPO_SPA.is_file(), f"missing {REPO_SPA}"
    assert BUNDLE_SPA.is_file(), f"missing {BUNDLE_SPA}"
    assert REPO_SPA.read_bytes() == BUNDLE_SPA.read_bytes(), (
        "repo and bundle SPA copies have drifted apart"
    )


def test_spa_is_selfcontained_no_external_resources() -> None:
    html = _spa()
    # The pdf.js vendor block is inlined (offline rendering) and clearly marked.
    assert re.search(r"<!--VENDOR:pdf\.js", html), "vendor marker missing"
    assert re.search(r"<!--END VENDOR-->", html), "vendor end marker missing"
    assert "Apache" in html, "vendor license notice missing"
    parts = re.split(r"<!--VENDOR:pdf\.js.*?<!--END VENDOR-->", html, flags=re.S)
    assert len(parts) >= 2, "vendor block not splittable"
    # No external script/link/image sources anywhere (vendor included).
    for pattern in ("<script src", "<link ", "<img "):
        assert pattern not in html, f"SPA must be offline-only: found {pattern!r}"
    # Reader-authored code must never phone home: no network fetches and no
    # non-local URLs. Two marked exceptions are scanned separately:
    # - the vendored pdf.js (inert network internals),
    # - the LOCAL-READ loader block, which may use fetch/XHR only to read the
    #   bundle's own carriers/ folder (relative path, no URLs allowed).
    for part in parts:
        assert "sendBeacon" not in part and "import " not in part
        assert not re.search(r"https://(?!localhost)", part), "non-local https reference"
        assert not re.search(r"http://(?!localhost)", part), "non-local http reference"
    local = re.search(r"<!--LOCAL-READ-->(.*?)<!--END LOCAL-READ-->", html, flags=re.S)
    assert local, "local-read loader block missing"
    body = local.group(1)
    assert "../carriers/" in body, "loader must read the bundle's own carriers folder"
    assert "://" not in body, "loader must never reference a URL scheme"
    outside = re.sub(r"<!--LOCAL-READ-->.*?<!--END LOCAL-READ-->", "", parts[-1], flags=re.S)
    for pattern in ("fetch(", "XMLHttpRequest"):
        assert pattern not in outside, f"network call outside the local-read block: {pattern!r}"
    # The vendor block must carry the worker (fake-worker fallback, no network).
    vendor = html[html.index("<!--VENDOR:pdf.js"):html.index("<!--END VENDOR-->")]
    assert "pdfjsWorker" in vendor, "pdf.js worker bootstrap missing"


def test_spa_emits_every_template_key() -> None:
    html = _spa()
    for key in TEMPLATE:
        assert key in html, f"template key {key!r} missing from SPA"


def test_spa_emits_schema_vocabularies() -> None:
    html = _spa()
    for kind in CONTEXT_KINDS:
        assert kind in html, f"context kind {kind!r} missing"
    for rot in ROTATIONS:
        assert rot in html, f"rotation value {rot!r} missing"
    for col in COLUMN_VALUES:
        assert col in html, f"column value {col!r} missing"
    for ann in ANNOTATION_TYPES:
        assert ann in html, f"annotation type {ann!r} missing"
    for status in CONTEXT_STATUSES:
        assert status in html, f"context status {status!r} missing"


def test_spa_offers_all_carriers() -> None:
    html = _spa()
    for carrier in CARRIERS:
        assert carrier in html, f"carrier {carrier!r} not offered by SPA"


def test_spa_supports_reader_ids_and_timing() -> None:
    html = _spa()
    assert "reader-a" in html and "reader-b" in html, "reader ids missing"
    assert "elapsed_minutes" in html, "elapsed timing missing"


def test_spa_serializes_unknown_as_schema_expects() -> None:
    """Tri-state booleans must serialize null for unknown; text unknowns stay
    the literal string 'unknown'."""
    html = _spa()
    assert "null" in html, "tri-state unknown must serialize as null"
    assert re.search(r"['\"]unknown['\"]", html), "text fields must offer 'unknown'"


def test_spa_documents_no_winner_election_and_unknown_is_an_answer() -> None:
    html = _spa()
    assert "unknown" in html
    # The ground rules must reach the reader through the UI itself.
    assert re.search(r"[Dd]o not resolve", html), "no-smoothing rule missing"
    assert re.search(r"[Ss]topwatch", html), "timing instruction missing"


def test_spa_is_a_guided_wizard_with_embedded_instructions() -> None:
    """The SPA must be self-explanatory: steps and CTAs embedded, no external
    README required."""
    html = _spa()
    # Step-by-step flow with navigation CTAs.
    assert re.search(r"Next\b", html), "wizard Next CTA missing"
    assert re.search(r"Back\b", html), "wizard Back CTA missing"
    # The reader must be told, in the UI, to open the carrier in a viewer.
    assert re.search(r"Open the carrier in a normal (PDF|viewer)", html), (
        "carrier-viewing instruction missing"
    )
    # The per-section field guidance must be embedded, not referenced.
    for guidance in (
        "nothing selectable",
        "continuation: a sentence or flow",
        "you looked and it is not there",
        "Do not add your own",
        "image content",
    ):
        assert guidance in html, f"embedded guidance missing: {guidance!r}"
    # Return instructions must be embedded too.
    assert re.search(r"zip", html.lower()), "zip-and-return instruction missing"
    assert re.search(r"Do not commit", html), "no-commit instruction missing"
    # Multi-carrier progress must be visible.
    assert re.search(r"carrier 1 of 4|Next carrier", html), "carrier progress missing"


def test_spa_embeds_the_carrier_viewer() -> None:
    """The carriers to check must be viewable inside the SPA itself (native
    browser PDF rendering), with a same-folder fallback and an EPUB note."""
    html = _spa()
    # The viewer points at the bundle-relative carriers directory.
    assert re.search(r"\.\./carriers/", html), "embedded carrier path missing"
    assert re.search(r'el\("object"', html), "embedded viewer element missing"
    # Graceful fallback when a browser refuses to render the file inline:
    # a direct new-tab link first, then the local-server last resort.
    assert re.search(r"Open in new tab", html), "new-tab fallback link missing"
    assert re.search(r"target=\"_blank\"", html), "new-tab link missing"
    assert re.search(r"http\.server", html), "local-server troubleshooting recipe missing"
    assert re.search(r"does not display|If the carrier does not", html), (
        "viewer fallback instruction missing"
    )
    # EPUB cannot render natively in browsers — the reader must be told.
    assert re.search(r"EPUB reader|EPUB cannot", html), "EPUB viewing note missing"
    # Using the built-in viewer must be explicitly allowed by the rules.
    assert re.search(r"built-in viewer[^<]*counts as", html), (
        "viewer-is-a-normal-viewer clarification missing"
    )


def test_template_structure_entries_carry_region_fields() -> None:
    """Structure entries must support drawn regions: a region type, the page,
    and a normalized bbox (0..1) with the viewport size at draw time."""
    for entry in TEMPLATE["structure"]:
        assert "type" in entry, "structure entry missing region type"
        assert "page" in entry, "structure entry missing page"
        assert "bbox" in entry, "structure entry missing bbox"
    if TEMPLATE["structure"] and isinstance(TEMPLATE["structure"][0].get("bbox"), dict):
        bbox = TEMPLATE["structure"][0]["bbox"]
        for key in ("x", "y", "w", "h", "viewport_w", "viewport_h"):
            assert key in bbox, f"bbox missing {key!r}"


def test_spa_structure_annotator_draws_rectangles() -> None:
    """The structure step must offer an interactive region annotator: the
    reader draws rectangles on the displayed carrier page, assigns a type,
    and steps through the regions."""
    html = _spa()
    # A draw-mode toggle gates the drawing overlay (so scrolling/zooming the
    # PDF stays possible when it is off).
    assert re.search(r"[Dd]raw (mode|regions)", html), "draw-mode toggle missing"
    # Pointer-event drawing on an overlay above the embedded page (pointer
    # events cover mouse, touch, and pen; capture keeps the drag alive when
    # the pointer leaves the overlay mid-rectangle).
    assert "pointerdown" in html and "pointermove" in html and "pointerup" in html, (
        "rectangle drawing handlers missing"
    )
    assert "setPointerCapture" in html, "pointer capture for off-overlay release missing"
    # The overlay sits above the page (absolute positioning over the viewer).
    assert re.search(r"overlay", html), "drawing overlay missing"
    # Every region type is offered when classifying a rectangle.
    for rt in REGION_TYPES:
        assert re.search(r"['\"]" + rt + r"['\"]", html), f"region type {rt!r} missing"
    # Regions render back as positioned boxes over the page.
    assert re.search(r"position:\s*absolute|position:absolute", html), (
        "region boxes must be absolutely positioned over the page"
    )
    # Normalized bbox serialization with the viewport at draw time.
    assert "bbox" in html and "viewport_w" in html and "viewport_h" in html, (
        "normalized bbox serialization missing"
    )


def test_template_has_page_frames() -> None:
    """The sheet records one calibration rectangle (page frame) per page;
    region bboxes are stored relative to it."""
    assert "page_frames" in TEMPLATE, "page_frames key missing from template"


def test_spa_annotator_calibrates_a_page_frame() -> None:
    """Before region rectangles mean anything, the reader draws one rectangle
    around the page itself; regions are then normalized (and clamped) inside
    that frame, and carry a relative marker distinguishing page-relative
    bboxes from legacy overlay-relative ones."""
    html = _spa()
    assert "page_frames" in html, "page frame storage missing"
    assert re.search(r"[Pp]age frame", html), "page-frame calibration UI missing"
    assert re.search(r"[Rr]edraw|[Rr]ecalibrate", html), "frame redraw control missing"
    # frame-relative normalization must clamp to the page rectangle
    assert re.search(r"Math\.max\(0", html) and re.search(r"Math\.min\(1", html), (
        "frame-relative bbox must clamp to [0,1]"
    )
    # bbox records what its coordinates are relative to
    assert re.search(r"relative", html), "bbox relative marker missing"


def test_spa_can_resume_a_saved_session() -> None:
    """A downloaded <carrier>.observations.json must be re-importable: the SPA
    offers a resume affordance (file input accepting .json), restores the
    full state (drawn regions, page frames, timer), and validates before
    adopting (reader/carrier required; arrays coerced)."""
    html = _spa()
    assert re.search(r"[Rr]esume a saved session", html), "resume affordance missing"
    assert re.search(r'type=["\']file["\']', html), "file input missing"
    assert re.search(r"accept=[\"'][^\"']*\.json", html), "file input must accept .json"
    assert "importSheetObject" in html, "import seam missing"
    assert re.search(r"missing reader|not valid JSON|not an object", html), (
        "import validation errors missing"
    )


def test_spa_annotator_renders_pages_on_canvas() -> None:
    """PDF pages must render onto our own canvas (vendored pdf.js), not into
    the browser's PDF plugin — so page fit and zoom are under the SPA's
    control and rectangles map 1:1 to page coordinates."""
    html = _spa()
    assert re.search(r'el\("canvas"\)|createElement\("canvas"\)', html), "annotator canvas missing"
    assert "pdfjsLib.getDocument" in html, "pdf.js document loading missing"
    assert re.search(r"numPages", html), "real page count missing"
    assert re.search(r"[Ff]it:? (width|page)", html), "fit controls missing"
    assert re.search(r"[Zz]oom", html), "zoom controls missing"
    # Loading paths: direct fetch, XHR, then a file-picker fallback for
    # browsers that block local reads over file://.
    assert re.search(r"[Ll]oad (the )?PDF", html), "PDF file-picker fallback missing"
    assert re.search(r"\.pdf|application/pdf", html), "picker accept missing"


def test_spa_region_boxes_have_direct_edit_and_delete() -> None:
    """A marked region must be editable and deletable directly on the page:
    its box carries a small toolbar (jump-to-entry + delete), not just the
    row list below the stage."""
    html = _spa()
    assert "annDeleteRegion" in html, "direct region deletion missing"
    assert re.search(r"boxtools", html), "on-box toolbar missing"
    assert re.search(r"boxtools button|\.boxtools \{", html), "on-box toolbar styling missing"
    # the toolbar must not start a drawing draft when clicked
    assert "stopPropagation" in html


def test_spa_annotator_navigates_pdf_pages() -> None:
    """Page navigation uses the real page count from the rendered document,
    with prev/next controls."""
    html = _spa()
    assert re.search(r"[Pp]rev", html) and re.search(r"[Nn]ext", html), (
        "page prev/next controls missing"
    )
    assert re.search(r"Page \"? ?\+|\"Page \" ?\+", html), "page indicator missing"


def test_spa_annotator_is_pdf_only_with_prose_fallback() -> None:
    """EPUB (and unknown carriers) cannot render pages to draw on — the
    annotator must detect PDF carriers and fall back to the manual prose
    form otherwise, without losing any recorded entry."""
    html = _spa()
    assert re.search(r"\.pdf", html), "PDF detection for annotator missing"
    assert re.search(r"EPUB.{0,120}(by hand|manual|prose)", html) or re.search(
        r"(by hand|manual|prose).{0,120}EPUB", html
    ), "manual fallback for non-PDF carriers missing"
    # The manual structure form must still exist (label/evidence/rank fields).
    for key in ("label", "evidence", "order_rank", "order_alternatives"):
        assert key in html, f"manual structure field {key!r} missing"


def test_spa_annotator_links_regions_to_entries() -> None:
    """Drawing a rectangle must create/attach a structure entry with the
    current page; selecting a region highlights its entry (stepping through
    regions in the next steps)."""
    html = _spa()
    assert re.search(r"structure", html), "structure section must host the annotator"
    # Entries store the page they were drawn on.
    assert re.search(r"page:\s*", html), "region page recording missing"
    # Region list rows and their removal must exist.
    assert re.search(r"[Rr]egion", html), "region list missing"
    assert re.search(r"[Dd]elete|[Rr]emove", html), "region removal missing"
