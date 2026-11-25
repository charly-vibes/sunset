# Purpose: Human visual-review bundle generator (sunset-e8t, sunset-fgg) —
#   the bridge between the raster visual oracles and a human
#   side-by-side/overlay comparison pass, extended with the document-structural
#   debugger's source-linked journeys (sunset-5bu, sunset-36n, sunset-j1c).
# Responsibilities: Render pinned carrier pages through the same
#   pinned-render configuration the oracles use, resolve the declared
#   geometry frames, map claimed descriptor region rects into pixel space,
#   and embed renders + mapped regions + render configuration + evidence
#   class into the offline review SPA template
#   (hitl/visual-review/templates/visual-review-spa.html). Correlated-lineage
#   render configs are refused per page with a typed reason
#   (CORRELATED_RENDER_REFUSED): oracle evaluation reads only independent
#   renders, so a correlated crop is absent from the record, never silently
#   skipped. Walks every
#   unique render target recorded in fixtures/visual/calibration.json for
#   the all-examples bundle, and walks every page of a DSC 0.3 descriptor
#   (as produced by `python3 -m digitization run`) for the
#   descriptor-sourced bundle. Missing renderers and unresolvable frames stay
#   typed (unavailable / unknown); regions are never silently dropped and
#   verdicts are never fabricated. `python -m dsc03.visual.review` builds
#   and optionally serves the bundle over loopback.
#   Debugger journeys (sunset-5bu/36n/j1c): import human observation sheets
#   through the sibling sheet-import API (dsc03.visual.sheet_import, shared
#   contract) and (5bu) render every imported region ON its PDF source page
#   via the recorded page-frame transform (region_to_source_px), keeping
#   import refusals, digest mismatches and missing frames as typed
#   unresolved/unmapped entries — never an invented highlight; (36n) render
#   two attributed readings side by side with per-page outcomes and witnesses
#   from dsc03.compare.scoped_compare under a declared scope, with no winner
#   field and no inferred cross-reader region identity; (j1c) pin the
#   disagreement at build time via dsc03.compare.export_counterexample +
#   serialize_bundle (source PDF bytes omitted — digest only) and reopen it
#   through load_bundle + replay after verifying the user-supplied local PDF
#   against the pinned source digest (typed mismatch / not-replayable states,
#   never a guessed outcome).
# Rationale: The oracles prove sensitivity mechanically; the deployed spec
#   keeps the human pass supreme. This module makes that pass concrete:
#   the human sees exactly what the oracle pipeline sees (same render, same
#   frame math) and records agree/differ/unknown verdicts with the same
#   no-winner-election, no-smoothing rules. The debugger journeys extend the
#   same surface to imported human sheets: source-linked inspection,
#   attributed comparison and reproducible disagreement export all run
#   through the same pinned-render and typed-refusal discipline.
"""Build self-contained human review bundles for visual-oracle regions."""

import argparse
import base64
import hashlib
import json
import re
import shutil
import sys
from dataclasses import replace
from pathlib import Path

from dsc03.visual import Binarization, RenderConfig, render
from dsc03.compare import (
    ComparatorSpec,
    ComparisonInput,
    ComparisonOutcome,
    NotReplayable,
    RULE_UNEXAMINED,
    export_counterexample,
    load_bundle,
    replay,
    scoped_compare,
    serialize_bundle,
)
from dsc03.visual.frames import PixelMapping, UnknownMapping, frame_mapping

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "hitl" / "visual-review" / "templates" / "visual-review-spa.html"
)

RULES = "no winner election, no smoothing; unknown is an answer"

# Design D5: oracle evaluation reads ONLY independent renders. A correlated
# config (render lineage == extractor lineage, e.g. the in-process PyMuPDF
# review-crop path) is refused with this typed reason — the crop is absent
# from the record, never silently skipped and never relabeled. The refusal
# is carried structurally in page_record["refusal"] = {code, reason}
# ("unavailable" keeps the prefixed display string for the review SPA).
CORRELATED_RENDER_REFUSED = "correlated-render-refused"

# Provenance label for verdicts ingested from a human (or human-supervised
# agent) review pass: every report, counterexample and evaluation summary
# this module emits carries it, so downstream consumers never mistake
# ingested verdicts for mechanical oracle outcomes.
PROVENANCE_LABEL = "AGENT-INGESTED-HUMAN-VERDICTS"

# Sunset-9rg caveat carried verbatim in every missed-ink report entry:
# missed-ink boxes are a proxy metric, not a measurement. Decorative and
# graphic ink can be invisible to native text observation (transcript
# 6ae4669e: on BORA gazettes the decorative heading band is invisible to
# native text objects; ink-coverage 71.89% -> 99.55% once graphic-region
# candidates are counted), so the count underestimates missed ink.
MISSING_INK_CAVEAT = (
    "ESTIMATE: proxy metric per sunset-9rg (transcript 6ae4669e): decorative/"
    "graphic ink can be invisible to native text observation (BORA gazettes: "
    "ink-coverage 71.89% -> 99.55% once graphic-region candidates are "
    "counted), so missed-ink boxes understate ink and are not a measurement."
)

# Typed refusal when the verdicts bundle was built against a different
# calibration record (record sha256 or base_commit mismatch). FP/FN
# statistics must never be attributed to the wrong record version, so this
# is a typed error, never a warning.
RECORD_MISMATCH = "record-version-mismatch"


class RecordVersionMismatch(ValueError):
    """Verdicts bundle does not pin the calibration record being compared
    against (record sha256 or base_commit mismatch). Refusal is typed and
    non-negotiable: ingest produces no statistics on a mismatch."""

    code = RECORD_MISMATCH

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason

# Declared geometry artifacts the calibration record names, mirroring the
# mapping in tests/tracer/test_visual_calibration.py.
_ROOT = Path(__file__).resolve().parents[2]
_GEOMETRY_ARTIFACTS = {
    "geometry-page-pt": _ROOT / "tests/tracer/profiles/geometry-page-pt.json",
    "geometry-rotated-strip": _ROOT / "tests/tracer/fixtures/visual/geometry-rotated-strip.json",
}
_CALIBRATION_PATH = _ROOT / "fixtures/visual/calibration.json"


def _pixmap_extent(data: bytes):
    """Decode rendered PNG bytes to the (width, height) raster extent."""
    import pymupdf

    pix = pymupdf.Pixmap(data)
    return pix.width, pix.height


def _pixel_rect(mapping: PixelMapping, region: dict):
    """Map a descriptor pt rect (bottom-left y-up) to a raster pixel rect."""
    px1 = mapping.descriptor_to_pixel(region["x"], region["y"])
    px2 = mapping.descriptor_to_pixel(region["x"] + region["w"], region["y"] + region["h"])
    x0, x1 = sorted((px1[0], px2[0]))
    y0, y1 = sorted((px1[1], px2[1]))
    return [round(x0), round(y0), round(x1 - x0), round(y1 - y0)]


def _default_config():
    executable = shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=executable,
        renderer_version=render.detect_renderer_version(executable),
        dpi=72,
        page=1,
        binarization=Binarization(enabled=True, method="fixed-threshold", threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


def _maybe_render(config, source_path):
    """Render unless correlated: refusal precedes rendering (Design D5).

    The typed refusal itself is constructed in _page_record; this helper is
    the single statement of "a correlated config never invokes a renderer".
    """
    if config.evidence_class == "correlated":
        return None
    return render.render_page(config, source_path)


def _regions_for(calibration, carrier_id):
    matches = [c for c in calibration["carriers"] if c["id"] == carrier_id]
    assert len(matches) == 1, f"carrier {carrier_id!r} not uniquely recorded"
    return [dict(r) for r in matches[0]["regions"]]


def _page_record(page_number, regions, config, rendered, geometry, frame_name,
                 file=None):
    """One page entry: pinned render + frame-mapped claimed regions."""
    record = {"page": page_number, "file": file, "unavailable": None,
              "refusal": None,
              "regions": [], "image": None, "width": None, "height": None,
              "frame": frame_name}
    if config.evidence_class == "correlated":
        # Spec "Render lineage labeling covers both paths": oracle evaluation
        # SHALL NOT read correlated renders. The crop stays absent and the
        # carrier entry still records evidence_class `correlated`.
        refusal_reason = ("evaluation reads only independent renders; this "
                          "in-process PyMuPDF crop is correlated evidence "
                          "(extractor_lineage == renderer_lineage) and never "
                          "enters oracle evaluation")
        # Structured refusal (rule-of-5 CLAR-001): machine-readable code and
        # reason, so consumers never prefix-match the display string.
        record["refusal"] = {"code": CORRELATED_RENDER_REFUSED,
                             "reason": refusal_reason}
        record["unavailable"] = CORRELATED_RENDER_REFUSED + ": " + refusal_reason
        return record
    if isinstance(rendered, render.RenderUnavailable):
        record["unavailable"] = rendered.reason
        return record
    width, height = _pixmap_extent(rendered.data)
    record["image"] = "data:image/png;base64," + base64.b64encode(
        rendered.data).decode("ascii")
    record["width"] = width
    record["height"] = height
    if not regions:
        return record  # nothing claimed on this page; no frame question
    if frame_name is None:
        mapping = UnknownMapping(
            "invalid_geometry_frame", "page has no single declared space")
    else:
        mapping = frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, UnknownMapping):
        record["unavailable"] = (
            f"frame unknown: {mapping.reason}: {mapping.detail}")
        record["regions"] = [
            {"id": r["id"], "rect_px": None, "expected": r.get("expected")}
            for r in regions
        ]
    else:
        record["regions"] = [
            {"id": r["id"], "rect_px": _pixel_rect(mapping, r),
             "expected": r.get("expected")}
            for r in regions
        ]
    return record


def _bundle_record(carriers):
    return {
        "kind": "visual-review-bundle",
        "version": 2,
        "rules": RULES,
        "carriers": carriers,
    }


def build_review_bundle(
    pdf_path,
    *,
    regions,
    geometry,
    frame_name,
    carrier,
    out_path,
    config=None,
):
    """Render one pinned page, map claimed regions, embed the review SPA.

    ``regions`` are claimed descriptor rects (``{id, x, y, w, h}``, optional
    ``expected``) in descriptor coordinates. ``geometry`` is the declared
    geometry artifact; ``frame_name`` the frame to resolve. ``out_path``
    receives the self-contained HTML bundle. Returns the embedded record.
    """
    config = config or _default_config()
    # Refusal precedes rendering: a correlated config never invokes a
    # renderer at all — the crop is absent, typed, before any pixels exist.
    rendered = _maybe_render(config, pdf_path)
    page_record = _page_record(config.page, regions, config, rendered,
                               geometry, frame_name)
    record = _bundle_record([{
        "carrier": carrier,
        "evidence_class": config.evidence_class,
        "render_config": config.to_dict(),
        "pages": [page_record],
    }])
    _write_bundle(out_path, record)
    return record


def build_calibration_review_bundle(out_path, record_path=None, config=None):
    """Walk every unique render target recorded in the calibration record.

    Each recorded carrier contributes one page entry per unique (file,
    page, geometry, frame) render target, so the human reviews exactly the
    pages the oracles were calibrated on — including both rotated-strip
    frames. Returns the embedded v2 record.
    """
    record_path = Path(record_path or _CALIBRATION_PATH)
    calibration = json.loads(record_path.read_text())
    config = config or _default_config()

    # first-seen unique render targets per carrier, in record order
    targets = []
    seen = set()
    for run in calibration["per_page_outcomes"]:
        key = (run["carrier"], run["file"], run["page"],
               run.get("geometry"), run.get("frame"))
        if key not in seen:
            seen.add(key)
            targets.append(key)

    entries = {}
    for (carrier, file_rel, page, geometry_name, frame_name) in targets:
        entry_config = replace(config, page=page)
        geometry = json.loads(_GEOMETRY_ARTIFACTS[geometry_name].read_text())
        rendered = _maybe_render(entry_config, _ROOT / file_rel)
        page_record = _page_record(page, _regions_for(calibration, carrier),
                                   entry_config, rendered, geometry,
                                   frame_name, file=file_rel)
        entries.setdefault(carrier, []).append(page_record)

    carriers = []
    for recorded in calibration["carriers"]:
        carrier = recorded["id"]
        carriers.append({
            "carrier": carrier,
            "evidence_class": config.evidence_class,
            "render_config": config.to_dict(),
            "pages": entries[carrier],
        })
    record = _bundle_record(carriers)
    _write_bundle(out_path, record)
    return record


_PAGE_ID_RE = re.compile(r"^(?:pg|page-)(\d+)$")


def _descriptor_geometry(descriptor, base_dir):
    """Load the descriptor's declared geometry profile artifact (or None).

    The profile uri resolves relative to the descriptor file, exactly like
    the digitization run layout (blobs/, carrier/). A declared-but-unreadable
    profile returns None — every frame then stays typed unknown downstream,
    never a guessed convention.
    """
    for profile in descriptor.get("profiles", []):
        if profile.get("kind") != "geometry":
            continue
        try:
            return json.loads((Path(base_dir) / profile["uri"]).read_text())
        except (OSError, ValueError, KeyError):
            return None
    return None


def _descriptor_page_targets(descriptor):
    """Enumerate (page_region, regions, spaces) targets from a descriptor.

    Pages are the descriptor's ``kind: page`` regions, ordered by their
    derivable page number (``pgN``/``page-N``); claimed regions attach
    through ``contains`` relations and keep their ids verbatim. ``spaces``
    are each region's declared geometry ``space`` — the frame name the
    declared geometry profile must resolve.
    """
    region_by_id = {r["id"]: r for r in descriptor.get("regions", [])}
    contained = {}
    for rel in descriptor.get("relations", []):
        if rel.get("kind") == "contains":
            contained.setdefault(rel["from"], []).append(rel["to"])

    pages = [r for r in descriptor.get("regions", []) if r.get("kind") == "page"]
    pages.sort(key=lambda p: (
        (int(m.group(1)), 0) if (m := _PAGE_ID_RE.match(p["id"])) else (10**9, 0)))

    targets = []
    for page in pages:
        regions, spaces = [], []
        for rid in contained.get(page["id"], []):
            region = region_by_id.get(rid)
            if region is None or "geometry" not in region:
                continue
            box = region["geometry"]
            regions.append({
                "id": region["id"],
                "x": box["x"],
                "y": box["y"],
                "w": box.get("w", box.get("width")),
                "h": box.get("h", box.get("height")),
            })
            spaces.append(box.get("space"))
        targets.append((page, regions, spaces))
    return targets


def build_descriptor_review_bundle(descriptor_path, out_path, config=None):
    """Render every page of a digitization descriptor for human review.

    ``descriptor_path`` is a DSC 0.3 descriptor as produced by
    ``python3 -m digitization run`` (artifact ``descriptor.json``, whose
    ``source.locator`` resolves relative to the descriptor's directory).
    One page entry per descriptor page — never truncated; a page whose
    claimed regions declare no single resolvable space stays typed unknown
    with regions kept (rect_px null), through the same declared-frame math
    the oracles use. Returns the embedded v2 record.
    """
    config = config or _default_config()
    descriptor_path = Path(descriptor_path)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    base_dir = descriptor_path.parent
    source = base_dir / descriptor["source"]["locator"]
    geometry = _descriptor_geometry(descriptor, base_dir)

    page_records = []
    for page, regions, spaces in _descriptor_page_targets(descriptor):
        frame_name = spaces[0] if spaces and len(set(spaces)) == 1 else None
        matched = _PAGE_ID_RE.match(page["id"])
        if matched is None:
            page_records.append({
                "page": None, "file": descriptor["source"]["locator"],
                "unavailable": (
                    f"page number not derivable from region id {page['id']!r}"),
                "regions": [
                    {"id": r["id"], "rect_px": None, "expected": None}
                    for r in regions],
                "image": None, "width": None, "height": None,
                "frame": None,
            })
            continue
        entry_config = replace(config, page=int(matched.group(1)))
        try:
            rendered = _maybe_render(entry_config, source)
        except render.RenderCommandError as exc:
            rendered = render.RenderUnavailable(config=entry_config,
                                                reason=str(exc))
        page_records.append(_page_record(
            entry_config.page, regions, entry_config, rendered, geometry,
            frame_name, file=descriptor["source"]["locator"]))

    record = _bundle_record([{
        "carrier": descriptor["id"],
        "evidence_class": config.evidence_class,
        "render_config": config.to_dict(),
        "pages": page_records,
    }])
    _write_bundle(out_path, record)
    return record


def _write_bundle(out_path, record):
    template = TEMPLATE_PATH.read_text()
    embedded = json.dumps(record, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__REVIEW_DATA_ISLAND__", embedded)
    assert "__REVIEW_DATA_ISLAND__" not in html
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


# -- source-linked inspection & attributed comparison (document-structural-
#    debugger: sunset-5bu, sunset-36n, sunset-j1c) --------------------------------


# Endpoint type and comparator identity for attributed-reading comparisons
# (36n): two readings of one carrier compare ONLY through this declared scope.
_READING_ENDPOINT_TYPE = "reading-claims"
_READING_COMPARATOR_ID = "reading-claims"
_READING_COMPARATOR_VERSION = "1"


def _reading_claims_spec():
    """The declared comparison policy for attributed readings: endpoint types,
    versioned comparator id and the observable scope under which two readings
    may be compared at all. Deliberately narrow — the scoped observable is each
    reading's flattened claim text. No cross-reader region identity is ever
    declared or inferred."""
    return ComparatorSpec(
        comparator_id=_READING_COMPARATOR_ID,
        version=_READING_COMPARATOR_VERSION,
        input_types=(_READING_ENDPOINT_TYPE, _READING_ENDPOINT_TYPE),
        observable_scope=("flattened_text",),
    )


def _import_sheets(sheet_paths, *, source_root):
    """Sibling producer API indirection (dsc03.visual.sheet_import, shared
    contract). Imported at call time so this module stays loadable — and the
    existing bundle modes unaffected — while that slice is in flight; the
    browser journeys stub this seam with contract-shaped results."""
    from dsc03.visual.sheet_import import import_sheets

    return import_sheets(sheet_paths, source_root=source_root)


def _order_key(region):
    """Claimed order: order_rank first (missing/blank last), region_id as the
    tiebreak. The sort never invents an order where none was claimed."""
    rank = region.get("order_rank")
    rank = str(rank) if rank not in (None, "") else None
    return (rank is None, rank or "", str(region.get("region_id")))


def region_to_source_px(region, mapping):
    """Map an imported region's annotation-space ``bbox_px`` onto the pinned
    rendered source page (sunset-5bu; pure frame-transform helper).

    ``mapping`` carries the sheet's recorded page frame (``page_frame``: the
    x/y/w/h fractions of the source page the annotation viewport covered, plus
    its viewport_w/viewport_h) and the rendered page extent
    (``width``/``height``). The transform is exactly: page fraction = frame
    origin + annotation fraction x frame extent, scaled by the rendered
    extent. No convention is guessed: a missing frame or extent returns None —
    the caller records a typed unmapped region, never an invented highlight.
    """
    frame = mapping.get("page_frame")
    width = mapping.get("width")
    height = mapping.get("height")
    if not frame or not width or not height:
        return None
    viewport_w, viewport_h = frame.get("viewport_w"), frame.get("viewport_h")
    if not viewport_w or not viewport_h:
        return None
    bx, by, bw, bh = region["bbox_px"]
    x0 = frame["x"] + (bx / viewport_w) * frame["w"]
    y0 = frame["y"] + (by / viewport_h) * frame["h"]
    w = (bw / viewport_w) * frame["w"]
    h = (bh / viewport_h) * frame["h"]
    return [round(x0 * width), round(y0 * height),
            round(w * width), round(h * height)]


def _sha256_path(path):
    path = Path(path)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_file_record(path):
    """Source file path relative to the repo root when possible (provenance)."""
    path = Path(path)
    try:
        return str(path.resolve().relative_to(_ROOT))
    except ValueError:
        return str(path)


def _refusal_dict(refusal):
    """ImportRefusal -> plain record dict (the shared contract names
    region_key/reason/detail; attribute access stays inside this module)."""
    return {"region_key": refusal.region_key, "reason": refusal.reason,
            "detail": refusal.detail}


def _sheet_id_of_region_key(region_key, sheet_ids):
    """The originating sheet of a sheet-scoped region key (longest prefix)."""
    matches = [s for s in sorted(sheet_ids, key=len, reverse=True)
               if region_key.startswith(s + ":")]
    if not matches:
        raise ValueError(
            f"import refusal {region_key!r} references no known sheet of "
            f"{sorted(sheet_ids)}; total accounting forbids dropping it")
    return matches[0]


def _import_region_entry(region, rect_px, unmapped_reason, page_frame):
    """Display record for one imported region — attribution and geometry
    provenance retained even when the region cannot be highlighted."""
    return {
        "region_id": region["region_id"],
        "sheet_id": region["sheet_id"],
        "reader": region.get("reader"),
        "page": region.get("page"),
        "rect_px": rect_px,
        "unmapped_reason": unmapped_reason,
        "page_frame": page_frame,
        "bbox_relative": region.get("bbox_relative"),
        "viewport_w": region.get("viewport_w"),
        "viewport_h": region.get("viewport_h"),
        "type": region.get("type"),
        "type_provenance": region.get("type_provenance"),
        "order_rank": region.get("order_rank"),
        "order_alternatives": list(region.get("order_alternatives") or []),
        "evidence": region.get("evidence"),
    }


def _source_page_record(page_number, config, rendered, source_file):
    """One pinned source page (shared by both debugger bundle modes): typed
    render outcomes, never silent — a correlated config refuses before pixels
    exist (Design D5), an unavailable render carries its reason."""
    record = {"page": page_number, "file": source_file, "unavailable": None,
              "refusal": None, "regions": [], "image": None,
              "width": None, "height": None}
    if config.evidence_class == "correlated":
        reason = ("evaluation reads only independent renders; this "
                  "in-process crop is correlated evidence "
                  "(extractor_lineage == renderer_lineage) and never enters "
                  "oracle evaluation")
        record["refusal"] = {"code": CORRELATED_RENDER_REFUSED, "reason": reason}
        record["unavailable"] = CORRELATED_RENDER_REFUSED + ": " + reason
    elif isinstance(rendered, render.RenderUnavailable):
        record["unavailable"] = rendered.reason
    else:
        width, height = _pixmap_extent(rendered.data)
        record["image"] = "data:image/png;base64," + base64.b64encode(
            rendered.data).decode("ascii")
        record["width"] = width
        record["height"] = height
    return record


def _frame_for_page(sheet, page):
    frames = sheet.get("page_frames") or {}
    if str(page) in frames:
        return frames[str(page)]
    return frames.get(page)


def _map_imported_region(region, sheet_by_id, page_record, mismatch_by_sheet):
    """(rect_px, unmapped_reason, page_frame) for one imported region against a
    rendered source page. Refusal order: render state first, then the sheet's
    pinned digest, then the recorded page frame — a region gets a highlight
    only when source bytes, digest and frame all verify."""
    sheet = sheet_by_id[region["sheet_id"]]
    if page_record["refusal"]:
        return None, f"render-refused: {page_record['refusal']['code']}", None
    if page_record["unavailable"]:
        return None, (f"source-render-unavailable: "
                      f"{page_record['unavailable']}"), None
    mismatch = mismatch_by_sheet.get(region["sheet_id"])
    if mismatch is not None:
        return None, (f"source-digest-mismatch: sheet {region['sheet_id']!r} pins "
                      f"{mismatch['expected']} but the bundled source hashes "
                      f"{mismatch['actual']}; refusing to invent a highlight"), None
    frame = _frame_for_page(sheet, page_record["page"])
    if frame is None:
        return None, (f"missing-frame: sheet {region['sheet_id']!r} records no "
                      f"page frame for page {page_record['page']}; no highlight "
                      f"can be derived"), None
    rect = region_to_source_px(region, {"page_frame": frame,
                                        "width": page_record["width"],
                                        "height": page_record["height"]})
    if rect is None:
        return None, "missing-frame: recorded page frame lacks an extent", frame
    return rect, None, frame


def _carriers_from_result(result, config, source_pdf):
    """Group an import result by carrier and render each carrier's source pages
    once through the pinned render path. Verifies each sheet's pinned source
    digest against the actually bundled PDF; refusals are routed to their
    originating sheet's carrier (total accounting: nothing dropped)."""
    sheets = [dict(s) for s in result.sheets]
    refusals = [_refusal_dict(r) for r in result.refusals]
    known_sheet_ids = {s["sheet_id"] for s in sheets}
    for region in result.regions:
        if region.get("sheet_id") not in known_sheet_ids:
            raise ValueError(
                f"imported region {region.get('region_id')!r} references "
                f"sheet_id {region.get('sheet_id')!r} which no sheet "
                f"declares; total accounting forbids dropping it")

    carriers = []
    for carrier in dict.fromkeys(s["carrier"] for s in sheets):
        carrier_sheets = [s for s in sheets if s["carrier"] == carrier]
        sheet_ids = {s["sheet_id"] for s in carrier_sheets}
        sheet_by_id = {s["sheet_id"]: s for s in carrier_sheets}
        carrier_regions = [r for r in result.regions if r["sheet_id"] in sheet_ids]
        carrier_refusals = [
            r for r in refusals
            if _sheet_id_of_region_key(r["region_key"], known_sheet_ids) in sheet_ids]
        pdf = (Path(source_pdf) if source_pdf is not None
               else _ROOT / "fixtures" / "carriers" / f"{carrier}.pdf")
        actual_sha = _sha256_path(pdf)
        mismatch_list = [{"sheet_id": s["sheet_id"], "expected": s["source_sha256"],
                          "actual": actual_sha}
                         for s in carrier_sheets
                         if s.get("source_sha256") and s["source_sha256"] != actual_sha]
        mismatch_by_sheet = {m["sheet_id"]: m for m in mismatch_list}

        pages = {}
        for region in carrier_regions:
            pages.setdefault(int(region["page"]), []).append(region)
        page_records = []
        for page_number in sorted(pages):
            entry_config = replace(config, page=page_number)
            try:
                rendered = _maybe_render(entry_config, pdf)
            except render.RenderCommandError as exc:
                rendered = render.RenderUnavailable(config=entry_config,
                                                    reason=str(exc))
            page_record = _source_page_record(page_number, entry_config, rendered,
                                              _source_file_record(pdf))
            entries = []
            for region in sorted(pages[page_number], key=_order_key):
                rect, reason, frame = _map_imported_region(
                    region, sheet_by_id, page_record, mismatch_by_sheet)
                entries.append(_import_region_entry(region, rect, reason, frame))
            page_record["regions"] = entries
            page_records.append(page_record)

        carriers.append({
            "carrier": carrier,
            "evidence_class": config.evidence_class,
            "render_config": config.to_dict(),
            "source_file": _source_file_record(pdf),
            "source_sha256": actual_sha,
            "sheets": carrier_sheets,
            "source_digest_mismatch": mismatch_list,
            "pages": page_records,
            "refusals": carrier_refusals,
        })
    return carriers


def build_imported_sheet_bundle(result, *, out_path, source_pdf=None, config=None):
    """sunset-5bu bundle core: embed imported human-sheet regions ON their PDF
    source pages (pinned render + recorded page-frame transform) so a reviewer
    can select each region by pointer or keyboard and see page, source
    highlight, stable identity, sheet attribution, type provenance and
    evidence together. Every import refusal renders as a typed unresolved
    entry; regions whose digest, render or frame cannot be verified stay
    typed-unmapped. Returns the embedded record."""
    config = config or _default_config()
    record = {
        "kind": "visual-review-bundle",
        "version": 2,
        "mode": "import-inspection",
        "rules": RULES,
        "carriers": _carriers_from_result(result, config, source_pdf),
    }
    _write_bundle(out_path, record)
    return record


def build_import_review_bundle(sheet_paths, *, source_root, out_path,
                               source_pdf=None, config=None):
    """sunset-5bu source-linked inspection browser: import human sheets through
    the sheet-import API (shared contract) and render every imported region on
    its PDF source page. Returns the embedded record."""
    result = _import_sheets(sheet_paths, source_root=source_root)
    return build_imported_sheet_bundle(result, out_path=out_path,
                                       source_pdf=source_pdf, config=config)


def _reading_payload(regions):
    """One reading's claims as the declared scoped observable: a flattened text
    with one line per region in claimed order carrying its type claim. Order
    claims are part of the text, so a reading-order disagreement is visible as
    a text difference. Each side is reduced independently — no cross-reader
    pairing happens here or anywhere else in the bundle."""
    return {"flattened_text": "\n".join(
        str(r.get("type") or "") for r in sorted(regions, key=_order_key))}


def _reading_entries(regions, sheet_by_id, source_pages, mismatch_by_sheet):
    """Region display entries for one reading, mapped onto the shared rendered
    pages (rect_px may be None with a typed unmapped reason)."""
    entries_by_page = {}
    for region in sorted(regions, key=_order_key):
        page_record = source_pages[int(region["page"])]
        rect, reason, frame = _map_imported_region(
            region, sheet_by_id, page_record, mismatch_by_sheet)
        entries_by_page.setdefault(int(region["page"]), []).append(
            _import_region_entry(region, rect, reason, frame))
    return entries_by_page


def build_comparison_bundle(result, *, out_path, source_pdf=None, spec=None,
                            config=None):
    """sunset-36n + sunset-j1c bundle core: two attributed readings of one
    carrier, side by side, with the pinned PDF source pane and per-page
    comparison outcomes and witnesses from dsc03.compare.scoped_compare under
    the declared scope. The record carries NO winner field and NO cross-reader
    region identity — only both sides' claims and the typed outcomes. A
    reading with no recorded claims on a page stays typed unexamined (absence
    is never converted into agreement). Non-equivalent, fully-attributed
    comparisons are pinned at build time via export_counterexample +
    serialize_bundle (source PDF bytes omitted — digest only), so the export
    button hands out exactly the pinned bytes. Returns the embedded record."""
    config = config or _default_config()
    spec = spec or _reading_claims_spec()
    sheets = [dict(s) for s in result.sheets]
    if not sheets:
        raise ValueError("ab-comparison needs imported sheets to compare")
    carrier_names = list(dict.fromkeys(s["carrier"] for s in sheets))
    if len(carrier_names) != 1:
        raise ValueError(
            f"ab-comparison compares two readings of ONE carrier; got "
            f"{len(carrier_names)}: {sorted(carrier_names)}")
    carrier = carrier_names[0]
    by_reader = {}
    for sheet in sheets:
        by_reader.setdefault(sheet.get("reader") or "reader-unattributed",
                             []).append(sheet)
    if len(by_reader) != 2:
        raise ValueError(
            f"ab-comparison compares exactly two attributed readings; got "
            f"{len(by_reader)}: {sorted(by_reader)}")

    pdf = (Path(source_pdf) if source_pdf is not None
           else _ROOT / "fixtures" / "carriers" / f"{carrier}.pdf")
    actual_sha = _sha256_path(pdf)
    source_file = _source_file_record(pdf)

    mismatch_list = [{"sheet_id": s["sheet_id"], "expected": s["source_sha256"],
                      "actual": actual_sha}
                     for s in sheets
                     if s.get("source_sha256") and s["source_sha256"] != actual_sha]
    mismatch_by_sheet = {m["sheet_id"]: m for m in mismatch_list}
    sheet_by_id = {s["sheet_id"]: s for s in sheets}

    regions_by_reader = {}
    for reader, reader_sheets in by_reader.items():
        reader_ids = {s["sheet_id"] for s in reader_sheets}
        regions_by_reader[reader] = [r for r in result.regions
                                     if r.get("sheet_id") in reader_ids]

    page_numbers = sorted({int(r["page"])
                           for regions in regions_by_reader.values()
                           for r in regions})
    source_pages = {}
    for page_number in page_numbers:
        entry_config = replace(config, page=page_number)
        try:
            rendered = _maybe_render(entry_config, pdf)
        except render.RenderCommandError as exc:
            rendered = render.RenderUnavailable(config=entry_config,
                                                reason=str(exc))
        source_pages[page_number] = _source_page_record(
            page_number, entry_config, rendered, source_file)

    readings = []
    for reader in sorted(regions_by_reader):
        entries_by_page = _reading_entries(
            regions_by_reader[reader], sheet_by_id, source_pages, mismatch_by_sheet)
        readings.append({
            "reader": reader,
            "sheet_ids": sorted(s["sheet_id"] for s in by_reader[reader]),
            "pages": [{"page": p, "regions": entries_by_page.get(p, [])}
                      for p in page_numbers],
        })

    left_reader, right_reader = sorted(regions_by_reader)
    comparisons, counterexamples = [], []
    for page_number in page_numbers:
        left_regions = [r for r in regions_by_reader[left_reader]
                        if int(r["page"]) == page_number]
        right_regions = [r for r in regions_by_reader[right_reader]
                         if int(r["page"]) == page_number]
        left_input = ComparisonInput(_READING_ENDPOINT_TYPE,
                                     _reading_payload(left_regions),
                                     source_sha256=actual_sha or "")
        right_input = ComparisonInput(_READING_ENDPOINT_TYPE,
                                      _reading_payload(right_regions),
                                      source_sha256=actual_sha or "")
        missing = None
        if not left_regions or not right_regions:
            missing = left_reader if not left_regions else right_reader
            outcome = ComparisonOutcome(
                "unexamined", RULE_UNEXAMINED, f"reading:{missing}",
                f"{missing} has no recorded claims on page {page_number}; "
                f"absence is not agreement")
        else:
            outcome = scoped_compare(spec, left_input, right_input)
        comparisons.append({
            "page": page_number,
            "scope": list(spec.observable_scope),
            "outcome": outcome.outcome,
            "rule_id": outcome.rule_id,
            "witness": outcome.witness,
            "message": outcome.message,
            "expected": outcome.details.get("expected"),
            "observed": outcome.details.get("observed"),
            "missing_reading": missing,
        })
        if outcome.outcome != "equivalent" and missing is None:
            exported = export_counterexample(outcome, spec, left_input, right_input)
            counterexamples.append({
                "page": page_number,
                "rule_id": outcome.rule_id,
                "outcome": outcome.outcome,
                "serialized": serialize_bundle(exported).decode("utf-8"),
            })

    record = {
        "kind": "visual-review-bundle",
        "version": 2,
        "mode": "ab-comparison",
        "rules": RULES,
        "carrier": carrier,
        "source_file": source_file,
        "source_sha256": actual_sha,
        "evidence_class": config.evidence_class,
        "render_config": config.to_dict(),
        "spec": {"comparator_id": spec.comparator_id, "version": spec.version,
                 "input_types": list(spec.input_types),
                 "observable_scope": list(spec.observable_scope)},
        "readings": readings,
        "source_pages": [source_pages[p] for p in page_numbers],
        "comparisons": comparisons,
        "counterexamples": counterexamples,
        "import_refusals": [_refusal_dict(r) for r in result.refusals],
    }
    _write_bundle(out_path, record)
    return record


def build_ab_comparison_bundle(sheet_paths, *, source_root, out_path,
                               source_pdf=None, spec=None, config=None):
    """sunset-36n attributed A/B comparison: import both human sheets through
    the sheet-import API and build the attributed comparison bundle. Returns
    the embedded record."""
    result = _import_sheets(sheet_paths, source_root=source_root)
    return build_comparison_bundle(result, out_path=out_path,
                                   source_pdf=source_pdf, spec=spec,
                                   config=config)


def reopen_counterexample(bundle_bytes, pdf_path):
    """sunset-j1c reopen path: load an exported counterexample bundle
    (dsc03.compare.load_bundle) and replay it (dsc03.compare.replay) against a
    user-supplied local PDF. The local PDF's sha256 must match the bundle's
    pinned source digests before anything is replayed; every refusal is a
    typed state — never a guessed outcome, never a claimed successful source
    replay on a mismatch. ``source-digest-mismatch`` / ``not-replayable`` (the
    NotReplayable signal) / ``source-digest-unavailable`` / ``invalid-bundle``
    are answers, not errors."""
    if isinstance(bundle_bytes, (str, Path)):
        bundle_bytes = Path(bundle_bytes).read_bytes()
    try:
        bundle = load_bundle(bundle_bytes)
    except (ValueError, UnicodeDecodeError) as exc:
        return {"status": "invalid-bundle", "detail": str(exc)}
    witness = bundle.get("witness") or {}
    if not witness.get("replayable", True):
        return {"status": "not-replayable",
                "rule_id": witness.get("rule_id"),
                "reason": "; ".join(witness.get("replay_limitations")
                                    or ["redacted"])}
    inputs = bundle.get("inputs") or {}
    left_in = inputs.get("left") or {}
    right_in = inputs.get("right") or {}
    pinned = [d for d in (left_in.get("source_sha256"),
                          right_in.get("source_sha256")) if d]
    if not pinned:
        return {"status": "source-digest-unavailable",
                "reason": ("bundle pins no source digest; refusing to replay "
                           "against an unverified local PDF")}
    actual = _sha256_path(pdf_path)
    if actual not in pinned:
        return {"status": "source-digest-mismatch",
                "expected": pinned, "actual": actual}

    def _input(record):
        return ComparisonInput(record.get("endpoint_type"),
                               record.get("payload") or {},
                               record.get("descriptor_sha256", ""),
                               record.get("source_sha256", ""))

    try:
        outcome = replay(bundle, _input(left_in), _input(right_in))
    except NotReplayable as exc:  # defensive: witness.replayable lied
        return {"status": "not-replayable", "reason": str(exc)}
    return {
        "status": "replayed",
        "outcome": outcome.outcome,
        "rule_id": outcome.rule_id,
        "witness": outcome.witness,
        "message": outcome.message,
        "locus": {"source_digest": actual, "witness": outcome.witness},
        "exported_outcome": witness.get("outcome"),
        "matches_exported": outcome.outcome == witness.get("outcome"),
    }


# -- verdicts ingest -------------------------------------------------------------------


_VERDICT_VOCABULARY = ("agree", "differ", "unknown")

# Ingest compares human verdicts against the derivation rows the review
# bundle was built from (build_calibration_review_bundle walks every unique
# (carrier, file, page, geometry, frame) target across all recorded runs);
# detection-run outcomes are a different oracle pass and are not attributed
# to the human pass.
_INGEST_RUN = "derivation"


def _record_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _oracle_rows(calibration):
    """derivation-run oracle outcomes keyed by (carrier, page, property)."""
    return {(row["carrier"], row["page"], row["property"]): row
            for row in calibration["per_page_outcomes"]
            if row.get("run", _INGEST_RUN) == _INGEST_RUN}


def _refuse(bundle, record_path):
    """Version pinning (typed refusal, never a warning)."""
    actual = _record_sha(record_path)
    if bundle.get("record_sha256") != actual:
        raise RecordVersionMismatch(
            f"verdicts bundle pins record sha256 "
            f"{bundle.get('record_sha256')!r} but {record_path} hashes to "
            f"{actual!r}; FP/FN statistics are never attributed to the "
            f"wrong record version")
    if bundle.get("base_commit") != _BASE_COMMIT:
        raise RecordVersionMismatch(
            f"verdicts bundle pins base_commit {bundle.get('base_commit')!r} "
            f"but ingest runs against {_BASE_COMMIT!r}; refusing to "
            f"attribute verdicts across commits")


def _base_commit():
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(_ROOT),
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 — provenance degrades to typed unknown
        return None


_BASE_COMMIT = _base_commit()


def _counterexample(row, record_sha, bundle_sha):
    """One differ row in the dsc03 counterexample format.

    replayable=false per existing convention (human verdicts are not
    machine-replayable); dsc03.compare.replay refuses the bundle."""
    return {
        "witness": {
            "rule_id": "visual-review-verdict-differ",
            "outcome": "differ",
            "comparator": {"id": "human-visual-review", "version": "1"},
            "endpoint_types": ["calibration-oracle", "human-verdict"],
            "observable_scope": ["carrier", "page", "region", "property"],
            "input_hashes": {
                "calibration_record": record_sha,
                "verdicts_bundle": bundle_sha,
            },
            "expected": "oracle agree",
            "observed": "human differ",
            "message": (f"human verdicts differ on region "
                        f"{row['region']!r} where the oracle recorded agree "
                        f"({row['carrier']} page {row['page']} "
                        f"{row['property']})"),
            "replayable": False,
            "redaction": {
                "omitted": ["rendered page pixels", "human review session"],
                "limitation": "human visual verdicts cannot be "
                              "machine-replayed; rerun requires the pinned "
                              "review bundle and a fresh human pass",
            },
            "replay_limitations": ["human verdicts are not machine-replayable"],
        },
        "inputs": {
            "carrier": row["carrier"],
            "page": row["page"],
            "region": row["region"],
            "property": row["property"],
        },
    }


def ingest_verdicts(verdicts_path, record_path=None, evaluation_record=None):
    """Ingest a review-verdicts bundle against the pinned calibration record.

    Returns the ingest report: per carrier × page × property agreement
    counts (human agree/differ/unknown vs the recorded derivation oracle
    outcome; oracle false-negative = human differ where oracle agree; human
    unknown never resolves — no winner election, no smoothing), per-page
    missed-ink accounting (labeled ESTIMATE with the sunset-9rg caveat), and
    the differ rows exported in the dsc03 counterexample format with
    replayable=false. Refuses with RecordVersionMismatch when the bundle
    does not pin ``record_path`` (record sha256) and the ingest commit
    (base_commit). Never modifies thresholds; when ``evaluation_record`` is
    a dict, the summary is appended to it via
    digitization.evaluation.append_visual_review_summary.
    """
    import copy

    from digitization.evaluation import append_visual_review_summary

    record_path = Path(record_path or _CALIBRATION_PATH)
    bundle = json.loads(Path(verdicts_path).read_text(encoding="utf-8"))
    if bundle.get("provenance") not in (None, PROVENANCE_LABEL):
        raise RecordVersionMismatch(
            f"unexpected bundle provenance {bundle.get('provenance')!r}; "
            f"ingest only accepts {PROVENANCE_LABEL} bundles")
    _refuse(bundle, record_path)

    calibration = json.loads(record_path.read_text(encoding="utf-8"))
    record_sha = _record_sha(record_path)
    bundle_sha = _record_sha(verdicts_path)
    oracle = _oracle_rows(calibration)

    agreement, missed_ink, unavailable_pages, counterexamples = [], [], [], []
    unknown_total = 0
    oracle_fn_total = 0

    for carrier_entry in bundle["verdicts"]["carriers"]:
        carrier = carrier_entry["carrier"]
        for page_entry in carrier_entry["pages"]:
            page = page_entry["page"]
            if page_entry.get("unavailable"):
                unavailable_pages.append({
                    "carrier": carrier,
                    "page": page,
                    "reason": page_entry["unavailable"],
                })
            # tri-state tally; verdicts outside the vocabulary are refused,
            # never coerced
            human = {"agree": 0, "differ": 0, "unknown": 0, "pending": 0}
            region_rows = []
            differs_here = []
            for region in page_entry.get("regions", []):
                verdict = region.get("verdict")
                if verdict is None:
                    human["pending"] += 1
                elif verdict not in _VERDICT_VOCABULARY:
                    raise RecordVersionMismatch(
                        f"verdict {verdict!r} outside the "
                        f"agree/differ/unknown vocabulary "
                        f"({carrier} page {page} region {region.get('id')!r})")
                else:
                    human[verdict] += 1
                    if verdict == "unknown":
                        unknown_total += 1
                    region_rows.append({"id": region["id"], "verdict": verdict})
                    if verdict == "differ":
                        differs_here.append(region["id"])

            properties = sorted(
                prop for (c, _p, prop) in oracle
                if c == carrier and _p == page)
            for prop in properties:
                oracle_status = oracle[(carrier, page, prop)]["status"]
                confusion = dict(human)
                confusion.pop("pending")
                oracle_fn = human["differ"] if oracle_status == "agree" else 0
                oracle_fn_total += oracle_fn
                row = {
                    "carrier": carrier,
                    "page": page,
                    "property": prop,
                    "oracle_status": oracle_status,
                    "human": dict(human),
                    "confusion": confusion,
                    "oracle_false_negatives": oracle_fn,
                    "regions": [dict(r) for r in region_rows],
                }
                if page_entry.get("unavailable"):
                    row["unavailable"] = page_entry["unavailable"]
                agreement.append(row)
            # one counterexample per differing region — the human verdict is
            # region-level, never re-counted per property
            for region_id in differs_here:
                counterexamples.append(_counterexample(
                    {"carrier": carrier, "page": page,
                     "region": region_id, "property": properties},
                    record_sha, bundle_sha))

            # missed-ink accounting: per page, count + total box area vs
            # page area — a proxy ESTIMATE, never a measurement
            page_size = page_entry.get("page_size_px") or None
            boxes = page_entry.get("missed_ink", [])
            total_area = sum(b["rect_px"][2] * b["rect_px"][3] for b in boxes)
            page_area = page_size[0] * page_size[1] if page_size else None
            missed_ink.append({
                "carrier": carrier,
                "page": page,
                "label": "ESTIMATE",
                "caveat": MISSING_INK_CAVEAT,
                "count": len(boxes),
                "total_area_px": total_area,
                "page_area_px": page_area,
                "area_fraction": (total_area / page_area
                                  if page_area else None),
            })

    report = {
        "kind": "visual-review-ingest-report",
        "version": 1,
        "provenance": PROVENANCE_LABEL,
        "record_path": str(record_path),
        "record_sha256": record_sha,
        "base_commit": bundle.get("base_commit"),
        "agreement": agreement,
        "missed_ink": missed_ink,
        "unavailable_pages": unavailable_pages,
        "counterexamples": counterexamples,
        "evaluation_summary": {
            "provenance": PROVENANCE_LABEL,
            "record_sha256": record_sha,
            "base_commit": bundle.get("base_commit"),
            "oracle_false_negatives": oracle_fn_total,
            "human_unknown_total": unknown_total,
            "missed_ink_pages": [
                {"carrier": m["carrier"], "page": m["page"],
                 "count": m["count"], "total_area_px": m["total_area_px"],
                 "area_fraction": m["area_fraction"]}
                for m in missed_ink if m["count"]],
            "differ_counterexamples": len(counterexamples),
        },
        "thresholds_modified": False,
        "recorded_thresholds": copy.deepcopy(calibration.get("thresholds")),
    }
    if isinstance(evaluation_record, dict):
        append_visual_review_summary(evaluation_record,
                                     report["evaluation_summary"])
    return report


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=".visual-review/index.html")
    parser.add_argument("--record", default=None,
                        help="calibration record (default fixtures/visual/calibration.json)")
    parser.add_argument("--descriptor", default=None,
                        help="DSC 0.3 descriptor (e.g. a digitization run output); "
                             "mutually exclusive with --record")
    parser.add_argument("--sheets", nargs="+", default=None, metavar="SHEET_JSON",
                        help="human observation sheets to import through the "
                             "sheet-import API (sunset-5bu/36n); builds the "
                             "source-linked inspection bundle, or with --ab the "
                             "attributed A/B comparison bundle; mutually "
                             "exclusive with --record/--descriptor")
    parser.add_argument("--ab", action="store_true",
                        help="with --sheets: build the attributed A/B comparison "
                             "bundle with pinned counterexamples (sunset-36n/j1c)")
    parser.add_argument("--source-pdf", default=None,
                        help="explicit carrier PDF to render (default: "
                             "fixtures/carriers/<carrier>.pdf under the repo root)")
    parser.add_argument("--serve", nargs="?", const="8123", default=None,
                        metavar="PORT")
    sub = parser.add_subparsers(dest="command")
    ingest = sub.add_parser(
        "ingest", help="ingest a review-verdicts bundle against the pinned "
                       "calibration record; prints the ingest report JSON")
    ingest.add_argument("verdicts", help="verdicts JSON from the review SPA pass")
    ingest.add_argument("--record", default=None,
                        help="calibration record the bundle must pin "
                             "(default fixtures/visual/calibration.json)")
    ingest.add_argument("--counterexamples", default=None,
                        help="write differ rows (dsc03 counterexample format, "
                             "replayable=false) to this JSON path")
    reopen = sub.add_parser(
        "reopen", help="reopen an exported counterexample bundle against a "
                       "local PDF (sunset-j1c); prints the typed replay "
                       "result JSON (source-digest-mismatch / "
                       "not-replayable / source-digest-unavailable / "
                       "invalid-bundle are answers, not errors)")
    reopen.add_argument("bundle", help="exported counterexample bundle (.json)")
    reopen.add_argument("--pdf", required=True,
                        help="local PDF to verify against the pinned source "
                             "digest and replay")
    return parser


def main(argv=None):
    """Build (and optionally serve) the all-examples review bundle.

    ``--out`` writes the self-contained HTML; ``--serve [port]`` then serves
    the output directory over loopback-only http.server and opens the page.
    ``--sheets SHEET [SHEET...] [--ab] [--source-pdf PDF]`` imports human
    observation sheets through the sheet-import API and builds the
    source-linked inspection bundle (sunset-5bu) or, with ``--ab``, the
    attributed A/B comparison bundle with pinned counterexamples
    (sunset-36n/j1c). ``ingest <verdicts.json> [--record RECORD]`` ingests a
    verdicts bundle (typed refusal on record-version mismatch) and prints the
    report JSON. ``reopen <bundle.json> --pdf LOCAL.pdf`` replays an exported
    counterexample bundle against a local PDF and prints the typed result
    JSON (sunset-j1c).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "reopen":
        print(json.dumps(reopen_counterexample(Path(args.bundle).read_bytes(),
                                               args.pdf),
                         indent=1, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "ingest":
        report = ingest_verdicts(args.verdicts, record_path=args.record)
        if args.counterexamples:
            out = Path(args.counterexamples)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(report["counterexamples"], indent=1,
                           ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True))
        return 0
    if args.sheets and (args.descriptor or args.record):
        parser.error("--sheets is mutually exclusive with --record/--descriptor")
    if args.descriptor and args.record:
        parser.error("--descriptor and --record are mutually exclusive")

    if args.sheets:
        if args.ab:
            record = build_ab_comparison_bundle(
                args.sheets, source_root=_ROOT, out_path=args.out,
                source_pdf=args.source_pdf)
            print(f"built {args.out}: A/B comparison — {record['carrier']} — "
                  f"{len(record['comparisons'])} comparisons, "
                  f"{len(record['counterexamples'])} pinned counterexamples")
        else:
            record = build_import_review_bundle(
                args.sheets, source_root=_ROOT, out_path=args.out,
                source_pdf=args.source_pdf)
            n_regions = sum(len(p["regions"]) for c in record["carriers"]
                            for p in c["pages"])
            n_refusals = sum(len(c["refusals"]) for c in record["carriers"])
            print(f"built {args.out}: source-linked inspection — "
                  f"{len(record['carriers'])} carrier(s), {n_regions} imported "
                  f"regions, {n_refusals} unresolved import refusals")
    elif args.descriptor:
        record = build_descriptor_review_bundle(args.descriptor, args.out)
        n_pages = sum(len(c["pages"]) for c in record["carriers"])
        print(f"built {args.out}: {record['carriers'][0]['carrier']} — "
              f"{n_pages} descriptor pages")
    else:
        record = build_calibration_review_bundle(args.out, record_path=args.record)
        n_pages = sum(len(c["pages"]) for c in record["carriers"])
        print(f"built {args.out}: {len(record['carriers'])} carriers, "
              f"{n_pages} render targets")

    if args.serve:
        port = int(args.serve)
        out_dir = Path(args.out).resolve().parent
        url = f"http://localhost:{port}/{Path(args.out).name}"
        print(f"serving {url} (Ctrl-C to stop)")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        import http.server
        import socketserver

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(out_dir), **kw)

            def log_message(self, fmt, *log_args):
                pass

        with socketserver.TCPServer(("127.0.0.1", port), _Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
