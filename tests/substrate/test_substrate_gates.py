# Purpose: Substrate gate tests for restore-document-substrate (sunset-7hs,
#   Stage B consumer harness).
# Responsibilities: Exercise, over committed screened carriers and validated
#   synthetic instances, the deterministic oracles required by the change's
#   verification matrix (native PDF without OCR, EPUB spine/navigation/links,
#   scanned with OCR as a derived observation, hybrid coexistence, financial
#   domain independence) and the design §4 law checks with negative
#   counterexamples (typed-edge rejection, identity/determinism, composition
#   identity+associativity, non-invention, loss/factorization, conditional
#   equivalence) plus the second independent reader agreement measurement.
#   MACHINERY-ONLY gates: nothing here claims real-carrier or human-reviewed
#   conformance; the second reader is an independently coded reading path,
#   not an independent human implementation.
# Rationale: openspec/changes/restore-document-substrate design §3-§4 and
#   document-purpose / document-categorical-model spec deltas; Stage B keeps
#   these gates in a separate consumer harness from tests/tracer/.
"""Substrate gates: deterministic oracles + categorical law checks (sunset-7hs)."""
import json
import tempfile
import unittest
from pathlib import Path

from dsc03 import adapters, canonical, validator
from dsc03.substrate import laws, oracles, reader_b

CARRIERS = Path(__file__).resolve().parents[2] / "fixtures" / "carriers"
NATIVE_PDF = CARRIERS / "budgeting-basics-excerpt.pdf"      # native text + images
EPUB = CARRIERS / "sunset-carrier-sample.epub"
SCANNED_PDF = CARRIERS / "diario-de-poesia-excerpt.pdf"     # image-only pages
HYBRID_PDF = CARRIERS / "resumen-periodical-excerpt.pdf"    # native header + scan on p6
FINANCIAL_PDF = CARRIERS / "invoice-arca-redacted.pdf"      # structured invoice


def check(res, name):
    """Fetch one named oracle check record (and assert it passed via caller)."""
    matches = [c for c in res["checks"] if c["name"] == name]
    assert matches, f"missing check {name!r} in {sorted(c['name'] for c in res['checks'])}"
    return matches[0]


class TestNativePdfOracle(unittest.TestCase):
    """Work req 4: native PDF oracle, no OCR, declared basis + honest coverage."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.res = oracles.native_pdf_oracle(NATIVE_PDF, Path(cls.tmp.name) / "native")

    def test_schema_valid_and_reports(self):
        rec = check(self.res, "schema_valid")
        self.assertTrue(rec["ok"], rec["detail"])
        self.assertEqual(self.res["reports"]["schema"]["status"], "valid")
        self.assertEqual(self.res["reports"]["coverage"]["status"], "verified")

    def test_no_ocr_prerequisite(self):
        # the native oracle never runs an OCR engine: no derived (extracted)
        # content and no transform evidence may appear
        rec = check(self.res, "no_ocr_prerequisite")
        self.assertTrue(rec["ok"], rec["detail"])

    def test_page_and_coordinate_basis_declared(self):
        rec = check(self.res, "page_and_coordinate_basis_declared")
        self.assertTrue(rec["ok"], rec["detail"])
        # one region per real page, geometry bound to the pinned geometry profile
        desc = self.res["descriptor"]
        pages = [r for r in desc["regions"] if r["kind"] == "page"]
        self.assertEqual(len(pages), 3)
        for r in pages:
            self.assertIn("geometry", r)
            self.assertEqual(r["geometry"]["profile_id"], "p-geo")
            self.assertEqual(r["geometry"]["space"], "page-pt")

    def test_text_runs_from_native_text_layer(self):
        rec = check(self.res, "text_runs_from_native_text_layer")
        self.assertTrue(rec["ok"], rec["detail"])
        # every page with native text carries a source-evidenced text content
        sha = self.res["source_sha256"]
        refs = {e["source_ref"] for e in self.res["descriptor"]["evidence"]
                if e["origin"] == "source"}
        self.assertIn(f"sha256:{sha}#page:1", refs)

    def test_unsupported_features_declared(self):
        rec = check(self.res, "unsupported_features_declared")
        self.assertTrue(rec["ok"], rec["detail"])
        # this carrier has page images: their disposition is declared, with a
        # reason, and is not silently reported preserved
        entries = [c for c in self.res["descriptor"]["coverage"] if c["feature"] == "pdf:images"]
        self.assertTrue(entries)
        self.assertTrue(all(c["status"] != "preserved" for c in entries))
        self.assertTrue(all(c["reason"] for c in entries))
        summary = self.res["reports"]["coverage"]["summaries"]["pdf:images"]
        self.assertEqual(summary, "approximated")

    def test_determinism_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            res2 = oracles.native_pdf_oracle(NATIVE_PDF, Path(tmp) / "again")
        a = canonical.reader_a(self.res["descriptor"])
        b = canonical.reader_a(res2["descriptor"])
        self.assertEqual(a, b)


class TestEpubOracle(unittest.TestCase):
    """Work req 5: spine/navigation oracle; no invented pagination."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.res = oracles.epub_oracle(EPUB, Path(cls.tmp.name) / "epub")

    def test_schema_valid_and_spine_preserved(self):
        self.assertTrue(check(self.res, "schema_valid")["ok"])
        rec = check(self.res, "spine_preserved")
        self.assertTrue(rec["ok"], rec["detail"])
        spine = json.loads(next(
            c["value"] for c in self.res["descriptor"]["contents"] if c["id"] == "c-spine"))
        self.assertEqual(spine["idrefs"], ["c1", "c2"])

    def test_navigation_preserved(self):
        self.assertTrue(check(self.res, "navigation_preserved")["ok"])

    def test_no_invented_pagination_or_geometry(self):
        rec = check(self.res, "no_invented_pagination_or_geometry")
        self.assertTrue(rec["ok"], rec["detail"])

    def test_no_reading_order_edges_invented(self):
        rec = check(self.res, "no_reading_order_edges_invented")
        self.assertTrue(rec["ok"], rec["detail"])
        self.assertEqual([r for r in self.res["descriptor"]["relations"]
                          if r["kind"] == "precedes"], [])

    def test_resources_fully_covered(self):
        rec = check(self.res, "resources_fully_covered")
        self.assertTrue(rec["ok"], rec["detail"])
        self.assertEqual(self.res["reports"]["coverage"]["summaries"]["epub:resources"],
                         "preserved")

    def test_footnote_backlink_is_not_a_precedes_edge(self):
        # design §4: an EPUB footnote backlink must not become reading order.
        # The committed carrier has nav/content hyperlinks; the backlink class
        # is exercised with a synthetic footnote fragment (not a fixture carrier).
        links = oracles.classify_epub_links(EPUB.read_bytes())
        self.assertTrue(all(l["class"] != "backlink" for l in links))
        footnote = [
            {"href": "#note-1", "class": "content-link", "source": "chapter1.xhtml"},
            {"href": "#p2", "class": "backlink", "source": "notes.xhtml"},
        ]
        edges = oracles.epub_link_edges(footnote)
        self.assertTrue(edges)
        self.assertNotIn("precedes", {e["kind"] for e in edges})
        self.assertIn("backlink", {e["class"] for e in edges})


class TestScannedHybridOracle(unittest.TestCase):
    """Work req 6: scanned carrier — image primary, OCR derived + provenance;
    hybrid carrier — coexisting observations never overwrite each other."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.res = oracles.scanned_oracle(SCANNED_PDF, Path(cls.tmp.name) / "scanned")

    def test_schema_valid(self):
        rec = check(self.res, "schema_valid")
        self.assertTrue(rec["ok"], rec["detail"])
        self.assertEqual(self.res["reports"]["schema"]["status"], "valid")

    def test_page_image_primary(self):
        rec = check(self.res, "page_image_primary")
        self.assertTrue(rec["ok"], rec["detail"])
        # every scanned page carries an image observation anchored to the page
        desc = self.res["descriptor"]
        img_pages = {e["source_ref"].split("#")[1] for e in desc["evidence"]
                     if e["origin"] == "source" and e["content_ids"]
                     and any(c["kind"] == "image" for c in desc["contents"]
                             if c["id"] == e["content_ids"][0])}
        self.assertEqual(img_pages, {f"page:{i}" for i in range(1, 7)})

    def test_ocr_is_derived_with_engine_provenance(self):
        rec = check(self.res, "ocr_is_derived_with_engine_provenance")
        self.assertTrue(rec["ok"], rec["detail"])
        transforms = [e["transform"] for e in self.res["descriptor"]["evidence"]
                      if "transform" in e]
        self.assertTrue(transforms)
        for t in transforms:
            self.assertTrue(any(d.startswith("engine:tesseract@") for d in t["dependencies"]))
            self.assertTrue(any(d.startswith("lang:") for d in t["dependencies"]))
            self.assertTrue(any(d.startswith("dpi:") for d in t["dependencies"]))

    def test_non_invention_holds(self):
        self.assertEqual(laws.non_invention_violations(self.res["descriptor"]), [])

    def test_non_invention_counterexample_flagged(self):
        # negative counterexample: OCR-derived text rebound as a source
        # observation must be flagged, not accepted
        bad = json.loads(canonical.reader_a(self.res["descriptor"]).decode())
        for e in bad["evidence"]:
            if "transform" in e:
                e["origin"] = "source"
                del e["transform"]
        bad = json.loads(bad and canonical.reader_a(bad).decode())
        violations = laws.non_invention_violations(bad)
        self.assertTrue(any(v.startswith("derived_marked_as_source:") for v in violations))

    def test_alternate_reading_orders_coexist(self):
        rec = check(self.res, "alternate_reading_orders_coexist")
        self.assertTrue(rec["ok"], rec["detail"])
        interps = self.res["descriptor"]["interpretations"]
        self.assertGreaterEqual(len(interps), 2)
        kinds = {i["id"]: i["status"] for i in interps}
        self.assertIn("supported", kinds.values())          # OCR-derived order
        self.assertIn("asserted_without_evidence", kinds.values())  # unproven alternative
        chains = {i["id"] for i in interps}
        for r in self.res["descriptor"]["relations"]:
            if r["kind"] == "precedes":
                self.assertIn(r["interpretation_id"], chains)

    def test_ocr_replay_reproduces_text(self):
        self.assertEqual(set(self.res["ocr_replay"].values()), {"replayed"})

    def test_determinism_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            res2 = oracles.scanned_oracle(SCANNED_PDF, Path(tmp) / "again")
        self.assertEqual(
            canonical.reader_a(self.res["descriptor"]),
            canonical.reader_a(res2["descriptor"]))

    def test_hybrid_native_and_ocr_coexist(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = oracles.hybrid_oracle(HYBRID_PDF, Path(tmp) / "hybrid")
        self.assertTrue(check(res, "schema_valid")["ok"])
        rec = check(res, "hybrid_observations_coexist")
        self.assertTrue(rec["ok"], rec["detail"])
        # page 6 keeps BOTH the native header text and the OCR text
        p6_contents = set(rec["detail"]["page6_contents"])
        self.assertEqual(len(p6_contents), 2)
        origins = rec["detail"]["origins"]
        self.assertEqual(origins["native"], "source")
        self.assertEqual(origins["ocr"], "extracted")


class TestFinancialOracle(unittest.TestCase):
    """Work req 7: structured financial carrier described by the same core."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.res = oracles.financial_oracle(FINANCIAL_PDF, Path(cls.tmp.name) / "fin")

    def test_schema_valid_and_reports(self):
        self.assertTrue(check(self.res, "schema_valid")["ok"])
        self.assertEqual(self.res["reports"]["schema"]["status"], "valid")
        self.assertEqual(self.res["reports"]["coverage"]["status"], "verified")

    def test_no_financial_primitive_in_core(self):
        rec = check(self.res, "no_financial_primitive_in_core")
        self.assertTrue(rec["ok"], rec["detail"])
        kinds = {r["kind"] for r in self.res["descriptor"]["relations"]}
        self.assertTrue(kinds <= laws.CORE_RELATIONS)
        # core relation semantics unchanged (wire frozen)
        self.assertEqual(validator.RELATION_RULES, laws.EXPECTED_CORE_RULES)

    def test_structure_recoverable_via_core(self):
        rec = check(self.res, "structure_recoverable_via_core")
        self.assertTrue(rec["ok"], rec["detail"])
        groups = rec["detail"]["logical_groups"]
        self.assertIn("header", groups)
        self.assertIn("line-items", groups)
        self.assertIn("totals", groups)

    def test_domain_labels_namespaced_not_core(self):
        rec = check(self.res, "domain_labels_namespaced_not_core")
        self.assertTrue(rec["ok"], rec["detail"])
        terms = {a["term"] for a in self.res["descriptor"]["annotations"]}
        self.assertTrue(terms)
        self.assertTrue(all(t.split(":", 1)[0] == "fin" for t in terms))
        # interpretations stay interpretations: honest partiality
        for a in self.res["descriptor"]["annotations"]:
            self.assertEqual(a["status"], "asserted_without_evidence")
            self.assertEqual(a["origin"], "inferred")


class TestLawChecks(unittest.TestCase):
    """Work req 8: law checks + negative counterexamples (synthetic, validated)."""

    def test_mistyped_edge_rejected_not_crashed(self):
        desc = laws.synthetic_instance()
        desc["relations"].append(
            {"id": "rel-bad", "kind": "has-content", "from": "c0", "to": "r-page"})
        status, reasons = laws.typed_check(desc)
        self.assertEqual(status, "rejected")
        self.assertIn("relation_type", reasons)

    def test_dangling_endpoint_rejected_not_crashed(self):
        desc = laws.synthetic_instance()
        desc["relations"].append(
            {"id": "rel-dang", "kind": "contains", "from": "r-page", "to": "r-ghost"})
        status, reasons = laws.typed_check(desc)
        self.assertEqual(status, "rejected")
        self.assertIn("dangling_reference", reasons)

    def test_identity_mapping_preserves_observables(self):
        desc = laws.synthetic_instance()
        f = laws.uppercase_mapping()
        fid = laws.identity_mapping()
        composed = laws.compose(fid, f)
        out = composed.fn(desc)
        self.assertEqual(out, f.fn(desc))
        self.assertEqual(composed.loss, f.loss)

    def test_composition_associativity_on_declared_observables(self):
        desc = laws.synthetic_instance()
        f = laws.uppercase_mapping()
        g = laws.strip_mapping()
        h = laws.flatten_mapping()
        left = laws.compose(h, laws.compose(g, f)).fn(desc)
        right = laws.compose(laws.compose(h, g), f).fn(desc)
        self.assertEqual(canonical.reader_a(left), canonical.reader_a(right))
        self.assertEqual(laws.compose(h, laws.compose(g, f)).loss,
                         laws.compose(laws.compose(h, g), f).loss)

    def test_incompatible_composition_rejected(self):
        f = laws.uppercase_mapping()
        stray = laws.stray_mapping()  # target schema does not match f's output
        with self.assertRaises(laws.TypedError) as ctx:
            laws.compose(stray, f)
        self.assertIn("incompatible_composition", str(ctx.exception))

    def test_loss_accounting_accumulates(self):
        f = laws.uppercase_mapping()
        h = laws.flatten_mapping()   # drops geometry/annotations, declares loss
        comp = laws.compose(h, f)
        self.assertLessEqual(set(f.loss) | set(h.loss), set(comp.loss))
        self.assertIn("geometry", comp.loss)

    def test_factorization_limit_sign_counterexample(self):
        a, b = laws.sign_instances()   # identical flattened text, different columns
        t = laws.text_only_mapping()
        verdict = laws.factorization_verdict(t, a, b)
        self.assertEqual(verdict, "loss_declared")
        self.assertIn("sign-column", t.loss)
        # the flattening itself is genuinely identical text
        self.assertEqual(canonical.reader_a(t.fn(a)), canonical.reader_a(t.fn(b)))

    def test_sign_claiming_mapping_refuted(self):
        a, b = laws.sign_instances()
        bad = laws.sign_claiming_mapping()
        verdict = laws.factorization_verdict(bad, a, b)
        self.assertEqual(verdict, "claimed_illegitimately")

    def test_equivalence_without_alignment_is_unsupported(self):
        a, b = laws.sign_instances()
        res = laws.equivalence_status(a, b)
        self.assertEqual(res["status"], "unsupported")
        self.assertNotIn("equivalent", res)

    def test_equivalence_with_alignment_compares_only_agreed_scope(self):
        a, b = laws.sign_instances()
        res = laws.equivalence_status(a, b, alignment={"scope": ("text",)})
        self.assertEqual(res["status"], "compared")
        self.assertEqual(res["agreed"], ("text",))


class TestSecondIndependentReader(unittest.TestCase):
    """Work req 10: second independent reading path; agreement + overhead +
    unrepresentable cases. Machinery-level independence (agent-executed);
    never reported as human review or real-carrier conformance."""

    PDFS = ["agentic-patterns-excerpt.pdf", "budgeting-basics-excerpt.pdf",
            "invoice-arca-redacted.pdf", "cta-cte-propietario-redacted.pdf"]

    def test_reader_b_pdf_page_inventory_and_text_presence_agree(self):
        for name in self.PDFS:
            with self.subTest(carrier=name):
                with tempfile.TemporaryDirectory() as tmp:
                    a = adapters.describe_pdf(CARRIERS / name, Path(tmp) / "a")
                    b = reader_b.describe_pdf_b(CARRIERS / name, Path(tmp) / "b")
                self.assertEqual(validator.validate(b), [])          # B validates too
                self.assertTrue(canonical.agree(b))                  # canonical readers agree on B
                ag = reader_b.agreement(a, b)
                self.assertEqual(ag["pages"], "agree", name)
                self.assertEqual(ag["text_presence"], "agree", name)

    def test_reader_b_reports_unexamined_features_honestly(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = reader_b.describe_pdf_b(CARRIERS / "budgeting-basics-excerpt.pdf",
                                        Path(tmp) / "b")
        feats = {c["feature"] for c in b["coverage"] if c["status"] == "unexamined"}
        self.assertLessEqual({"pdf:images", "pdf:vectors", "pdf:annotations"}, feats)
        for c in b["coverage"]:
            if c["status"] == "unexamined":
                self.assertTrue(c["reason"])

    def test_reader_b_epub_full_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = adapters.describe_epub(EPUB, Path(tmp) / "a")
            b = reader_b.describe_epub_b(EPUB, Path(tmp) / "b")
        self.assertEqual(validator.validate(b), [])
        ag = reader_b.agreement(a, b)
        for key in ("manifest_items", "spine", "nav", "resources"):
            self.assertEqual(ag[key], "agree", key)

    def test_reader_agreement_table_recorded(self):
        table = reader_b.agreement_table(self.PDFS + ["sunset-carrier-sample.epub"])
        self.assertEqual(len(table), len(self.PDFS) + 1)
        for row in table:
            self.assertIn(row["carrier"], [p for p in self.PDFS] + ["sunset-carrier-sample.epub"])
            self.assertIn("a_bytes", row)
            self.assertIn("b_bytes", row)
            self.assertIn(row["verdict"], ("agree", "partial-agree"))
            self.assertTrue(row["independence_note"].startswith("machinery-only"))


if __name__ == "__main__":
    unittest.main()
