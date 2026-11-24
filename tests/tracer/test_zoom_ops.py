# Purpose: Zoom operations over the scale ladder (add-scale-complete-regions
#   tasks 4.1, 4.2): composed restriction equals direct restriction (canonical
#   bytes); excluded edges recorded as coverage loss; lift attaches a claim at
#   the smallest containing scope and returns a typed ambiguity on equal
#   candidates, never a pick.
# Rationale: add-scale-complete-regions "Zoom in is restriction on the ladder"
#   and "Lift without guessing"; restriction reuses the scoped projection
#   semantics owned by dsc03.substrate.views.
from dsc03.canonical import reader_a
from dsc03.substrate.views import magazine_fixture
from dsc03.zoom import lift, restrict


def ladder_fixture():
    """A validated two-page ladder: r-doc -> pages -> blocks -> lines -> words,
    each line carrying one text content item so restrictions have edges to
    exclude. Region kind carries the ladder scale."""
    desc = magazine_fixture()
    desc["views"] = [{"id": "v-phys", "kind": "physical", "root": "r-doc"},
                     {"id": "v-log", "kind": "logical", "root": "r-log"}]
    desc["regions"] = [
        {"id": "r-doc", "view_id": "v-phys", "kind": "document"},
        {"id": "r-log", "view_id": "v-log", "kind": "article"},
        {"id": "p1", "view_id": "v-phys", "kind": "page"},
        {"id": "p2", "view_id": "v-phys", "kind": "page"},
        {"id": "b1", "view_id": "v-phys", "kind": "block"},
        {"id": "b2", "view_id": "v-phys", "kind": "block"},
        {"id": "b3", "view_id": "v-phys", "kind": "block"},
        {"id": "l1", "view_id": "v-phys", "kind": "line"},
        {"id": "l2", "view_id": "v-phys", "kind": "line"},
        {"id": "l3", "view_id": "v-phys", "kind": "line"},
        {"id": "l4", "view_id": "v-phys", "kind": "line"},
        {"id": "w1", "view_id": "v-phys", "kind": "word"},
        {"id": "w2", "view_id": "v-phys", "kind": "word"},
        {"id": "w3", "view_id": "v-phys", "kind": "word"},
        {"id": "w4", "view_id": "v-phys", "kind": "word"},
        {"id": "w5", "view_id": "v-phys", "kind": "word"},
    ]
    desc["contents"] = [{"id": f"c{i}", "kind": "text", "value": f"line {i}"}
                        for i in range(1, 5)]
    contains = [("r-doc", "p1"), ("r-doc", "p2"),
                ("p1", "b1"), ("p1", "b2"), ("p2", "b3"),
                ("b1", "l1"), ("b1", "l2"), ("b3", "l3"), ("b2", "l4"),
                ("l1", "w1"), ("l1", "w2"), ("l2", "w3"),
                ("l3", "w4"), ("l4", "w5")]
    has_content = [("l1", "c1"), ("l2", "c2"), ("l3", "c3"), ("l4", "c4")]
    desc["relations"] = (
        [{"id": f"rc{i}", "kind": "contains", "from": a, "to": b}
         for i, (a, b) in enumerate(contains)]
        + [{"id": f"rh{i}", "kind": "has-content", "from": a, "to": b}
           for i, (a, b) in enumerate(has_content)]
    )
    desc["evidence"] = [
        {"id": f"e{i}", "origin": "source", "source_ref": f"urn:sub:x#page:{i}",
         "content_ids": [f"c{i}"], "selector_ids": []} for i in range(1, 5)]
    return desc


def canonical_bytes(desc):
    return reader_a(desc)


def test_composed_restriction_equals_direct_restriction():
    desc = ladder_fixture()
    once = restrict(desc, "b1")
    assert once["status"] == "restricted"
    twice = restrict(once["descriptor"], "l1")
    direct = restrict(desc, "l1")
    assert twice["status"] == "restricted"
    assert canonical_bytes(twice["descriptor"]) == canonical_bytes(direct["descriptor"])


def test_composed_two_step_restriction_equals_direct_from_document():
    desc = ladder_fixture()
    step = restrict(restrict(desc, "p1")["descriptor"], "b2")
    direct = restrict(desc, "b2")
    assert canonical_bytes(step["descriptor"]) == canonical_bytes(direct["descriptor"])


def test_zoom_in_returns_exactly_scope_regions_and_internal_edges():
    desc = ladder_fixture()
    out = restrict(desc, "b1")
    ids = {r["id"] for r in out["descriptor"]["regions"]}
    # scope + descendants + the ancestor chain to the kept roots
    assert ids == {"r-doc", "p1", "b1", "l1", "l2", "w1", "w2", "w3", "r-log"}
    # nothing outside the scope survives
    assert "b2" not in ids and "w4" not in ids and "p2" not in ids and "l4" not in ids
    endpoints = {(r["from"], r["to"]) for r in out["descriptor"]["relations"]}
    region_and_content_ids = ids | {c["id"] for c in out["descriptor"]["contents"]}
    assert all(a in region_and_content_ids and b in region_and_content_ids
               for a, b in endpoints)


def test_excluded_edges_recorded_as_coverage_loss():
    desc = ladder_fixture()
    out = restrict(desc, "b1")
    # l3/l4 edges excluded by the restriction are reported as coverage loss,
    # never silently dropped.
    loss = out["coverage_loss"]
    assert loss, "expected coverage-loss entries"
    lost_features = {entry["feature"] for entry in loss}
    assert "has-content:rh2" in lost_features and "has-content:rh3" in lost_features
    # and the excluded relation list names the dropped edges
    excluded_ids = {e["id"] for e in out["excluded"]}
    assert "rh2" in excluded_ids and "rh3" in excluded_ids


def test_zoom_in_refuses_unknown_scope():
    out = restrict(ladder_fixture(), "nope")
    assert out["status"] == "refused"
    assert out["reason"] == "unknown-scope"


def test_lift_attaches_at_smallest_containing_scope():
    desc = ladder_fixture()
    # two words of one line lift to the line
    out = lift(desc, ["w1", "w2"])
    assert out["status"] == "lifted"
    assert out["scope"] == "l1" and out["scale"] == "line"
    # words of two lines in one block lift to the block
    out = lift(desc, ["w2", "w3"])
    assert out["status"] == "lifted"
    assert out["scope"] == "b1" and out["scale"] == "block"
    # words in different blocks of one page lift to the page
    out = lift(desc, ["w3", "w5"])
    assert out["status"] == "lifted"
    assert out["scope"] == "p1" and out["scale"] == "page"


def split_fixture():
    """Two disjoint physical trees (one per view) over the same ladder:
    w1 lives under page-root ra, w4 under page-root rb. No single scope
    contains both — several scopes qualify equally."""
    desc = ladder_fixture()
    desc["views"] = [
        {"id": "v-a", "kind": "physical", "root": "ra"},
        {"id": "v-b", "kind": "physical", "root": "rb"},
        {"id": "v-log", "kind": "logical", "root": "r-log"},
    ]
    desc["regions"] = [
        {"id": "ra", "view_id": "v-a", "kind": "page"},
        {"id": "rb", "view_id": "v-b", "kind": "page"},
        {"id": "r-log", "view_id": "v-log", "kind": "article"},
        {"id": "l1", "view_id": "v-a", "kind": "line"},
        {"id": "l2", "view_id": "v-b", "kind": "line"},
        {"id": "w1", "view_id": "v-a", "kind": "word"},
        {"id": "w4", "view_id": "v-b", "kind": "word"},
    ]
    desc["relations"] = [
        {"id": "ra1", "kind": "contains", "from": "ra", "to": "l1"},
        {"id": "ra2", "kind": "contains", "from": "l1", "to": "w1"},
        {"id": "rb1", "kind": "contains", "from": "rb", "to": "l2"},
        {"id": "rb2", "kind": "contains", "from": "l2", "to": "w4"},
        {"id": "rh1", "kind": "has-content", "from": "l1", "to": "c1"},
    ]
    desc["contents"] = [{"id": "c1", "kind": "text", "value": "line 1"}]
    desc["evidence"] = [{"id": "e1", "origin": "source",
                         "source_ref": "urn:sub:x#page:1",
                         "content_ids": ["c1"], "selector_ids": []}]
    desc["coverage"] = []
    return desc


def test_lift_returns_typed_ambiguity_on_equal_candidates():
    # w1 and w4 sit in disjoint trees whose page roots qualify equally at
    # the minimal scale: typed ambiguity with BOTH candidates, no pick.
    out = lift(split_fixture(), ["w1", "w4"])
    assert out["status"] == "ambiguous"
    assert out["reason"] == "equal-candidates"
    assert sorted(out["candidates"]) == ["ra", "rb"]
    assert "scope" not in out


def test_lift_refuses_unknown_or_disjoint_anchors():
    assert lift(ladder_fixture(), ["w1", "ghost"])["status"] == "refused"
    assert lift(ladder_fixture(), [])["status"] == "refused"
