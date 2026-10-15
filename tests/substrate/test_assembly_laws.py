# Purpose: Assembly-law fixtures for the document-assembly spec delta
#   (define-document-composition-semantics, sunset-905.1) — synthetic only.
# Responsibilities: Exercise the six named properties of the delta's
#   Properties table (compatible_pair, duplicate_conflict, left_right_identity,
#   associate_three, no_invented_order, shared_id_merges) plus two decision
#   backstops (same-source conflicting claims; namespace mismatch) against the
#   consumer-side assembly module dsc03/substrate/assembly.py. Every refusal is
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
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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


if __name__ == "__main__":
    unittest.main()
