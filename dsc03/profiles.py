# Purpose: Pinned local profile resolution for DSC 0.3 (sunset-r68.1.3).
# Responsibilities: Resolve declared profiles (id/kind/uri/version/sha256) against
#   an explicitly supplied local registry of artifact bytes; return typed outcomes
#   (resolved artifact, unsupported_profile, profile_digest_mismatch) with no
#   network fetch and no latest-version fallback — the declared version+digest
#   identity always wins over the URI hint.
# Rationale: add-dsc-03 document-core "Pinned profile declarations" requirement.
"""Pinned profile resolution: a local registry supplies exact artifact bytes."""
import hashlib
import json
from pathlib import Path

IMPLEMENTED_KINDS = {"selector"}


class Registry:
    """Explicit local registry: a root directory holding profile artifacts.

    The declared URI is a lookup hint resolved relative to the root; identity is
    the declared (kind, version, sha256), never the URI or any 'latest' notion.
    """

    def __init__(self, root):
        self.root = Path(root)

    def artifact_bytes(self, decl):
        path = self.root / decl["uri"]
        if not path.is_file():
            return None
        return path.read_bytes()


def resolve(decl, registry):
    """Resolve one well-formed profile declaration against a local registry.

    Returns (status, payload): status is 'resolved' (payload = parsed artifact),
    'unsupported_profile' (unavailable locally, version mismatch, or unimplemented
    kind/artifact grammar), or 'profile_digest_mismatch' (supplied bytes whose
    digest differs from the declaration).
    """
    raw = registry.artifact_bytes(decl)
    if raw is None:
        return "unsupported_profile", None
    digest = hashlib.sha256(raw).hexdigest()
    if digest != decl["sha256"]:
        return "profile_digest_mismatch", None
    try:
        artifact = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return "unsupported_profile", None
    if not isinstance(artifact, dict):
        return "unsupported_profile", None
    if artifact.get("version") != decl["version"]:
        return "unsupported_profile", None
    if decl["kind"] not in IMPLEMENTED_KINDS:
        return "unsupported_profile", None
    if artifact.get("kind") != decl["kind"]:
        return "unsupported_profile", None
    return "resolved", artifact
