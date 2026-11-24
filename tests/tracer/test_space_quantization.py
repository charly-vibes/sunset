# Purpose: Witness the quantized-geometry laws (add-anchor-derived-identity
#   §4, sunset-7af): a declared-quantum box quantizer with a pinned rounding
#   rule, an explicit quantization transform record in the native evidence
#   convention, and an exact (tolerance-0) rot90 round trip over REAL
#   carrier word boxes.
# Responsibilities: (1) quantize_box rounds half-even at the declared
#   quantum and is applied once (quantization_quantum, quantization_ties),
#   (2) quantization_transform_record names quantum, rounding rule and
#   extractor version with native.py field names (quantization_record),
#   (3) quantized real boxes from fixtures/carriers/budgeting-basics-excerpt.pdf
#   page 1 round trip through transform_rot90 EXACTLY (rotation_round_trip).
# Rationale: rot90 is exact on integers; quantization is what makes real
#   boxes integers, so the tolerance-0 claim is grounded in a real-carrier
#   property, not a fixture-family assertion.
import pymupdf
import pytest

from dsc03.substrate import space


CARRIER = "fixtures/carriers/budgeting-basics-excerpt.pdf"


class TestQuantization:
    def test_quantization_quantum(self):
        """Exact quantized geometry: boxes quantize to integers in the
        declared quantum (default 1/1000 pt), applied once; the
        pre-quantization float is not retained."""
        box = {"x": 71.87750244140625, "y": 194.672119140625,
               "width": 75.94586181640625, "height": 10.958999633789062}
        q = space.quantize_box(box)
        assert all(type(v) is int for v in q.values()), q
        assert q == {"x": 71878, "y": 194672, "width": 75946,
                     "height": 10959}
        # Declared quantum is 1/1000 pt: dividing by the scale recovers pt.
        assert q["x"] == round(box["x"] * 1000)

    def test_quantization_ties(self):
        """Declared rounding rule: round-half-even (banker's rounding),
        pinned explicitly — 0.0005 pt ties round to even, never
        round-half-up by accident."""
        # 1.0005 * 1000 = 1000.5 -> tie -> even -> 1000
        assert space.quantize_box({"x": 1.0005, "y": 0.0, "width": 0.0,
                                   "height": 0.0})["x"] == 1000
        # 1.0015 * 1000 = 1001.5 -> tie -> even -> 1002
        assert space.quantize_box({"x": 1.0015, "y": 0.0, "width": 0.0,
                                   "height": 0.0})["x"] == 1002
        # Non-tie cases are ordinary rounding.
        assert space.quantize_box({"x": 1.0019, "y": 0.0, "width": 0.0,
                                   "height": 0.0})["x"] == 1002


class TestQuantizationRecord:
    def test_quantization_record(self):
        """The quantization is recorded as an explicit transform naming
        quantum, rounding rule and extractor version, in the native
        evidence transform dict convention (id/version/config_sha256/
        dependencies/inputs/outputs)."""
        rec = space.quantization_transform_record(
            config_sha256="abc123",
            dependencies=["pymupdf@1.0"],
            inputs=["native-text-1"], outputs=["native-text-1"])
        assert rec["id"] == "box-quantization"
        assert rec["version"] == "1"
        assert rec["quantum"] == space.QUANTUM
        assert rec["rounding"] == "round-half-even"
        assert rec["extractor_version"] == pymupdf.VersionBind
        assert rec["config_sha256"] == "abc123"
        assert rec["dependencies"] == ["pymupdf@1.0"]
        assert rec["inputs"] == ["native-text-1"]
        assert rec["outputs"] == ["native-text-1"]
        assert list(rec)[:2] == ["id", "version"]


class TestRotationRoundTrip:
    def test_rotation_round_trip(self):
        """Rotation round trip (deployed scenario): quantized real carrier
        word boxes transformed forward and back through rot90 are EQUAL
        EXACTLY — the declared tolerance is 0 because the boxes are
        integers after quantization, not because the fixtures are
        convenient."""
        page = pymupdf.open(CARRIER)[0]
        w, h = page.rect.width, page.rect.height
        qh = space.quantize_scalar(h)
        t = space.transform_rot90(space.quantize_scalar(w), qh)
        words = page.get_text("words")
        assert words, "carrier page 1 must yield native word boxes"
        exact = 0
        for wd in words:
            x0, y0, x1, y1 = wd[:4]
            src = {"space": "page-1-pt",
                   "x": space.quantize_scalar(x0),
                   "y": space.quantize_scalar(y0),
                   "width": space.quantize_scalar(x1 - x0),
                   "height": space.quantize_scalar(y1 - y0)}
            roundtripped = space.normalize(t, space.denormalize(t, src))
            assert roundtripped == src, (src, roundtripped)
            assert space.within_tolerance(roundtripped, src,
                                          t.tolerance) is True
            exact += 1
        assert exact == len(words)


def test_non_finite_coordinates_are_refused():
    """Non-finite extractor output is malformed input, never quantizable
    geometry (rule-of-5 EDGE-001): quantize_scalar refuses it typed."""
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="non-finite"):
            space.quantize_scalar(bad)
