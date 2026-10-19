"""Purpose: Guard the deployed DSC specs against superseded baseline rules.

Responsibilities:
- Check the deployed 0.3 specs carry the archived change's replacements.
- Verify changed baseline contracts were replaced, not appended side by side.
Rationale: sunset-6pi found strict lint accepted contradictory additive deltas.
The replacement itself was exercised against the live archive operation while
change `add-dsc-03` was active (see its archived task 4.x); the change was
deployed on 2026-10-15.
"""

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_CHANGE = ROOT / "openspec/changes/archive/2026-10-14-add-dsc-03"
REPLACEMENTS = {
    "document-core": {
        "Descriptor shape validation",
        "Snapshot-local identity and referential integrity",
        "Containment tree integrity",
        "Reading order is a strict partial order",
        "Optional typed geometry",
        "Canonicalization stability",
        "Validation outcome states",
    },
    "document-structure": {
        "View declaration", "Containment ownership", "Reading order partiality",
    },
    "document-conformance": {"Reader independence"},
    "document-evidence": {
        "Evidence link resolution", "Replay material for derived observations",
    },
    "document-semantics": {"Typed annotation claims"},
}

# Editorial splits (sunset-rtl, openspec 1.x 500-char requirement-text limit):
# the archived requirement was split into these deployed parts, in document
# order, with the normative prose partitioned verbatim and sentence order
# preserved. The union must still equal the archived body, so a contradictory
# replacement or a lost rule still fails the guard.
SPLITS = {
    "document-core": {
        "Descriptor shape validation": [
            "Descriptor shape validation", "Text encoding and wire scope",
        ],
        "Validation outcome states": [
            "Validation outcome states", "Resource exhaustion is typed",
        ],
    },
    "document-conformance": {
        "Reader independence": [
            "Reader independence", "Pinned projection and comparator",
            "Anchored matching without silent resolution",
            "Comparator reporting completeness",
            "Pinned rerun divergence is explained",
        ],
    },
    "document-evidence": {
        "Evidence link resolution": [
            "Evidence link resolution", "Evidence object bindings",
        ],
        "Replay material for derived observations": [
            "Replay material for derived observations",
            "Transform lineage edges",
        ],
    },
}


def requirements(text):
    """Read requirement bodies without depending on whitespace formatting."""
    return {
        name.strip(): body.strip()
        for name, body in re.findall(
            r"^### Requirement: ([^\n]+)\n(.*?)(?=^### Requirement: |^## |\Z)",
            text, re.M | re.S,
        )
    }


def prose(body):
    """Normative text of a requirement body: everything before its first
    scenario, collapsed to single whitespace."""
    lines = []
    for line in body.splitlines():
        if line.startswith("#### "):
            break
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return " ".join(" ".join(lines).split())


class SpecCompositionTest(unittest.TestCase):
    def test_deployed_specs_carry_archived_replacements(self):
        self.assertTrue(
            ARCHIVED_CHANGE.is_dir(),
            "archived change missing; update ARCHIVED_CHANGE after future deploys",
        )
        for capability, names in REPLACEMENTS.items():
            relative = Path("specs") / capability / "spec.md"
            delta = requirements((ARCHIVED_CHANGE / relative).read_text())
            merged = requirements((ROOT / "openspec" / relative).read_text())
            splits = SPLITS.get(capability, {})
            for name in sorted(names):
                with self.subTest(capability=capability, requirement=name):
                    self.assertIn(name, delta, "Changed baseline rule needs an explicit replacement")
                    if name in splits:
                        parts = splits[name]
                        missing = [p for p in parts if p not in merged]
                        self.assertFalse(
                            missing,
                            "Split part missing from deployed spec: %s" % missing,
                        )
                        self.assertEqual(
                            " ".join(prose(merged[p]) for p in parts),
                            prose(delta[name]),
                            "Deployed split parts must reproduce the archived "
                            "requirement prose verbatim and in order",
                        )
                    else:
                        self.assertEqual(merged[name], delta[name])


if __name__ == "__main__":
    unittest.main()
