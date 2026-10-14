# Purpose: Real-carrier PDF/EPUB adapters for DSC 0.3 (sunset-r68.11, task 3.1).
# Responsibilities: Read a committed carrier from fixtures/carriers/ and produce
#   a 0.3 descriptor that preserves the source observations actually present in
#   the carrier bytes: per-page regions and text contents, source annotations
#   bound to evidence, and scoped coverage over the full independent inventory
#   (glyphs/images/vectors/annotations/attachments for PDF; manifest/spine/
#   navigation/resources for EPUB). Also provide enumeration helpers that
#   compute scope lists from the actual source bytes (page counts from the PDF
#   structure, archive members from the ZIP central directory), as required by
#   document-adapters "Scoped coverage dispositions".
# Rationale: add-dsc-03 document-adapters delta; synthetic descriptors do not
#   count per tasks.md 3.1 — this module only ever reads real carrier bytes.
"""Real-carrier adapters: PDF/EPUB bytes -> 0.3 descriptors preserving source observations."""
import hashlib
import io
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf

ADAPTER_ID = "sunset-carrier"
ADAPTER_VERSION = "0.1"
INVENTORY_VERSION = "1"

PDF_FEATURES = [
    ("pdf:glyphs", "pdf-page"),
    ("pdf:images", "pdf-page"),
    ("pdf:vectors", "pdf-page"),
    ("pdf:annotations", "pdf-page"),
    ("pdf:attachments", "document"),
]
EPUB_FEATURES = [
    ("epub:manifest", "document"),
    ("epub:spine", "document"),
    ("epub:navigation", "document"),
    ("epub:resources", "epub-resource"),
]

CONTAINER_NS = "{urn:oasis:names:tc:opendocument:xmlns:container}"
OPF_NS = "{http://www.idpf.org/2007/opf}"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _config_sha256():
    canonical = json.dumps(
        {"adapter_id": ADAPTER_ID, "adapter_version": ADAPTER_VERSION, "options": {}},
        sort_keys=True,
    )
    return _sha256(canonical.encode("utf-8"))


# -- enumeration from actual source bytes -----------------------------------------
def pdf_scopes(data, scope_kind):
    """Enumerate scopes for a PDF's real bytes; None if enumeration cannot complete."""
    if scope_kind == "document":
        return ["document"]
    if scope_kind != "pdf-page":
        return None
    try:
        with pymupdf.open(stream=data, filetype="application/pdf") as doc:
            return [f"page:{i}" for i in range(1, doc.page_count + 1)]
    except Exception:
        return None


def epub_scopes(data, scope_kind):
    """Enumerate scopes for an EPUB's real bytes; None if enumeration cannot complete."""
    if scope_kind == "document":
        return ["document"]
    if scope_kind != "epub-resource":
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
        if len(set(names)) != len(names):
            return None  # duplicate member paths prevent complete enumeration
        return [f"resource:{n}" for n in names]
    except zipfile.BadZipFile:
        return None


def enumerate_scopes(source_format, data, scope_kind):
    if source_format == "application/pdf":
        return pdf_scopes(data, scope_kind)
    if source_format == "application/epub+zip":
        return epub_scopes(data, scope_kind)
    return None


def _write_artifacts(out_dir, inventory, manifest):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inv_bytes = (json.dumps(inventory, indent=1, sort_keys=True) + "\n").encode("utf-8")
    man_bytes = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8")
    (out_dir / "inventory.json").write_bytes(inv_bytes)
    (out_dir / "manifest.json").write_bytes(man_bytes)
    return inv_bytes, man_bytes


def _base_descriptor(desc_id, source_format, data, locator, view_kind):
    return {
        "version": "0.3",
        "id": desc_id,
        "source": {"format": source_format, "sha256": _sha256(data), "locator": locator},
        "views": [
            {"id": "v-main", "kind": view_kind, "root": "r-root"},
            {"id": "v-log", "kind": "logical", "root": "r-log"},
        ],
        "regions": [
            {"id": "r-root", "view_id": "v-main", "kind": "document"},
            {"id": "r-log", "view_id": "v-log", "kind": "article"},
        ],
        "contents": [],
        "relations": [],
        "annotations": [],
        "evidence": [],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [],
    }


def _coverage_entry(feature, scope, status, reason, inv_id, man_id):
    return {
        "inventory_id": inv_id,
        "manifest_id": man_id,
        "feature": feature,
        "scope": scope,
        "status": status,
        "reason": reason,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "config_sha256": _config_sha256(),
    }


# -- PDF --------------------------------------------------------------------------
def describe_pdf(source_path, out_dir):
    """Adapter for a real PDF carrier; returns a 0.3 descriptor dict.

    Writes inventory.json/manifest.json artifacts under out_dir and pins them
    in the descriptor's profile declarations (kind, version, sha256).
    """
    data = Path(source_path).read_bytes()
    sha = _sha256(data)
    desc = _base_descriptor(
        f"adapter-{Path(source_path).stem}", "application/pdf", data,
        str(source_path), "physical",
    )

    with pymupdf.open(stream=data, filetype="application/pdf") as doc:
        attachments = doc.embfile_count()
        page_regions = []
        for i, page in enumerate(doc, start=1):
            rid = f"pg{i}"
            page_regions.append(rid)
            desc["regions"].append({"id": rid, "view_id": "v-main", "kind": "page"})
            desc["relations"].append(
                {"id": f"rel-rc{i}", "kind": "contains", "from": "r-root", "to": rid}
            )
            text = page.get_text().strip()
            cid = None
            if text:
                cid = f"txt{i}"
                desc["contents"].append({"id": cid, "kind": "text", "value": text})
                desc["relations"].append(
                    {"id": f"rel-hc{i}", "kind": "has-content", "from": rid, "to": cid}
                )
                desc["evidence"].append({
                    "id": f"ev-txt{i}",
                    "origin": "source",
                    "source_ref": f"sha256:{sha}#page:{i}",
                    "content_ids": [cid],
                    "selector_ids": [],
                })
            # source annotations are observations: preserve them as descriptor
            # annotations bound to page-text evidence where text exists
            for k, annot in enumerate(page.annots(), start=1):
                kind = annot.type[1].lower().replace(" ", "-")
                aid = f"an{i}-{k}"
                info = annot.info or {}
                value = info.get("content") or info.get("title") or f"{kind} on page {i}"
                has_support = cid is not None
                desc["annotations"].append({
                    "id": aid,
                    "target": cid if has_support else rid,
                    "term": f"ex:{kind}",
                    "value": value,
                    "origin": "source",
                    "status": "supported" if has_support else "asserted_without_evidence",
                    "evidence": [f"ev-txt{i}"] if has_support else [],
                    "view_id": "v-main",
                })

        coverage_entries = []
        for i, page in enumerate(doc, start=1):
            scope = f"page:{i}"
            text = page.get_text().strip()
            coverage_entries.append(_coverage_entry(
                "pdf:glyphs", scope, "preserved", "", "p-inv", "p-man"))
            images = page.get_images(full=True)
            coverage_entries.append(_coverage_entry(
                "pdf:images", scope,
                "approximated" if images else "preserved",
                "image presence observed; pixels not extracted" if images else "",
                "p-inv", "p-man"))
            vectors = page.get_drawings()
            coverage_entries.append(_coverage_entry(
                "pdf:vectors", scope,
                "approximated" if vectors else "preserved",
                "vector presence observed; geometry not extracted" if vectors else "",
                "p-inv", "p-man"))
            annotations = list(page.annots())
            coverage_entries.append(_coverage_entry(
                "pdf:annotations", scope, "preserved", "", "p-inv", "p-man"))

    coverage_entries.append(_coverage_entry(
        "pdf:attachments", "document",
        "unsupported" if attachments else "preserved",
        "embedded-file extraction not implemented" if attachments else "",
        "p-inv", "p-man"))

    inventory = {
        "version": INVENTORY_VERSION,
        "source_format": "application/pdf",
        "features": [{"name": n, "scope_kind": k} for n, k in PDF_FEATURES],
    }
    # manifest lists the features this run supports; attachment absence is
    # verified (embfile_count), so a carrier without attachments claims
    # preserved and must then name pdf:attachments in the manifest
    supported = ["pdf:glyphs", "pdf:images", "pdf:vectors", "pdf:annotations"]
    if attachments == 0:
        supported.append("pdf:attachments")
    manifest = {
        "version": INVENTORY_VERSION,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_format": "application/pdf",
        "features": supported,
    }
    inv_bytes, man_bytes = _write_artifacts(out_dir, inventory, manifest)
    desc["coverage"] = coverage_entries
    desc["profiles"] = [
        {"id": "p-inv", "kind": "carrier-inventory", "uri": "inventory.json",
         "version": INVENTORY_VERSION, "sha256": _sha256(inv_bytes)},
        {"id": "p-man", "kind": "adapter-manifest", "uri": "manifest.json",
         "version": INVENTORY_VERSION, "sha256": _sha256(man_bytes)},
    ]
    return desc


# -- EPUB -------------------------------------------------------------------------
def _parse_opf(data):
    """Parse container.xml -> OPF; returns (manifest_items, spine_idrefs, nav_href)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        opf_path = container.find(f"{CONTAINER_NS}rootfiles/{CONTAINER_NS}rootfile").get("full-path")
        opf = ET.fromstring(z.read(opf_path))
    items = []
    nav_href = None
    for item in opf.find(f"{OPF_NS}manifest"):
        href = item.get("href")
        props = (item.get("properties") or "").split()
        if "nav" in props:
            nav_href = href
        items.append({
            "id": item.get("id"),
            "href": href,
            "media_type": item.get("media-type"),
            "properties": props,
        })
    spine = [ref.get("idref") for ref in opf.find(f"{OPF_NS}spine")]
    return items, spine, nav_href


def describe_epub(source_path, out_dir):
    """Adapter for a real EPUB carrier; returns a 0.3 descriptor dict."""
    data = Path(source_path).read_bytes()
    sha = _sha256(data)
    desc = _base_descriptor(
        f"adapter-{Path(source_path).stem}", "application/epub+zip", data,
        str(source_path), "carrier",
    )
    items, spine, nav_href = _parse_opf(data)

    observations = [
        ("c-manifest", {"items": items}, "sha256:%s#package-manifest" % sha),
        ("c-spine", {"idrefs": spine}, "sha256:%s#package-spine" % sha),
    ]
    if nav_href is not None:
        observations.append(("c-nav", {"path": nav_href}, "sha256:%s#nav" % sha))
    # content values are strings: structured observations are serialized as
    # canonical JSON (document-core FIELD_SPECS types value as a string field)
    for cid, value, ref in observations:
        desc["contents"].append({
            "id": cid, "kind": "structured",
            "value": json.dumps(value, sort_keys=True, separators=(",", ":")),
        })
        desc["relations"].append(
            {"id": f"rel-hc-{cid}", "kind": "has-content", "from": "r-root", "to": cid}
        )
        desc["evidence"].append({
            "id": f"ev-{cid}",
            "origin": "source",
            "source_ref": ref,
            "content_ids": [cid],
            "selector_ids": [],
        })

    inventory = {
        "version": INVENTORY_VERSION,
        "source_format": "application/epub+zip",
        "features": [{"name": n, "scope_kind": k} for n, k in EPUB_FEATURES],
    }
    manifest = {
        "version": INVENTORY_VERSION,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_format": "application/epub+zip",
        "features": [n for n, _ in EPUB_FEATURES],
    }
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        members = [n for n in z.namelist() if not n.endswith("/")]

    coverage_entries = [
        _coverage_entry("epub:manifest", "document", "preserved", "", "p-inv", "p-man"),
        _coverage_entry("epub:spine", "document", "preserved", "", "p-inv", "p-man"),
        _coverage_entry(
            "epub:navigation", "document",
            "preserved" if nav_href is not None else "unexamined",
            "" if nav_href is not None else "no nav item found in package manifest",
            "p-inv", "p-man"),
    ]
    # every non-directory archive member is enumerated and covered
    for name in members:
        coverage_entries.append(_coverage_entry(
            "epub:resources", f"resource:{name}", "preserved", "", "p-inv", "p-man"))

    inv_bytes, man_bytes = _write_artifacts(out_dir, inventory, manifest)
    desc["coverage"] = coverage_entries
    desc["profiles"] = [
        {"id": "p-inv", "kind": "carrier-inventory", "uri": "inventory.json",
         "version": INVENTORY_VERSION, "sha256": _sha256(inv_bytes)},
        {"id": "p-man", "kind": "adapter-manifest", "uri": "manifest.json",
         "version": INVENTORY_VERSION, "sha256": _sha256(man_bytes)},
    ]
    return desc
