# Purpose: Ingest human review verdicts back into the pipeline (typed
#   version pinning, agreement report, missed-ink accounting, counterexample
#   feed) — tests/tracer/test_visual_review_ingest.py.
# Responsibilities: Pin the ingest report key-by-key against the committed
#   fixture (fixtures/visual/verdicts-agent-sample.json), assert the typed
#   refusal on calibration-record hash mismatch, assert unknown verdicts are
#   never counted as agreement, and assert the counterexample feed carries
#   replayable=false so dsc03.compare.replay refuses it.
# Rationale: FP/FN statistics must never be attributed to the wrong record
#   version; the human pass stays supreme (unknown is an answer, no winner
#   election, no smoothing) and human verdicts are never machine-replayable.
import json
from pathlib import Path

import pytest

from dsc03.visual.review import (
    MISSING_INK_CAVEAT,
    PROVENANCE_LABEL,
    RecordVersionMismatch,
    ingest_verdicts,
)

ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "fixtures" / "visual" / "calibration.json"
VERDICTS_PATH = ROOT / "fixtures" / "visual" / "verdicts-agent-sample.json"


def _ingest(record_path=RECORD_PATH):
    # The committed bundle pins the commit its verdicts were recorded
    # against; ingest refuses cross-commit attribution by design. Re-pin a
    # copy to the live HEAD so the positive path tracks HEAD movement the
    # way a fresh recording session would. The fixture itself stays the
    # untouched historical artifact.
    import dsc03.visual.review as _review
    import tempfile
    bundle = json.loads(VERDICTS_PATH.read_text())
    if bundle.get("base_commit") != _review._BASE_COMMIT:
        bundle["base_commit"] = _review._BASE_COMMIT
        with tempfile.TemporaryDirectory() as tmp:
            repinned = Path(tmp) / "verdicts-agent-sample.json"
            repinned.write_text(json.dumps(bundle))
            return ingest_verdicts(repinned, record_path=record_path)
    return ingest_verdicts(VERDICTS_PATH, record_path=record_path)


def test_typed_refusal_on_record_hash_mismatch(tmp_path):
    other = tmp_path / "other-record.json"
    record = json.loads(RECORD_PATH.read_text())
    record["faint_mechanism"] = record.get("faint_mechanism")
    other.write_text(json.dumps(record))
    with pytest.raises(RecordVersionMismatch) as exc:
        _ingest(record_path=other)
    assert exc.value.code == "record-version-mismatch"


def test_typed_refusal_on_base_commit_mismatch(tmp_path):
    bundle = json.loads(VERDICTS_PATH.read_text())
    bundle["base_commit"] = "0" * 40
    path = tmp_path / "wrong-commit.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(RecordVersionMismatch) as exc:
        ingest_verdicts(path, record_path=RECORD_PATH)
    assert exc.value.code == "record-version-mismatch"
    assert "base_commit" in str(exc.value)


def test_unknown_verdicts_never_counted_as_agreement():
    report = _ingest()
    diario = next(row for row in report["agreement"]
                  if row["carrier"] == "diario-de-poesia-excerpt"
                  and row["property"] == "ink-coverage")
    assert diario["human"]["unknown"] == 1
    assert diario["human"]["agree"] == 1
    # one unknown verdict must not raise the agreement tally
    assert diario["confusion"]["agree"] == 1
    assert diario["oracle_false_negatives"] == 0


def test_report_pinned_key_by_key():
    report = _ingest()
    assert report["kind"] == "visual-review-ingest-report"
    assert report["version"] == 1
    assert report["provenance"] == PROVENANCE_LABEL
    assert report["record_path"].endswith("fixtures/visual/calibration.json")
    import hashlib
    assert report["record_sha256"] == hashlib.sha256(
        RECORD_PATH.read_bytes()).hexdigest()

    by_key = {(row["carrier"], row["property"]): row
              for row in report["agreement"]}

    bank = by_key[("bank-statement-ca-excerpt", "ink-coverage")]
    assert bank == {
        "carrier": "bank-statement-ca-excerpt",
        "page": 1,
        "property": "ink-coverage",
        "oracle_status": "agree",
        "human": {"agree": 1, "differ": 1, "unknown": 0, "pending": 0},
        "confusion": {"agree": 1, "differ": 1, "unknown": 0},
        "oracle_false_negatives": 1,
        "regions": [
            {"id": "ledger-block", "verdict": "differ"},
            {"id": "margin-lower", "verdict": "agree"},
        ],
    }

    # the oracle recorded differ on the detection run for visual-strip
    # ink-coverage; the ingest compares against the derivation rows the
    # review bundle was built from
    strip = by_key[("visual-strip", "ink-coverage")]
    assert strip["oracle_status"] == "agree"
    assert strip["human"] == {"agree": 0, "differ": 0, "unknown": 0, "pending": 0}
    assert strip["unavailable"] == "render unavailable: no renderer on PATH"
    assert strip["oracle_false_negatives"] == 0

    # region-alignment rows exist per carrier too
    assert ("diario-de-poesia-excerpt", "region-alignment") in by_key


def test_missed_ink_accounting_is_labeled_estimate():
    report = _ingest()
    bank = next(row for row in report["missed_ink"]
                if row["carrier"] == "bank-statement-ca-excerpt")
    assert bank == {
        "carrier": "bank-statement-ca-excerpt",
        "page": 1,
        "label": "ESTIMATE",
        "caveat": MISSING_INK_CAVEAT,
        "count": 2,
        "total_area_px": 30 * 40 + 50 * 60,
        "page_area_px": 612 * 792,
        "area_fraction": (30 * 40 + 50 * 60) / (612 * 792),
    }
    diario = next(row for row in report["missed_ink"]
                  if row["carrier"] == "diario-de-poesia-excerpt")
    assert diario["count"] == 0
    assert diario["total_area_px"] == 0
    # sunset-9rg caveat is carried, not dropped
    assert "sunset-9rg" in diario["caveat"]


def test_counterexample_feed_is_not_replayable():
    from dsc03 import compare

    report = _ingest()
    differs = report["counterexamples"]
    assert len(differs) == 1
    witness = differs[0]["witness"]
    assert witness["replayable"] is False
    assert witness["expected"] == "oracle agree"
    assert witness["observed"] == "human differ"
    assert differs[0]["inputs"] == {
        "carrier": "bank-statement-ca-excerpt",
        "page": 1,
        "region": "ledger-block",
        "property": ["ink-coverage", "region-alignment"],
    }
    with pytest.raises(compare.NotReplayable):
        compare.replay(differs[0], left=None, right=None)


def test_summary_appends_to_evaluation_record():
    from digitization.evaluation import append_visual_review_summary

    report = _ingest()
    record = {"version": "1", "status": "measured", "thresholds": {"cer": "pass"}}
    append_visual_review_summary(record, report["evaluation_summary"])
    assert record["visual_review_ingest"]["provenance"] == PROVENANCE_LABEL
    assert record["visual_review_ingest"]["record_sha256"] == report["record_sha256"]
    # FN is counted per property row: the single region-level differ
    # registers once for each of the two recorded properties
    assert record["visual_review_ingest"]["oracle_false_negatives"] == 2
    assert record["visual_review_ingest"]["human_unknown_total"] == 1
    # ingest never touches evaluation thresholds
    assert record["thresholds"] == {"cer": "pass"}


def test_ingest_does_not_modify_thresholds():
    report = _ingest()
    record = json.loads(RECORD_PATH.read_text())
    assert report["thresholds_modified"] is False
    assert report["recorded_thresholds"] == record["thresholds"]


def test_cli_ingest_subcommand(tmp_path, capsys):
    from dsc03.visual import review

    # Re-pin a copy to the live HEAD (fresh-recording-session semantics);
    # the committed fixture keeps its historical pin (see _ingest).
    import dsc03.visual.review as _review
    bundle = json.loads(VERDICTS_PATH.read_text())
    bundle["base_commit"] = _review._BASE_COMMIT
    repinned = tmp_path / "verdicts-repinned.json"
    repinned.write_text(json.dumps(bundle))

    out = tmp_path / "counterexamples.json"
    rc = review.main(["ingest", str(repinned),
                      "--record", str(RECORD_PATH),
                      "--counterexamples", str(out)])
    assert rc == 0
    assert out.exists()
    bundles = json.loads(out.read_text())
    assert bundles and all(b["witness"]["replayable"] is False for b in bundles)
    report = json.loads(capsys.readouterr().out)
    assert report["kind"] == "visual-review-ingest-report"


def test_cli_build_path_still_works():
    """The pre-existing build invocation must be untouched by subparsers."""
    from dsc03.visual import review

    parser = review._build_parser()
    args = parser.parse_args(["--out", "x.html", "--serve", "9000"])
    assert args.command is None
    assert args.out == "x.html"
    assert args.serve == "9000"
