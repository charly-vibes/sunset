# Purpose: Consumer-side law fixtures for the document-views spec delta
#   (define-document-composition-semantics, sunset-905.2) — structural views,
#   hierarchies and partial orders over shared regions.
# Responsibilities: Provide (1) synthetic validated magazine fixtures
#   (magazine_fixture, cycle_fixture, order_fixture) exercising overlapping
#   physical/logical views, (2) content_bindings — cross-view membership
#   reading (view_overlap), (3) containment_cycle_report — classified refusal
#   WITH the cycle path witness (cycle_refused), (4) order_status — partial
#   reading order with incomparable regions preserved and declared-cycle
#   rejection with path witness (partial_order_ok), (5) project — scoped
#   projection keeping selected regions and internal edges and recording
#   excluded links as wire coverage loss (projection), (6) refinement_check —
#   supersession/conflict classification for edge-removing refinements
#   (refinement_conflict), (7) link_check — cross-page continuation and
#   reference edges stay typed links, no contains edge invented
#   (links_not_containment). All fixtures are validated descriptors; all
#   outcomes are classified, never exceptions, never invented edges.
# Rationale: the delta is a proposal (not deployed truth); these fixtures
#   witness the proposed laws machinery-side — the deployed kernel rejects
#   containment/reading-order cycles but has no projection, refinement or
#   link-checker, so those laws live here under dsc03/substrate/ beside the
#   existing Mapping algebra. No wire change, no conformance claim.
"""Views laws: overlap, cycles with witnesses, order, projection, refinement."""
import copy

from dsc03.substrate.laws import typed_check


def magazine_fixture():
    """A validated magazine: one physical page tree, one logical article,
    a cross-page continuation link and a reference (derived-from) lineage.

    - v-phys: r-doc (root) contains r-p1, r-p2 (pages)
    - v-log:  r-art (root, article); pages realize it
    - rel-cont: precedes r-p1 -> r-p2 under reading-order interpretation
      (a cross-page CONTINUATION — a typed link, not containment)
    - rel-ref: derived-from e-ref-dst -> e-ref-src (a typed reference)
    """
    return {
        "version": "0.3",
        "id": "views-magazine",
        "source": {"format": "application/pdf",
                   "sha256": sha("views-magazine-source"),
                   "locator": "urn:sub:magazine"},
        "views": [
            {"id": "v-phys", "kind": "physical", "root": "r-doc"},
            {"id": "v-log", "kind": "logical", "root": "r-art"},
        ],
        "regions": [
            {"id": "r-doc", "view_id": "v-phys", "kind": "document"},
            {"id": "r-p1", "view_id": "v-phys", "kind": "page"},
            {"id": "r-p2", "view_id": "v-phys", "kind": "page"},
            {"id": "r-art", "view_id": "v-log", "kind": "article"},
        ],
        "contents": [
            {"id": "c1", "kind": "text", "value": "column one"},
            {"id": "c2", "kind": "text", "value": "column two"},
            {"id": "c-ref", "kind": "text", "value": "cited note"},
        ],
        "relations": [
            {"id": "rel-doc1", "kind": "contains", "from": "r-doc", "to": "r-p1"},
            {"id": "rel-doc2", "kind": "contains", "from": "r-doc", "to": "r-p2"},
            {"id": "rel-hc1", "kind": "has-content", "from": "r-p1", "to": "c1"},
            {"id": "rel-hc2", "kind": "has-content", "from": "r-p2", "to": "c2"},
            {"id": "rel-hca", "kind": "has-content", "from": "r-art", "to": "c1"},
            {"id": "rel-hca2", "kind": "has-content", "from": "r-art", "to": "c2"},
            {"id": "rel-real1", "kind": "realizes", "from": "r-p1", "to": "r-art"},
            {"id": "rel-real2", "kind": "realizes", "from": "r-p2", "to": "r-art"},
            {"id": "rel-cont", "kind": "precedes", "from": "r-p1", "to": "r-p2",
             "interpretation_id": "int-ro"},
            {"id": "rel-ref", "kind": "derived-from",
             "from": "e-ref-dst", "to": "e-ref-src"},
        ],
        "annotations": [],
        "evidence": [
            {"id": "e1", "origin": "source",
             "source_ref": "urn:sub:magazine#page:1",
             "content_ids": ["c1"], "selector_ids": []},
            {"id": "e2", "origin": "source",
             "source_ref": "urn:sub:magazine#page:2",
             "content_ids": ["c2"], "selector_ids": []},
            {"id": "e-ref-src", "origin": "source",
             "source_ref": "urn:sub:magazine#page:1",
             "content_ids": ["c1"], "selector_ids": []},
            {"id": "e-ref-dst", "origin": "source",
             "source_ref": "urn:sub:magazine#page:2",
             "content_ids": ["c-ref"], "selector_ids": []},
        ],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [],
        "interpretations": [
            {"id": "int-ro", "kind": "reading-order", "view_id": "v-phys",
             "origin": "inferred", "status": "asserted_without_evidence",
             "evidence": []},
        ],
        "coverage": [],
        "profiles": [
            {"id": "p-inv", "kind": "carrier-inventory",
             "uri": "inventory.json", "version": "1",
             "sha256": sha("views-inventory")},
            {"id": "p-man", "kind": "adapter-manifest",
             "uri": "manifest.json", "version": "1",
             "sha256": sha("views-manifest")},
        ],
    }


def cycle_fixture():
    """magazine_fixture plus a two-region containment cycle (r-p1 -> r-p2
    -> r-p1) inside the physical view."""
    desc = magazine_fixture()
    desc["relations"].append(
        {"id": "rel-cyc1", "kind": "contains", "from": "r-p1", "to": "r-p2"})
    desc["relations"].append(
        {"id": "rel-cyc2", "kind": "contains", "from": "r-p2", "to": "r-p1"})
    return desc


def order_fixture():
    """A single-page two-column layout: root r-cols contains two column
    regions declared under a reading-order interpretation with NO precedes
    edge between them — they stay incomparable."""
    desc = magazine_fixture()
    desc["views"] = [
        {"id": "v-phys", "kind": "physical", "root": "r-cols"},
        {"id": "v-log", "kind": "logical", "root": "r-art"},
    ]
    desc["regions"] = [
        {"id": "r-cols", "view_id": "v-phys", "kind": "page"},
        {"id": "r-col-1", "view_id": "v-phys", "kind": "column"},
        {"id": "r-col-2", "view_id": "v-phys", "kind": "column"},
        {"id": "r-art", "view_id": "v-log", "kind": "article"},
    ]
    desc["relations"] = [
        {"id": "rel-cols1", "kind": "contains", "from": "r-cols",
         "to": "r-col-1"},
        {"id": "rel-cols2", "kind": "contains", "from": "r-cols",
         "to": "r-col-2"},
        {"id": "rel-hc1", "kind": "has-content", "from": "r-col-1", "to": "c1"},
        {"id": "rel-hc2", "kind": "has-content", "from": "r-col-2", "to": "c2"},
        {"id": "rel-real1", "kind": "realizes", "from": "r-col-1",
         "to": "r-art"},
    ]
    desc["evidence"] = [desc["evidence"][0], desc["evidence"][1]]
    return desc


def sha(label):
    """Honest synthetic digest: sha256 of the named synthetic payload."""
    import hashlib
    return hashlib.sha256(label.encode()).hexdigest()


def content_bindings(desc):
    """content_id -> set of view ids whose regions bind it via has-content.

    A content bound from regions of two different views is the overlap
    witness: both memberships survive on the shared region set.
    """
    region_view = {r["id"]: r["view_id"] for r in desc["regions"]}
    out = {}
    for rel in desc["relations"]:
        if rel["kind"] == "has-content":
            out.setdefault(rel["to"], set()).add(region_view[rel["from"]])
    return {k: v for k, v in out.items()}


def _contains_edges(desc):
    return [(r["from"], r["to"]) for r in desc["relations"]
            if r["kind"] == "contains"]


def _find_cycle(edges):
    """First cycle found in a directed edge list, as a path a -> ... -> a."""
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    for start in sorted(adj):
        seen = {start}

        def walk(node, path):
            for nxt in sorted(adj.get(node, ())):
                if nxt == start:
                    return path + [start]
                if nxt not in seen:
                    seen.add(nxt)
                    found = walk(nxt, path + [nxt])
                    if found:
                        return found
                    seen.discard(nxt)
            return None

        found = walk(start, [start])
        if found:
            return found
    return None


def containment_cycle_report(desc):
    """Classified containment-cycle refusal WITH a path witness.

    The deployed validator already rejects containment cycles; this report
    adds the missing diagnostic the delta names: the cycle path itself
    (first region == last region).
    """
    status, reasons = typed_check(desc)
    if "containment_cycle" not in reasons:
        return {"status": "accepted" if status == "accepted" else "rejected",
                "reasons": reasons}
    return {"status": "rejected", "reason": "containment_cycle",
            "cycle_path": _find_cycle(_contains_edges(desc))}


def _precedes_edges(desc, interp_id):
    return [(r["from"], r["to"]) for r in desc["relations"]
            if r["kind"] == "precedes" and r.get("interpretation_id") == interp_id]


def order_status(desc, interp_id):
    """Partial reading order under one interpretation.

    - accepted: validator accepts AND no total order is inferred; the
      incomparable region pairs are listed (their order is simply unknown,
      never guessed).
    - rejected with reason order_cycle and the cycle path witness: a DECLARED
      cycle under that interpretation.
    """
    status, reasons = typed_check(desc)
    if "order_cycle" in reasons:
        return {"status": "rejected", "reason": "order_cycle",
                "cycle_path": _find_cycle(_precedes_edges(desc, interp_id))}
    edges = _precedes_edges(desc, interp_id)
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
    # Reading order is over leaf content blocks: container regions (those
    # with contains children) are structural, not sequence members.
    children = _contains_children(desc)
    regions = [r["id"] for r in desc["regions"]
               if r["view_id"] == desc["views"][0]["id"]
               and r["id"] not in children]

    def reachable(a, b, seen):
        if a == b:
            return True
        return any(reachable(n, b, seen | {n})
                   for n in adj.get(a, ()) if n not in seen)

    incomparable = []
    for i, a in enumerate(regions):
        for b in regions[i + 1:]:
            if not reachable(a, b, {a}) and not reachable(b, a, {b}):
                incomparable.append(sorted([a, b]))
    return {"status": "accepted", "incomparable": sorted(incomparable)}


def project(desc, keep_region_ids):
    """Scoped projection: keep exactly the selected regions (plus each
    declared view root) and their internal edges; every dropped edge is
    reported in `excluded`, and dropped reading-order links are additionally
    recorded as wire coverage entries (status omitted, with a reason) —
    the projection never claims full fidelity. The projected descriptor is
    validated; an invalid result is a classified refusal.
    """
    keep = set(keep_region_ids) | {v["root"] for v in desc["views"]}
    out = copy.deepcopy(desc)
    excluded, coverage, recorded = [], [], set()

    while True:
        before = (len(out["regions"]), len(out["contents"]),
                  len(out["evidence"]), len(out["relations"]),
                  len(out["annotations"]), len(out["views"]))
        regions_ = {r["id"] for r in out["regions"] if r["id"] in keep}
        contents_ = {c["id"] for c in out["contents"]}
        evidence_ = {e["id"] for e in out["evidence"]}

        kept_rels = []
        for rel in out["relations"]:
            if _relation_resolves(rel, regions_, contents_, evidence_):
                kept_rels.append(rel)
            else:
                excluded.append({"id": rel["id"], "kind": rel["kind"],
                                 "from": rel["from"], "to": rel["to"]})
                if rel["kind"] == "precedes" and rel["id"] not in recorded:
                    recorded.add(rel["id"])
                    coverage.append({
                        "inventory_id": "p-inv", "manifest_id": "p-man",
                        "feature": f"continuation:{rel['id']}",
                        "scope": "document", "status": "omitted",
                        "reason": "excluded by projection",
                        "adapter_id": "substrate-project",
                        "adapter_version": "1",
                        "config_sha256": "unavailable"})
        out["relations"] = kept_rels

        # Contents survive only when a kept region binds them; evidence
        # survives only over kept contents; annotations survive only over
        # kept targets, evidence and views (the cascade runs to a fixpoint).
        bound = {r["to"] for r in kept_rels if r["kind"] == "has-content"}
        out["contents"] = [c for c in out["contents"] if c["id"] in bound]
        kept_contents = {c["id"] for c in out["contents"]}
        out["evidence"] = [e for e in out["evidence"]
                           if set(e["content_ids"]) <= kept_contents]
        evidence_kept = {e["id"] for e in out["evidence"]}
        view_ids = {v["id"] for v in out["views"] if v["root"] in keep}
        kept_annotations = []
        for a in out["annotations"]:
            ok = (a["target"] in regions_ or a["target"] in kept_contents) \
                and set(a["evidence"]) <= evidence_kept \
                and a["view_id"] in view_ids
            if ok:
                kept_annotations.append(a)
            else:
                excluded.append({"id": a["id"], "kind": "annotation",
                                 "from": a["target"], "to": ""})
        out["annotations"] = kept_annotations
        out["regions"] = [r for r in out["regions"] if r["id"] in keep]
        out["views"] = [v for v in out["views"] if v["root"] in keep]

        after = (len(out["regions"]), len(out["contents"]),
                 len(out["evidence"]), len(out["relations"]),
                 len(out["annotations"]), len(out["views"]))
        if after == before:
            break
    out["coverage"] = out.get("coverage", []) + coverage

    status, reasons = typed_check(out)
    if status != "accepted":
        return {"status": "refused", "rule": "projected_invalid",
                "reasons": reasons}
    return {"status": "projected", "descriptor": out,
            "excluded": sorted(excluded, key=lambda e: e["id"])}


def _relation_resolves(rel, regions_, contents_, evidence_):
    kind, a, b = rel["kind"], rel["from"], rel["to"]
    if kind in ("contains", "precedes", "realizes"):
        return a in regions_ and b in regions_
    if kind == "has-content":
        return a in regions_ and b in contents_
    if kind == "derived-from":
        return a in evidence_ and b in evidence_
    return False


def _contains_children(desc):
    out = {}
    for r in desc["relations"]:
        if r["kind"] == "contains":
            out.setdefault(r["from"], set()).add(r["to"])
    return out


def refinement_check(base, refined, superseded=(), policy=None):
    """Refinement classification: no established scoped edge may be removed
    silently. An edge present in base but absent in refined must be declared
    superseded under an explicit policy — otherwise the refinement is a
    conflict (both classifications name the removed edges as witnesses).
    """
    base_edges = {r["id"] for r in base["relations"]}
    refined_edges = {r["id"] for r in refined["relations"]}
    removed = sorted(base_edges - refined_edges)
    undeclared = [e for e in removed if e not in set(superseded)]
    if undeclared:
        return {"status": "conflict", "removed": removed,
                "undeclared": undeclared}
    if removed:
        return {"status": "superseded", "removed": removed,
                "policy": policy}
    return {"status": "preserved", "removed": []}


def link_check(desc, endpoint_a, endpoint_b):
    """Typed links between two endpoints: every edge touching either
    endpoint in the other's direction must be a LINK kind (precedes,
    derived-from) — never contains. No parent pointer is invented: the
    function only reads; it never adds edges."""
    # Only edges whose BOTH endpoints are the given pair count; edges that
    # merely touch one endpoint leave the pair's linkage untouched.
    links = [r["kind"] for r in desc["relations"]
             if {r["from"], r["to"]} == {endpoint_a, endpoint_b}]
    contains_between = "contains" in links
    return {"status": "typed_links" if not contains_between else "violated",
            "link_kinds": sorted(set(links)),
            "contains_between": contains_between}
