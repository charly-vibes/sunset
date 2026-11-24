# Purpose: Per-page sensitivity-certificate suite (sunset-7b4.5). Pins the
#   certificate mechanism added in dsc03/visual/certificates.py: per-page
#   typed records (certified / unknown with reason `certificate-unsupported`
#   carrying the failing condition), thresholds derived from the seeded
#   mutation classes each oracle property claims (ink-coverage: omission,
#   duplication; region-alignment: shift, wrong frame — deployed spec
#   "Mutation-validated sensitivity", claim mapping pinned in
#   test_visual_mutations.py), determinism across processes, and the EDGE-002
#   BINDING CONSTRAINT: certification is per-page ONLY — a dense page that
#   cannot be certified carries a typed per-page reason and neither blocks
#   sibling pages nor aggregates into any permanent uncertified status (this
#   suite pins the absence of any aggregate-blocking API).
# Responsibilities: Render the committed mutation fixtures through the pinned
#   RenderConfig exactly as test_visual_mutations.py does; derive
#   certificates through dsc03/visual/certificates.py; demonstrate the
#   certified bands against the REAL oracles (a seeded defect strictly below
#   the certificate threshold keeps the oracle at `agree` — the
#   certified-unsensitive attribution; at/above it the oracle flips to
#   `differ`); and prove per-page independence and cross-process
#   determinism. Hand-derived check numbers below come from the committed
#   fixture geometry (visual-strip: 300x24 pt ink strip, integer-exact at
#   72 dpi) and the recorded bounds; every oracle verdict is agent-executed.
# Rationale: improve-geometry-render-binding proposal.md Non-goals records
#   the deferred certificate requirement with the EDGE-002 tension; this
#   suite pins the mechanism that resolves it without aggregate blocking.
"""Per-page sensitivity certificate tests (sunset-7b4.5)."""
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import certificates, coverage, masks, render
from dsc03.visual._pixels import comparison_mask
from dsc03.visual.render import Rendered

from conftest import make_carrier, render_config

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visual"
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

# Committed visual-strip geometry (hand-computed, seed-free; see the
# fixtures README and test_visual_mutations.py): 300x24 pt ink strip,
# integer-exact raw ink at raster px x 100..400, y 468..492; the pinned
# ink-dilation-2px simplification grows it to x 98..402, y 466..494
# (304x28 = 8512 px on a 612x792 = 484,704 px page).
REGION_INK_STRIP = {"id": "ink-strip", "x": 100, "y": 300, "w": 300, "h": 24,
                    "expected": "ink"}
REGION_BLANK_LOWER = {"id": "blank-lower", "x": 100, "y": 60, "w": 300, "h": 24,
                      "expected": "no-ink"}
ALN_BOUNDS = {"min": 0.95, "max": 1.0}
COV_BOUNDS = {"min": 0.01, "max": 1.0}

STRIP_RAW_INK_PX = 300 * 24
STRIP_SIMPLIFIED_INK_PX = 304 * 28
PAGE_AREA = 612 * 792


def _calibration(property_name, carrier, bounds):
    return {"property": property_name, "carrier": carrier, "page": 1,
            "min": bounds["min"], "max": bounds["max"]}


def _geometry():
    return json.loads((PROFILES_DIR / "geometry-page-pt.json").read_text())


def _rendered(fixture_name="visual-strip.pdf", config=None):
    result = render.render_page(config or render_config(),
                                FIXTURES_DIR / fixture_name)
    assert isinstance(result, render.Rendered), getattr(result, "reason", result)
    return result


def _strip_regions():
    return [dict(REGION_INK_STRIP), dict(REGION_BLANK_LOWER)]


def _coverage_certificate(fixture="visual-strip.pdf", carrier="visual-strip",
                          regions=None, calibration=None, rendered=None):
    regions = _strip_regions() if regions is None else regions
    calibration = (calibration if calibration is not None
                   else _calibration("ink-coverage", carrier, COV_BOUNDS))
    rendered = rendered or _rendered(fixture)
    outcome = coverage.coverage_outcome(
        rendered, carrier=carrier, regions=regions, calibration=calibration,
        geometry=_geometry(), frame_name="page-1",
    )
    cert = certificates.sensitivity_certificate(
        outcome, render_result=rendered, regions=regions,
        calibration=calibration, geometry=_geometry(), frame_name="page-1",
    )
    return outcome, cert


def _alignment_certificate(fixture="visual-strip.pdf", carrier="visual-strip",
                           regions=None, calibration=None, rendered=None):
    regions = _strip_regions() if regions is None else regions
    calibration = (calibration if calibration is not None
                   else _calibration("region-alignment", carrier, ALN_BOUNDS))
    rendered = rendered or _rendered(fixture)
    outcome = masks.masks_outcome(
        rendered, carrier=carrier, regions=regions, calibration=calibration,
        geometry=_geometry(), frame_name="page-1",
    )
    cert = certificates.sensitivity_certificate(
        outcome, render_result=rendered, regions=regions,
        calibration=calibration, geometry=_geometry(), frame_name="page-1",
    )
    return outcome, cert


def _entry(cert, class_name):
    matches = [e for e in cert.thresholds if e["class"] == class_name]
    assert len(matches) == 1, (class_name, cert.thresholds)
    return matches[0]


def _erase_rect(raw, width, height, x0, y0, w, h):
    """Zero the raw ink inside the half-open pixel rect (seeded omission)."""
    for y in range(y0, min(y0 + h, height)):
        base = y * width
        raw[base + x0:base + min(x0 + w, width)] = b"\x00" * (
            min(x0 + w, width) - x0)
    return raw


def _translate_diagonal(raw, width, height, s):
    """Translate the raw ink by (+s, +s) px (seeded shift defect shape)."""
    out = bytearray(len(raw))
    for y in range(height - s):
        src = y * width
        dst = (y + s) * width + s
        out[dst:dst + width - s] = raw[src:src + width - s]
    return out


def _mask_png(raw, width, height):
    """Deterministic 8-bit grayscale PNG bytes: mask px 1 -> gray 0 (ink)."""
    import struct
    import zlib

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    table = bytes.maketrans(b"\x00\x01", b"\xff\x00")  # ink -> 0, paper -> 255
    scanlines = b"".join(
        b"\x00" + raw[y * width:(y + 1) * width].translate(table)
        for y in range(height))
    idat = zlib.compress(scanlines, 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


# --- per-class thresholds on the committed strip fixture ----------------------


def test_coverage_certificate_thresholds_on_strip():
    # Hand-derived from the committed fixture geometry and COV_BOUNDS
    # (agent-executed): simplified page ink 8512/484704 -> page omission
    # margin (8512/484704 - 0.01) * 484704 = 3664.96 simplified-ink px;
    # strip region margin (1.0 - 0.01) * 7200 = 7128 px; no-ink region
    # duplication margin (0.01 - 0.0) * 7200 = 72 px; page duplication
    # margin (1.0 - 8512/484704) * 484704 = 476192 px.
    outcome, cert = _coverage_certificate()
    assert outcome.status == "agree", outcome
    assert cert.status == "certified", cert
    assert cert.reason is None and cert.condition is None
    assert cert.outcome_status == "agree"
    assert cert.property == "ink-coverage"

    omission = _entry(cert, "omission")
    assert omission["unit"] == "simplified-ink-px"
    assert omission["threshold"] == pytest.approx(3664.96, rel=1e-9)
    assert omission["governing-scope"] == "page"
    scopes = dict(omission["scopes"])
    assert scopes["region:ink-strip"] == pytest.approx(7128.0, rel=1e-9)
    assert scopes["page"] == pytest.approx(3664.96, rel=1e-9)

    duplication = _entry(cert, "duplication")
    assert duplication["threshold"] == pytest.approx(72.0, rel=1e-9)
    assert duplication["governing-scope"] == "region:blank-lower"
    assert dict(duplication["scopes"])["page"] == pytest.approx(476192.0)

    bands = {b["class"]: b["threshold"] for b in cert.unsensitive_below}
    assert bands["omission"] == omission["threshold"]
    assert bands["duplication"] == duplication["threshold"]


def test_alignment_certificate_thresholds_on_strip():
    # Hand-derived (agent-executed): dilation d=2, low=0.95, strip rect
    # 300x24 px. The seeded shift defect shape is the diagonal (+s, +s) px
    # translation; post-shift rect ink is bounded by
    # (300-s+2)*(24-s+2) px, so `differ` is guaranteed once that product
    # drops below 0.95*7200 = 6840: (302-3)*(26-3) = 6877 >= 6840, but
    # (302-4)*(26-4) = 6556 < 6840 -> threshold s* = 4 px-diagonal.
    outcome, cert = _alignment_certificate()
    assert outcome.status == "agree", outcome
    assert cert.status == "certified", cert
    assert cert.property == "region-alignment"

    shift = _entry(cert, "shift")
    assert shift["unit"] == "px-diagonal"
    assert shift["threshold"] == 4
    assert shift["governing-scope"] == "region:ink-strip"

    wrong_frame = _entry(cert, "wrong-frame")
    assert wrong_frame["unit"] == "px-diagonal"
    assert wrong_frame["threshold"] == 4
    assert wrong_frame.get("derived") is True


# --- certified-unsensitive demonstrations against the REAL oracles -----------


def test_seeded_shift_below_threshold_stays_agree():
    # Certified-unsensitive attribution, demonstrated (agent-executed): a
    # diagonal shift of 3 px is strictly below the certificate threshold of
    # 4 px, and the REAL alignment oracle still agrees; at exactly the
    # threshold the oracle flips to `differ`. Detection is attributable to
    # crossing the certified band edge, never to baseline miscalibration.
    rendered = _rendered()
    _, cert = _alignment_certificate(rendered=rendered)
    threshold = _entry(cert, "shift")["threshold"]
    config = rendered.config
    width, height, raw, _simplified = comparison_mask(rendered, config)

    below = masks.masks_outcome(
        Rendered(config=config, data=_mask_png(
            _translate_diagonal(raw, width, height, threshold - 1),
            width, height)),
        carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("region-alignment", "visual-strip", ALN_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert below.status == "agree", below

    at = masks.masks_outcome(
        Rendered(config=config, data=_mask_png(
            _translate_diagonal(raw, width, height, threshold),
            width, height)),
        carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("region-alignment", "visual-strip", ALN_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert at.status == "differ", at


def test_seeded_omission_below_threshold_stays_agree():
    # Certified-unsensitive attribution, demonstrated (agent-executed): the
    # governing page-scope omission threshold is ~3664.96 simplified-ink px.
    # Erasing k full-height 40-px-wide raw columns from the solid strip
    # creates a simplified hole of (40k - 4) x 24 px (the 2 px dilation ring
    # survives at both ends): k=3 -> 2784 px below the threshold, and the
    # REAL coverage oracle agrees; k=4 -> 3744 px above it, and the oracle
    # flips to `differ`.
    rendered = _rendered()
    _, cert = _coverage_certificate(rendered=rendered)
    threshold = _entry(cert, "omission")["threshold"]
    config = rendered.config
    width, height, raw, _simplified = comparison_mask(rendered, config)

    def erased(k):
        return _erase_rect(bytearray(raw), width, height, 100, 468, 40 * k, 24)

    below = coverage.coverage_outcome(
        Rendered(config=config, data=_mask_png(erased(3), width, height)),
        carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert below.status == "agree", below

    above = coverage.coverage_outcome(
        Rendered(config=config, data=_mask_png(erased(4), width, height)),
        carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert above.status == "differ", above


# --- differ baseline: margins clamp at zero, nothing invented -----------------


def test_differ_outcome_certificate_margins_clamped():
    # The committed seeded-omission fixture ends `differ` (strip absent);
    # the certificate still records per-page sensitivity, with the omission
    # margins clamped at 0 (the current state is already out of window at
    # magnitude zero) and no unsensitive band for a zero threshold.
    outcome, cert = _coverage_certificate(fixture="visual-strip-omission.pdf")
    assert outcome.status == "differ", outcome
    assert cert.status == "certified", cert
    assert cert.outcome_status == "differ"
    omission = _entry(cert, "omission")
    assert omission["threshold"] == 0.0
    assert dict(omission["scopes"])["region:ink-strip"] == 0.0
    bands = {b["class"]: b["threshold"] for b in cert.unsensitive_below}
    assert "omission" not in bands
    assert bands["duplication"] == pytest.approx(72.0, rel=1e-9)


# --- dense pages: typed per-page verdicts, never a global block (EDGE-002) ---


def _dense_carrier(tmp_path, name):
    # Two full-width inked bands (~76% of the page): a genuinely dense page.
    return make_carrier(tmp_path, name,
                        rects=[(0, 0, 612, 300), (0, 492, 612, 792)],
                        width=612, height=792)


def test_dense_page_gets_per_page_verdict_never_blocks(tmp_path):
    # EDGE-002 BINDING CONSTRAINT (agent-executed): the dense page is a
    # first-class per-page verdict. A CALIBRATED dense page certifies
    # normally (dense pages are not second-class); a dense page with no
    # recorded calibration produces a typed per-page `unknown` with reason
    # `certificate-unsupported` and the failing condition carried verbatim;
    # and the sparse page's certificate is completely unaffected — the
    # module has no aggregate API to block through, ever.
    dense_path = _dense_carrier(tmp_path, "dense.pdf")
    dense_rendered = render.render_page(render_config(), dense_path)
    assert isinstance(dense_rendered, render.Rendered), dense_rendered
    dense_regions = [{"id": "dense-band", "x": 100, "y": 100, "w": 300,
                      "h": 100, "expected": "ink"}]

    uncalibrated_path = _dense_carrier(tmp_path, "dense-uncalibrated.pdf")
    uncal_rendered = render.render_page(render_config(), uncalibrated_path)

    sparse_outcome, sparse_cert = _coverage_certificate()
    assert sparse_cert.status == "certified"

    dense_outcome = coverage.coverage_outcome(
        dense_rendered, carrier="dense-carrier", regions=dense_regions,
        calibration=_calibration("ink-coverage", "dense-carrier", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    dense_cert = certificates.sensitivity_certificate(
        dense_outcome, render_result=dense_rendered, regions=dense_regions,
        calibration=_calibration("ink-coverage", "dense-carrier", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )

    uncal_outcome = coverage.coverage_outcome(
        uncal_rendered, carrier="dense-uncalibrated", regions=dense_regions,
        calibration=None, geometry=_geometry(), frame_name="page-1",
    )
    uncal_cert = certificates.sensitivity_certificate(
        uncal_outcome, render_result=uncal_rendered, regions=dense_regions,
        calibration=None, geometry=_geometry(), frame_name="page-1",
    )

    # The calibrated dense page certifies like any other page.
    assert dense_outcome.status == "agree", dense_outcome
    assert dense_cert.status == "certified", dense_cert
    assert _entry(dense_cert, "omission")["threshold"] > 0

    # The uncalibrated dense page carries a typed PER-PAGE unknown — never a
    # permanent global `uncertified` status, never a block of other pages.
    assert uncal_outcome.status == "unknown", uncal_outcome
    assert uncal_cert.status == "unknown"
    assert uncal_cert.reason == "certificate-unsupported"
    assert uncal_cert.condition == "uncalibrated"
    assert uncal_cert.outcome_status == "unknown"
    assert uncal_cert.thresholds == ()

    # Per-page independence: recomputing the sparse certificate after the
    # dense/unknown pages were certified yields the identical record — no
    # shared state, no aggregate gate to hide behind.
    _, sparse_again = _coverage_certificate()
    assert sparse_again == sparse_cert

    # Structural EDGE-002 pin: the certificate module exposes NO aggregate
    # blocking API at all — per-page records are the only output.
    assert not hasattr(certificates, "aggregate")


# --- typed certificate-unknown conditions -------------------------------------


def test_certificate_unknown_for_typed_oracle_failures(tmp_path):
    # Unavailable render, undecodable bytes and an unsupported property all
    # yield `unknown` certificates whose condition is carried verbatim —
    # per-page, vocabulary-compatible, never guessed into a verdict.
    missing = render_config(executable="/nonexistent/pdftoppm")
    unavailable_render = render.render_page(missing, FIXTURES_DIR
                                            / "visual-strip.pdf")
    assert isinstance(unavailable_render, render.RenderUnavailable)
    outcome = coverage.coverage_outcome(
        unavailable_render, carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    cert = certificates.sensitivity_certificate(
        outcome, render_result=unavailable_render, regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert cert.status == "unknown"
    assert cert.reason == "certificate-unsupported"
    assert cert.condition == outcome.reason
    assert cert.outcome_status == "unavailable"
    assert cert.thresholds == ()

    corrupt = Rendered(config=render_config(), data=b"not a png at all")
    outcome = coverage.coverage_outcome(
        corrupt, carrier="visual-strip", regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    cert = certificates.sensitivity_certificate(
        outcome, render_result=corrupt, regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert cert.status == "unknown"
    assert cert.condition == "render-decode-failed"
    assert cert.outcome_status == "unknown"

    class ForeignOutcome:
        property = "not-an-oracle-property"
        status = "agree"
        carrier = "visual-strip"

    cert = certificates.sensitivity_certificate(
        ForeignOutcome(), render_result=_rendered(), regions=_strip_regions(),
        calibration=_calibration("ink-coverage", "visual-strip", COV_BOUNDS),
        geometry=_geometry(), frame_name="page-1",
    )
    assert cert.status == "unknown"
    assert cert.condition == "unsupported-property:not-an-oracle-property"


def test_certificate_vocabulary_is_oracle_compatible():
    # Every certificate's outcome_status comes from the oracle outcome
    # vocabulary, and the certificate status vocabulary is exactly
    # {certified, unknown} — agree/differ certify (when margins are
    # computable), unknown/unavailable yield typed unknowns.
    cases = [
        _coverage_certificate(),
        _alignment_certificate(),
        _coverage_certificate(fixture="visual-strip-omission.pdf"),
    ]
    for outcome, cert in cases:
        assert cert.outcome_status == outcome.status
        assert cert.outcome_status in {"agree", "differ", "unknown",
                                       "unavailable"}
        assert cert.status in {"certified", "unknown"}
        if outcome.status in {"agree", "differ"}:
            assert cert.status == "certified"
            assert cert.reason is None
        else:
            assert cert.status == "unknown"
            assert cert.reason == "certificate-unsupported"
            assert cert.condition


# --- determinism across processes ---------------------------------------------


_SUBPROCESS_SCRIPT = """
import json, sys
from dataclasses import asdict
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tests" / "tracer"))
from dsc03.visual import certificates, coverage, masks, render
from conftest import render_config

fixtures = root / "tests" / "tracer" / "fixtures" / "visual"
profiles = root / "tests" / "tracer" / "profiles"
geometry = json.loads((profiles / "geometry-page-pt.json").read_text())
regions = [{"id": "ink-strip", "x": 100, "y": 300, "w": 300, "h": 24,
            "expected": "ink"},
           {"id": "blank-lower", "x": 100, "y": 60, "w": 300, "h": 24,
            "expected": "no-ink"}]
rendered = render.render_page(render_config(), fixtures / "visual-strip.pdf")
cov_cal = {"property": "ink-coverage", "carrier": "visual-strip", "page": 1,
           "min": 0.01, "max": 1.0}
aln_cal = {"property": "region-alignment", "carrier": "visual-strip",
           "page": 1, "min": 0.95, "max": 1.0}
cov_outcome = coverage.coverage_outcome(rendered, carrier="visual-strip",
                                        regions=regions, calibration=cov_cal,
                                        geometry=geometry, frame_name="page-1")
aln_outcome = masks.masks_outcome(rendered, carrier="visual-strip",
                                  regions=regions, calibration=aln_cal,
                                  geometry=geometry, frame_name="page-1")
certs = [
    certificates.sensitivity_certificate(cov_outcome, render_result=rendered,
                                         regions=regions, calibration=cov_cal,
                                         geometry=geometry,
                                         frame_name="page-1"),
    certificates.sensitivity_certificate(aln_outcome, render_result=rendered,
                                         regions=regions, calibration=aln_cal,
                                         geometry=geometry,
                                         frame_name="page-1"),
]
print(json.dumps([asdict(c) for c in certs], sort_keys=True))
"""


def test_certificate_deterministic_across_processes():
    # Identical recorded inputs give byte-identical certificates in
    # separate OS processes (agent-executed): two subprocess runs under
    # DIFFERENT PYTHONHASHSEED values and the in-process computation all
    # serialize identically.
    root = Path(__file__).resolve().parents[2]
    in_process = []
    rendered = _rendered()
    cov_cal = _calibration("ink-coverage", "visual-strip", COV_BOUNDS)
    aln_cal = _calibration("region-alignment", "visual-strip", ALN_BOUNDS)
    for oracle, cal in ((coverage, cov_cal), (masks, aln_cal)):
        outcome = (oracle.coverage_outcome if oracle is coverage
                   else oracle.masks_outcome)(
            rendered, carrier="visual-strip", regions=_strip_regions(),
            calibration=cal, geometry=_geometry(), frame_name="page-1")
        cert = certificates.sensitivity_certificate(
            outcome, render_result=rendered, regions=_strip_regions(),
            calibration=cal, geometry=_geometry(), frame_name="page-1")
        in_process.append(asdict(cert))
    expected = json.dumps(in_process, sort_keys=True)

    outputs = []
    for seed in ("1", "2"):
        proc = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_SCRIPT, str(root)],
            capture_output=True, text=True, env={"PYTHONHASHSEED": seed,
                                                 "PATH": __import__("os")
                                                 .environ["PATH"]},
            check=True,
        )
        outputs.append(proc.stdout)

    assert outputs[0] == outputs[1], (outputs[0], outputs[1])
    assert outputs[0] == expected + "\n"
