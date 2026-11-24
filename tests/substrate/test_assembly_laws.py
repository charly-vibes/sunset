# Purpose: Assembly-law fixtures for the document-assembly spec delta
#   (define-document-composition-semantics, sunset-905.1) — synthetic only.
# Responsibilities: Exercise the six named properties of the delta's
#   Properties table (compatible_pair, duplicate_conflict, left_right_identity,
#   associate_three, no_invented_order, shared_id_merges) plus two decision
#   backstops (same-source conflicting claims; namespace mismatch) against the
#   consumer-side assembly module dsc03/substrate/assembly.py, and the
#   identity-profile ordering regime (add-anchor-derived-identity 5.3): under
#   declared identity profiles compose(a,b) and compose(b,a) are canonically
#   equal (ascending id order); without the profile the label-id left-first
#   order is kept byte-identical. Every refusal is
#   classified and structured (never a crash); canonical equality is measured
#   with both independent readers from dsc03.canonical. No real-carrier
#   conformance is claimed anywhere.
# Rationale: the deployed kernel has no composition checker (mapping.md law 5
#   is partial); these fixtures witness the proposed assembly laws
#   machinery-side over validated synthetic parts, exactly as the substrate
#   harness did for the transformation algebra (sunset-7hs).
"""Assembly law fixtures: identity, associativity, refusal, merge, order."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import identity
from dsc03.substrate.assembly import canonically_equal, compose, empty_part
from dsc03.substrate.laws import typed_check

# Synthetic carrier digests: two distinct "editions" for conflict fixtures.
SHA_EDITION_A = hashlib.sha256(b"magazine-edition-a").hexdigest()
SHA_EDITION_B = hashlib.sha256(b"magazine-edition-b").hexdigest()
CARRIER = "urn:sub:magazine"


def _part(page, art, text, sha=SHA_EDITION_A):
    """A self-contained magazine part: shared issue root + one article."""
    return {
        "version": "0.3",
        "id": f"part-{art}",
        "source": {"format": "application/pdf", "sha256": sha,
                   "locator": CARRIER},
        "views": [{"id": "v-log", "kind": "logical", "root": "r-issue"}],
        "regions": [
            {"id": "r-issue", "view_id": "v-log", "kind": "issue"},
            {"id": art, "view_id": "v-log", "kind": "article"},
        ],
        "contents": [{"id": f"c-{art}", "kind": "text", "value": text}],
        "relations": [
            {"id": f"rel-c-{art}", "kind": "contains", "from": "r-issue",
             "to": art},
            {"id": f"rel-hc-{art}", "kind": "has-content", "from": art,
             "to": f"c-{art}"},
        ],
        "annotations": [],
        "evidence": [{
            "id": f"e-{art}", "origin": "source",
            "source_ref": f"{CARRIER}#page:{page}",
            "content_ids": [f"c-{art}"], "selector_ids": [],
        }],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [], "interpretations": [], "coverage": [], "profiles": [],
    }


def _continued(part, from_art, to_art):
    """Part carrying a DECLARED continuation edge into another part's region.

    The edge is a declared binding, not an invented one: it only becomes
    resolvable once the target part is assembled (design §2 — parts are
    partial; references resolve against the union).
    """
    out = copy.deepcopy(part)
    out["interpretations"] = [{
        "id": "int-ro", "kind": "reading-order", "view_id": "v-log",
        "origin": "inferred", "status": "asserted_without_evidence",
        "evidence": [],
    }]
    out["relations"].append({
        "id": "rel-continuation", "kind": "precedes", "from": from_art,
        "to": to_art, "interpretation_id": "int-ro",
    })
    return out


def _assembled(result):
    return result["descriptor"] if result["status"] == "assembled" else None


def _edge_set(desc):
    return frozenset((r["id"], r["kind"], r["from"], r["to"])
                     for r in desc["relations"])


class TestAssemblyLaws(unittest.TestCase):
    def test_left_right_identity(self):
        """assembly_identity: canonical(compose(A,empty)) == canonical(A)
        == canonical(compose(empty,A)) — up to canonical representation."""
        a = _part(1, "r-art-1", "column one")
        right = compose(a, empty_part())
        left = compose(empty_part(), a)
        self.assertEqual(right["status"], "assembled")
        self.assertEqual(left["status"], "assembled")
        self.assertTrue(canonically_equal(_assembled(right), a))
        self.assertTrue(canonically_equal(_assembled(left), a))

    def test_associate_three(self):
        """assembly_associative: jointly compatible triple, grouping-
        independent constraints → both bracketings canonically equal."""
        a = _continued(_part(1, "r-art-1", "column one"), "r-art-1", "r-art-2")
        b = _part(2, "r-art-2", "column two")
        c = _part(3, "r-art-3", "column three")
        left_assoc = compose(compose(a, b), c)
        right_assoc = compose(a, compose(b, c))
        self.assertEqual(left_assoc["status"], "assembled")
        self.assertEqual(right_assoc["status"], "assembled")
        self.assertEqual(
            typed_check(_assembled(left_assoc))[0], "accepted")
        self.assertEqual(
            typed_check(_assembled(right_assoc))[0], "accepted")
        self.assertTrue(canonically_equal(_assembled(left_assoc),
                                          _assembled(right_assoc)))

    def test_compatible_pair(self):
        """compatible_pair: compose succeeds, preserves nodes and edges."""
        a = _continued(_part(1, "r-art-1", "column one"), "r-art-1", "r-art-2")
        b = _part(2, "r-art-2", "column two")
        result = compose(a, b)
        self.assertEqual(result["status"], "assembled")
        merged = _assembled(result)
        self.assertEqual(typed_check(merged)[0], "accepted")
        node_ids = {r["id"] for r in merged["regions"]}
        self.assertEqual(node_ids, {"r-issue", "r-art-1", "r-art-2"})
        expected_edges = _edge_set(a) | _edge_set(b)
        self.assertEqual(_edge_set(merged), expected_edges)
        # the declared continuation is retained verbatim, never renamed
        self.assertIn(("rel-continuation", "precedes", "r-art-1", "r-art-2"),
                      _edge_set(merged))

    def test_no_invented_order(self):
        """order_not_implicit: unrelated regions gain NO precedes edge (and
        no edge at all beyond the operands' own declared edges)."""
        a = _part(1, "r-art-1", "column one")
        b = _part(2, "r-art-2", "column two")  # no continuation declared
        result = compose(a, b)
        self.assertEqual(result["status"], "assembled")
        merged = _assembled(result)
        precedes = [r for r in merged["relations"] if r["kind"] == "precedes"]
        self.assertEqual(precedes, [])
        self.assertEqual(_edge_set(merged), _edge_set(a) | _edge_set(b))

    def test_shared_id_merges(self):
        """boundaries_preserved: a shared region ID under identical claims
        composes into a single identity retaining original edges and
        provenance."""
        a = _part(1, "r-art-1", "column one")
        b = _part(2, "r-art-2", "column two")  # shares r-issue, page differs
        result = compose(a, b)
        self.assertEqual(result["status"], "assembled")
        merged = _assembled(result)
        self.assertEqual(typed_check(merged)[0], "accepted")
        issue_regions = [r for r in merged["regions"] if r["id"] == "r-issue"]
        self.assertEqual(len(issue_regions), 1)  # single source identity
        # original per-part edges and provenance both retained
        self.assertEqual(_edge_set(merged), _edge_set(a) | _edge_set(b))
        evidence_ids = {e["id"] for e in merged["evidence"]}
        self.assertEqual(evidence_ids, {"e-r-art-1", "e-r-art-2"})
        page_refs = sorted(e["source_ref"] for e in merged["evidence"])
        self.assertEqual(page_refs, [f"{CARRIER}#page:1", f"{CARRIER}#page:2"])

    def test_duplicate_conflict(self):
        """assembly_compatible: same ID under conflicting intrinsic source →
        structured refusal with the smallest known witness, no crash."""
        a = _part(1, "r-art-1", "column one")
        b = _part(2, "r-art-1", "counterfeit column", sha=SHA_EDITION_B)
        result = compose(a, b)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["rule"], "same_id_conflicting_source")
        self.assertIn("r-art-1", result["smallest"])

    def test_same_source_conflicting_claims_refused(self):
        """assembly_compatible backstop: same ID, same source, conflicting
        intrinsic claims → refusal, never a silent merge or rename."""
        a = _part(1, "r-art-1", "column one")
        b = copy.deepcopy(a)
        b["regions"][1]["kind"] = "table"  # same id, conflicting claims
        result = compose(a, b)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["rule"], "same_id_conflicting_claims")
        self.assertIn("r-art-1", result["smallest"])

    def test_namespace_mismatch_refused(self):
        """assembly_compatible backstop: aligned namespace is required — the
        same vocabulary namespace under different versions refuses."""
        a = _part(1, "r-art-1", "column one")
        b = _part(2, "r-art-2", "column two")
        b["vocabularies"] = [{"namespace": "mag", "version": "2"}]
        result = compose(a, b)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["rule"], "namespace_mismatch")
        self.assertIn("mag", result["smallest"])

    def test_source_mismatch_disjoint_ids_refused(self):
        """assembly_compatible backstop: two parts from different carriers
        with disjoint ids cannot compose on this wire (one source record per
        descriptor; cross-carrier identity has no deployed entity)."""
        a = _part(1, "r-art-1", "column one", sha=SHA_EDITION_A)
        b = {
            "version": "0.3",
            "id": "part-other",
            "source": {"format": "application/pdf", "sha256": SHA_EDITION_B,
                       "locator": "urn:sub:other-magazine"},
            "views": [{"id": "v-log-b", "kind": "logical", "root": "r-issue-b"}],
            "regions": [{"id": "r-issue-b", "view_id": "v-log-b",
                         "kind": "issue"}],
            "contents": [], "relations": [], "annotations": [],
            "evidence": [], "vocabularies": [{"namespace": "mag", "version": "1"}],
            "selectors": [], "interpretations": [], "coverage": [],
            "profiles": [],
        }
        result = compose(a, b)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["rule"], "source_mismatch")


# -- identity-profile ordering regime (add-anchor-derived-identity 5.3) -------------

IDENTITY_PROFILE_ID = "p-id"


def _identity_decl():
    """The pinned identity profile declaration (same artifact bytes as
    tests/tracer/test_identity.py resolves at profiles/identity-v1.json)."""
    artifact = {"kind": "identity", "version": "1",
                "digest": {"algorithm": "sha256", "truncation_bits": 128, "prefix": "a:"}}
    return {
        "id": IDENTITY_PROFILE_ID, "kind": "identity",
        "uri": "profiles/identity-v1.json", "version": "1",
        "sha256": hashlib.sha256(
            json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def _anchored(rec_kind, locator, **fields):
    """A record whose id derives from its declared anchor under (p-id, "1")."""
    source = fields.get("source_sha256", SHA_EDITION_A)
    rec = dict(fields)
    rec["anchor"] = {"record_kind": rec_kind, "locator_path": locator}
    rec["id"] = identity.derive_id((source, rec_kind, locator, IDENTITY_PROFILE_ID, "1"))[1]
    return rec


def _id_part(page, art, text):
    """An identity-profile part: shared issue root + one anchored article.

    Mirrors _part()'s shape, but every region/content/evidence record is
    anchored and derives its id; the issue root carries the same anchor in
    every part, so its derived id is the shared assembly identity.
    """
    shared = _anchored("region", f"{CARRIER}#issue", view_id="v-log", kind="issue")
    region = _anchored("region", f"page:{page}", view_id="v-log", kind="article")
    content = _anchored("content", f"raw:[{page}00,{page}05)", kind="text", value=text)
    evidence = _anchored("evidence", f"{CARRIER}#page:{page}", origin="source",
                         source_ref=f"{CARRIER}#page:{page}",
                         content_ids=[content["id"]], selector_ids=[])
    return {
        "version": "0.3",
        "id": f"part-id-{art}",
        "source": {"format": "application/pdf", "sha256": SHA_EDITION_A,
                   "locator": CARRIER},
        "views": [{"id": "v-log", "kind": "logical", "root": shared["id"]}],
        "regions": [shared, region],
        "contents": [content],
        "relations": [
            {"id": f"rel-c-{art}", "kind": "contains", "from": shared["id"],
             "to": region["id"]},
            {"id": f"rel-hc-{art}", "kind": "has-content", "from": region["id"],
             "to": content["id"]},
        ],
        "annotations": [],
        "evidence": [evidence],
        "vocabularies": [{"namespace": "mag", "version": "1"}],
        "selectors": [], "interpretations": [], "coverage": [],
        "profiles": [_identity_decl()],
    }


class TestCanonicalOrderUnderIdentityProfile(unittest.TestCase):
    def test_compose_is_commutative_under_identity_profile(self):
        """Under declared identity profiles in BOTH operands, merged
        set-like sections emit ascending by id, so compose(a,b) and
        compose(b,a) are canonically equal (both independent readers)."""
        a = _id_part(1, "essay", "first column")
        b = _id_part(2, "poem", "second column")
        self.assertEqual(typed_check(a)[0], "accepted")  # fixture soundness
        self.assertEqual(typed_check(b)[0], "accepted")
        ab, ba = compose(a, b), compose(b, a)
        self.assertEqual(ab["status"], "assembled")
        self.assertEqual(ba["status"], "assembled")
        merged_ab, merged_ba = _assembled(ab), _assembled(ba)
        self.assertEqual(typed_check(merged_ab)[0], "accepted")
        self.assertTrue(canonically_equal(merged_ab, merged_ba))
        # the emission order is the ascending-id order, per section
        for section in ("views", "regions", "contents", "relations",
                        "annotations", "evidence", "selectors",
                        "interpretations", "profiles"):
            ids = [item["id"] for item in merged_ab[section]]
            self.assertEqual(ids, sorted(ids), section)
        self.assertEqual([item["id"] for item in merged_ab["regions"]],
                         [item["id"] for item in merged_ba["regions"]])

    def test_label_id_pair_keeps_left_first_order(self):
        """Hard constraint: without the profile, today's left-operand-first
        behavior is byte-identical — operand order stays observable."""
        a = _part(1, "r-art-1", "column one")
        b = _part(2, "r-art-2", "column two")
        ab = _assembled(compose(a, b))
        ba = _assembled(compose(b, a))
        self.assertEqual([r["id"] for r in ab["regions"]],
                         ["r-issue", "r-art-1", "r-art-2"])  # left's items first
        self.assertEqual([r["id"] for r in ba["regions"]],
                         ["r-issue", "r-art-2", "r-art-1"])
        self.assertFalse(canonically_equal(ab, ba))


if __name__ == "__main__":
    unittest.main()
