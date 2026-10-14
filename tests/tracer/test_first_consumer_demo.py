# Purpose: First-consumer demonstration tests (sunset-r68.13, tasks.md 5.4).
# Responsibilities: Exercise the demo workflow end to end over the committed
#   demo issue (fixtures/carriers/resumen-periodical-excerpt.pdf): both pinned
#   extractors run, each output adapts into a 0.3 descriptor snapshot, both
#   snapshots agree under the two independent canonical readers, extractor
#   outputs compare through the pinned projection against the reviewers'
#   oracle, and the measurement sheet carries every published field with the
#   agent-executed deviation honestly labeled. Labels from dsc03.conformance
#   must stay honest: traceability may be demonstrated, speed only when review
#   time did not increase, and never release conformance.
# Rationale: add-dsc-03 document-conformance "First-consumer demonstration".
"""First-consumer demo (sunset-r68.13): extractors, snapshots, projection, measurement."""
import json
import tempfile
import unittest
from pathlib import Path

from dsc03 import adapters, canonical, conformance, demo

CARRIER = Path("fixtures/carriers/resumen-periodical-excerpt.pdf")


class TestExtractors(unittest.TestCase):
    def test_both_extractors_read_every_page(self):
        run = demo.run_extractors(CARRIER)
        self.assertEqual(set(run["pages"]), set(range(1, 7)))
        for page in range(1, 7):
            for ex in ("pdftotext", "pymupdf"):
                self.assertTrue(run["pages"][page][ex].strip(), (page, ex))
        # pinned versions are recorded, not guessed
        self.assertIn("26.01", run["pinned"]["pdftotext_version"])
        self.assertIn("1.28", run["pinned"]["pymupdf_version"])
        self.assertIn("spa", run["pinned"]["ocr_lang"])

    def test_ocr_pass_surfaces_native_ocr_disagreement(self):
        run = demo.run_extractors(CARRIER)
        # scanned p6 (original p13): OCR-only page — OCR must read far more
        # than the ~146-char native header, and it must differ
        ocr6 = run["pages"][6]["ocr"].strip()
        nat6 = run["pages"][6]["pymupdf"].strip()
        self.assertGreater(len(ocr6), len(nat6))
        self.assertNotEqual(ocr6, nat6)
        # and the runner flags which pages disagree
        self.assertIn(6, run["native_ocr_disagreements"])

    def test_peak_memory_recorded_per_extractor(self):
        run = demo.run_extractors(CARRIER)
        for ex in ("pdftotext", "pymupdf", "ocr"):
            self.assertGreater(run["peak_memory_kb"][ex], 0)


class TestSnapshots(unittest.TestCase):
    def test_two_extractor_snapshots_with_canonical_agreement(self):
        run = demo.run_extractors(CARRIER)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "snapshots"
            snaps = demo.build_snapshots(CARRIER, out, run)
            self.assertEqual(
                sorted(snaps), ["snapshot-pdftotext", "snapshot-pymupdf"])
            for name, snap in snaps.items():
                self.assertTrue(canonical.agree(snap["descriptor"]), name)
                self.assertGreater(snap["descriptor_bytes"], 0)
                self.assertTrue(Path(snap["path"]).exists())
            # artifacts (inventory/manifest) exist per snapshot
            for d in out.iterdir():
                if d.is_dir():
                    self.assertTrue((d / "inventory.json").exists())
                    self.assertTrue((d / "manifest.json").exists())

    def test_snapshot_carries_extractor_text_as_contents(self):
        run = demo.run_extractors(CARRIER)
        with tempfile.TemporaryDirectory() as tmp:
            snaps = demo.build_snapshots(CARRIER, Path(tmp), run)
            desc = snaps["snapshot-pymupdf"]["descriptor"]
            page3 = next(c for c in desc["contents"] if c["id"] == "txt3")
            self.assertEqual(page3["value"], run["pages"][3]["pymupdf"].strip())
            self.assertEqual(desc["source"]["sha256"], adapters._sha256(CARRIER.read_bytes()))


class TestProjectionAgainstOracle(unittest.TestCase):
    def test_comparison_passes_against_reviewer_oracle(self):
        run = demo.run_extractors(CARRIER)
        result = demo.compare_extractors(run)
        self.assertEqual(result["status"], "complete", result)
        self.assertGreater(result["matches"], 0)
        self.assertEqual(result["false_negatives"], [])
        self.assertEqual(result["false_positives"], [])
        # disagreements are retained, not smoothed: allowed unresolved list
        # must be nonempty and cover everything unresolved
        self.assertTrue(result["retained_alternatives"] or result["unresolved"])
        self.assertEqual(set(result["unresolved"]), set(demo.ORACLE["allowed_unresolved"]))
        self.assertTrue(result["pass"], result["reasons"])

    def test_pin_names_projection_and_source_digests(self):
        run = demo.run_extractors(CARRIER)
        pin = demo.projection_pin()
        for key in ("projection_id", "version", "projection_sha256", "source_sha256"):
            self.assertIsInstance(pin[key], str) and self.assertTrue(pin[key])
        self.assertEqual(pin["source_sha256"], adapters._sha256(CARRIER.read_bytes()))


class TestMeasurementSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheet = demo.run_full_demo(CARRIER)

    def test_sheet_has_all_published_fields(self):
        self.assertEqual(self.sheet["source"]["sha256"], adapters._sha256(CARRIER.read_bytes()))
        self.assertIn("license", self.sheet["source"])
        tasks = self.sheet["review_tasks"]
        self.assertEqual(
            sorted(tasks), ["R1", "R2", "R3", "R4", "R5"])
        for tid, t in tasks.items():
            self.assertGreater(t["time_dsc_s"], 0, tid)
            self.assertGreater(t["time_native_s"], 0, tid)
            self.assertIn(t["decision_dsc"], ("correct", "incorrect"), tid)
            self.assertIn(t["decision_native"], ("correct", "incorrect"), tid)
        self.assertIn("descriptor_bytes", self.sheet)
        self.assertEqual(sorted(self.sheet["descriptor_bytes"]),
                         ["snapshot-pdftotext", "snapshot-pymupdf"])
        self.assertTrue(self.sheet["peak_memory_kb"]["pdftotext"] > 0)
        self.assertIn("memory_method", self.sheet)

    def test_deviation_honestly_labeled(self):
        self.assertTrue(self.sheet["reviewers_agent_executed"])
        self.assertIn("human reviewer pass can supersede", self.sheet["deviation_note"])

    def test_raw_json_serializable_without_narrative(self):
        raw = json.dumps(self.sheet)
        self.assertNotIn("summary", self.sheet)
        self.assertTrue(raw)


class TestConformanceLabels(unittest.TestCase):
    def test_labels_stay_honest_after_demo(self):
        suite = {
            "v03_schema": True, "v03_profiles": True, "v03_coverage": True,
            "real_carriers": True, "adversarial_corpus": True,
            "independent_readers": 2, "extractor_comparison": True,
            "anchor_mapping_reviewed": True,
            "first_consumer_demo": True, "native_output_baseline": True,
            "demo_result": {
                "functional_gates_passed": True,
                "review_time_delta": 3.7,
            },
        }
        out = conformance.classify(suite)
        self.assertEqual(out["workflow_benefit"]["traceability"], "demonstrated")
        self.assertEqual(out["workflow_benefit"]["speed"], "not claimed")


if __name__ == "__main__":
    unittest.main()
