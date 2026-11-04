# Purpose: Content-class-aware observation layer (sunset-pkj, per sunset-9rg;
#   transcript 6ae4669e: on BORA gazettes the decorative heading band is
#   invisible to native text objects; ink-coverage 71.89% -> 99.55% once
#   graphic-region candidates are counted).
# Responsibilities: observe ONE source-PDF page through FOUR typed classes —
#   text spans / vector paths / raster placements (carrier observations) +
#   graphic-region candidates from connected-component morphology over the
#   PINNED render; every entry tied to source sha256, declared frame, page;
#   typed outcomes (observed / invalid-source / invalid-page); unknown frame
#   keeps rect_pt with rect_px null; render unavailable -> no candidates with
#   a carried reason — never guessed coordinates, never silent drops.
# Rationale: O-A01 boundary (hard): class-4 entries are hypotheses with
#   provenance — never DSC observations, never projected without a declared
#   equivalence (dsc03.boundaries); outside normative DSC core.
"""Content-class observations: text / vector / raster + morphology hypotheses."""
from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from dsc03.visual import RenderConfig, render
from dsc03.visual.coverage import _decode_grayscale, _dilate, _ink_table, _parse_dilation
from dsc03.visual.frames import UnknownMapping, frame_mapping

KIND = "content-class-observations"
VERSION = 1
MIN_AREA_PX = 4
CONNECTIVITY = 8
DRAW_TYPES = {"s": "stroke", "f": "fill", "fs": "fill-stroke"}
OBJECT_CLASSES = ("text", "vector", "raster")


@dataclass
class _PageEnv:
    """Per-page observation context threaded through every helper."""

    file: str
    page_number: int
    sha: str
    frame_name: str
    mapping: object
    page: object = None
    width: int = None
    height: int = None
    simplified: bytearray = None
    masks: dict = None
    seen: bytearray = None


def _default_config(page):
    executable = shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return RenderConfig(
        renderer_name="pdftoppm", renderer_executable=executable,
        renderer_version=render.detect_renderer_version(executable), dpi=72,
        page=page, binarization=render.Binarization(
            enabled=True, method="fixed-threshold", threshold=128),
        source_simplification="ink-dilation-2px", extractor_lineage="pymupdf",
        renderer_lineage="poppler")


def _empty_record(source, page_frame, status, reason):
    """Typed non-observed record: no entries, nothing guessed, nothing dropped."""
    page_number, frame_name = page_frame
    sections = {name: {"role": "carrier-observation", "count": 0, "entries": []}
                for name in OBJECT_CLASSES}
    sections["graphic-hypothesis"] = {"role": "hypothesis", "count": 0, "status": "not-derived", "entries": []}
    return {
        "kind": KIND, "version": VERSION, "status": status, "reason": reason,
        "page": page_number,
        "source": {"file": str(source), "sha256": None, "extractor": {"id": "pymupdf"}},
        "frame": {"name": frame_name, "status": "unknown", "reason": reason},
        "render": {"status": "unavailable", "reason": reason, "config": None},
        "evidence_class": "independent", "classes": sections}


def _open_pdf(path):
    import pymupdf

    try:
        data = path.read_bytes()
    except OSError:
        return None, None, "unreadable source"
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        return None, None, "undecodable pdf"
    return data, doc, None


def _valid_page(page_number, doc):
    return (isinstance(page_number, int) and not isinstance(page_number, bool)
            and 1 <= page_number <= doc.page_count)


def _canonical_rect(bbox, height):
    x0, y0, x1, y1 = bbox
    return [round(x0, 6), round(height - y1, 6), round(x1, 6), round(height - y0, 6)]


def _base_entry(class_name, env):
    return {"class": class_name, "page": env.page_number,
            "source_sha256": env.sha, "frame": env.frame_name}


def _span_entries(block, page, env):
    if block["type"] != 0:
        return []
    return [_text_entry(s, page, env) for l in block["lines"] for s in l["spans"]]


def _text_entry(span, page, env):
    entry = _base_entry("text", env)
    entry["rect_pt"] = _canonical_rect(span["bbox"], page.rect.height)
    entry.update({"text": span["text"], "font": span["font"], "size": span["size"]})
    return entry


def _text_entries(page, env):
    entries = []
    for block in page.get_text("dict")["blocks"]:
        entries.extend(_span_entries(block, page, env))
    return entries


def _vector_entry(item, page, env):
    entry = _base_entry("vector", env)
    entry["rect_pt"] = _canonical_rect(list(item["rect"]), page.rect.height)
    entry["draw_type"] = DRAW_TYPES.get(item["type"], str(item["type"]))
    entry["items"] = len(item["items"])
    return entry


def _vector_entries(page, env):
    return [_vector_entry(item, page, env) for item in page.get_drawings()]


def _raster_entry(info, page, env):
    entry = _base_entry("raster", env)
    entry["rect_pt"] = _canonical_rect(list(info["bbox"]), page.rect.height)
    entry["image_size"] = [info["width"], info["height"]]
    return entry


def _raster_entries(page, env):
    return [_raster_entry(info, page, env) for info in page.get_image_info()]


def _px_rect(mapping, rect_pt):
    x0, y0, x1, y1 = rect_pt
    pa = mapping.descriptor_to_pixel(x0, y0)
    pb = mapping.descriptor_to_pixel(x1, y1)
    return [int(round(min(pa[0], pb[0]))), int(round(min(pa[1], pb[1]))),
            int(round(max(pa[0], pb[0]))), int(round(max(pa[1], pb[1])))]


def _pt_rect(mapping, bbox):
    """Map a px corner rect back to canonical pt through the declared frame."""
    pa = mapping.pixel_to_descriptor(bbox[0], bbox[1])
    pb = mapping.pixel_to_descriptor(bbox[2], bbox[3])
    return [round(min(pa[0], pb[0]), 6), round(min(pa[1], pb[1]), 6),
            round(max(pa[0], pb[0]), 6), round(max(pa[1], pb[1]), 6)]


def _apply_mapping(entries, mapping):
    """Attach rect_px / mapping; unknown keeps canonical pt and nulls px."""
    for entry in entries:
        if isinstance(mapping, UnknownMapping):
            entry["mapping"] = "unknown"
            entry["rect_px"] = None
        else:
            entry["mapping"] = "resolved"
            entry["rect_px"] = _px_rect(mapping, entry["rect_pt"])


def _neighbors(x, y, env):
    """Yield in-bounds 8-connected neighbor indices of one pixel."""
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if (dx or dy) and 0 <= nx < env.width and 0 <= ny < env.height:
                yield ny * env.width + nx


def _flood(start, env):
    env.seen[start] = 1
    stack = [start]
    minx = maxx = start % env.width
    miny = maxy = start // env.width
    area = 0
    while stack:
        cur = stack.pop()
        x, y = cur % env.width, cur // env.width
        minx, maxx = min(minx, x), max(maxx, x)
        miny, maxy = min(miny, y), max(maxy, y)
        area += 1
        for idx in _neighbors(x, y, env):
            if env.simplified[idx] == 1 and not env.seen[idx]:
                env.seen[idx] = 1
                stack.append(idx)
    return (minx, miny, maxx + 1, maxy + 1, area)


def _components(env, min_area):
    env.seen = bytearray(env.width * env.height)
    found = []
    for start in range(env.width * env.height):
        if env.simplified[start] == 1 and not env.seen[start]:
            box = _flood(start, env)
            if box[4] >= min_area:
                found.append(box)
    found.sort(key=lambda c: (c[1], c[0]))
    return found


def _paint_rect(mask, rect, width, height):
    x0, y0, x1, y1 = rect
    if x1 <= x0:
        x1 = x0 + 1
    if y1 <= y0:
        y1 = y0 + 1
    for y in range(max(0, y0), min(height, y1)):
        base = y * width
        lo, hi = max(0, x0), min(width, x1)
        if hi > lo:
            mask[base + lo:base + hi] = b"\x01" * (hi - lo)


def _class_pixel_masks(entries_px, width, height):
    masks = {}
    for name in OBJECT_CLASSES:
        mask = bytearray(width * height)
        for rect in entries_px[name]:
            _paint_rect(mask, rect, width, height)
        masks[name] = mask
    return masks


def _ink_indices(env, bbox):
    x0, y0, x1, y1 = bbox
    for y in range(y0, y1):
        base = y * env.width
        for offset, is_ink in enumerate(env.simplified[base + x0:base + x1]):
            if is_ink:
                yield base + x0 + offset


def _component_attribution(component, env):
    """Typed shares over ink matching >=1 class mask; dominant = max >= 0.5."""
    hits = {name: sum(1 for idx in _ink_indices(env, component[:4])
                      if env.masks[name][idx])
            for name in OBJECT_CLASSES}
    attributed = sum(1 for idx in _ink_indices(env, component[:4])
                     if any(env.masks[name][idx] for name in OBJECT_CLASSES))
    shares = {name: round(hits[name] / attributed, 6) if attributed else 0.0
              for name in OBJECT_CLASSES}
    top = max(shares.values())
    dominant = max(shares, key=shares.get) if top >= 0.5 else None
    return shares, dominant


def _hypothesis_entry(component, env, method):
    x0, y0, x1, y1, area = component
    entry = _base_entry("graphic-hypothesis", env)
    unknown = isinstance(env.mapping, UnknownMapping)
    entry["mapping"] = "unknown" if unknown else "resolved"
    entry["interpretation_status"] = "hypothesis"
    entry["rect_px"] = [x0, y0, x1, y1]
    if unknown:
        entry["rect_pt"] = None
        entry["attribution"] = None
        entry["attribution_status"] = "unknown-mapping"
    else:
        entry["rect_pt"] = _pt_rect(env.mapping, (x0, y1, x1, y0))
        shares, dominant = _component_attribution(component, env)
        entry["attribution"] = dict(shares, dominant=dominant)
        entry["attribution_status"] = "measured"
    entry["area_px"] = area
    entry["fill_share"] = round(area / ((x1 - x0) * (y1 - y0)), 6)
    entry["provenance"] = dict(method)
    return entry


def _hypothesis_entries(components, env, method):
    return [_hypothesis_entry(component, env, method) for component in components]


def _morphology_usable(config):
    b = config.binarization
    return (b.enabled and b.method == "fixed-threshold"
            and isinstance(b.threshold, int)
            and _parse_dilation(config.source_simplification) is not None)


def _simplified_mask(rendered, config, width, height):
    threshold = config.binarization.threshold
    dilation = _parse_dilation(config.source_simplification)
    _w, _h, gray = _decode_grayscale(rendered.data)
    return _dilate(bytearray(bytes(gray.translate(_ink_table(threshold)))),
                   width, height, dilation)


def _method_record(config):
    return {"derived_from": "pinned-render-morphology",
            "renderer": config.renderer_name, "dpi": config.dpi,
            "renderer_version": config.renderer_version,
            "threshold": config.binarization.threshold,
            "dilation_px": _parse_dilation(config.source_simplification),
            "connectivity": CONNECTIVITY, "min_area_px": MIN_AREA_PX}


def _px_by_class(entries):
    return {n: [e["rect_px"] for e in entries[n]] for n in OBJECT_CLASSES}


def _morphology_section(rendered, config, entries, env):
    section = {"role": "hypothesis", "count": 0, "status": "not-derived", "method": None, "entries": []}
    if not isinstance(rendered, render.Rendered):
        section["status"] = "render-unavailable"
        return section
    if not _morphology_usable(config):
        section["status"] = "unsupported-config"
        return section
    env.simplified = _simplified_mask(rendered, config, env.width, env.height)
    if not isinstance(env.mapping, UnknownMapping):
        env.masks = _class_pixel_masks(_px_by_class(entries), env.width, env.height)
    components = _components(env, MIN_AREA_PX)
    section["status"] = "derived"
    section["method"] = _method_record(config)
    section["entries"] = _hypothesis_entries(components, env, section["method"])
    section["count"] = len(section["entries"])
    return section


def _render_and_mapping(path, config, geometry, frame_name):
    rendered = render.render_page(config, path)
    if not isinstance(rendered, render.Rendered):
        mapping = UnknownMapping("render-unavailable", "no pinned render available")
        return rendered, None, None, mapping
    width, height, _gray = _decode_grayscale(rendered.data)
    mapping = frame_mapping(geometry, frame_name, config, (width, height))
    return rendered, width, height, mapping


def _frame_record(mapping, frame_name):
    unknown = isinstance(mapping, UnknownMapping)
    return {"name": frame_name, "status": "unknown" if unknown else "resolved",
            "reason": mapping.reason if unknown else None}


def _render_record(rendered, config):
    ok = isinstance(rendered, render.Rendered)
    return {"status": "rendered" if ok else "unavailable",
            "reason": None if ok else rendered.reason, "config": config.to_dict()}


def _classes_record(entries, morphology):
    record = {name: {"role": "carrier-observation", "count": len(entries[name]),
                     "entries": entries[name]}
              for name in OBJECT_CLASSES}
    record["graphic-hypothesis"] = morphology
    return record


def _observed_record(env, config, rendered, classes):
    return {
        "kind": KIND, "version": VERSION, "status": "observed", "reason": None,
        "page": env.page_number,
        "source": {"file": env.file, "sha256": env.sha,
                   "extractor": {"id": "pymupdf"}},
        "frame": _frame_record(env.mapping, env.frame_name),
        "render": _render_record(rendered, config),
        "evidence_class": render.evidence_class(config.extractor_lineage, config.renderer_lineage),
        "classes": classes}

def observe_page(source, geometry, page_number=1, frame_name="page-1"):
    """Observe one PDF page: four typed content classes + full provenance."""
    path = Path(source)
    data, doc, failure = _open_pdf(path)
    if failure is not None:
        return _empty_record(source, (page_number, frame_name),
                             "invalid-source", failure)
    if not _valid_page(page_number, doc):
        return _empty_record(source, (page_number, frame_name),
                             "invalid-page", "page out of range")
    page = doc[page_number - 1]
    config = _default_config(page_number)
    rendered, width, height, mapping = _render_and_mapping(
        path, config, geometry, frame_name)
    env = _PageEnv(file=str(path), page_number=page_number,
                   sha=hashlib.sha256(data).hexdigest(), frame_name=frame_name,
                   mapping=mapping, page=page, width=width, height=height)
    makers = {"text": _text_entries, "vector": _vector_entries, "raster": _raster_entries}
    entries = {name: makers[name](page, env) for name in OBJECT_CLASSES}
    for section in entries.values():
        _apply_mapping(section, mapping)
    morphology = _morphology_section(rendered, config, entries, env)
    return _observed_record(env, config, rendered,
                            _classes_record(entries, morphology))
