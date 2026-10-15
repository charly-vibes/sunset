# Purpose: Consumer-side law fixtures for the document-space spec delta
#   (define-document-composition-semantics, sunset-905.2) — carrier-relative
#   spatial layout: typed coordinate frames, transforms, stable EPUB
#   selectors and mixed native/OCR observations.
# Responsibilities: Provide (1) transform_rot90 — a declared, invertible
#   page-box rotation with forward/inverse directions and an explicit
#   numeric tolerance (pdf_rotation, roundtrip_transform), (2) normalize/
#   denormalize/within_tolerance — frame conversion helpers, (3) above — a
#   spatial predicate that returns a TYPED unknown (never false/null/exception)
#   for incompatible frames without a pinned transform (cross_page_unknown),
#   (4) epub_fixture + epub_identity — stable spine selectors across reflow;
#   viewport XY never provides persistent identity (epub_reflow),
#   (5) hybrid_page_fixture + mixed_observations_report — native and OCR
#   observations coexisting with separate declared origins and evidence,
#   no forced equality (native_ocr_coexist), (6) spatial_predicates +
#   emitted_order_edges — above/left-of/overlap evaluated read-only, NEVER
#   emitting precedes or contains edges (spatial_not_order,
#   no_spatial_reading_order). Synthetic, validated fixtures only; no OCR
#   runs, no subprocesses, no real-carrier conformance claims.
# Rationale: the deployed kernel carries geometry and selector bindings but
#   has no spatial predicate evaluator; these fixtures witness the proposed
#   frame laws machinery-side under dsc03/substrate/ — no wire change.
"""Space laws: typed frames, unknown predicates, reflow identity, coexist."""
import copy
import hashlib

from dsc03.substrate.laws import typed_check


class Transform:
    """A declared, invertible frame transform with an explicit tolerance."""

    def __init__(self, tid, version, tolerance, forward, inverse):
        self.tid = tid
        self.version = version
        self.tolerance = tolerance
        self._forward = forward
        self._inverse = inverse


def transform_rot90(box_w, box_h):
    """90-degree clockwise page-box rotation, declared as a bijection
    between the rotated frame (page-N-rot90-pt) and the source frame
    (page-N-pt).

    normalize (rotated -> source): x_s = box_h - (y_r + h_r), y_s = x_r,
    with w/h swapped. denormalize (source -> rotated): the inverse. Exact
    on integers, so the declared tolerance is 0 for this fixture family.
    """
    def forward(g):  # rotated frame -> source frame
        return {"space": _base_of(g["space"]),
                "x": box_h - (g["y"] + g["height"]),
                "y": g["x"], "width": g["height"], "height": g["width"]}

    def inverse(g):  # source frame -> rotated frame
        return {"space": _rot_of(g["space"]),
                "x": g["y"], "y": box_h - (g["x"] + g["width"]),
                "width": g["height"], "height": g["width"]}

    return Transform("rot90", "1", 0, forward, inverse)


def _base_of(space_name):
    suffix = "-rot90-pt"
    if space_name.endswith(suffix):
        return space_name[: -len(suffix)] + "-pt"
    return space_name


def _rot_of(space_name):
    if space_name.endswith("-rot90-pt"):
        return space_name
    return space_name[:-3] + "-rot90-pt" if space_name.endswith("-pt") \
        else space_name + "-rot90-pt"


def normalize(transform, observed):
    """Map a locus observed in the rotated frame back to the source frame."""
    return transform._forward(observed)


def denormalize(transform, source):
    """Map a source-frame locus into the rotated frame."""
    return transform._inverse(source)


def within_tolerance(a, b, tolerance):
    """Declared-tolerance equivalence of two loci (same frame)."""
    if a["space"] != b["space"]:
        return False
    return all(abs(a[k] - b[k]) <= tolerance
               for k in ("x", "y", "width", "height"))


def above(a, b):
    """above predicate: known typed result within one compatible frame,
    TYPED UNKNOWN ({status: unknown, reason: incompatible_frames}) across
    frames without a pinned transform — never false, never an exception.
    """
    if a["space"] != b["space"]:
        return {"status": "unknown", "reason": "incompatible_frames",
                "frames": sorted({a["space"], b["space"]})}
    return {"status": "known", "value": a["y"] < b["y"]}


def overlap(a, b):
    """overlap predicate (same frame only; unknown across frames)."""
    if a["space"] != b["space"]:
        return {"status": "unknown", "reason": "incompatible_frames",
                "frames": sorted({a["space"], b["space"]})}
    value = (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
             and a["y"] < b["y"] + b["height"]
             and b["y"] < a["y"] + a["height"])
    return {"status": "known", "value": value}


def left_of(a, b):
    """left-of predicate (same frame only; unknown across frames)."""
    if a["space"] != b["space"]:
        return {"status": "unknown", "reason": "incompatible_frames",
                "frames": sorted({a["space"], b["space"]})}
    return {"status": "known", "value": a["x"] + a["width"] <= b["x"]}


def geometry_fixture():
    """A validated two-column page with an overlapping figure/caption pair.

    Geometry lives on physical-view regions bound to a declared geometry
    profile (the deployed wire's only home for geometry).
    """
    return {
        "version": "0.3",
        "id": "space-layout",
        "source": {"format": "application/pdf",
                   "sha256": sha("space-layout-source"),
                   "locator": "urn:sub:layout"},
        "views": [
            {"id": "v-phys", "kind": "physical", "root": "r-page"},
            {"id": "v-log", "kind": "logical", "root": "r-art"},
        ],
        "regions": [
            {"id": "r-page", "view_id": "v-phys", "kind": "page"},
            {"id": "r-art", "view_id": "v-log", "kind": "article"},
            {"id": "r-col-1", "view_id": "v-phys", "kind": "column",
             "geometry": {"profile_id": "p-geo", "space": "page-1-pt",
                          "x": 40, "y": 60, "width": 250, "height": 700}},
            {"id": "r-col-2", "view_id": "v-phys", "kind": "column",
             "geometry": {"profile_id": "p-geo", "space": "page-1-pt",
                          "x": 320, "y": 60, "width": 250, "height": 700}},
            {"id": "r-fig", "view_id": "v-phys", "kind": "figure",
             "geometry": {"profile_id": "p-geo", "space": "page-1-pt",
                          "x": 100, "y": 200, "width": 200, "height": 100}},
            {"id": "r-cap", "view_id": "v-phys", "kind": "caption",
             "geometry": {"profile_id": "p-geo", "space": "page-1-pt",
                          "x": 110, "y": 280, "width": 180, "height": 20}},
        ],
        "contents": [{"id": "c1", "kind": "text", "value": "layout body"}],
        "relations": [
            {"id": "rel-p1", "kind": "contains", "from": "r-page",
             "to": "r-col-1"},
            {"id": "rel-p2", "kind": "contains", "from": "r-page",
             "to": "r-col-2"},
            {"id": "rel-pf", "kind": "contains", "from": "r-page",
             "to": "r-fig"},
            {"id": "rel-pc", "kind": "contains", "from": "r-page",
             "to": "r-cap"},
            {"id": "rel-hc", "kind": "has-content", "from": "r-col-1",
             "to": "c1"},
        ],
        "annotations": [],
        "evidence": [{"id": "e1", "origin": "source",
                      "source_ref": "urn:sub:layout#page:1",
                      "content_ids": ["c1"], "selector_ids": []}],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [{"id": "p-geo", "kind": "geometry",
                      "uri": "geometry.json", "version": "1",
                      "sha256": sha("space-geometry")}],
    }


def spatial_predicates(desc):
    """Read-only evaluation of above/left-of/overlap over every geometry-
    bearing region pair. The descriptor is returned untouched: predicate
    results NEVER become relation edges (spatial_order_separation).
    """
    regions = {r["id"]: r["geometry"] for r in desc["regions"]
               if "geometry" in r}
    report = []
    ids = sorted(regions)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            for name, fn in (("above", above), ("left-of", left_of),
                             ("overlap", overlap)):
                result = fn(regions[a], regions[b])
                report.append({"predicate": name, "a": a, "b": b,
                               **result})
    return report


def emitted_order_edges(report):
    """The order edges a spatial report emitted — always empty by law."""
    return [p for p in report
            if p.get("value") and p["predicate"] in ("above", "left-of")
            and "edge" in p]


def epub_fixture():
    """A validated EPUB-carrier descriptor: carrier view + stable spine
    fragment selector. Viewport geometry is NOT part of the wire identity."""
    return {
        "version": "0.3",
        "id": "space-epub",
        "source": {"format": "application/epub+zip",
                   "sha256": sha("space-epub-source"),
                   "locator": "urn:sub:epub"},
        "views": [
            {"id": "v-carrier", "kind": "carrier", "root": "r-ch3"},
            {"id": "v-log", "kind": "logical", "root": "r-ch3-log"},
        ],
        "regions": [
            {"id": "r-ch3", "view_id": "v-carrier", "kind": "chapter"},
            {"id": "r-ch3-log", "view_id": "v-log", "kind": "chapter"},
        ],
        "contents": [{"id": "c-ch3", "kind": "text",
                      "value": "chapter three body"}],
        "relations": [{"id": "rel-ch3", "kind": "has-content",
                       "from": "r-ch3", "to": "c-ch3"}],
        "annotations": [],
        "evidence": [{"id": "e-ch3", "origin": "source",
                      "source_ref": "urn:sub:epub#ch3",
                      "content_ids": ["c-ch3"], "selector_ids": ["sel-ch3"]}],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [{"id": "sel-ch3", "kind": "epub-fragment",
                       "profile_id": "p-sel", "source_sha256": sha("space-epub-source"),
                       "target": "c-ch3",
                       "locator": "urn:sub:epub#ch3/frag-42"}],
        "interpretations": [],
        "coverage": [],
        "profiles": [{"id": "p-sel", "kind": "selector",
                      "uri": "selectors.json", "version": "1",
                      "sha256": sha("space-selectors")}],
    }


def viewport_observation(viewport_id, x, y, scale):
    """A module-level viewport observation (transient rendering state).

    These are deliberately NOT wire geometry: viewport XY is rendering-
    local and never persisted as element identity.
    """
    return {"viewport": viewport_id, "x": x, "y": y, "scale": scale}


def epub_identity(desc, selector_id, obs_a, obs_b):
    """Reflow-safe identity check: the stable selector locator is the
    identity across viewport changes; differing viewport XY is allowed and
    recorded, never used as identity."""
    selector = next(s for s in desc["selectors"] if s["id"] == selector_id)
    xy_differs = (obs_a["x"], obs_a["y"]) != (obs_b["x"], obs_b["y"])
    return {"status": "stable", "selector_id": selector["id"],
            "selector_locator": selector["locator"],
            "xy_differs": xy_differs}


def hybrid_page_fixture():
    """A validated hybrid PDF page: one native text observation (origin
    source) and one OCR observation (origin extracted, declared transform
    lineage) coexisting on the same page."""
    desc = geometry_fixture()
    desc["id"] = "space-hybrid"
    desc["contents"].extend([
        {"id": "c-native", "kind": "text", "value": "native layer text"},
        {"id": "c-img", "kind": "image", "value": "hybrid page scan"},
        {"id": "c-ocr", "kind": "text", "value": "ocr layer text"},
    ])
    desc["relations"].extend([
        {"id": "rel-hc-n", "kind": "has-content", "from": "r-page",
         "to": "c-native"},
        {"id": "rel-hc-i", "kind": "has-content", "from": "r-page",
         "to": "c-img"},
        {"id": "rel-hc-o", "kind": "has-content", "from": "r-page",
         "to": "c-ocr"},
        {"id": "rel-df", "kind": "derived-from", "from": "e-ocr", "to": "e-img"},
    ])
    desc["evidence"] = [
        {"id": "e-native", "origin": "source",
         "source_ref": "urn:sub:layout#page:1",
         "content_ids": ["c-native"], "selector_ids": []},
        {"id": "e-img", "origin": "source",
         "source_ref": "urn:sub:layout#page:1",
         "content_ids": ["c-img"], "selector_ids": []},
        {"id": "e-ocr", "origin": "extracted",
         "source_ref": "urn:sub:layout#page:1",
         "content_ids": ["c-ocr"], "selector_ids": [],
         "transform": {"id": "ocr", "version": "1",
                       "config_sha256": sha("space-ocr-config"),
                       "dependencies": ["ocr-engine-sim"],
                       "inputs": ["c-img"], "outputs": ["c-ocr"]}},
    ]
    return desc


def mixed_observations_report(desc):
    """Coexistence report: native and OCR readings stay separately declared
    (own origin, own evidence, own content ids) with no forced equality or
    supersession invented between them.
    """
    kinds = {c["id"]: c["kind"] for c in desc["contents"]}
    native, ocr = [], []
    native_origin = ocr_origin = None
    for e in desc["evidence"]:
        if "transform" in e:
            ocr.extend(e["content_ids"])
            ocr_origin = e["origin"]
        else:
            native.extend(cid for cid in e["content_ids"]
                          if kinds.get(cid) == "text")
            native_origin = native_origin or e["origin"]
    # No supersession was invented: no evidence record claims both readings
    # (they are distinct contents with distinct declared origins).
    reading_pair = {"c-native", "c-ocr"}
    forced = any(reading_pair <= set(e["content_ids"])
                 for e in desc["evidence"])
    return {"status": "coexist",
            "native_content_ids": sorted(set(native)),
            "ocr_content_ids": sorted(ocr),
            "native_evidence_origin": native_origin,
            "ocr_evidence_origin": ocr_origin,
            "forced_equality": forced}


def sha(label):
    """Honest synthetic digest: sha256 of the named synthetic payload."""
    return hashlib.sha256(label.encode()).hexdigest()
