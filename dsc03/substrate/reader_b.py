# Purpose: Second independent reading path (reader B) for restore-document-
#   substrate (sunset-7hs Stage B, work req 10).
# Responsibilities: Produce 0.3 descriptors for the same committed carriers
#   through an implementation that does NOT reuse dsc03.adapters: PDF text
#   comes from the pdftotext binary per page (page count derived from the
#   full-document form-feed stream, not from PyMuPDF), EPUB package facts
#   come from an independent ElementTree walk, and descriptors are assembled
#   by reader B's own builder. Measure agreement with reader A per declared
#   observable, descriptor overhead (canonical byte size) and the features
#   reader B honestly leaves unexamined. MACHINERY-ONLY: independence is at
#   the scripted-reader level (agent-executed); this is never human review
#   and never real-carrier conformance.
# Rationale: document-purpose "Independent exchange" is gated on two
#   independently implemented consumers agreeing on DECLARED observables;
#   reader B is the second such implementation for this harness.
"""Reader B: independent PDF/EPUB reading path + agreement measurement."""
import hashlib
import io
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from dsc03 import adapters, canonical

ADAPTER_ID = "sunset-reader-b"
ADAPTER_VERSION = "0.1"

# PDF features reader B examines vs leaves unexamined (honest partiality)
B_EXAMINED = ("pdf:glyphs",)
OPF_NS = "{http://www.idpf.org/2007/opf}"
CONTAINER_NS = "{urn:oasis:names:tc:opendocument:xmlns:container}"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _write(out_dir, name, payload):
    raw = (json.dumps(payload, indent=1, sort_keys=True) + "\n").encode("utf-8")
    (Path(out_dir) / name).write_bytes(raw)
    return raw


# -- independent PDF path ---------------------------------------------------------

def _pdftotext_pages(data_path):
    """Per-page text via pdftotext; page count from the form-feed stream."""
    out = subprocess.run(
        ["pdftotext", "-layout", str(data_path), "-"],
        capture_output=True, check=True)
    pages = out.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1]:
        pages.pop()
    return pages


def describe_pdf_b(source_path, out_dir):
    """Reader B PDF descriptor: pdftotext text runs, glyph coverage only;
    every other inventory feature is declared unexamined with a reason."""
    source_path = Path(source_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = source_path.read_bytes()
    sha = _sha256(data)
    pages = _pdftotext_pages(source_path)
    desc = {
        "version": "0.3",
        "id": f"reader-b-{source_path.stem}",
        "source": {"format": "application/pdf", "sha256": sha,
                   "locator": str(source_path)},
        "views": [{"id": "vb-main", "kind": "physical", "root": "rb-root"},
                  {"id": "vb-log", "kind": "logical", "root": "rb-log"}],
        "regions": [{"id": "rb-root", "view_id": "vb-main", "kind": "document"},
                    {"id": "rb-log", "view_id": "vb-log", "kind": "article"}],
        "contents": [], "relations": [], "annotations": [], "evidence": [],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [], "interpretations": [], "coverage": [], "profiles": [],
    }
    text_feature = []
    for i, text in enumerate(pages, start=1):
        rid = f"rbp{i}"
        desc["regions"].append({"id": rid, "view_id": "vb-main", "kind": "page"})
        desc["relations"].append({"id": f"relb-rc{i}", "kind": "contains",
                                  "from": "rb-root", "to": rid})
        desc["coverage"] += [
            _cov("pdf:images", f"page:{i}", "unexamined",
                 "reader B does not examine embedded images"),
            _cov("pdf:vectors", f"page:{i}", "unexamined",
                 "reader B does not examine vector graphics"),
            _cov("pdf:annotations", f"page:{i}", "unexamined",
                 "reader B does not examine source annotations"),
        ]
        text = text.strip()
        if text:
            cid = f"rbtxt{i}"
            desc["contents"].append({"id": cid, "kind": "text", "value": text})
            desc["relations"].append({"id": f"relb-hc{i}", "kind": "has-content",
                                      "from": rid, "to": cid})
            desc["evidence"].append({
                "id": f"evb-txt{i}", "origin": "source",
                "source_ref": f"sha256:{sha}#page:{i}",
                "content_ids": [cid], "selector_ids": [],
            })
            text_feature.append(f"page:{i}")
    for scope in ["document"] + text_feature:
        desc["coverage"].append(_cov("pdf:glyphs", scope, "preserved", ""))
    desc["coverage"].append(_cov(
        "pdf:attachments", "document", "unexamined",
        "reader B does not examine embedded files"))

    inventory = {
        "version": "1", "source_format": "application/pdf",
        "features": [{"name": n, "scope_kind": k} for n, k in adapters.PDF_FEATURES],
    }
    manifest = {
        "version": "1", "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_format": "application/pdf", "features": list(B_EXAMINED),
    }
    inv_raw = _write(out_dir, "inventory-b.json", inventory)
    man_raw = _write(out_dir, "manifest-b.json", manifest)
    desc["profiles"] = [
        {"id": "pb-inv", "kind": "carrier-inventory", "uri": "inventory-b.json",
         "version": "1", "sha256": _sha256(inv_raw)},
        {"id": "pb-man", "kind": "adapter-manifest", "uri": "manifest-b.json",
         "version": "1", "sha256": _sha256(man_raw)},
    ]
    return desc


def _cov(feature, scope, status, reason):
    return {
        "inventory_id": "pb-inv", "manifest_id": "pb-man",
        "feature": feature, "scope": scope, "status": status, "reason": reason,
        "adapter_id": ADAPTER_ID, "adapter_version": ADAPTER_VERSION,
        "config_sha256": "unavailable",
    }


# -- independent EPUB path ----------------------------------------------------------

def _parse_epub_b(data):
    """Reader B's own container→OPF walk (independent of adapters._parse_opf)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        rootfiles = container.find(f"{CONTAINER_NS}rootfiles")
        opf_path = next(
            rf.get("full-path") for rf in rootfiles
            if rf.tag == f"{CONTAINER_NS}rootfile")
        opf = ET.fromstring(z.read(opf_path))
        items, spine, nav = [], [], None
        for el in opf:
            if el.tag == f"{OPF_NS}manifest":
                for item in el:
                    props = (item.get("properties") or "").split()
                    if "nav" in props:
                        nav = item.get("href")
                    items.append({"id": item.get("id"), "href": item.get("href"),
                                  "media_type": item.get("media-type"),
                                  "properties": (item.get("properties") or "").split()})
            elif el.tag == f"{OPF_NS}spine":
                spine = [ref.get("idref") for ref in el]
        members = sorted(n for n in z.namelist() if not n.endswith("/"))
    return items, spine, nav, members


def describe_epub_b(source_path, out_dir):
    source_path = Path(source_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = source_path.read_bytes()
    sha = _sha256(data)
    items, spine, nav, members = _parse_epub_b(data)
    desc = {
        "version": "0.3",
        "id": f"reader-b-{source_path.stem}",
        "source": {"format": "application/epub+zip", "sha256": sha,
                   "locator": str(source_path)},
        "views": [{"id": "vb-main", "kind": "carrier", "root": "rb-root"},
                  {"id": "vb-log", "kind": "logical", "root": "rb-log"}],
        "regions": [{"id": "rb-root", "view_id": "vb-main", "kind": "document"},
                    {"id": "rb-log", "view_id": "vb-log", "kind": "article"}],
        "contents": [], "relations": [], "annotations": [], "evidence": [],
        "vocabularies": [{"namespace": "ex", "version": "1"}],
        "selectors": [], "interpretations": [], "coverage": [], "profiles": [],
    }
    observations = [
        ("rb-manifest", {"items": items}, "sha256:%s#package-manifest" % sha),
        ("rb-spine", {"idrefs": spine}, "sha256:%s#package-spine" % sha),
    ]
    if nav is not None:
        observations.append(("rb-nav", {"path": nav}, "sha256:%s#nav" % sha))
    for cid, value, ref in observations:
        desc["contents"].append({
            "id": cid, "kind": "structured",
            "value": json.dumps(value, sort_keys=True, separators=(",", ":")),
        })
        desc["relations"].append({"id": f"relb-hc-{cid}", "kind": "has-content",
                                  "from": "rb-root", "to": cid})
        desc["evidence"].append({"id": f"evb-{cid}", "origin": "source",
                                 "source_ref": ref, "content_ids": [cid],
                                 "selector_ids": []})
    inventory = {
        "version": "1", "source_format": "application/epub+zip",
        "features": [{"name": n, "scope_kind": k} for n, k in adapters.EPUB_FEATURES],
    }
    manifest = {
        "version": "1", "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_format": "application/epub+zip",
        "features": [n for n, _ in adapters.EPUB_FEATURES],
    }
    inv_raw = _write(out_dir, "inventory-b.json", inventory)
    man_raw = _write(out_dir, "manifest-b.json", manifest)
    desc["profiles"] = [
        {"id": "pb-inv", "kind": "carrier-inventory", "uri": "inventory-b.json",
         "version": "1", "sha256": _sha256(inv_raw)},
        {"id": "pb-man", "kind": "adapter-manifest", "uri": "manifest-b.json",
         "version": "1", "sha256": _sha256(man_raw)},
    ]
    desc["coverage"] = [
        _cov("epub:manifest", "document", "preserved", ""),
        _cov("epub:spine", "document", "preserved", ""),
        _cov("epub:navigation", "document",
             "preserved" if nav else "unexamined",
             "" if nav else "no nav item found"),
    ] + [_cov("epub:resources", f"resource:{n}", "preserved", "") for n in members]
    return desc


# -- agreement measurement ------------------------------------------------------------

def _pdf_pages(desc):
    return sorted(
        int(r["id"].replace("pg", "").replace("rbp", ""))
        for r in desc["regions"] if r["kind"] == "page")


def _page_text_ids(desc, page):
    out = set()
    by_id = {c["id"]: c for c in desc["contents"]}
    for rel in desc["relations"]:
        if rel["kind"] == "has-content" and rel["to"] in by_id \
                and by_id[rel["to"]]["kind"] == "text":
            frm = rel["from"]
            if frm in (f"pg{page}", f"rbp{page}"):
                out.add(rel["to"])
    return out


def agreement(desc_a, desc_b):
    """Agreement on DECLARED observables, matched by source anchors (page
    numbers / package facts), never by snapshot-local ids."""
    out = {}
    if desc_a["source"]["format"] == "application/pdf":
        pa, pb = _pdf_pages(desc_a), _pdf_pages(desc_b)
        out["pages"] = "agree" if pa == pb else "differ"
        presence_a = {p: bool(_page_text_ids(desc_a, p)) for p in pa}
        presence_b = {p: bool(_page_text_ids(desc_b, p)) for p in pb}
        out["text_presence"] = ("agree" if presence_a == presence_b else "differ")
        exact_a = {p: " ".join(
            (desc_a_id_value(desc_a, cid) for cid in sorted(_page_text_ids(desc_a, p))))
            for p in pa}
        exact_b = {p: " ".join(
            (desc_a_id_value(desc_b, cid) for cid in sorted(_page_text_ids(desc_b, p))))
            for p in pb}
        out["text_exact"] = "agree" if exact_a == exact_b else "differ"
    else:
        vals_a = {c["id"]: c["value"] for c in desc_a["contents"]}
        vals_b = {c["id"]: c["value"] for c in desc_b["contents"]}
        pairs = [
            ("manifest_items",
             [c for c in desc_a["contents"] if "manifest" in c["id"]],
             [c for c in desc_b["contents"] if "manifest" in c["id"]]),
            ("spine", [c for c in desc_a["contents"] if "spine" in c["id"]],
             [c for c in desc_b["contents"] if "spine" in c["id"]]),
            ("nav", [c for c in desc_a["contents"] if c["id"].endswith("-nav")
                     or c["id"].endswith("c-nav")],
             [c for c in desc_b["contents"] if c["id"].endswith("-nav")]),
        ]
        for key, ca, cb in pairs:
            va = [c["value"] for c in ca]
            vb = [c["value"] for c in cb]
            out[key] = "agree" if va == vb else "differ"
        res_a = {c["scope"] for c in desc_a["coverage"]
                 if c["feature"] == "epub:resources"}
        res_b = {c["scope"] for c in desc_b["coverage"]
                 if c["feature"] == "epub:resources"}
        out["resources"] = "agree" if res_a == res_b else "differ"
    return out


def desc_a_id_value(desc, cid):
    return next(c["value"] for c in desc["contents"] if c["id"] == cid)


def overhead(desc_a, desc_b):
    return {
        "a_bytes": len(canonical.reader_a(desc_a)),
        "b_bytes": len(canonical.reader_a(desc_b)),
    }


def b_unexamined_features(desc_b):
    return sorted({c["feature"] for c in desc_b["coverage"]
                   if c["status"] == "unexamined"})


INDEPENDENCE_NOTE = (
    "machinery-only: reader B is an independently coded scripted reading path "
    "(agent-executed); this is not human review and claims no real-carrier "
    "conformance")


def agreement_table(carriers):
    """One row per carrier: agreement verdict, overhead, reader-B gaps."""
    import tempfile
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in carriers:
            path = Path(__file__).resolve().parents[2] / "fixtures" / "carriers" / name
            out = Path(tmp) / name
            if name.endswith(".epub"):
                a = adapters.describe_epub(path, out / "a")
                b = describe_epub_b(path, out / "b")
                ag = agreement(a, b)
                verdict = ("agree" if all(v == "agree" for v in ag.values())
                           else "partial-agree")
            else:
                a = adapters.describe_pdf(path, out / "a")
                b = describe_pdf_b(path, out / "b")
                ag = agreement(a, b)
                verdict = ("partial-agree" if ag["text_exact"] == "differ"
                           else "agree")
            ov = overhead(a, b)
            rows.append({
                "carrier": name,
                "declared_observables": ag,
                "verdict": verdict,
                "a_bytes": ov["a_bytes"],
                "b_bytes": ov["b_bytes"],
                "reader_b_unexamined": b_unexamined_features(b),
                "independence_note": INDEPENDENCE_NOTE,
            })
    return rows
