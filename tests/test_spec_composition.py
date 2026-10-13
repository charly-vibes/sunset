"""Purpose: Guard the DSC proposal against retaining superseded baseline rules.

Responsibilities:
- Exercise the real OpenSpec archive operation in a temporary workspace.
- Check that changed baseline contracts are replaced rather than appended.
Rationale: sunset-6pi found strict lint accepted contradictory additive deltas.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
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
    def test_archive_replaces_changed_baseline_contracts(self):
        with tempfile.TemporaryDirectory(prefix="sunset-spec-") as temporary:
            workspace = Path(temporary)
            shutil.copytree(ROOT / "openspec", workspace / "openspec")
            result = subprocess.run(
                ["openspec", "archive", "add-dsc-03", "--yes"],
                cwd=workspace, capture_output=True, text=True,
                env={**os.environ, "NO_COLOR": "1", "OPENSPEC_TELEMETRY": "0"},
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for capability, names in REPLACEMENTS.items():
                relative = Path("specs") / capability / "spec.md"
                baseline = requirements((ROOT / "openspec" / relative).read_text())
                delta = requirements((ROOT / "openspec/changes/add-dsc-03" / relative).read_text())
                merged = requirements((workspace / "openspec" / relative).read_text())
                for name in sorted(names):
                    with self.subTest(capability=capability, requirement=name):
                        self.assertIn(name, delta, "Changed baseline rule needs an explicit replacement")
                        self.assertNotEqual(merged[name], baseline[name])
                        self.assertEqual(merged[name], delta[name])


if __name__ == "__main__":
    unittest.main()
