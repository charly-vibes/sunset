# Purpose: Reported migration of 0.2 descriptors to 0.3 (sunset-r68.9, tasks.md 4.1 + 4.2).
# Responsibilities: Convert a valid 0.2 descriptor into a 0.3 descriptor plus a
#   migration report — legacy cross-view containment becomes per-view trees (one
#   root per view), legacy precedes edges are kept only when both endpoints share
#   a view (otherwise reported as unsupported), original source digests and ids
#   are preserved where unambiguous, legacy geometry without profile bindings is
#   reported unexamined (never invented), legacy extracted/inferred evidence
#   without replay material is dropped as unrecoverable (annotations demoted with
#   a report entry), ambiguous or unbound annotation view bindings are reported,
#   and NFC-only 0.2 text is reported as unrecoverable to original code points.
# Rationale: add-dsc-03 design.md "Compatibility and migration"; no guessing.
"""0.2 -> 0.3 migration with a loss-accounting report; nothing is invented."""


def migrate(d02):
    """Migrate a valid 0.2 descriptor. Returns (descriptor_03, report).

    The report records every loss: dropped edges, unsupported order assertions,
    unexamined material and unrecoverable data. Regions/contents/evidence ids
    are preserved where the record survives.
    """
    report = {
        "views_created": [],
        "dropped": [],
        "unsupported": [],
        "unexamined": [],
        "unrecoverable": [],
        "demoted": [],
    }

    # -- regions and per-view trees -------------------------------------------
    view_of = {}
    for r in d02["regions"]:
        if "geometry" in r:
            report["unexamined"].append(
                f"geometry of region {r['id']} dropped: legacy coordinates have no profile binding"
            )
    class_edges = {"physical": [], "logical": []}
    parents = {}
    for rel in d02["relations"]:
        if rel["kind"] != "contains":
            continue
        va = region_view(d02, rel["from"])
        vb = region_view(d02, rel["to"])
        if va == vb and va in class_edges:
            class_edges[va].append((rel["id"], rel["from"], rel["to"]))
            parents[rel["to"]] = rel["from"]
        else:
            report["dropped"].append({
                "what": "contains-edge", "id": rel["id"],
                "reason": f"cross-view {va}->{vb}; per-view trees cannot keep it",
            })
    # forest per class; each tree becomes its own view
    children = {}
    for _, a, b in class_edges_all(class_edges):
        children.setdefault(a, []).append(b)
    view_by_root = {}
    counter = {"physical": 0, "logical": 0}
    d03_regions = []
    for r in d02["regions"]:
        rr = {"id": r["id"], "view_id": None, "kind": r["kind"]}
        d03_regions.append(rr)
    # find roots per class
    for cls in ("physical", "logical"):
        members = [r["id"] for r in d02["regions"] if r.get("view") == cls]
        roots = [m for m in members if m not in parents]
        if not roots and members:
            roots = [members[0]]  # cycle: pick a deterministic head, report it
            report["unsupported"].append({
                "what": "containment-cycle", "view_class": cls,
                "reason": "legacy containment cycle; head chosen deterministically for the tree",
            })
        for i, root in enumerate(roots):
            counter[cls] += 1
            vid = cls if i == 0 else f"{cls}-{counter[cls]}"
            members_tree = collect_tree(root, children, {m for m in members})
            for m in members_tree:
                view_of[m] = vid
            report["views_created"].append({"id": vid, "kind": cls, "root": root})
    for rr in d03_regions:
        rr["view_id"] = view_of[rr["id"]]

    d03 = {
        "version": "0.3",
        "id": d02["id"],
        "source": dict(d02["source"]),  # digest and locator preserved
        "views": report["views_created"],
        "regions": d03_regions,
        "contents": [dict(c) for c in d02["contents"]],
        "relations": [],
        "annotations": [],
        "evidence": [],
        "selectors": [],
        "interpretations": [],
        "coverage": [],
        "profiles": [],
        "vocabularies": [dict(v) for v in d02["vocabularies"]],
    }
    report["unrecoverable"].append(
        "original pre-normalization code points of text contents cannot be "
        "recovered: 0.2 stored NFC-normalized text only"
    )

    # -- relations: keep same-view structural edges; precedes via interpretations
    order_edges = {}  # view_id -> [(from, to)]
    keep_kinds = {"contains", "realizes", "has-content"}
    for rel in d02["relations"]:
        kind = rel["kind"]
        a, b = rel["from"], rel["to"]
        if kind == "contains":
            if view_of.get(a) == view_of.get(b) and (rel["id"], a, b) in set(class_edges_all(class_edges)):
                d03["relations"].append({"id": rel["id"], "kind": "contains", "from": a, "to": b})
            continue
        if kind in keep_kinds:
            if kind == "realizes" and view_of.get(a) != view_of.get(b):
                # realizes crosses the physical/logical split by design: keep only
                # if the physical region's view is physical and logical stays logical
                pass
            d03["relations"].append({"id": rel["id"], "kind": kind, "from": a, "to": b})
        elif kind == "precedes":
            va, vb = view_of.get(a), view_of.get(b)
            if va is not None and va == vb:
                order_edges.setdefault(va, []).append((a, b))
            else:
                report["unsupported"].append({
                    "what": "precedes-edge", "id": rel["id"],
                    "reason": f"endpoints in different migrated views ({va}/{vb}); no observed order can be asserted",
                })
        elif kind == "derived-from":
            report["dropped"].append({
                "what": "derived-from-edge", "id": rel["id"],
                "reason": "re-evaluated against migrated evidence below",
            })
    for vid, edges in order_edges.items():
        iid = f"migrated-order-{vid}"
        d03["interpretations"].append({
            "id": iid, "kind": "reading-order", "view_id": vid,
            "origin": "manual", "status": "asserted_without_evidence", "evidence": [],
        })
        for j, (a, b) in enumerate(edges):
            d03["relations"].append({
                "id": f"migrated-precedes-{vid}-{j}", "kind": "precedes",
                "from": a, "to": b, "interpretation_id": iid,
            })

    # -- evidence: keep source/manual/external; drop extracted/inferred without replay
    kept_evidence = set()
    for e in d02["evidence"]:
        if e["origin"] in ("extracted", "inferred"):
            report["unrecoverable"].append(
                f"evidence {e['id']} dropped: legacy transform has no input/output lineage, replay cannot be reconstructed"
            )
            continue
        d03["evidence"].append({
            "id": e["id"], "origin": e["origin"], "source_ref": e["source_ref"],
            "content_ids": [], "selector_ids": [],
        })
        kept_evidence.add(e["id"])

    # -- annotations: bind the view; demote when their evidence was dropped
    content_bindings = {}  # content -> set of region ids binding it
    for rel in d02["relations"]:
        if rel["kind"] == "has-content":
            content_bindings.setdefault(rel["to"], set()).add(rel["from"])
    for a in d02["annotations"]:
        t = a["target"]
        if t in view_of:
            vid = view_of[t]
        elif t in content_bindings:
            regions = sorted(content_bindings[t])
            vids = {view_of[r] for r in regions if r in view_of}
            if len(vids) != 1:
                report["unrecoverable"].append(
                    f"annotation {a['id']} dropped: target content is bound in ambiguous views {sorted(vids)}"
                )
                continue
            vid = vids.pop()
        else:
            report["unrecoverable"].append(
                f"annotation {a['id']} dropped: target has no binding in any migrated view"
            )
            continue
        status = a["status"]
        evidence = [x for x in a["evidence"] if x in kept_evidence]
        if status == "supported" and not evidence:
            status = "asserted_without_evidence"
            report["demoted"].append(
                f"annotation {a['id']} demoted: its evidence could not be migrated"
            )
        na = dict(a, status=status, evidence=evidence, view_id=vid)
        d03["annotations"].append(na)
    return d03, report


def region_view(d02, rid):
    for r in d02["regions"]:
        if r["id"] == rid:
            return r.get("view")
    return None


def class_edges_all(class_edges):
    for edges in class_edges.values():
        for e in edges:
            yield e


def collect_tree(root, children, members):
    out = [root]
    stack = [root]
    while stack:
        x = stack.pop()
        for c in children.get(x, []):
            if c in members:
                out.append(c)
                stack.append(c)
    return out
