# Purpose: The scale ladder and zoom operations for DSC 0.3
#   (add-scale-complete-regions tasks 2.1-2.3, 4.1-4.3).
# Responsibilities: Own the scale ladder word < line < block < page (owner
#   ruling sunset-gpd, 2026-11-24, gate G6) with checked containment (raw-text
#   interval containment exact; box containment within the tolerance declared
#   by the geometry profile, default 0.5 pt; violations refused with a witness
#   naming child and parent; sub-tolerance overhang accepted and recorded);
#   zoom_in — restriction to a scope reusing the scoped projection semantics
#   owned by dsc03.substrate.views (views owns general projection semantics;
#   zoom owns the ladder and operations), returning exactly the regions within
#   the scope and their internal edges with every excluded edge reported as
#   coverage loss; lift — attach a claim at the smallest containing scope,
#   returning a typed ambiguity when several scopes qualify equally, never a
#   pick. Block scale serves containment and statistics only and never enters
#   identity locator paths (sunset-gpd open owner flag, 2026-11-24).
# Rationale: add-scale-complete-regions design Decisions 1, 4, 5 and the
#   document-zoom spec delta.
"""Scale ladder: checked containment, zoom_in restriction, typed lift."""
from dsc03.substrate import views

# Innermost first (tasks 2.2 / owner ruling 2.3): word < line < block < page.
SCALE_ORDER = ("word", "line", "block", "page")
DOCUMENT_SCALE = "document"
DEFAULT_TOLERANCE_PT = 0.5
# views.project marks its coverage-loss entries with this adapter id; zoom_in
# lifts them out of the descriptor into its report so restriction composes.
PROJECTION_ADAPTER_ID = "substrate-project"


def geometry_tolerance(profile):
    """The box containment tolerance declared by a geometry profile.

    Defaults to 0.5 pt when the profile declares none; a declared tolerance
    must be a finite non-negative number (add-scale-complete-regions
    Decision 1)."""
    value = profile.get("tolerance", DEFAULT_TOLERANCE_PT)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError("invalid declared geometry tolerance")
    return float(value)


def _scale_index(scale):
    if scale == DOCUMENT_SCALE:
        return len(SCALE_ORDER)
    return SCALE_ORDER.index(scale)


def containment(child, parent, tolerance=DEFAULT_TOLERANCE_PT):
    """Checked containment of one ladder scope inside another.

    child/parent: {"id", "scale", "interval": (start, end), "box": [x0,y0,x1,y1]}.
    Raw-text interval containment is exact; box containment holds within
    `tolerance` on each edge. Returns:
      {"status": "refused", "reason", "witness"} for ladder-order violations
        and containment violations beyond tolerance (witness names child and
        parent);
      {"status": "accepted", "overhang": None | {child, parent, edges}} with
        sub-tolerance overhang recorded, never refused.
    """
    try:
        child_index, parent_index = _scale_index(child["scale"]), _scale_index(parent["scale"])
    except (KeyError, ValueError):
        return {"status": "refused", "reason": "unknown-scale",
                "witness": {"child": child.get("id"), "parent": parent.get("id")}}
    if child_index >= parent_index:
        return {"status": "refused", "reason": "invalid-ladder-order",
                "witness": {"child": child["id"], "parent": parent["id"],
                            "child_scale": child["scale"], "parent_scale": parent["scale"]}}
    child_start, child_end = child["interval"]
    parent_start, parent_end = parent["interval"]
    interval_outside = child_start < parent_start or child_end > parent_end
    child_box, parent_box = child["box"], parent["box"]
    # positive value = the child box overhangs that edge of the parent box
    edges = [parent_box[0] - child_box[0], parent_box[1] - child_box[1],
             child_box[2] - parent_box[2], child_box[3] - parent_box[3]]
    if interval_outside or any(edge > tolerance for edge in edges):
        return {"status": "refused", "reason": "scope-outside-parent",
                "witness": {"child": child["id"], "parent": parent["id"],
                            "interval_outside": interval_outside,
                            "box_overhang": edges, "tolerance": tolerance}}
    if any(edge > 0 for edge in edges):
        return {"status": "accepted", "overhang": {"child": child["id"],
                                                   "parent": parent["id"],
                                                   "edges": edges}}
    return {"status": "accepted", "overhang": None}


def ladder_report(region_of, contains, tolerance=None, geometry_profile=None):
    """Run containment over every ladder contains edge (parent, child).

    region_of: id -> {"id", "scale", "interval", "box"}; contains: iterable of
    (parent_id, child_id). tolerance defaults to the geometry profile's
    declared tolerance (or 0.5 pt). Edges whose parent is the document scope
    carry no box and are not checked. Returns {"status", "checked",
    "overhangs", "violations"} — accepted-with-overhang is recorded, never
    refused (Decision 1).
    """
    if tolerance is None:
        tolerance = (geometry_tolerance(geometry_profile)
                     if geometry_profile is not None else DEFAULT_TOLERANCE_PT)
    checked, overhangs, violations = 0, [], []
    for parent_id, child_id in contains:
        parent, child = region_of(parent_id), region_of(child_id)
        if parent is None or child is None:
            violations.append({"witness": {"child": child_id, "parent": parent_id,
                                           "reason": "missing-region"}})
            continue
        if _scale_index(parent["scale"]) == len(SCALE_ORDER):
            continue  # document scope: no geometry to contain against
        outcome = containment(child, parent, tolerance=tolerance)
        checked += 1
        if outcome["status"] == "refused":
            violations.append(outcome)
        elif outcome["overhang"] is not None:
            overhangs.append(outcome["overhang"])
    return {"status": "refused" if violations else "accepted",
            "checked": checked, "overhangs": overhangs, "violations": violations}


def _contains_children(desc):
    children = {}
    for rel in desc["relations"]:
        if rel["kind"] == "contains":
            children.setdefault(rel["from"], set()).add(rel["to"])
    return children


def _closure(desc, scope_id):
    """The scope region, its descendant closure and its ancestor chain up to
    the view root — the ancestor chain keeps every kept region at exactly one
    parent, so the restricted descriptor stays a valid containment tree."""
    children, parents = {}, {}
    for rel in desc["relations"]:
        if rel["kind"] == "contains":
            children.setdefault(rel["from"], set()).add(rel["to"])
            parents.setdefault(rel["to"], set()).add(rel["from"])
    keep = {scope_id}
    # ancestors: climb to the roots; descendants: walk down from the scope.
    frontier = [scope_id]
    while frontier:
        node = frontier.pop()
        for parent in parents.get(node, set()):
            if parent not in keep:
                keep.add(parent)
                frontier.append(parent)
    frontier = [scope_id]
    while frontier:
        node = frontier.pop()
        for child in children.get(node, set()):
            if child not in keep:
                keep.add(child)
                frontier.append(child)
    return keep


def restrict(desc, scope_id):
    """zoom_in: restriction of the descriptor to one ladder scope.

    Keeps exactly the scope region, its descendant closure and the declared
    view roots, with their internal edges — via the scoped projection owned
    by dsc03.substrate.views. Every edge the projection excludes is reported
    as coverage loss (projection coverage entries are lifted out of the
    returned descriptor into the report, so restriction composes: two
    restrictions equal one direct restriction to the inner scope, by
    canonical bytes). Returns a classified outcome, never an exception.
    """
    region_ids = {r["id"] for r in desc["regions"]}
    if scope_id not in region_ids:
        return {"status": "refused", "reason": "unknown-scope", "scope": scope_id}
    result = views.project(desc, _closure(desc, scope_id))
    if result["status"] != "projected":
        return {"status": "refused", "reason": result.get("rule", "projection-refused"),
                "reasons": result.get("reasons", [])}
    out = result["descriptor"]
    coverage_loss = [c for c in out["coverage"]
                     if c.get("adapter_id") == PROJECTION_ADAPTER_ID]
    out["coverage"] = [c for c in out["coverage"]
                       if c.get("adapter_id") != PROJECTION_ADAPTER_ID]
    # every excluded edge is recorded as coverage loss in the report —
    # never embedded in the descriptor, so restriction composes.
    coverage_loss += [{"feature": f"{e['kind']}:{e['id']}",
                       "scope": "document", "status": "omitted",
                       "reason": "excluded by zoom restriction",
                       "adapter_id": "substrate-zoom", "adapter_version": "1",
                       "config_sha256": "unavailable"}
                      for e in result["excluded"]]
    return {"status": "restricted", "scope": scope_id, "descriptor": out,
            "excluded": result["excluded"], "coverage_loss": coverage_loss}


# zoom_in is the operation name; restrict is the restriction law it applies.
zoom_in = restrict


def lift(desc, anchors):
    """Attach a claim at the smallest scope containing all its anchors.

    anchors: region ids on the ladder. The smallest containing scope is the
    minimal-scale common ancestor (anchors contained in themselves count).
    Several minimal candidates at the same scale are a typed ambiguity with
    every candidate named — never a pick (Decision 5).
    """
    region_by_id = {r["id"]: r for r in desc["regions"]}
    if not anchors or any(a not in region_by_id for a in anchors):
        return {"status": "refused", "reason": "unknown-anchor", "anchors": list(anchors)}
    parents = {}
    for rel in desc["relations"]:
        if rel["kind"] == "contains":
            parents.setdefault(rel["to"], set()).add(rel["from"])
    common = None
    for anchor in anchors:
        ancestors, frontier = set(), [anchor]
        while frontier:
            node = frontier.pop()
            if node in ancestors:
                continue
            ancestors.add(node)
            frontier.extend(parents.get(node, ()))
        common = ancestors if common is None else common & ancestors
    if not common:
        # Anchors in disjoint containment trees: no single scope contains
        # them all, so the claim attaches at no scope — each tree's topmost
        # scope qualifies equally and the ambiguity is typed, never picked.
        tops = set()
        for anchor in anchors:
            node = anchor
            while parents.get(node):
                node = sorted(parents[node])[0]
            tops.add(node)
        return {"status": "ambiguous", "reason": "equal-candidates",
                "candidates": sorted(tops)}
    best = min(_scale_index(region_by_id[r]["kind"]) for r in common)
    candidates = sorted(r for r in common
                        if _scale_index(region_by_id[r]["kind"]) == best)
    if len(candidates) > 1:
        return {"status": "ambiguous", "reason": "equal-candidates",
                "candidates": candidates}
    scope = candidates[0]
    return {"status": "lifted", "scope": scope,
            "scale": region_by_id[scope]["kind"]}
