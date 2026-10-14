# Purpose: Pinned local profile resolution tests for the tracer path (sunset-r68.1.3).
# Responsibilities: Resolve a declared profile from an explicitly supplied local
#   registry against the pinned version+digest; assert unavailable/tampered/
#   unimplemented declarations yield unsupported_profile or profile_digest_mismatch;
#   assert a newer registry version never overrides a version-1 pin and that a
#   registry change under the pin is detected.
# Rationale: add-dsc-03 document-core "Pinned profile declarations" scenarios —
#   no network fetch, no latest-version fallback, digest identity over URI.
"""Pinned profile resolution tests (sunset-r68.1.3)."""
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import profiles

PROFILES = Path(__file__).parent / "profiles"
V1 = "selector-text-scalar.json"
V2 = "selector-text-scalar-v2.json"


def decl(uri, version, kind="selector", sha=None):
    return {
        "id": "p-sel",
        "kind": kind,
        "uri": uri,
        "version": version,
        "sha256": sha or hashlib.sha256((PROFILES / uri).read_bytes()).hexdigest(),
    }


def test_pinned_selector_profile_resolves():
    status, artifact = profiles.resolve(decl(V1, "1"), profiles.Registry(PROFILES))
    assert status == "resolved"
    assert artifact["version"] == "1"
    assert artifact["offset_unit"] == "unicode-scalar-values"


def test_pin_survives_newer_registry_version():
    # the registry also holds a newer version-2 artifact; the version-1 pin wins
    status, artifact = profiles.resolve(decl(V1, "1"), profiles.Registry(PROFILES))
    assert status == "resolved" and artifact["version"] == "1"
    # and a pin on the newer artifact resolves version 2, not version 1
    status, artifact = profiles.resolve(decl(V2, "2"), profiles.Registry(PROFILES))
    assert status == "resolved" and artifact["version"] == "2"


def test_registry_change_under_the_pin_is_detected(tmp_path):
    # the pinned uri now serves version-2 bytes: the digest pin must catch it
    shutil.copy(PROFILES / V2, tmp_path / V1)
    status, info = profiles.resolve(decl(V1, "1"), profiles.Registry(tmp_path))
    assert status == "profile_digest_mismatch"


def test_unavailable_profile_is_unsupported(tmp_path):
    status, info = profiles.resolve(decl(V1, "1"), profiles.Registry(tmp_path))
    assert status == "unsupported_profile"


def test_tampered_artifact_is_digest_mismatch():
    status, info = profiles.resolve(decl(V1, "1", sha="0" * 64), profiles.Registry(PROFILES))
    assert status == "profile_digest_mismatch"


def test_unimplemented_profile_kind_is_unsupported():
    status, info = profiles.resolve(
        decl(V1, "1", kind="carrier-inventory"), profiles.Registry(PROFILES)
    )
    assert status == "unsupported_profile"
