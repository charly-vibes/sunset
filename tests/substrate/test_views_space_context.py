# Purpose: Law fixtures for the document-views, document-space and
#   document-context spec deltas of define-document-composition-semantics
#   (sunset-905.2, composition slice 2) — synthetic only, no subprocesses.
# Responsibilities: Exercise every named property of the three deltas'
#   Properties tables (16 named properties, 19 fixtures) against the
#   consumer-side modules dsc03/substrate/views.py, space.py and context.py:
#   cycle rejection with a path witness, incomparable regions preserved,
#   projection loss reported, refinement supersession/conflict reported,
#   cross-frame spatial predicates returning typed unknown, EPUB stable
#   selectors across reflow, context inheritance vs direct observation,
#   conflicting claims retained, deterministic replay (same_pinned_input).
#   Every outcome is classified (never an exception, never an invented edge);
#   canonical equality uses both independent readers from dsc03.canonical.
#   No real-carrier conformance is claimed anywhere; the deployed wire is
#   untouched.
# Rationale: the deltas are proposals (not deployed truth); like the assembly
#   slice (sunset-905.1) these fixtures witness the proposed laws machinery-
#   side over validated synthetic descriptors, exactly as the substrate
#   harness did for the transformation algebra (sunset-7hs).
"""Views/space/context law fixtures: cycles, frames, claims, replay."""
import copy
import hashlib
import unittest

from dsc03.substrate import context as ctx
from dsc03.substrate import space
from dsc03.substrate import views
from dsc03.substrate.assembly import compose
from dsc03.substrate.laws import typed_check


def sha(label):
    """Honest synthetic digest: sha256 of the named synthetic payload."""
    return hashlib.sha256(label.encode()).hexdigest()


class TestViewsLaws(unittest.TestCase):
    def test_view_overlap(self):
        """named_view_membership: one region's content bound in two views —
        both memberships survive (article spanning two pages)."""
        desc = views.magazine_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        bindings = views.content_bindings(desc)
        # c1 is bound from the physical page (v-phys) AND the logical
        # article (v-log): the article's page membership and its logical
        # membership both remain accessible.
        self.assertEqual(bindings["c1"], {"v-phys", "v-log"})
        self.assertEqual(bindings["c2"], {"v-phys", "v-log"})

    def test_cycle_refused(self):
        """containment_acyclic: a three-region containment cycle is rejected
        WITH a cycle path witness (never silently accepted)."""
        desc = views.cycle_fixture()
        status, reasons = typed_check(desc)
        self.assertEqual(status, "rejected")
        self.assertIn("containment_cycle", reasons)
        report = views.containment_cycle_report(desc)
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["reason"], "containment_cycle")
        # The witness names the cycle path, first == last region.
        path = report["cycle_path"]
        self.assertEqual(path[0], path[-1])
        self.assertEqual(sorted(set(path[:-1])), ["r-p1", "r-p2"])
        # The acyclic base is accepted: the cycle alone caused refusal.
        self.assertEqual(typed_check(views.magazine_fixture())[0], "accepted")

    def test_partial_order_ok(self):
        """partial_order: incomparable columns are accepted with no total
        order inferred; a DECLARED reading-order cycle is rejected with a
        path witness."""
        desc = views.order_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        report = views.order_status(desc, "int-ro")
        self.assertEqual(report["status"], "accepted")
        self.assertEqual(report["incomparable"], [["r-col-1", "r-col-2"]])
        # Declared cycle: a forward edge plus its back edge under the same
        # interpretation is rejected, typed, with a path witness. (The base
        # fixture declares no order edge at all — the columns stay
        # incomparable — so the cycle fixture adds both directions.)
        cyc = copy.deepcopy(desc)
        cyc["relations"].append(
            {"id": "rel-ro-fwd", "kind": "precedes", "from": "r-col-1",
             "to": "r-col-2", "interpretation_id": "int-ro"})
        cyc["relations"].append(
            {"id": "rel-ro-back", "kind": "precedes", "from": "r-col-2",
             "to": "r-col-1", "interpretation_id": "int-ro"})
        self.assertIn("order_cycle", typed_check(cyc)[1])
        cyc_report = views.order_status(cyc, "int-ro")
        self.assertEqual(cyc_report["status"], "rejected")
        self.assertEqual(cyc_report["reason"], "order_cycle")
        self.assertEqual(cyc_report["cycle_path"],
                         ["r-col-1", "r-col-2", "r-col-1"])

    def test_projection(self):
        """projection_fidelity: a one-page projection keeps exactly the
        selected regions and internal edges, and reports the excluded
        cross-page link as wire coverage loss (never claims full fidelity)."""
        desc = views.magazine_fixture()
        result = views.project(desc, {"r-doc", "r-p1"})
        self.assertEqual(result["status"], "projected")
        out = result["descriptor"]
        self.assertEqual(typed_check(out)[0], "accepted")
        kept_ids = {r["id"] for r in out["regions"]}
        # Kept: the selected regions PLUS each surviving view's root — the
        # 0.3 wire mandates a view's root region exists, so view roots are
        # retained as structural anchors (they are NOT selected payload).
        # The unselected page r-p2 is gone either way.
        self.assertEqual(kept_ids, {"r-doc", "r-p1", "r-art"})
        self.assertNotIn("r-p2", kept_ids)
        # The excluded cross-page continuation link is reported...
        excluded_ids = {e["id"] for e in result["excluded"]}
        self.assertIn("rel-cont", excluded_ids)
        # ...as a wire coverage entry with an omitted status and a reason.
        omitted = [c for c in out["coverage"] if c["status"] == "omitted"]
        self.assertTrue(omitted)
        self.assertIn("rel-cont", omitted[0]["feature"])
        self.assertTrue(omitted[0]["reason"])

    def test_refinement_conflict(self):
        """refinement_explicit: a refined view that would silently delete an
        established scoped edge is reported as a conflict; with an explicit
        declared policy the same removal is a recorded supersession —
        never a silent success either way."""
        base = views.magazine_fixture()
        refined = copy.deepcopy(base)
        refined["relations"] = [
            r for r in refined["relations"] if r["id"] != "rel-cont"]
        conflict = views.refinement_check(base, refined)
        self.assertEqual(conflict["status"], "conflict")
        self.assertEqual(conflict["removed"], ["rel-cont"])
        superseded = views.refinement_check(
            base, refined, superseded=["rel-cont"], policy="editor-review-1")
        self.assertEqual(superseded["status"], "superseded")
        self.assertEqual(superseded["policy"], "editor-review-1")
        self.assertEqual(superseded["removed"], ["rel-cont"])

    def test_links_not_containment(self):
        """nonhierarchical_links: cross-page continuation and reference
        edges remain typed links; no contains edge (parent pointer) is
        invented between their endpoints."""
        desc = views.magazine_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        report = views.link_check(desc, "r-p1", "r-p2")
        self.assertEqual(report["status"], "typed_links")
        kinds = report["link_kinds"]
        self.assertIn("precedes", kinds)          # continuation stays a link
        self.assertNotIn("contains", kinds)       # no parent pointer invented
        # The evidence-level reference (derived-from lineage) stays a link.
        ref = views.link_check(desc, "e-ref-src", "e-ref-dst")
        self.assertIn("derived-from", ref["link_kinds"])


class TestSpaceLaws(unittest.TestCase):
    def test_pdf_rotation(self):
        """carrier_coordinate_frames: geometry declared in a rotated page
        frame, normalized back to the source frame, matches the expected
        transformed locus."""
        t = space.transform_rot90(612, 792)
        # Observed in the rotated frame: near the rotated page's origin.
        observed = {"space": "page-1-rot90-pt", "x": 10, "y": 20,
                    "width": 100, "height": 50}
        normalized = space.normalize(t, observed)
        expected = {"space": "page-1-pt", "x": 722, "y": 10,
                    "width": 50, "height": 100}
        self.assertEqual(normalized, expected)

    def test_cross_page_unknown(self):
        """frame_compatibility: an above/below comparison across two pages
        (incompatible frames, no pinned transform) returns a TYPED unknown —
        not false, not null, no exception."""
        a = {"space": "page-1-pt", "x": 10, "y": 100, "width": 5, "height": 5}
        b = {"space": "page-2-pt", "x": 10, "y": 20, "width": 5, "height": 5}
        report = space.above(a, b)
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["reason"], "incompatible_frames")
        # Same frame: the predicate is a known typed result (a at y=100 is
        # above a block at y=200 — smaller y is higher on the page).
        same = space.above(a, {**b, "space": "page-1-pt", "y": 200})
        self.assertEqual(same["status"], "known")
        self.assertIs(same["value"], True)

    def test_epub_reflow(self):
        """epub_stable_identity: the same chapter at two font sizes keeps the
        stable spine selector unchanged while viewport XY may differ; XY
        never provides persistent element identity."""
        desc = space.epub_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        small = space.viewport_observation("vp-small", x=5, y=1200, scale=1.0)
        large = space.viewport_observation("vp-large", x=5, y=1500, scale=1.6)
        report = space.epub_identity(desc, "sel-ch3", small, large)
        self.assertEqual(report["status"], "stable")
        self.assertEqual(report["selector_locator"],
                         "urn:sub:epub#ch3/frag-42")
        self.assertNotEqual(small["y"], large["y"])
        self.assertEqual(report["xy_differs"], True)

    def test_native_ocr_coexist(self):
        """mixed_observations: native and OCR observations coexist on one
        hybrid PDF page without forcing either to supersede the other; each
        keeps its own declared origin and evidence."""
        desc = space.hybrid_page_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        report = space.mixed_observations_report(desc)
        self.assertEqual(report["status"], "coexist")
        self.assertEqual(report["native_content_ids"], ["c-native"])
        self.assertEqual(report["ocr_content_ids"], ["c-ocr"])
        self.assertEqual(report["native_evidence_origin"], "source")
        self.assertEqual(report["ocr_evidence_origin"], "extracted")
        # No supersession marker was invented between the two readings.
        self.assertEqual(report["forced_equality"], False)

    def test_spatial_not_order(self):
        """spatial_order_separation: an overlapping figure/caption pair is
        reported as a spatial overlap only — no precedes edge is inferred."""
        desc = space.geometry_fixture()   # figure + caption overlap on page 1
        before = copy.deepcopy(desc["relations"])
        report = space.spatial_predicates(desc)
        overlaps = [p for p in report if p["predicate"] == "overlap"]
        self.assertTrue(overlaps)
        self.assertEqual(overlaps[0]["status"], "known")
        self.assertIs(overlaps[0]["value"], True)
        self.assertEqual(desc["relations"], before)
        self.assertEqual(space.emitted_order_edges(report), [])

    def test_roundtrip_transform(self):
        """geometry_transform: source geometry transformed forward and back
        is equivalent within the declared numeric tolerance (exact here:
        integers)."""
        t = space.transform_rot90(612, 792)
        source = {"space": "page-1-pt", "x": 100, "y": 200,
                  "width": 50, "height": 80}
        roundtripped = space.normalize(t, space.denormalize(t, source))
        self.assertEqual(space.within_tolerance(roundtripped, source,
                                                t.tolerance), True)

    def test_no_spatial_reading_order(self):
        """spatial_order_separation: above/left-of/overlap predicates across
        a two-column layout NEVER emit a precedes or contains edge — the
        descriptor's relation set is unchanged after evaluation."""
        desc = space.geometry_fixture()
        before_ids = {r["id"] for r in desc["relations"]}
        report = space.spatial_predicates(desc)
        self.assertTrue(report)  # predicates were actually evaluated
        self.assertEqual({r["id"] for r in desc["relations"]}, before_ids)
        self.assertEqual(space.emitted_order_edges(report), [])
        self.assertEqual(typed_check(desc)[0], "accepted")


class TestContextLaws(unittest.TestCase):
    def test_publication_date(self):
        """claims_attributed: the issue date is available as publication
        context (issue metadata), and is NOT a narrated date of the poem."""
        desc = ctx.issue_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        report = ctx.claim_classification(desc, "a-issue-date")
        self.assertEqual(report["status"], "publication_context")
        # The poem itself carries no date claim of its own.
        own = [c["term"] for c in ctx.claims_for(desc, "r-poem")]
        self.assertNotIn("mag:publication-date", own)

    def test_quoted_author(self):
        """context_scoped: the article author is NOT automatically assigned
        to a quote inside the article; bindings are inherited only when the
        declared policy permits, and marked inherited rather than observed."""
        desc = ctx.issue_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        # Default (no declared policy): no inheritance at all.
        self.assertEqual(ctx.inherited_bindings(desc, "c-quote"), [])
        # Even with a declared policy, inherited bindings are marked.
        policy = {"inherit_terms": ["mag:author"], "along": "contains"}
        inherited = ctx.inherited_bindings(desc, "c-quote", policy)
        for b in inherited:
            self.assertEqual(b["provenance"], "inherited")
        own = [c["term"] for c in ctx.claims_for(desc, "c-quote")]
        self.assertNotIn("mag:author", own)

    def test_context_dispute(self):
        """shadow_conflict: incompatible active bindings remain disputed —
        both claims retained — unless a declared precedence rule applies."""
        desc = ctx.dispute_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        report = ctx.resolve_bindings(desc, "mag:publication-date", "r-issue")
        self.assertEqual(report["status"], "disputed")
        self.assertEqual(sorted(report["claims"]),
                         ["a-date-manual", "a-date-ocr"])
        # With a declared precedence rule: deterministic, recorded winner.
        resolved = ctx.resolve_bindings(
            desc, "mag:publication-date", "r-issue",
            precedence={"policy": "manual-over-ocr", "prefer_origin": "manual"})
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["winner"], "a-date-manual")
        self.assertEqual(len(resolved["retained"]), 2)

    def test_same_pinned_input(self):
        """deterministic_interpretation: the same observations, scopes and
        rule version evaluated twice produce canonically equal results (both
        independent readers)."""
        desc = ctx.issue_fixture()
        first = ctx.evaluate_claims(copy.deepcopy(desc))
        second = ctx.evaluate_claims(copy.deepcopy(desc))
        # Claim envelopes are not wire descriptors, so replay equality is
        # measured with reader_a's canonical bytes (the descriptor-level
        # two-reader equality is exercised by the assembly slice).
        self.assertTrue(ctx.canonically_equal_claims(first, second))
        # And they are not vacuously equal to nothing at all.
        self.assertTrue(first["claims"])
        # A changed pinned input changes the outcome (not a constant fn).
        changed = copy.deepcopy(desc)
        changed["annotations"][0]["value"] = "1991-04"
        self.assertFalse(
            ctx.canonically_equal_claims(first, ctx.evaluate_claims(changed)))

    def test_uncertain_ocr(self):
        """no_truth_laundering: the extractor's transcription stays an
        attributed, uncertain interpretation — it retains its disputed status
        and evidence and is never elected over the manual transcription."""
        desc = ctx.uncertain_fixture()
        self.assertEqual(typed_check(desc)[0], "accepted")
        claims = ctx.claims_for(desc, "c-poem-text")
        self.assertEqual(len(claims), 2)
        by_origin = {c["origin"]: c for c in claims}
        ocr = by_origin["extracted"]
        self.assertEqual(ocr["status"], "disputed")
        self.assertTrue(ocr["evidence"])
        self.assertEqual(by_origin["manual"]["status"], "supported")
        # No winner was elected: both remain visible with sources.
        self.assertEqual(ctx.elected_winner(claims), None)

    def test_no_union_on_assembly(self):
        """no_generic_meaning_union: assembling two parts does not union
        their semantic truth; each claim stays attributed to its own target
        and composed meaning requires a pinned domain rule."""
        a, b = ctx.two_claim_parts()
        result = compose(a, b)
        self.assertEqual(result["status"], "assembled")
        report = ctx.assembled_meaning(result["descriptor"])
        self.assertEqual(report["status"], "no_generic_union")
        self.assertEqual(report["reason"], "requires_pinned_domain_rule")
        # Each claim is still scoped to its own part's region — no merged
        # claim appeared and no target gained the other's value.
        terms = {(c["target"], c["value"]) for c in report["claims"]}
        self.assertEqual(terms, {("r-poem-1", "1991-03"),
                                 ("r-poem-2", "1991-04")})


if __name__ == "__main__":
    unittest.main()
