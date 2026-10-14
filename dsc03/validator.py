# Purpose: Reference validator for DSC 0.3 descriptors per the add-dsc-03 deltas.
# Responsibilities: Parse and validate descriptors in two phases — a lexical/type
#   phase (invalid_shape before reference lookup or graph traversal, NFC walk with
#   the text-content exception) and a semantic phase (identity, referential
#   integrity, per-view containment trees, scoped reading order, typed
#   geometry/selector/interpretation/evidence/coverage/profile bindings) —
#   returning typed outcome states: valid/invalid with sorted reason codes,
#   parse_error for malformed JSON.
# Rationale: add-dsc-03 document-core/structure/evidence/semantics/adapters deltas
#   supersede the preserved research draft. The frozen 0.2 validator is never
#   upgraded in place; this module lives outside the frozen bundle.
"""DSC 0.3 descriptor validator (not a PDF/EPUB extractor).

Implemented limits (resource_limit reporting): no size limits are enforced yet;
nesting depth is bounded by Python's JSON parser recursion limit and a document
exceeding it surfaces as a parse_error, never as a valid descriptor.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ID_RE = re.compile("[A-Za-z0-9][A-Za-z0-9_.:-]*")
SHA256_RE = re.compile("[0-9a-f]{64}")
PAGE_SCOPE_RE = re.compile("page:(0|[1-9][0-9]*)")
ORIGINS = {"source", "extracted", "inferred", "manual", "external"}
STATUSES = {"supported", "disputed", "asserted_without_evidence"}
CONTENT_KINDS = {"text", "image", "number", "structured", "binary-reference"}
VIEW_KINDS = {"physical", "logical", "carrier"}
PROFILE_KINDS = {"selector", "geometry", "carrier-inventory", "adapter-manifest", "alignment"}
SELECTOR_KINDS = {"pdf-area", "pdf-object", "pdf-text-range", "epub-resource", "epub-fragment", "text-range", "external"}
INTERPRETATION_KINDS = {"reading-order", "segmentation"}
COVERAGE_STATUSES = {"preserved", "transformed", "approximated", "omitted", "unsupported", "unexamined"}
RELATION_RULES = {
    "contains": ("regions", "regions"),
    "precedes": ("regions", "regions"),
    "realizes": ("regions", "regions"),
    "has-content": ("regions", "contents"),
    "derived-from": ("evidence", "evidence"),
}
TOP_LEVEL = [
    "version", "id", "source", "regions", "contents", "relations", "annotations",
    "evidence", "vocabularies", "views", "selectors", "interpretations",
    "coverage", "profiles",
]

# Phase-A field type specs: collection -> (required_keys, optional_keys,
# string_fields, list_of_str_fields, int_fields)
FIELD_SPECS = {
    "views": (("id", "kind", "root"), (), ("id", "kind", "root"), (), ()),
    "regions": (("id", "view_id", "kind"), ("geometry",), ("id", "view_id", "kind"), (), ("x", "y", "width", "height")),
    "contents": (("id", "kind", "value"), (), ("id", "kind", "value"), (), ()),
    "relations": (("id", "kind", "from", "to"), ("evidence", "interpretation_id"), ("id", "kind", "from", "to", "interpretation_id"), ("evidence",), ()),
    "annotations": (("id", "target", "term", "value", "origin", "status", "evidence", "view_id"), ("alignment_profile_id", "selector_ids"), ("id", "target", "term", "value", "origin", "status", "view_id", "alignment_profile_id"), ("evidence", "selector_ids"), ()),
    "evidence": (("id", "origin", "source_ref", "content_ids", "selector_ids"), ("transform",), ("id", "origin", "source_ref"), ("content_ids", "selector_ids"), ()),
    "selectors": (("id", "kind", "profile_id", "source_sha256", "target", "locator"), (), ("id", "kind", "profile_id", "source_sha256", "target", "locator"), (), ()),
    "interpretations": (("id", "kind", "view_id", "origin", "status", "evidence"), (), ("id", "kind", "view_id", "origin", "status"), ("evidence",), ()),
    "coverage": (("inventory_id", "manifest_id", "feature", "scope", "status", "reason", "adapter_id", "adapter_version", "config_sha256"), (), ("inventory_id", "manifest_id", "feature", "scope", "status", "reason", "adapter_id", "adapter_version", "config_sha256"), (), ()),
    "profiles": (("id", "kind", "uri", "version", "sha256"), (), ("id", "kind", "uri", "version", "sha256"), (), ()),
    "vocabularies": (("namespace", "version"), (), ("namespace", "version"), (), ()),
}


class Duplicate(Exception):
    """Duplicate JSON key in an input document."""


def pairs(xs):
    out = {}
    for k, v in xs:
        if k in out:
            raise Duplicate("duplicate_key")
        out[k] = v
    return out


def loads(text):
    d = json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite")),
    )
    _check_unicode_scalars(d)
    return d


def load(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def canonical(x):
    return json.dumps(
        x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _has_surrogate(s):
    return any(0xD800 <= ord(c) <= 0xDFFF for c in s)


def _check_unicode_scalars(x):
    """Malformed JSON Unicode (unpaired surrogates) is a parse-time failure."""
    if isinstance(x, str):
        if _has_surrogate(x):
            raise ValueError("invalid_unicode_scalar_sequence")
    elif isinstance(x, dict):
        for k, v in x.items():
            _check_unicode_scalars(k)
            _check_unicode_scalars(v)
    elif isinstance(x, list):
        for v in x:
            _check_unicode_scalars(v)


def _shape_errors(errors, obj, required, optional=()):
    if not isinstance(obj, dict):
        errors.add("invalid_shape")
        return False
    if not set(required) <= set(obj) or set(obj) - set(required) - set(optional):
        errors.add("invalid_shape")
        return False
    return True


def type_phase(d):
    """Lexical/type checks. Malformed field types yield invalid_shape before
    reference lookup or graph traversal (document-core outcome states)."""
    errors = set()
    if not _shape_errors(errors, d, TOP_LEVEL):
        return errors
    if d["version"] != "0.3" or not _is_str(d["id"]):
        errors.add("invalid_shape")
    if not _shape_errors(errors, d["source"], ["format", "sha256", "locator"]):
        errors.add("invalid_shape")
    else:
        if not all(_is_str(d["source"][k]) for k in ("format", "locator")):
            errors.add("invalid_shape")
        if not isinstance(d["source"]["sha256"], str):
            errors.add("invalid_shape")
    for key in TOP_LEVEL[3:]:
        if not isinstance(d[key], list):
            errors.add("invalid_shape")
    if errors:
        return errors

    for key, (required, optional, str_fields, list_fields, int_fields) in FIELD_SPECS.items():
        for item in d[key]:
            if not _shape_errors(errors, item, required, optional):
                continue
            for f in str_fields:
                if f in item and not _is_str(item[f]):
                    errors.add("invalid_shape")
            for f in list_fields:
                if f in item:
                    v = item[f]
                    if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                        errors.add("invalid_shape")
            if key == "regions" and "geometry" in item:
                g = item["geometry"]
                if not _shape_errors(errors, g, ["profile_id", "space", "x", "y", "width", "height"]):
                    continue
                if not _is_str(g["space"]):
                    errors.add("invalid_shape")
                for f in int_fields:
                    if type(g.get(f)) is not int or g[f] < 0:
                        errors.add("invalid_geometry")
            if key == "evidence" and "transform" in item:
                t = item["transform"]
                if not _shape_errors(errors, t, ["id", "version", "config_sha256", "dependencies", "inputs", "outputs"]):
                    continue
                if not _is_str(t["id"]) or not _is_str(t["version"]):
                    errors.add("invalid_shape")
                if not isinstance(t["config_sha256"], str):
                    errors.add("invalid_shape")
                for f in ("dependencies", "inputs", "outputs"):
                    v = t[f]
                    if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                        errors.add("invalid_shape")
            if key == "contents" and item.get("kind") == "text" and not isinstance(item.get("value"), str):
                errors.add("invalid_content")
    _nfc_walk(d, errors)
    return errors


def _is_str(x):
    return isinstance(x, str) and bool(x)


def _nfc_walk(x, errors, text_content=False):
    """All strings SHALL be NFC except contents[].value when kind is text.
    Object keys and identifiers SHALL be ASCII. No nulls/booleans/floats."""
    if isinstance(x, str):
        if not text_content and unicodedata.normalize("NFC", x) != x:
            errors.add("not_nfc")
    elif isinstance(x, dict):
        for k, v in x.items():
            if not k.isascii():
                errors.add("non_ascii_key")
            _nfc_walk(v, errors, text_content)
    elif isinstance(x, list):
        for v in x:
            _nfc_walk(v, errors, text_content)
    elif x is None or isinstance(x, (float, bool)):
        errors.add("invalid_scalar")
    elif not isinstance(x, int):
        errors.add("invalid_scalar")


def _is_text_content(obj):
    return (
        isinstance(obj, dict)
        and set(obj) == {"id", "kind", "value"}
        and obj.get("kind") == "text"
    )


def _walk_doc(x, errors, text_content=False):
    """Document walk applying the NFC text-content exception in place."""
    if isinstance(x, dict):
        if not text_content and _is_text_content(x):
            for k, v in x.items():
                if not k.isascii():
                    errors.add("non_ascii_key")
                if k == "value":
                    _nfc_walk(v, errors, text_content=True)
                else:
                    _walk_doc(v, errors)
            return
        for k, v in x.items():
            if not k.isascii():
                errors.add("non_ascii_key")
            _walk_doc(v, errors, text_content)
    elif isinstance(x, list):
        for v in x:
            _walk_doc(v, errors, text_content)
    else:
        _nfc_walk(x, errors, text_content)


def validate(d):
    # Phase A: malformed field types are invalid_shape before reference lookup
    # or graph traversal (document-core, Validation outcome states).
    lexical = type_phase(d)
    if lexical:
        return sorted(lexical)

    errors = set()

    def err(x):
        errors.add(x)

    def nonempty_str(x):
        return isinstance(x, str) and bool(x)

    def digest_ok(x):
        return isinstance(x, str) and SHA256_RE.fullmatch(x)

    def same_view(a, b):
        va, vb = view_of.get(a), view_of.get(b)
        return va is not None and va == vb

    # -- source digest --------------------------------------------------------
    if not digest_ok(d["source"]["sha256"]):
        err("invalid_digest")

    # -- vocabularies ---------------------------------------------------------
    vocab_namespaces = set()
    for v in d["vocabularies"]:
        if not nonempty_str(v["namespace"]) or not nonempty_str(v["version"]):
            err("invalid_vocabulary")
        elif v["namespace"] in vocab_namespaces:
            err("duplicate_vocabulary")
        else:
            vocab_namespaces.add(v["namespace"])

    # -- named views ----------------------------------------------------------
    view_kinds = {}
    view_root = {}
    for v in d["views"]:
        if v["kind"] not in VIEW_KINDS:
            err("invalid_view")
        if not ID_RE.fullmatch(v["id"]):
            err("invalid_id")
            continue
        if v["id"] in view_kinds:
            err("duplicate_id")
            continue
        view_kinds[v["id"]] = v["kind"]
        view_root[v["id"]] = v["root"]
    if not any(k == "logical" for k in view_kinds.values()):
        err("invalid_view")

    # -- profiles (declared before binding checks) -----------------------------
    profile_ids = {}
    for p in d["profiles"]:
        if p["kind"] not in PROFILE_KINDS:
            err("invalid_profile")
        if not digest_ok(p["sha256"]):
            err("invalid_digest")
        if not ID_RE.fullmatch(p["id"]):
            err("invalid_id")
            continue
        if p["id"] in profile_ids:
            err("duplicate_id")
            continue
        profile_ids[p["id"]] = p

    # -- interpretations (referenced by precedes) -------------------------------
    interp_ids = set()
    interp_seen = set()
    for i in d["interpretations"]:
        if ID_RE.fullmatch(i["id"]):
            interp_ids.add(i["id"])

    # -- regions ----------------------------------------------------------------
    region_ids = set()
    view_of = {}
    for r in d["regions"]:
        if not ID_RE.fullmatch(r["id"]):
            err("invalid_id")
            continue
        if r["id"] in region_ids:
            err("duplicate_id")
            continue
        region_ids.add(r["id"])
        if r["view_id"] not in view_kinds:
            err("dangling_reference")
            continue
        view_of[r["id"]] = r["view_id"]
        if "geometry" in r:
            g = r["geometry"]
            pid = g["profile_id"]
            if view_kinds.get(r["view_id"]) != "physical":
                err("logical_geometry")
            if pid not in profile_ids or profile_ids[pid].get("kind") != "geometry":
                err("dangling_reference")

    # view roots must exist and belong to their own view
    for vid, root in view_root.items():
        if root not in region_ids or view_of.get(root) != vid:
            err("containment_roots")

    # -- contents ----------------------------------------------------------------
    content_ids = set()
    for c in d["contents"]:
        if not ID_RE.fullmatch(c["id"]):
            err("invalid_id")
            continue
        if c["id"] in content_ids:
            err("duplicate_id")
            continue
        content_ids.add(c["id"])
        if c["kind"] not in CONTENT_KINDS:
            err("invalid_content")

    # -- selectors ----------------------------------------------------------------
    selector_ids = set()
    for sl in d["selectors"]:
        if not ID_RE.fullmatch(sl["id"]):
            err("invalid_id")
            continue
        if sl["id"] in selector_ids:
            err("duplicate_id")
            continue
        selector_ids.add(sl["id"])
        if sl["kind"] not in SELECTOR_KINDS:
            err("invalid_selector")
        if not digest_ok(sl["source_sha256"]):
            err("invalid_digest")
        if sl["profile_id"] not in profile_ids or profile_ids[sl["profile_id"]].get("kind") != "selector":
            err("dangling_reference")
        t = sl["target"]
        if t not in region_ids and t not in content_ids:
            err("dangling_reference")
        elif sl["kind"] == "text-range":
            # a text-range target SHALL be text content
            tgt = next((c for c in d["contents"] if c.get("id") == t), None)
            if tgt is None or tgt.get("kind") != "text":
                err("invalid_selector")

    # -- evidence -------------------------------------------------------------------
    evidence_ids = set()
    for e in d["evidence"]:
        if not ID_RE.fullmatch(e["id"]):
            err("invalid_id")
            continue
        if e["id"] in evidence_ids:
            err("duplicate_id")
            continue
        evidence_ids.add(e["id"])
        if e["origin"] not in ORIGINS:
            err("invalid_evidence")
        if not all(x in content_ids for x in e["content_ids"]) or not all(x in selector_ids for x in e["selector_ids"]):
            err("dangling_reference")
        elif len(set(e["content_ids"])) != len(e["content_ids"]) or len(set(e["selector_ids"])) != len(e["selector_ids"]):
            err("invalid_evidence")
        if "transform" in e:
            t = e["transform"]
            ins, outs = t["inputs"], t["outputs"]
            if not digest_ok(t["config_sha256"]):
                err("invalid_transform")
            if not (t["dependencies"] and all(x for x in t["dependencies"])):
                err("invalid_transform")
            if not (ins and all(x in content_ids for x in ins) and len(set(ins)) == len(ins)):
                err("invalid_transform")
            elif not (outs and all(x in content_ids for x in outs) and len(set(outs)) == len(outs)):
                err("invalid_transform")
            elif set(ins) & set(outs):
                err("invalid_transform")
            elif set(outs) != set(e["content_ids"]):
                err("invalid_transform")
        elif e["origin"] in ("extracted", "inferred"):
            err("missing_transform")

    # -- relations -------------------------------------------------------------------
    parents = {}
    contains_edges = []
    precedes_by_interp = {}
    hc_in_view = set()  # (view_id, content_id) bound by has-content
    edges = set()
    ns_map = {"regions": region_ids, "contents": content_ids, "evidence": evidence_ids}
    for r in d["relations"]:
        if not ID_RE.fullmatch(r["id"]):
            err("invalid_id")
            continue
        kind, a, b = r["kind"], r["from"], r["to"]
        if kind not in RELATION_RULES:
            err("unknown_relation")
            continue
        ta = next((n for n, ids in ns_map.items() if a in ids), None)
        tb = next((n for n, ids in ns_map.items() if b in ids), None)
        if ta is None or tb is None:
            err("dangling_reference")
            continue
        if (ta, tb) != RELATION_RULES[kind]:
            err("relation_type")
            continue
        if kind == "precedes":
            interp = r.get("interpretation_id")
            if interp is None:
                err("invalid_shape")
                continue
            if interp not in interp_ids:
                err("dangling_reference")
                continue
            if not same_view(a, b):
                err("relation_type")
                continue
            key = (kind, a, b, interp)
            if key in edges:
                err("duplicate_edge")
            edges.add(key)
            precedes_by_interp.setdefault(interp, []).append((a, b))
            continue
        if "interpretation_id" in r:
            err("invalid_shape")
            continue
        key = (kind, a, b)
        if key in edges:
            err("duplicate_edge")
        edges.add(key)
        if kind == "contains":
            if not same_view(a, b):
                err("relation_type")
                continue
            contains_edges.append((a, b))
            parents[b] = parents.get(b, 0) + 1
        elif kind == "realizes":
            va = view_kinds.get(view_of.get(a))
            vb = view_kinds.get(view_of.get(b))
            if va != "physical" or vb != "logical":
                err("relation_type")
        elif kind == "has-content":
            v = view_of.get(a)
            if v is not None:
                hc_in_view.add((v, b))

    # containment tree integrity per named view
    for vid, root in view_root.items():
        if root not in region_ids or view_of.get(root) != vid:
            continue
        if root in parents:
            err("containment_roots")
        for rid, v in view_of.items():
            if v == vid and rid != root and parents.get(rid, 0) != 1:
                err("containment_roots")

    def has_cycle(pairs_edges):
        adj = {}
        for a, b in pairs_edges:
            adj.setdefault(a, []).append(b)
        temp, done = set(), set()

        def visit(x):
            if x in temp:
                return True
            if x in done:
                return False
            temp.add(x)
            if any(visit(y) for y in adj.get(x, [])):
                return True
            temp.remove(x)
            done.add(x)
            return False

        return any(visit(x) for x in adj)

    if has_cycle(contains_edges):
        err("containment_cycle")
    for interp, es in precedes_by_interp.items():
        if has_cycle(es):
            err("order_cycle")

    # -- annotations ------------------------------------------------------------------
    for a in d["annotations"]:
        if not ID_RE.fullmatch(a["id"]):
            err("invalid_id")
            continue
        if ("alignment_profile_id" in a) != ("selector_ids" in a):
            err("invalid_annotation")
        elif "alignment_profile_id" in a:
            pid = a["alignment_profile_id"]
            if pid not in profile_ids or profile_ids[pid].get("kind") != "alignment":
                err("dangling_reference")
            sids = a["selector_ids"]
            if not (sids and all(x in selector_ids for x in sids) and len(set(sids)) == len(sids)):
                err("dangling_reference")
        if a["view_id"] not in view_kinds:
            err("dangling_reference")
        tgt = a["target"]
        if tgt in region_ids:
            if view_of.get(tgt) != a["view_id"]:
                err("dangling_reference")
        elif tgt in content_ids:
            if (a["view_id"], tgt) not in hc_in_view:
                err("dangling_reference")
        else:
            err("dangling_reference")
        term = a["term"]
        if ":" not in term or term.split(":", 1)[0] not in vocab_namespaces:
            err("unknown_term")
        if a["origin"] not in ORIGINS or a["status"] not in STATUSES:
            err("invalid_annotation")
        ev = a["evidence"]
        if any(x not in evidence_ids for x in ev):
            err("dangling_reference")
        if a["status"] == "supported" and not ev:
            err("missing_support")
        if a["status"] == "asserted_without_evidence" and ev:
            err("invalid_annotation")

    # -- interpretations ------------------------------------------------------------------
    for i in d["interpretations"]:
        if not ID_RE.fullmatch(i["id"]):
            err("invalid_id")
            continue
        if i["id"] in interp_seen:
            err("duplicate_id")
            continue
        interp_seen.add(i["id"])
        if i["kind"] not in INTERPRETATION_KINDS:
            err("invalid_interpretation")
        if i["view_id"] not in view_kinds:
            err("dangling_reference")
        if i["origin"] not in ORIGINS or i["status"] not in STATUSES:
            err("invalid_interpretation")
        ev = i["evidence"]
        if any(x not in evidence_ids for x in ev):
            err("dangling_reference")
        if i["status"] == "supported" and not ev:
            err("missing_support")
        if i["status"] == "asserted_without_evidence" and ev:
            err("invalid_interpretation")

    # -- coverage entries ------------------------------------------------------------
    cov_keys = set()
    for c in d["coverage"]:
        inv_id, man_id = c["inventory_id"], c["manifest_id"]
        if inv_id not in profile_ids or profile_ids[inv_id].get("kind") != "carrier-inventory":
            err("dangling_reference")
        if man_id not in profile_ids or profile_ids[man_id].get("kind") != "adapter-manifest":
            err("dangling_reference")
        scope = c["scope"]
        scope_ok = (
            scope == "document"
            or PAGE_SCOPE_RE.fullmatch(scope)
            or scope.startswith("resource:")
        )
        if not scope_ok:
            err("invalid_coverage")
        if c["status"] not in COVERAGE_STATUSES:
            err("invalid_coverage")
        if not c["reason"] and c["status"] != "preserved":
            err("invalid_coverage")
        cfg = c["config_sha256"]
        if cfg != "unavailable" and not digest_ok(cfg):
            err("invalid_coverage")
        if scope_ok:
            k = (inv_id, c["feature"], scope)
            if k in cov_keys:
                err("invalid_coverage")
            cov_keys.add(k)

    # -- global id namespace: entity ids never collide across collections -------------
    all_ids = {}
    for key, ids in [
        ("regions", region_ids),
        ("contents", content_ids),
        ("selectors", selector_ids),
        ("evidence", evidence_ids),
        ("interpretations", interp_seen),
        ("profiles", set(profile_ids)),
    ]:
        for i in ids:
            if i in all_ids:
                err("duplicate_id")
            all_ids[i] = key

    return sorted(errors)


def run(path):
    try:
        result = validate(load(path))
    except (Duplicate, ValueError, json.JSONDecodeError, UnicodeError) as e:
        result = ["parse_error:" + str(e)]
    return result


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        base = Path(__file__).resolve().parents[1] / "tests" / "tracer"
        count = 0
        for p in sorted(base.glob("fixture_*.json")):
            result = run(p)
            assert not result, (p, result)
            count += 1
        print("PASS", count, "tracer fixtures")
        return
    result = run(sys.argv[1])
    print(json.dumps({"status": "invalid" if result else "valid", "reasons": result}, sort_keys=True))
    if result:
        sys.exit(1)


if __name__ == "__main__":
    main()
