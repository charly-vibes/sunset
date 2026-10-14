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
import re
from pathlib import Path

IMPLEMENTED_KINDS = {"selector", "geometry", "carrier-inventory", "adapter-manifest"}
OFFSET_UNITS = {"unicode-scalar-values", "utf-8-bytes"}  # grapheme-clusters: unimplemented
ENDPOINTS = {"half-open", "closed"}
HALF_OPEN_RE = re.compile(r"\[(\d+),(\d+)\)")
CLOSED_RE = re.compile(r"\[(\d+),(\d+)\]")


def apply_text_range(value, locator, artifact):
    """Apply a declared text-range grammar to the exact (unnormalized) value.

    Returns ('selected', text) or ('invalid_selector', None). Offsets index the
    exact value; byte ranges must not split code points. A profile declaring an
    offset unit or endpoint convention this implementation does not provide was
    already refused at resolution (unsupported_profile).
    """
    if artifact.get("offset_unit") not in OFFSET_UNITS:
        return "invalid_selector", None
    if artifact.get("endpoints") not in ENDPOINTS:
        return "invalid_selector", None
    closed = artifact["endpoints"] == "closed"
    m = (CLOSED_RE if closed else HALF_OPEN_RE).fullmatch(locator)
    if m is None:
        return "invalid_selector", None
    start, end = int(m.group(1)), int(m.group(2))
    if closed:
        end += 1
    if artifact["offset_unit"] == "utf-8-bytes":
        data = value.encode("utf-8")
        n = len(data)
        if not (0 <= start <= end <= n):
            return "invalid_selector", None
        # boundaries must not split a code point
        starts = set()
        acc = 0
        for ch in value:
            starts.add(acc)
            acc += len(ch.encode("utf-8"))
        starts.add(n)
        if start not in starts or end not in starts:
            return "invalid_selector", None
        return "selected", data[start:end].decode("utf-8")
    n = len(value)  # Python str length == number of Unicode scalar values
    if not (0 <= start <= end <= n):
        return "invalid_selector", None
    return "selected", value[start:end]


def resolve_frame(artifact, frame_name):
    """Resolve a named frame from a resolved geometry profile artifact.

    Returns ('resolved', frame) or ('invalid_geometry_frame', None).
    """
    if not isinstance(artifact, dict) or artifact.get("kind") != "geometry":
        return "invalid_geometry_frame", None
    for frame in artifact.get("frames", []):
        if isinstance(frame, dict) and frame.get("name") == frame_name:
            return "resolved", frame
    return "invalid_geometry_frame", None


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
    if decl["kind"] in ("selector", "geometry") and artifact.get("kind") != decl["kind"]:
        return "unsupported_profile", None
    if decl["kind"] == "selector":
        if artifact.get("offset_unit") not in OFFSET_UNITS:
            return "unsupported_profile", None  # unimplemented segmentation
        if artifact.get("endpoints") not in ENDPOINTS:
            return "unsupported_profile", None
    if decl["kind"] == "geometry":
        frames = artifact.get("frames")
        if not (isinstance(frames, list) and frames and all(isinstance(f, dict) and f.get("name") for f in frames)):
            return "unsupported_profile", None
    if decl["kind"] in ("carrier-inventory", "adapter-manifest"):
        # artifact grammar itself is verified by dsc03.coverage
        if not all(isinstance(artifact.get(k), str) and artifact[k] for k in ("version", "source_format")):
            return "unsupported_profile", None
    return "resolved", artifact
