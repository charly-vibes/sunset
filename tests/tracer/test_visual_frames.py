# Purpose: Declared frame mapping tests (sunset-xzy.2, tasks.md 3.2).
# Responsibilities: Pin the document-visual-oracles "Declared frame mapping"
#   requirement: pixel↔descriptor coordinates resolve ONLY through a declared
#   geometry profile frame, derived exclusively from the declared frame fields
#   (unit, origin/axes, scale, rotation, crop, source_scope); missing,
#   incompatible, ambiguous or non-resolvable frames yield a typed `unknown`
#   outcome — never a guessed coordinate convention, never an identity
#   fallback, and never `agree`/`differ` (comparison verdicts belong to the
#   oracle's 4.x tasks, not coordinate resolution). Expected pixels in the
#   rotation tests are hand-computed against the declared convention and
#   pinned by the module's pixel tolerance constant; round-trips recover the
#   original descriptor point within that same tolerance.
# Rationale: design rule — wrong frames must never yield a coordinate verdict;
#   spec scenarios "Rotated page" and "Missing frame".
"""Declared frame mapping (pixel↔descriptor) tests (sunset-xzy.2)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import frames
from dsc03.visual.render import RenderConfig

PROFILES = Path(__file__).resolve().parent / "profiles"


def _artifact(name):
    return json.loads((PROFILES / name).read_text())


def _render_config(dpi=72, page=1):
    return RenderConfig(
        renderer_name="poppler-pdftoppm",
        renderer_executable="/usr/bin/pdftoppm",
        renderer_version="24.02",
        dpi=dpi,
        page=page,
        extractor_lineage="pymupdf-1.24",
        renderer_lineage="poppler-24.02",
    )


# --- (a) native carrier: canonical pt frame, rotation 0, matching page -------


def test_native_frame_resolves_and_maps_known_point():
    artifact = _artifact("geometry-page-pt.json")
    config = _render_config(dpi=72, page=1)
    result = frames.frame_mapping(artifact, "page-1", config, (612, 792))
    assert isinstance(result, frames.PixelMapping)
    assert result.status == "resolved"
    # 72dpi ⇒ 1pt = 1px; y=650pt up from bottom-left ⇒ 792-650 = 142px down
    # from top. Hand-computed, not code-derived.
    assert result.descriptor_to_pixel(100.0, 650.0) == (100.0, 142.0)


def test_native_frame_unit_scale_at_144dpi():
    artifact = _artifact("geometry-page-pt.json")
    config = _render_config(dpi=144, page=1)
    result = frames.frame_mapping(artifact, "page-1", config, (1224, 1584))
    assert isinstance(result, frames.PixelMapping)
    # 144dpi ⇒ 1pt = 2px; y=650pt from bottom of a 792pt page ⇒ 142pt from
    # top ⇒ 284px from top; x=100pt ⇒ 200px.
    assert result.descriptor_to_pixel(100.0, 650.0) == (200.0, 284.0)


def test_native_frame_inverse_pixel_to_descriptor():
    artifact = _artifact("geometry-page-pt.json")
    result = frames.frame_mapping(
        _artifact("geometry-page-pt.json"), "page-1",
        _render_config(dpi=72, page=1), (612, 792),
    )
    assert isinstance(result, frames.PixelMapping)
    assert result.pixel_to_descriptor(100.0, 142.0) == (100.0, 650.0)


def test_round_trip_recovers_descriptor_points_within_pinned_tolerance():
    artifact = _artifact("geometry-page-pt.json")
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=144, page=1), (1224, 1584)
    )
    assert isinstance(result, frames.PixelMapping)
    for point in [(0.0, 0.0), (306.0, 396.0), (611.5, 791.25), (0.375, 12.75)]:
        pixel = result.descriptor_to_pixel(*point)
        recovered = result.pixel_to_descriptor(*pixel)
        assert abs(recovered[0] - point[0]) <= frames.PINNED_PIXEL_TOLERANCE_PX
        assert abs(recovered[1] - point[1]) <= frames.PINNED_PIXEL_TOLERANCE_PX


# --- (b) rotated carrier: declared rotation, hand-computed pixels ------------


def test_rotated_90_maps_to_hand_computed_pixel():
    artifact = _artifact("geometry-rotated-page.json")
    # rotation 90: the 612x792pt page raster appears as a 792x612 raster.
    result = frames.frame_mapping(
        artifact, "page-1-rot90", _render_config(dpi=72, page=1), (792, 612)
    )
    assert isinstance(result, frames.PixelMapping)
    # Descriptor (100, 650): unrotated y-down v = (100, 792-650=142); 90° CW
    # maps (x, y) -> (H0 - y, x) = (792-142, 100) = (650, 100). Hand-computed.
    assert result.descriptor_to_pixel(100.0, 650.0) == (650.0, 100.0)


def test_rotated_180_maps_to_hand_computed_pixel():
    artifact = _artifact("geometry-rotated-page.json")
    result = frames.frame_mapping(
        artifact, "page-1-rot180", _render_config(dpi=72, page=1), (612, 792)
    )
    assert isinstance(result, frames.PixelMapping)
    # Descriptor (100, 650): v = (100, 142); 180° maps (x, y) -> (W0-x, H0-y)
    # = (612-100, 792-142) = (512, 650). Hand-computed.
    assert result.descriptor_to_pixel(100.0, 650.0) == (512.0, 650.0)


def test_rotated_frames_round_trip_within_pinned_tolerance():
    artifact = _artifact("geometry-rotated-page.json")
    rot90 = frames.frame_mapping(
        artifact, "page-1-rot90", _render_config(dpi=144, page=1), (1584, 1224)
    )
    rot180 = frames.frame_mapping(
        artifact, "page-1-rot180", _render_config(dpi=144, page=1), (1224, 1584)
    )
    for mapping in (rot90, rot180):
        assert isinstance(mapping, frames.PixelMapping)
        for point in [(0.0, 0.0), (306.0, 396.0), (611.5, 791.25)]:
            pixel = mapping.descriptor_to_pixel(*point)
            recovered = mapping.pixel_to_descriptor(*pixel)
            assert abs(recovered[0] - point[0]) <= frames.PINNED_PIXEL_TOLERANCE_PX
            assert abs(recovered[1] - point[1]) <= frames.PINNED_PIXEL_TOLERANCE_PX


# --- (c) cropped carrier: declared crop offset honored ------------------------


def test_cropped_frame_honors_declared_offset():
    artifact = _artifact("geometry-cropped-page.json")
    result = frames.frame_mapping(
        artifact, "page-1-crop", _render_config(dpi=72, page=1), (612, 792)
    )
    assert isinstance(result, frames.PixelMapping)
    # crop offset (36, 72)pt is added in descriptor space before the rest of
    # the pipeline: (10+36, 20+72) = (46, 92)pt ⇒ v = (46, 792-92=700).
    assert result.descriptor_to_pixel(10.0, 20.0) == (46.0, 700.0)
    # Round trip: pixel -> descriptor undoes the declared offset exactly.
    assert result.pixel_to_descriptor(46.0, 700.0) == (10.0, 20.0)


# --- (d) missing frame name ---------------------------------------------------


def test_missing_frame_name_yields_unknown_and_not_a_mapping():
    artifact = _artifact("geometry-page-pt.json")
    result = frames.frame_mapping(
        artifact, "no-such-frame", _render_config(dpi=72, page=1), (612, 792)
    )
    assert not isinstance(result, frames.PixelMapping)
    assert result.status == "unknown"
    assert result.reason == "invalid_geometry_frame"


# --- (e) unsupported / unknown unit -------------------------------------------


def test_unit_px_is_unsupported_not_assumed():
    artifact = {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "px",
            "origin": "bottom-left",
            "axes": "x-right-y-up",
            "scale": [1, 1],
            "rotation": 0,
            "crop": None,
            "source_scope": "page:1",
        }],
    }
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert not isinstance(result, frames.PixelMapping)
    assert result.status == "unknown"
    assert result.reason == "unsupported_unit"


def test_unknown_unit_is_unknown():
    artifact = {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "em-furlongs",
            "origin": "bottom-left",
            "axes": "x-right-y-up",
            "scale": [1, 1],
            "rotation": 0,
            "crop": None,
            "source_scope": "page:1",
        }],
    }
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert result.status == "unknown"
    assert result.reason == "unsupported_unit"


# --- (f) source_scope page binding ---------------------------------------------


def test_source_scope_page_mismatch_is_unknown():
    artifact = _artifact("geometry-page-pt.json")  # frame binds "page:1"
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=2), (612, 792)
    )
    assert not isinstance(result, frames.PixelMapping)
    assert result.status == "unknown"
    assert result.reason == "unresolvable_source_scope"


def test_missing_source_scope_is_ambiguous_unknown():
    artifact = {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "pt",
            "origin": "bottom-left",
            "axes": "x-right-y-up",
            "scale": [1, 1],
            "rotation": 0,
            "crop": None,
        }],
    }
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert result.status == "unknown"
    assert result.reason == "unresolvable_source_scope"


# --- (g) invalid artifact through the profiles.resolve_frame path --------------


def test_non_geometry_artifact_yields_invalid_geometry_frame_unknown():
    artifact = _artifact("selector-text-scalar.json")  # kind != geometry
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert not isinstance(result, frames.PixelMapping)
    assert result.status == "unknown"
    assert result.reason == "invalid_geometry_frame"


def test_unresolvable_frame_is_never_identity_fallback():
    # The dangerous failure mode: an unresolvable frame silently mapping like
    # the canonical frame. UnknownMapping must expose no transforms at all.
    artifact = _artifact("geometry-page-pt.json")
    result = frames.frame_mapping(
        artifact, "no-such-frame", _render_config(dpi=72, page=1), (612, 792)
    )
    assert result.status == "unknown"
    assert not hasattr(result, "descriptor_to_pixel")
    assert not hasattr(result, "pixel_to_descriptor")


# --- outcome vocabulary ---------------------------------------------------------


def test_outcomes_are_resolved_or_unknown_only_never_verdicts():
    # Comparison verdicts (agree/differ) belong to oracle tasks 4.x; this
    # module's outcome vocabulary is exactly {resolved, unknown}.
    assert set(frames.OUTCOME_STATUSES) == {"resolved", "unknown"}
    assert "agree" not in frames.OUTCOME_STATUSES
    assert "differ" not in frames.OUTCOME_STATUSES


def test_unsupported_rotation_is_unknown_never_guessed():
    artifact = {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "pt",
            "origin": "bottom-left",
            "axes": "x-right-y-up",
            "scale": [1, 1],
            "rotation": 45,
            "crop": None,
            "source_scope": "page:1",
        }],
    }
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert result.status == "unknown"
    assert result.reason == "unsupported_rotation"


def test_non_canonical_axes_is_unknown_never_guessed():
    artifact = {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "pt",
            "origin": "top-left",
            "axes": "x-right-y-down",
            "scale": [1, 1],
            "rotation": 0,
            "crop": None,
            "source_scope": "page:1",
        }],
    }
    result = frames.frame_mapping(
        artifact, "page-1", _render_config(dpi=72, page=1), (612, 792)
    )
    assert result.status == "unknown"
    assert result.reason == "unsupported_axes"


# --- (h) extent binding via source_dimensions (tasks 2.2, design D2) ---------


def _extent_frame(rotation, dims):
    return {
        "kind": "geometry",
        "version": "1",
        "subunit": "integers-are-points",
        "frames": [{
            "name": "page-1",
            "unit": "pt",
            "origin": "bottom-left",
            "axes": "x-right-y-up",
            "scale": [1, 1],
            "rotation": rotation,
            "crop": None,
            "source_scope": "page:1",
            "source_dimensions": dims,
        }],
    }


def test_extent_rotation0_matches_declared_extent():
    # 612x792 pt at 72 dpi -> exactly (612, 792) pixels.
    result = frames.frame_mapping(
        _extent_frame(0, [612.0, 792.0]),
        "page-1", _render_config(dpi=72, page=1), (612, 792))
    assert result.status == "resolved"
    assert result.page_px == (612, 792)


def test_extent_rotation90_swaps_width_height_hand_computed():
    # 612x792 pt at 150 dpi -> round(1275.0) x round(1650.0); rotation 90
    # renders the raster rotated, so the expected extent is (1650, 1275).
    result = frames.frame_mapping(
        _extent_frame(90, [612.0, 792.0]),
        "page-1", _render_config(dpi=150, page=1), (1650, 1275))
    assert result.status == "resolved"
    assert result.page_px == (1650, 1275)


def test_extent_rotation270_swaps_width_height_hand_computed():
    # 612x792 pt at 100 dpi -> round(850.0) x round(1100.0); rotation 270
    # swaps exactly like 90 (same _forward_axes convention).
    result = frames.frame_mapping(
        _extent_frame(270, [612.0, 792.0]),
        "page-1", _render_config(dpi=100, page=1), (1100, 850))
    assert result.status == "resolved"
    assert result.page_px == (1100, 850)


def test_extent_mismatch_is_typed_page_extent_mismatch():
    result = frames.frame_mapping(
        _extent_frame(0, [612.0, 792.0]),
        "page-1", _render_config(dpi=72, page=1), (600, 792))
    assert result.status == "unknown"
    assert result.reason == "page-extent-mismatch"


def test_extent_mismatch_on_unswapped_rotated_extent_is_unknown():
    # Feeding the UNswapped extent to a 90-degree frame is exactly the
    # double-swap mistake the check exists to catch.
    result = frames.frame_mapping(
        _extent_frame(90, [612.0, 792.0]),
        "page-1", _render_config(dpi=150, page=1), (1275, 1650))
    assert result.status == "unknown"
    assert result.reason == "page-extent-mismatch"


def test_frame_without_source_dimensions_skips_extent_check():
    frame = _extent_frame(0, [612.0, 792.0])
    del frame["frames"][0]["source_dimensions"]
    result = frames.frame_mapping(
        frame, "page-1", _render_config(dpi=72, page=1), (300, 400))
    assert result.status == "resolved"


def test_malformed_source_dimensions_is_unknown():
    result = frames.frame_mapping(
        _extent_frame(0, [612.0]), "page-1",
        _render_config(dpi=72, page=1), (612, 792))
    assert result.status == "unknown"
    assert result.reason == "malformed_frame"


# --- (i) crop-box render support (tasks 2.1, design D1) -----------------------


def test_supports_cropbox_version_boundaries():
    from dsc03.visual.render import supports_cropbox
    assert supports_cropbox("0.26.0") is True
    assert supports_cropbox("0.26") is True
    assert supports_cropbox("0.25.4") is False
    assert supports_cropbox("0.25") is False
    assert supports_cropbox("26.01.0") is True  # new-style poppler versioning
    assert supports_cropbox("0.90.0") is True
    assert supports_cropbox("") is False
    assert supports_cropbox("unknown") is False


def test_render_config_cropbox_defaults_and_round_trips():
    from dsc03.visual.render import RenderConfig
    config = RenderConfig(
        renderer_name="pdftoppm", renderer_executable="pdftoppm",
        renderer_version="26.01.0", dpi=150, page=1,
        extractor_lineage="pymupdf-1.28.2", renderer_lineage="poppler-26.01.0")
    assert config.render_cropbox is False  # recorded configs load unchanged
    record = config.to_dict()
    assert record["render_cropbox"] is False
    assert RenderConfig.from_dict(record) == config
    pinned = dict(record, render_cropbox=True)
    assert RenderConfig.from_dict(pinned).render_cropbox is True
