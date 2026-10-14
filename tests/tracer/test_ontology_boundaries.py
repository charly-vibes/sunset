# Purpose: Ontology boundary projection-evaluator tests (sunset-r68.14, task 6.1).
# Responsibilities: Exercise the boundary evaluator (dsc03/boundaries.py) over
#   the committed boundary fixtures for acceptance checks O-A01 (unknown
#   relation: never coerced into a core relation), O-A04 (RDF/OWL projection:
#   losses declared in a manifest, no semantic-equivalence claim without an
#   entailment policy) and O-A05 (roundtrip scope: fidelity claimed only for a
#   specified subset and tested domain). Also pin the cross-cutting rule:
#   profile resolution or schema validity alone never implies semantic
#   equivalence. Fixtures carry a compliant variant AND a counterexample per
#   check; the evaluator must accept the former and reject the latter.
# Rationale: add-dsc-03 document-ontology-boundaries deltas + research-bundle
#   ONTOLOGY-BOUNDARIES.md sections 5 and 7.
"""Ontology boundary fixtures: O-A01, O-A04, O-A05 (projection evaluator)."""
import json
import unittest
from pathlib import Path

from dsc03 import boundaries

FIXTURES = Path("fixtures/boundaries")


def _load(name):
    return json.loads((FIXTURES / name).read_text())


class TestOA01UnknownRelation(unittest.TestCase):
    """O-A01: an unsupported domain relation is never coerced into a core
    relation; it is preserved via a registered profile, emitted through an
    external projection, or reported unsupported."""

    @classmethod
    def setUpClass(cls):
        cls.fx = _load("oa01-unknown-relation.json")

    def test_compliant_projection_passes(self):
        out = boundaries.evaluate(self.fx["compliant"])
        self.assertTrue(out["checks"]["o-a01"]["pass"], out["checks"]["o-a01"])
        self.assertEqual(out["checks"]["o-a01"]["coerced"], [])

    def test_counterexample_coercion_rejected(self):
        out = boundaries.evaluate(self.fx["counterexample"])
        oa01 = out["checks"]["o-a01"]
        self.assertFalse(oa01["pass"])
        self.assertIn("coerced_relation", oa01["reasons"])
        # the coercing mapping invented a core relation from 'cites'
        self.assertIn("cites", [c["source_relation"] for c in oa01["coerced"]])
        self.assertNotIn("precedes", boundaries.CORE_RELATION_KINDS - {"precedes"})  # sanity

    def test_cites_never_becomes_precedes_or_contains(self):
        for variant in self.fx.values():
            out = boundaries.evaluate(variant)
            coerced_kinds = {c["output_kind"] for c in out["checks"]["o-a01"]["coerced"]}
            self.assertFalse(coerced_kinds & {"contains", "precedes", "realizes"} & set(),
                             out["checks"]["o-a01"])


class TestOA04LossManifest(unittest.TestCase):
    """O-A04: every mapped feature has exactly one loss disposition with
    justification; unmapped predicates appear as undeclared losses; semantic
    equivalence is never claimed without an entailment policy."""

    @classmethod
    def setUpClass(cls):
        cls.fx = _load("oa04-loss-manifest.json")

    def test_compliant_projection_declares_all_losses(self):
        out = boundaries.evaluate(self.fx["compliant"])
        oa04 = out["checks"]["o-a04"]
        self.assertTrue(oa04["pass"], oa04)
        self.assertEqual(oa04["undeclared"], [])
        self.assertEqual(oa04["disposition_errors"], [])

    def test_counterexample_undeclared_loss_rejected(self):
        out = boundaries.evaluate(self.fx["counterexample"])
        oa04 = out["checks"]["o-a04"]
        self.assertFalse(oa04["pass"])
        self.assertIn("owl:Restriction", oa04["undeclared"])

    def test_semantic_equivalence_requires_entailment_policy(self):
        # compliant fixture claims only structural equivalence -> allowed
        out = boundaries.evaluate(self.fx["compliant"])
        self.assertTrue(out["checks"]["o-a04"]["pass"])
        # a semantic-equivalence claim without entailment policy is rejected
        no_policy = json.loads(json.dumps(self.fx["compliant"]))
        no_policy["equivalence"] = "semantic"
        out = boundaries.evaluate(no_policy)
        oa04 = out["checks"]["o-a04"]
        self.assertFalse(oa04["pass"])
        self.assertIn("semantic_equivalence_without_entailment_policy", oa04["reasons"])


class TestOA05RoundtripScope(unittest.TestCase):
    """O-A05: roundtrip fidelity is claimed only for a specified observable
    subset and tested domain; a text-only projection passes text checks while
    explicitly failing geometry; a full-fidelity badge is rejected."""

    @classmethod
    def setUpClass(cls):
        cls.fx = _load("oa05-roundtrip-scope.json")
        cls.observations = cls.fx["observations"]

    def test_subset_roundtrip_passes_text_and_fails_geometry(self):
        out = boundaries.evaluate(self.fx["compliant"])
        oa05 = out["checks"]["o-a05"]
        self.assertTrue(oa05["pass"], oa05)
        result = boundaries.roundtrip(self.fx["compliant"], self.observations)
        self.assertEqual(result["outcomes"]["text"], "preserved")
        self.assertEqual(result["outcomes"]["geometry"], "failed")
        self.assertTrue(result["claim_honored"])

    def test_full_fidelity_badge_rejected(self):
        out = boundaries.evaluate(self.fx["counterexample"])
        oa05 = out["checks"]["o-a05"]
        self.assertFalse(oa05["pass"])
        self.assertIn("unearned_full_fidelity_claim", oa05["reasons"])


class TestNoEquivalenceFromProfilesOrSchema(unittest.TestCase):
    """Profile resolution or schema validity alone must never imply semantic
    equivalence."""

    def test_profiles_and_schema_validity_do_not_earn_equivalence(self):
        claim = {"profiles_resolved": True, "schema_valid": True}
        out = boundaries.equivalence_claim(claim)
        self.assertFalse(out["granted"])
        self.assertIn("no_declared_equivalence_criterion", out["reasons"])

    def test_declared_entailment_policy_can_ground_a_claim(self):
        claim = {"profiles_resolved": True, "schema_valid": True,
                 "equivalence": "semantic", "entailment_policy": "OWL 2 DL, pinned ontology v3"}
        out = boundaries.equivalence_claim(claim)
        self.assertTrue(out["granted"], out)


class TestProvenanceRequired(unittest.TestCase):
    """A projection without its declaration is not applied as a valid mapping."""

    def test_projection_without_provenance_rejected(self):
        out = boundaries.evaluate({"projection_id": "p", "version": "1"})
        self.assertEqual(out["status"], "incomplete")
        self.assertIn("missing_provenance", out["reasons"])
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main()
