# Purpose: Adversarial conformance corpus for DSC 0.3 (sunset-r68.12, task 5.1).
# Responsibilities: Build one descriptor per adversarial case required by
#   document-conformance: columns, page continuation, shared pages, mixed
#   OCR/native text, poetry, EPUB links, conflicting interpretations, coordinate
#   transforms, roundtrip, omission, replay and exact Unicode text. Gate the
#   corpus: a missing listed case makes the suite status "incomplete". Cases
#   needing real bytes reuse the committed carriers through dsc03.adapters;
#   every synthetic descriptor is still schema-validated by the tests.
# Rationale: add-dsc-03 document-conformance "Adversarial corpus" and its
#   corpus-gate scenario. MACHINERY-ONLY artifacts: these descriptors exercise
#   the validator/readers/comparator machinery and claim no extraction
#   conformance; the HITL reviewed-anchor-mapping pass remains open.
"""Adversarial corpus builder + corpus gate (machinery-only)."""
import hashlib
import json
from pathlib import Path

from dsc03 import adapters

CARRIERS = Path(__file__).resolve().parents[1] / "fixtures" / "carriers"

REQUIRED = [
    "columns", "page-continuation", "shared-pages", "ocr-native", "poetry",
    "epub-links", "epub-footnotes", "conflicting-interpretations",
    "coordinate-transforms", "roundtrip", "omission", "replay", "exact-unicode",
]


def gate(cases):
    missing = [name for name in REQUIRED if name not in cases]
    return {
        "status": "incomplete" if missing else "complete",
        "missing": missing,
        "covered": [name for name in REQUIRED if name in cases],
    }


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _base(desc_id):
    return {
        "version": "0.3",
        "id": desc_id,
        "source": {
            "format": "application/json",
            "sha256": "0" * 64,
            "locator": "corpus/%s.json" % desc_id,
        },
        "views": [
            {"id": "v-phys", "kind": "physical", "root": "r-root"},
            {"id": "v-log", "kind": "logical", "root": "r-log"},
        ],
        "regions": [
            {"id": "r-root", "view_id": "v-phys", "kind": "document"},
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


def _text(d, cid, value, ev_ref=None):
    d["contents"].append({"id": cid, "kind": "text", "value": value})
    if ev_ref is not None:
        d["evidence"].append({
            "id": "ev-" + cid, "origin": "source", "source_ref": ev_ref,
            "content_ids": [cid], "selector_ids": [],
        })
    return cid


def build(out_dir):
    """Build the corpus. out_dir receives adapter artifacts for carrier cases."""
    cases = {}

    # -- columns -------------------------------------------------------------------
    d = _base("corpus-columns")
    d["regions"] += [
        {"id": "r-colL", "view_id": "v-phys", "kind": "column"},
        {"id": "r-colR", "view_id": "v-phys", "kind": "column"},
    ]
    d["relations"] += [
        {"id": "rel-1", "kind": "contains", "from": "r-root", "to": "r-colL"},
        {"id": "rel-2", "kind": "contains", "from": "r-root", "to": "r-colR"},
    ]
    for col, cid, text in (("r-colL", "c-L", "left column text"),
                           ("r-colR", "c-R", "right column text")):
        _text(d, cid, text)
        d["relations"].append({"id": "rel-hc-" + cid, "kind": "has-content", "from": col, "to": cid})
    d["interpretations"].append({
        "id": "i-col", "kind": "segmentation", "view_id": "v-phys",
        "origin": "manual", "status": "asserted_without_evidence", "evidence": [],
    })
    cases["columns"] = {"descriptor": d}

    # -- page continuation -----------------------------------------------------------
    d = _base("corpus-continuation")
    d["regions"] += [
        {"id": "r-p1", "view_id": "v-phys", "kind": "page"},
        {"id": "r-p2", "view_id": "v-phys", "kind": "page"},
    ]
    d["relations"].append({"id": "rel-c1", "kind": "contains", "from": "r-root", "to": "r-p1"})
    d["relations"].append({"id": "rel-c2", "kind": "contains", "from": "r-root", "to": "r-p2"})
    _text(d, "c-p1", "sentence begins on page one", "sha256:%s#page:1" % ("1" * 64))
    _text(d, "c-p2", "and continues on page two", "sha256:%s#page:2" % ("1" * 64))
    d["interpretations"].append({
        "id": "i-ro", "kind": "reading-order", "view_id": "v-phys",
        "origin": "manual", "status": "asserted_without_evidence", "evidence": [],
    })
    d["relations"].append({
        "id": "rel-cont", "kind": "precedes", "from": "r-p1", "to": "r-p2",
        "interpretation_id": "i-ro",
    })
    cases["page-continuation"] = {"descriptor": d}

    # -- shared pages ----------------------------------------------------------------
    d = _base("corpus-shared-pages")
    d["regions"] += [
        {"id": "r-pg", "view_id": "v-phys", "kind": "page"},
        {"id": "r-a1", "view_id": "v-log", "kind": "article"},
        {"id": "r-a2", "view_id": "v-log", "kind": "article"},
    ]
    d["relations"] += [
        {"id": "rel-c", "kind": "contains", "from": "r-root", "to": "r-pg"},
        {"id": "rel-l1", "kind": "contains", "from": "r-log", "to": "r-a1"},
        {"id": "rel-l2", "kind": "contains", "from": "r-log", "to": "r-a2"},
        {"id": "rel-r1", "kind": "realizes", "from": "r-pg", "to": "r-a1"},
        {"id": "rel-r2", "kind": "realizes", "from": "r-pg", "to": "r-a2"},
    ]
    cases["shared-pages"] = {"descriptor": d}

    # -- OCR vs native text -----------------------------------------------------------
    d = _base("corpus-ocr-native")
    _text(d, "c-native", "temperature 21 C recorded", "sha256:%s#native" % ("2" * 64))
    _text(d, "c-ocr", "temperature 2l C recorded", "sha256:%s#ocr" % ("2" * 64))
    cases["ocr-native"] = {"descriptor": d}

    # -- poetry (exact line breaks are content) ----------------------------------------
    d = _base("corpus-poetry")
    _text(d, "c-poem", "la tarde cae,\nel sol se apaga,\ny el río lleva\nsu canto abajo", "sha256:%s#poem" % ("3" * 64))
    cases["poetry"] = {"descriptor": d}

    # -- conflicting interpretations: two incompatible supported hypotheses -------------
    d = _base("corpus-conflicting")
    d["evidence"] += [
        {"id": "e-a", "origin": "source", "source_ref": "reviewer-alpha:order",
         "content_ids": [], "selector_ids": []},
        {"id": "e-b", "origin": "source", "source_ref": "reviewer-beta:order",
         "content_ids": [], "selector_ids": []},
    ]
    d["interpretations"] += [
        {"id": "i-alpha", "kind": "reading-order", "view_id": "v-log",
         "origin": "manual", "status": "supported", "evidence": ["e-a"]},
        {"id": "i-beta", "kind": "reading-order", "view_id": "v-log",
         "origin": "manual", "status": "supported", "evidence": ["e-b"]},
    ]
    cases["conflicting-interpretations"] = {"descriptor": d}

    # -- coordinate transforms ----------------------------------------------------------
    geo = {
        "version": "1", "kind": "geometry",
        "frames": [{
            "name": "page-pt", "unit": "pt", "origin": "top-left",
            "axes": "x-right,y-down", "rotation": 0, "binding": "page:1",
        }],
    }
    geo_bytes = (json.dumps(geo, sort_keys=True, separators=(",", ":"))).encode("utf-8")
    d = _base("corpus-transforms")
    d["regions"].append({
        "id": "r-pg", "view_id": "v-phys", "kind": "page",
        "geometry": {"profile_id": "p-geo", "space": "page-pt",
                     "x": 0, "y": 0, "width": 612, "height": 792},
    })
    d["relations"].append({"id": "rel-c", "kind": "contains", "from": "r-root", "to": "r-pg"})
    d["profiles"].append({
        "id": "p-geo", "kind": "geometry", "uri": "geometry-page-pt.json",
        "version": "1", "sha256": _sha(geo_bytes),
    })
    cases["coordinate-transforms"] = {"descriptor": d, "artifacts": {"p-geo": geo_bytes}}

    # -- roundtrip ----------------------------------------------------------------------
    d = _base("corpus-roundtrip")
    _text(d, "c-rt", "byte stable under re-serialization")
    cases["roundtrip"] = {"descriptor": d}

    # -- exact Unicode text (NFD survives; schema exempts text values from NFC) ----------
    d = _base("corpus-exact-unicode")
    _text(d, "c-nfd", "cafe\u0301 nai\u0308ve", "sha256:%s#unicode" % ("4" * 64))
    cases["exact-unicode"] = {"descriptor": d}

    # -- replay (evidence transform chain over a pinned callable) ------------------------
    cfg = json.dumps({"transform": "strip-line-numbers"}, sort_keys=True, separators=(",", ":"))
    cfg_sha = _sha(cfg.encode("utf-8"))

    def strip_line_numbers(value, _cfg=cfg):
        return "\n".join(
            line.split("\t", 1)[1] if "\t" in line else line
            for line in value.splitlines()
        )

    d = _base("corpus-replay")
    _text(d, "c-raw", "1\tFirst line\n2\tSecond line", "sha256:%s#raw" % ("5" * 64))
    _text(d, "c-clean", "First line\nSecond line")
    d["evidence"].append({
        "id": "e-t", "origin": "extracted", "source_ref": "sha256:%s#normalized" % cfg_sha,
        "content_ids": ["c-clean"], "selector_ids": [],
        "transform": {"id": "t-line-numbers", "version": "1", "config_sha256": cfg_sha,
                      "dependencies": ["ev-c-raw"], "inputs": ["c-raw"], "outputs": ["c-clean"]},
    })
    # document-evidence: the transform declares a derived-from edge to the
    # input's producing evidence record
    d["relations"].append({
        "id": "rel-df", "kind": "derived-from", "from": "e-t", "to": "ev-c-raw",
    })
    cases["replay"] = {"descriptor": d, "transform_fns": {cfg_sha: strip_line_numbers}}

    # -- EPUB footnotes (document-conformance lists footnotes as a required case) -------
    d = _base("corpus-epub-footnotes")
    d["source"] = {
        "format": "application/epub+zip", "sha256": "6" * 64,
        "locator": "corpus/epub-footnotes.epub",
    }
    d["regions"].append({"id": "r-res", "view_id": "v-phys", "kind": "resource"})
    d["relations"].append({"id": "rel-res", "kind": "contains", "from": "r-root", "to": "r-res"})
    d["evidence"].append({
        "id": "ev-fn", "origin": "source", "source_ref": "sha256:%s#resource:OEBPS/chapter1.xhtml" % ("6" * 64),
        "content_ids": [], "selector_ids": [],
    })
    d["annotations"].append({
        "id": "a-fn", "target": "r-res", "term": "ex:footnote",
        "value": "footnote observed on resource chapter1.xhtml",
        "origin": "source", "status": "supported", "evidence": ["ev-fn"],
        "view_id": "v-phys",
    })
    cases["epub-footnotes"] = {"descriptor": d}

    # -- EPUB links + omission: reuse the committed real carriers ------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    epub_desc = adapters.describe_epub(
        CARRIERS / "sunset-carrier-sample.epub", out_dir / "epub-links",
    )
    cases["epub-links"] = {"descriptor": epub_desc}

    pdf_path = CARRIERS / "agentic-patterns-excerpt.pdf"
    pdf_desc = adapters.describe_pdf(pdf_path, out_dir / "omission")
    last_glyph = max(
        (c for c in pdf_desc["coverage"] if c["feature"] == "pdf:glyphs"),
        key=lambda c: int(c["scope"].split(":")[1]),
    )
    last_glyph["status"] = "omitted"
    last_glyph["reason"] = "corpus case: glyphs on the last page omitted"
    cases["omission"] = {"descriptor": pdf_desc}

    return cases
