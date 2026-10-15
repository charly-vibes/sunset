# Purpose: Deterministic carrier oracles for restore-document-substrate
#   (sunset-7hs Stage B).
# Responsibilities: Over committed screened carriers only, build enriched 0.3
#   descriptors and record named check records: native PDF (declared page +
#   coordinate basis via a pinned geometry profile, native text runs, honest
#   unsupported/approximated feature declarations, no OCR prerequisite), EPUB
#   (spine/navigation preserved, no invented pagination or reading-order
#   edges, footnote-backlink classification that can never emit a precedes),
#   scanned PDF (page image primary, OCR text as a DERIVED observation with
#   engine provenance and replayable transforms, competing reading-order
#   interpretations), hybrid PDF (native and OCR text coexist without
#   overwriting) and a financial statement described by the unchanged core.
#   Each oracle re-runs the deployed report stack (schema / profiles /
#   coverage / interpretation). Determinism of every oracle is checked by the
#   tests through canonical re-runs; OCR results are pinned to the recorded
#   engine/lang/dpi configuration.
# Rationale: restore-document-substrate design §3 (carrier fidelity) and §6
#   verification matrix; document-purpose property generators. Oracles verify
#   the deployed adapters; they claim no extraction or human-review
#   conformance.
"""Carrier oracles: native PDF / EPUB / scanned / hybrid / financial."""
import hashlib
import io
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pymupdf

from dsc03 import adapters, evidence, profiles, report, validator

OCR_LANG = "spa"
OCR_DPI = 200
GEOMETRY_URI = "geometry.json"
GEOMETRY_VERSION = "1"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _check(res, name, ok, detail=""):
    res["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    return res


# -- pinned geometry (coordinate basis) ---------------------------------------------

def geometry_artifact():
    return {
        "version": GEOMETRY_VERSION,
        "kind": "geometry",
        "frames": [
            {"name": "page-pt", "unit": "pt", "origin": "bottom-left"},
            {"name": "page-image-200dpi", "unit": "px", "origin": "top-left",
             "dpi": OCR_DPI},
        ],
    }


def add_page_basis(desc, out_dir, rects):
    """Pin a geometry profile and declare the coordinate basis of page regions.

    rects: {page_number: (x, y, width, height)} in PDF points (rounded to
    integers, the descriptor's geometry value space).
    """
    art = geometry_artifact()
    raw = (json.dumps(art, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (Path(out_dir) / GEOMETRY_URI).write_bytes(raw)
    desc["profiles"].append({
        "id": "p-geo", "kind": "geometry", "uri": GEOMETRY_URI,
        "version": GEOMETRY_VERSION, "sha256": _sha256(raw),
    })
    for r in desc["regions"]:
        if r["kind"] != "page":
            continue
        i = int(r["id"][2:])
        x, y, w, h = rects[i]
        r["geometry"] = {"profile_id": "p-geo", "space": "page-pt",
                         "x": int(x), "y": int(y), "width": int(w), "height": int(h)}
    return desc


def _page_rects(data):
    rects = {}
    with pymupdf.open(stream=data, filetype="application/pdf") as doc:
        for i, page in enumerate(doc, start=1):
            rect = page.rect
            rects[i] = (rect.x0, rect.y0, rect.width, rect.height)
    return rects


def _registry(root):
    return profiles.Registry(root)


def resolve_all(desc, out_dir):
    reg = _registry(out_dir)
    return {p["id"]: profiles.resolve(p, reg) for p in desc["profiles"]}


def run_reports(desc, out_dir, source_data=None):
    """Schema / profile / source-coverage / interpretation reports, with real
    enumeration from the carrier bytes when available."""
    resolved = resolve_all(desc, out_dir)
    enumerator = None
    if source_data is not None:
        def enumerator(fmt, kind):
            return adapters.enumerate_scopes(fmt, source_data, kind)
    return report.assess(desc, resolved, _registry(out_dir), enumerator)


# -- OCR (derived observations only) -------------------------------------------------

def ocr_engine_version():
    out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
    return out.stdout.splitlines()[0].strip()


def _ocr_png(png_bytes, tsv=False):
    """Run pinned tesseract over one rendered page; text or TSV lines.
    The tessdata dir is pinned to the system traineddata (spa + tsv config)."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(png_bytes)
        tmp = tf.name
    tessdata = ["--tessdata-dir", "/usr/share/tesseract/tessdata"]
    try:
        if tsv:
            out = subprocess.run(
                ["tesseract", tmp, "stdout", *tessdata, "-l", OCR_LANG, "tsv"],
                capture_output=True, text=True)
            lines = {}
            for row in out.stdout.splitlines()[1:]:
                cols = row.split("\t")
                if len(cols) < 12 or not cols[11].strip():
                    continue
                key = (cols[2], cols[3], cols[4])  # block, par, line
                box = (int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9]))
                acc = lines.setdefault(key, {"box": box, "words": []})
                acc["words"].append(cols[11])
                b = acc["box"]
                acc["box"] = (min(b[0], box[0]), min(b[1], box[1]),
                              max(b[0] + b[2], box[0] + box[2]) - min(b[0], box[0]),
                              max(b[1] + b[3], box[1] + box[3]) - min(b[1], box[1]))
            return [
                {"bbox": v["box"], "text": " ".join(v["words"])}
                for _, v in sorted(lines.items())
            ]
        out = subprocess.run(
            ["tesseract", tmp, "stdout", *tessdata, "-l", OCR_LANG],
            capture_output=True, text=True)
        return out.stdout.strip()
    finally:
        Path(tmp).unlink(missing_ok=True)


def _render_png(data, page_no):
    with pymupdf.open(stream=data, filetype="application/pdf") as doc:
        return doc[page_no - 1].get_pixmap(dpi=OCR_DPI).tobytes("png")


def _ocr_transform(desc_id, extra=None):
    cfg = {"engine": "tesseract", "engine_version": ocr_engine_version(),
           "lang": OCR_LANG, "dpi": OCR_DPI, "descriptor": desc_id}
    if extra:
        cfg.update(extra)
    if "page" not in cfg:  # every OCR record is page-scoped: replayable
        raise ValueError("ocr transform needs a page discriminator")
    cfg_sha = _sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode())
    deps = [
        f"engine:tesseract@{cfg['engine_version']}",
        f"lang:{OCR_LANG}", f"dpi:{OCR_DPI}",
    ]
    return cfg_sha, deps + [f"config:{cfg_sha}"]


# -- native PDF oracle ---------------------------------------------------------------

def native_pdf_oracle(carrier_path, out_dir):
    """Structural oracle over a native-text PDF; OCR never runs."""
    carrier_path = Path(carrier_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = carrier_path.read_bytes()
    desc = adapters.describe_pdf(carrier_path, out_dir)
    add_page_basis(desc, out_dir, _page_rects(data))

    native_pages = {}
    with pymupdf.open(stream=data, filetype="application/pdf") as doc:
        for i, page in enumerate(doc, start=1):
            native_pages[i] = bool(page.get_text().strip())

    res = {"descriptor": desc, "checks": [], "source_sha256": _sha256(data)}
    reasons = validator.validate(desc)
    _check(res, "schema_valid", not reasons, str(reasons))

    transforms = [e for e in desc["evidence"] if "transform" in e]
    _check(res, "no_ocr_prerequisite", not transforms,
           f"{len(transforms)} transform records")

    resolved = resolve_all(desc, out_dir)
    pages = [r for r in desc["regions"] if r["kind"] == "page"]
    ok_basis = bool(pages) and all(
        r.get("geometry", {}).get("profile_id") == "p-geo"
        and r["geometry"].get("space") == "page-pt"
        and resolved.get("p-geo", ("unavailable", None))[0] == "resolved"
        for r in pages)
    _check(res, "page_and_coordinate_basis_declared", ok_basis,
           f"{len(pages)} pages")

    sha = _sha256(data)
    page_content_ids = set()
    for rel in desc["relations"]:
        if rel["kind"] == "has-content" and rel["from"].startswith("pg"):
            page_content_ids.add(rel["to"])
    by_id = {c["id"]: c for c in desc["contents"]}
    text_ok = True
    for i, has_native in native_pages.items():
        texts = [by_id[c] for c in page_content_ids
                 if by_id[c]["kind"] == "text" and c.startswith("txt")
                 and c == f"txt{i}"]
        if has_native != bool(texts):
            text_ok = False
    src_refs = {e["source_ref"] for e in desc["evidence"] if e["origin"] == "source"}
    _check(res, "text_runs_from_native_text_layer", text_ok,
           f"source refs include page anchors: {f'sha256:{sha}#page:1' in src_refs}")

    unpreserved = [c for c in desc["coverage"] if c["status"] != "preserved"]
    _check(res, "unsupported_features_declared",
           all(c["reason"] for c in unpreserved),
           "; ".join(f"{c['feature']}@{c['scope']}={c['status']}" for c in unpreserved))

    res["reports"] = run_reports(desc, out_dir, data)
    return res


# -- EPUB oracle ---------------------------------------------------------------------

def classify_epub_links(data):
    """Classify hyperlinks found in the EPUB XHTML members.

    nav = navigation-document links; backlink = intra-document reference
    starting with '#'; content-link = any other XHTML hyperlink.
    """
    links = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if not name.endswith(".xhtml"):
                continue
            root = ET.fromstring(z.read(name))
            for a in root.iter("{http://www.w3.org/1999/xhtml}a"):
                href = a.get("href")
                if not href:
                    continue
                if href.startswith("#"):
                    cls = "backlink"
                else:
                    cls = "nav" if name.endswith("nav.xhtml") else "content-link"
                links.append({"source": name, "href": href, "class": cls})
    return links


def epub_link_edges(links):
    """Map classified hyperlinks to typed link records. A footnote backlink is
    a link observation only: this mapping NEVER emits a reading-order edge,
    regardless of link class."""
    edges = []
    for l in links:
        edges.append({
            "kind": "link",          # never "precedes"
            "class": l["class"],
            "from": l["source"],
            "to": l["href"],
        })
    return edges


def epub_oracle(carrier_path, out_dir):
    """Spine/navigation/footnote oracle; no OCR, no invented pagination."""
    carrier_path = Path(carrier_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = carrier_path.read_bytes()
    desc = adapters.describe_epub(carrier_path, out_dir)

    res = {"descriptor": desc, "checks": [], "source_sha256": _sha256(data)}
    reasons = validator.validate(desc)
    _check(res, "schema_valid", not reasons, str(reasons))

    items, spine, nav_href = adapters._parse_opf(data)
    spine_content = next((c for c in desc["contents"] if c["id"] == "c-spine"), None)
    _check(res, "spine_preserved",
           spine_content is not None
           and json.loads(spine_content["value"])["idrefs"] == spine,
           str(spine))

    nav_content = next((c for c in desc["contents"] if c["id"] == "c-nav"), None)
    nav_cov = [c for c in desc["coverage"] if c["feature"] == "epub:navigation"]
    _check(res, "navigation_preserved",
           nav_href is not None and nav_content is not None
           and json.loads(nav_content["value"]) == {"path": nav_href}
           and nav_cov and nav_cov[0]["status"] == "preserved",
           f"nav={nav_href}")

    no_geom = not any("geometry" in r for r in desc["regions"])
    no_pages = not any(c["scope"].startswith("page:") for c in desc["coverage"])
    _check(res, "no_invented_pagination_or_geometry", no_geom and no_pages,
           f"geometry={no_geom} page-scopes={no_pages}")

    precedes = [r for r in desc["relations"] if r["kind"] == "precedes"]
    _check(res, "no_reading_order_edges_invented", not precedes and
           not desc["interpretations"], f"{len(precedes)} precedes edges")

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members = {n for n in z.namelist() if not n.endswith("/")}
    res_cov = {c["scope"] for c in desc["coverage"] if c["feature"] == "epub:resources"}
    _check(res, "resources_fully_covered",
           res_cov == {f"resource:{n}" for n in members}
           and all(c["status"] == "preserved"
                   for c in desc["coverage"] if c["feature"] == "epub:resources"),
           f"{len(res_cov)}/{len(members)} members")

    res["links"] = classify_epub_links(data)
    res["reports"] = run_reports(desc, out_dir, data)
    return res


# -- scanned PDF oracle ---------------------------------------------------------------

def _attach_ocr(desc, data, page_no, png_bytes, ocr_text, line_infos=None):
    """Attach a page image observation plus DERIVED OCR text with pinned
    engine provenance; optionally per-line regions for the poem page."""
    sha = _sha256(data)
    img_id, ocr_id = f"pgimg{page_no}", f"ocr{page_no}"
    desc["contents"].append({"id": img_id, "kind": "image", "value": _sha256(png_bytes)})
    desc["contents"].append({"id": ocr_id, "kind": "text", "value": ocr_text})
    desc["relations"].append({"id": f"rel-hc-img{page_no}", "kind": "has-content",
                              "from": f"pg{page_no}", "to": img_id})
    desc["relations"].append({"id": f"rel-hc-ocr{page_no}", "kind": "has-content",
                              "from": f"pg{page_no}", "to": ocr_id})
    desc["evidence"].append({
        "id": f"ev-img{page_no}", "origin": "source",
        "source_ref": f"sha256:{sha}#page:{page_no}:image@{OCR_DPI}dpi",
        "content_ids": [img_id], "selector_ids": [],
    })
    cfg_sha, deps = _ocr_transform(desc["id"], {"mode": "page-ocr", "page": page_no})
    desc["evidence"].append({
        "id": f"ev-ocr{page_no}", "origin": "extracted",
        "source_ref": f"ocr:{cfg_sha[:12]}#page:{page_no}",
        "content_ids": [ocr_id], "selector_ids": [],
        "transform": {"id": "tesseract-ocr", "version": "1", "config_sha256": cfg_sha,
                      "dependencies": deps, "inputs": [img_id], "outputs": [ocr_id]},
    })
    desc["relations"].append({"id": f"rel-df-ocr{page_no}", "kind": "derived-from",
                              "from": f"ev-ocr{page_no}", "to": f"ev-img{page_no}"})
    fns = {cfg_sha: (lambda png: lambda _vals: _ocr_png(png))(png_bytes)}

    if line_infos:
        interp_ocr = {
            "id": f"i-ro-ocr-{page_no}", "kind": "reading-order",
            "view_id": "v-main", "origin": "extracted", "status": "supported",
            "evidence": [f"ev-ocr{page_no}"],
        }
        interp_alt = {
            "id": f"i-ro-alt-{page_no}", "kind": "reading-order",
            "view_id": "v-main", "origin": "manual",
            "status": "asserted_without_evidence", "evidence": [],
        }
        desc["interpretations"] += [interp_ocr, interp_alt]
        prev = None
        for k, info in enumerate(line_infos, start=1):
            rid = f"ln{page_no}-{k}"
            txt_id = f"lntxt{page_no}-{k}"
            x, y, w, h = info["bbox"]
            desc["regions"].append({
                "id": rid, "view_id": "v-main", "kind": "line",
                "geometry": {"profile_id": "p-geo", "space": "page-image-200dpi",
                             "x": x, "y": y, "width": w, "height": h},
            })
            desc["relations"].append({"id": f"rel-cln{k}", "kind": "contains",
                                      "from": f"pg{page_no}", "to": rid})
            desc["contents"].append({"id": txt_id, "kind": "text", "value": info["text"]})
            desc["relations"].append({"id": f"rel-hc-ln{k}", "kind": "has-content",
                                      "from": rid, "to": txt_id})
            lcfg_sha, ldeps = _ocr_transform(
                desc["id"], {"mode": "line-boxes", "page": page_no, "line": k})
            desc["evidence"].append({
                "id": f"ev-ln{k}", "origin": "extracted",
                "source_ref": f"ocr:{lcfg_sha[:12]}#page:{page_no}:line:{k}",
                "content_ids": [txt_id], "selector_ids": [],
                "transform": {"id": "tesseract-line-boxes", "version": "1",
                              "config_sha256": lcfg_sha, "dependencies": ldeps,
                              "inputs": [img_id], "outputs": [txt_id]},
            })
            desc["relations"].append({"id": f"rel-df-ln{k}", "kind": "derived-from",
                                      "from": f"ev-ln{k}", "to": f"ev-img{page_no}"})
            fns[lcfg_sha] = (lambda lng: lambda _vals: lng["text"])(
                {"text": info["text"], **info})
            if prev is not None:
                desc["relations"].append({
                    "id": f"rel-pre-ocr{k}", "kind": "precedes",
                    "from": prev, "to": rid, "interpretation_id": interp_ocr["id"]})
                desc["relations"].append({
                    "id": f"rel-pre-alt{k}", "kind": "precedes",
                    "from": rid, "to": prev, "interpretation_id": interp_alt["id"]})
            prev = rid
    return fns


def scanned_oracle(carrier_path, out_dir):
    """Scanned-carrier oracle: page image primary, OCR strictly derived."""
    carrier_path = Path(carrier_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = carrier_path.read_bytes()
    desc = adapters.describe_pdf(carrier_path, out_dir)
    rects = {}
    with pymupdf.open(stream=data, filetype="application/pdf") as doc:
        for i, page in enumerate(doc, start=1):
            rect = page.rect
            rects[i] = (rect.x0, rect.y0, rect.width, rect.height)
    add_page_basis(desc, out_dir, rects)

    transform_fns = {}
    replay = {}
    page_count = len(rects)
    for i in range(1, page_count + 1):
        png = _render_png(data, i)
        text = _ocr_png(png)
        line_infos = _ocr_png(png, tsv=True) if i == 1 else None
        transform_fns.update(
            _attach_ocr(desc, data, i, png, text, line_infos=line_infos))

    res = {"descriptor": desc, "checks": [], "source_sha256": _sha256(data)}
    reasons = validator.validate(desc)
    _check(res, "schema_valid", not reasons, str(reasons))

    img_evs = {e["content_ids"][0]: e for e in desc["evidence"]
               if e["origin"] == "source" and e["content_ids"]
               and any(c["id"] == e["content_ids"][0] and c["kind"] == "image"
                       for c in desc["contents"])}
    _check(res, "page_image_primary", len(img_evs) == page_count,
           f"{len(img_evs)}/{page_count} pages with image observations")

    resolved = resolve_all(desc, out_dir)
    ocr_evs = [e for e in desc["evidence"] if "transform" in e]
    ok_prov = True
    for e in ocr_evs:
        deps = e["transform"]["dependencies"]
        if not (any(d.startswith("engine:tesseract@") for d in deps)
                and any(d.startswith("lang:") for d in deps)
                and any(d.startswith("dpi:") for d in deps)):
            ok_prov = False
    _check(res, "ocr_is_derived_with_engine_provenance", ok_prov,
           f"{len(ocr_evs)} transform records")

    for e in desc["evidence"]:
        if "transform" in e and e["id"].startswith("ev-ocr"):
            status, _ = evidence.replay(e, desc, resolved, transform_fns)
            replay[e["id"]] = status
    res["ocr_replay"] = replay

    interps = {i["id"]: i["status"] for i in desc["interpretations"]}
    ok_ro = (
        len(interps) >= 2
        and "supported" in interps.values()
        and "asserted_without_evidence" in interps.values()
        and all(r["interpretation_id"] in interps
                for r in desc["relations"] if r["kind"] == "precedes")
    )
    _check(res, "alternate_reading_orders_coexist", ok_ro, str(interps))

    res["reports"] = run_reports(desc, out_dir, data)
    return res


# -- hybrid PDF oracle ----------------------------------------------------------------

def hybrid_oracle(carrier_path, out_dir):
    """Hybrid carrier: native text and OCR observations of the same page
    region coexist; neither overwrites the other."""
    carrier_path = Path(carrier_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = carrier_path.read_bytes()
    desc = adapters.describe_pdf(carrier_path, out_dir)
    add_page_basis(desc, out_dir, _page_rects(data))

    png = _render_png(data, 6)
    ocr6 = _ocr_png(png)
    transform_fns = _attach_ocr(desc, data, 6, png, ocr6)

    res = {"descriptor": desc, "checks": [], "source_sha256": _sha256(data)}
    reasons = validator.validate(desc)
    _check(res, "schema_valid", not reasons, str(reasons))

    texts_on_p6 = []
    origins = {}
    by_id = {c["id"]: c for c in desc["contents"]}
    for rel in desc["relations"]:
        if rel["kind"] == "has-content" and rel["from"] == "pg6":
            c = by_id.get(rel["to"])
            if c is not None and c["kind"] == "text":
                texts_on_p6.append(c["id"])
    for cid in texts_on_p6:
        producer = next(e for e in desc["evidence"] if cid in e["content_ids"])
        origins["native" if cid.startswith("txt") else "ocr"] = producer["origin"]
    _check(res, "hybrid_observations_coexist", len(texts_on_p6) == 2
           and origins.get("native") == "source" and origins.get("ocr") == "extracted",
           {"page6_contents": sorted(texts_on_p6), "origins": origins})

    replay = {}
    for e in desc["evidence"]:
        if "transform" in e and e["id"].startswith("ev-ocr"):
            status, _ = evidence.replay(e, desc, resolve_all(desc, out_dir), transform_fns)
            replay[e["id"]] = status
    res["ocr_replay"] = replay
    res["reports"] = run_reports(desc, out_dir, data)
    return res


# -- financial oracle ------------------------------------------------------------------

def financial_oracle(carrier_path, out_dir):
    """Structured financial statement described by the unchanged core: logical
    grouping regions + namespaced role annotations, no financial primitive."""
    carrier_path = Path(carrier_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = carrier_path.read_bytes()
    desc = adapters.describe_pdf(carrier_path, out_dir)
    add_page_basis(desc, out_dir, _page_rects(data))

    desc["vocabularies"].append({"namespace": "fin", "version": "1"})
    page_ids = [r["id"] for r in desc["regions"] if r["kind"] == "page"]
    groups = ["header", "line-items", "totals"]
    for i, pg in enumerate(page_ids, start=1):
        for g in groups:
            rid = f"lg-{g}-{i}"
            desc["regions"].append({"id": rid, "view_id": "v-log", "kind": g})
            desc["relations"].append({"id": f"rel-c-{rid}", "kind": "contains",
                                      "from": "r-log", "to": rid})
            desc["relations"].append({"id": f"rel-rz-{rid}", "kind": "realizes",
                                      "from": pg, "to": rid})
            desc["annotations"].append({
                "id": f"an-{rid}", "target": rid, "term": f"fin:{g}",
                "value": f"inferred grouping role {g}",
                "origin": "inferred", "status": "asserted_without_evidence",
                "evidence": [], "view_id": "v-log",
            })
        txt = next((rel["to"] for rel in desc["relations"]
                    if rel["kind"] == "has-content" and rel["from"] == pg), None)
        if txt:
            desc["relations"].append({"id": f"rel-hc-fin{i}", "kind": "has-content",
                                      "from": f"lg-line-items-{i}", "to": txt})

    res = {"descriptor": desc, "checks": [], "source_sha256": _sha256(data)}
    reasons = validator.validate(desc)
    _check(res, "schema_valid", not reasons, str(reasons))

    from dsc03.substrate import laws
    kinds = {r["kind"] for r in desc["relations"]}
    _check(res, "no_financial_primitive_in_core", kinds <= laws.CORE_RELATIONS,
           str(sorted(kinds)))

    children = {}
    for rel in desc["relations"]:
        if rel["kind"] == "contains" and rel["from"] == "r-log":
            children[rel["to"]] = True
    kinds_found = sorted({r["kind"] for r in desc["regions"] if r["id"] in children})
    _check(res, "structure_recoverable_via_core",
           {"header", "line-items", "totals"} <= set(kinds_found),
           {"logical_groups": kinds_found})

    terms = {a["term"] for a in desc["annotations"]}
    vocabs = {v["namespace"] for v in desc["vocabularies"]}
    ok_ns = bool(terms) and all(t.split(":", 1)[0] in vocabs for t in terms)
    core_terms = {"ex"} & {t.split(":", 1)[0] for t in terms}
    _check(res, "domain_labels_namespaced_not_core", ok_ns,
           f"terms={sorted(terms)} core-terms={sorted(core_terms)}")

    res["reports"] = run_reports(desc, out_dir, data)
    return res
