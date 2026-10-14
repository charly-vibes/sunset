# Purpose: Profile artifact grammar tests — selector offset units and geometry
#   frames (sunset-r68.5, tasks.md 2.1 + 2.3).
# Responsibilities: Resolve concrete selector and geometry profiles from the local
#   registry; apply text-range locators under declared offset units (scalar vs
#   UTF-8 bytes select different ranges of the same string; closed vs half-open
#   endpoints); reject reversed/out-of-bounds/code-point-splitting ranges with
#   invalid_selector; report unimplemented segmentation as unsupported_profile;
#   resolve named geometry frames and yield invalid_geometry_frame for a missing
#   frame and unsupported_profile for an unavailable declared profile.
# Rationale: add-dsc-03 document-evidence "Typed profile-defined source selectors"
#   and document-adapters "Declared coordinate frames".
"""Profile artifact grammar tests (sunset-r68.5)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03 import profiles

PROFILES = Path(__file__).parent / "profiles"
VALUE = "AéB"  # A, U+00E9 (2 UTF-8 bytes), B


def decl(uri, kind="selector"):
    return {
        "id": "p-x",
        "kind": kind,
        "uri": uri,
        "version": "1",
        "sha256": hashlib.sha256((PROFILES / uri).read_bytes()).hexdigest(),
    }


def res(uri, kind="selector"):
    return profiles.resolve(decl(uri, kind), profiles.Registry(PROFILES))


def sel(locator, artifact, value=VALUE):
    return profiles.apply_text_range(value, locator, artifact)


# -- selector offset units ----------------------------------------------------
def test_scalar_half_open_selects_the_accent():
    status, artifact = res("selector-text-scalar.json")
    assert (status, artifact["offset_unit"]) == ("resolved", "unicode-scalar-values")
    status, out = sel("[1,2)", artifact)
    assert (status, out) == ("selected", "é")


def test_byte_half_open_selects_the_same_character():
    status, artifact = res("selector-text-bytes.json")
    assert (status, artifact["offset_unit"]) == ("resolved", "utf-8-bytes")
    status, out = sel("[1,3)", artifact)
    assert (status, out) == ("selected", "é")


def test_byte_range_splitting_a_code_point_is_invalid_selector():
    status, artifact = res("selector-text-bytes.json")
    assert sel("[1,2)", artifact)[0] == "invalid_selector"


def test_closed_endpoints_are_inclusive():
    status, artifact = res("selector-text-closed.json")
    assert artifact["endpoints"] == "closed"
    status, out = sel("[1,2]", artifact)
    assert (status, out) == ("selected", "éB")


def test_reversed_range_is_invalid_selector():
    status, artifact = res("selector-text-scalar.json")
    assert sel("[2,1)", artifact)[0] == "invalid_selector"


def test_out_of_bounds_range_is_invalid_selector():
    status, artifact = res("selector-text-scalar.json")
    assert sel("[0,99)", artifact)[0] == "invalid_selector"


def test_malformed_locator_is_invalid_selector():
    status, artifact = res("selector-text-scalar.json")
    assert sel("(1,2)", artifact)[0] == "invalid_selector"


def test_unimplemented_segmentation_is_unsupported_profile():
    # a grapheme-cluster profile requires a segmentation algorithm this
    # implementation does not provide — declared, not guessed
    status, artifact = res("selector-text-graphemes.json")
    assert status == "unsupported_profile"


# -- geometry frames ----------------------------------------------------------
def test_geometry_frame_resolves():
    status, artifact = res("geometry-page-pt.json", kind="geometry")
    assert status == "resolved"
    status, frame = profiles.resolve_frame(artifact, "page-1")
    assert status == "resolved"
    assert frame["unit"] == "pt" and frame["origin"] == "bottom-left"
    assert frame["source_scope"] == "page:1"


def test_missing_frame_is_invalid_geometry_frame():
    status, artifact = res("geometry-page-pt.json", kind="geometry")
    assert profiles.resolve_frame(artifact, "page-99")[0] == "invalid_geometry_frame"


def test_unavailable_geometry_profile_is_unsupported(tmp_path):
    status, artifact = profiles.resolve(
        decl("geometry-page-pt.json", kind="geometry"), profiles.Registry(tmp_path)
    )
    assert status == "unsupported_profile"
