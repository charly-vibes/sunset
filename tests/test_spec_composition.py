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


def requirements(text):
    """Read requirement bodies without depending on whitespace formatting."""
    return {
        name.strip(): body.strip()
        for name, body in re.findall(
            r"^### Requirement: ([^\n]+)\n(.*?)(?=^### Requirement: |^## |\Z)",
            text, re.M | re.S,
        )
    }


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
            for name in sorted(names):
                with self.subTest(capability=capability, requirement=name):
                    self.assertIn(name, delta, "Changed baseline rule needs an explicit replacement")
                    self.assertEqual(merged[name], delta[name])


if __name__ == "__main__":
    unittest.main()
