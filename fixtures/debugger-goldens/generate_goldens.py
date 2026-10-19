# Purpose: Deterministically regenerate the debugger goldens (JSON) from
#   committed inputs — the real carrier fixtures/carriers/accounting-made-simple-excerpt.pdf
#   via dsc03.adapters, plus the in-module negative fixtures.
# Responsibilities: Build each golden bundle with dsc03.compare
#   (export_counterexample + serialize_bundle), sorted keys, fixed indent, no
#   timestamps; record provenance (carrier filename + real source sha256 from
#   the adapter descriptor) and honor redaction state (replayable=false for
#   golden-03). Run: python3 fixtures/debugger-goldens/generate_goldens.py
# Rationale: sunset-xx7.3 slice 3 — goldens live outside openspec/ so they
#   survive change archival; this script is the provenance record.
"""Deterministic golden generator for the debugger comparison slice."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dsc03 import adapters, compare  # noqa: E402
from dsc03.compare import ComparatorSpec, ComparisonInput  # noqa: E402

OUT = Path(__file__).resolve().parent
CARRIER = ROOT / "fixtures" / "carriers" / "accounting-made-simple-excerpt.pdf"


def _spec(scope=("flattened_text", "sign_column_positions")):
    return ComparatorSpec("dbg.text-flatten", "1.0.0", ("descriptor", "descriptor"), tuple(scope))


def _sha(data) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _payloads_from_carrier():
    """Real-carrier descriptor -> comparison payloads (full vs flattened-only)."""
    with tempfile.TemporaryDirectory() as out:
        desc = adapters.describe_pdf(CARRIER, Path(out))
    texts = [c["value"] for c in desc["contents"] if c.get("kind") == "text"]
    full = {"flattened_text": "\n".join(texts), "sign_column_positions": {"page:1": 0}}
    # mutation: remove spatial column info (financial-sign-loss oracle) -> sign loss
    flat = {"flattened_text": "\n".join(texts), "sign_column_positions": {"page:1": 2}}
    return desc, full, flat


def main():
    desc, full, flat = _payloads_from_carrier()
    left = ComparisonInput("descriptor", full, _sha(json.dumps(full, sort_keys=True).encode()),
                           desc["source"]["sha256"])
    right = ComparisonInput("descriptor", flat, _sha(json.dumps(flat, sort_keys=True).encode()),
                            desc["source"]["sha256"])
    out = compare.scoped_compare(_spec(), left, right)
    bundle = compare.export_counterexample(out, _spec(), left, right)
    bundle["provenance"] = {
        "carrier": CARRIER.name,
        "source_sha256": desc["source"]["sha256"],
        "adapter": adapters.ADAPTER_ID,
        "adapter_version": adapters.ADAPTER_VERSION,
        "generator": "fixtures/debugger-goldens/generate_goldens.py",
    }
    (OUT / "golden-01-carrier-text-compare.json").write_bytes(compare.serialize_bundle(bundle))

    # golden-02: wrong reading order counterexample, fully replayable
    l2 = ComparisonInput("descriptor", {"reading_edges": ["r-a->r-b"]}, "aa" * 32, "bb" * 32)
    r2 = ComparisonInput("descriptor", {"reading_edges": ["r-b->r-a"]}, "cc" * 32, "bb" * 32)
    out2 = compare.scoped_compare(_spec(("reading_edges",)), l2, r2)
    b2 = compare.export_counterexample(out2, _spec(("reading_edges",)), l2, r2)
    b2["provenance"] = {"fixture": "ahira-wrong-order oracle (fixtures README)",
                        "generator": "fixtures/debugger-goldens/generate_goldens.py"}
    (OUT / "golden-02-wrong-order-counterexample.json").write_bytes(compare.serialize_bundle(b2))

    # golden-03: private-redaction — secret source bytes omitted, nonreplayable
    l3 = ComparisonInput("descriptor", {"flattened_text": "PRIVATE -77.00", "sign_column_positions": {"page:1": 0}}, "dd" * 32, "ee" * 32)
    r3 = ComparisonInput("descriptor", {"flattened_text": "PRIVATE -77.00", "sign_column_positions": {"page:1": 4}}, "ff" * 32, "ee" * 32)
    out3 = compare.scoped_compare(_spec(), l3, r3)
    b3 = compare.export_counterexample(out3, _spec(), l3, r3, redact=True)
    b3["provenance"] = {"fixture": "private-redaction oracle (fixtures README)",
                        "redaction_state": "redacted; source bytes withheld; replayable=false",
                        "generator": "fixtures/debugger-goldens/generate_goldens.py"}
    (OUT / "golden-03-private-redaction.json").write_bytes(compare.serialize_bundle(b3))
    print("goldens written:", sorted(p.name for p in OUT.glob("golden-*.json")))


if __name__ == "__main__":
    main()
