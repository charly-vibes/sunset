# Purpose: Per-page sensitivity certificates for oracle outcomes
#   (sunset-7b4.5; the improve-geometry-render-binding deferred non-goal
#   "per-page sensitivity certificates", resolving review finding EDGE-002).
# Responsibilities: Given a typed oracle outcome (`coverage.CoverageOutcome`
#   or `masks.AlignmentOutcome`) and the SAME pinned inputs the oracle
#   consumed (render result, claimed regions, recorded calibration entry,
#   declared geometry frame), derive the certificate: how large a defect of
#   each seeded mutation class must be for the oracle's own decision rule to
#   be GUARANTEED to leave `agree` on this page, per class the property
#   claims (ink-coverage: omission, duplication; region-alignment: shift,
#   wrong frame — deployed spec "Mutation-validated sensitivity", claim
#   mapping pinned in tests/tracer/test_visual_mutations.py), and emit the
#   typed per-page record: `certified` with per-class threshold entries, or
#   `unknown` with reason `certificate-unsupported` carrying the failing
#   condition verbatim. Certification is PER-PAGE ONLY: this module exposes
#   no aggregate API and never yields a permanent `uncertified` status
#   (EDGE-002 BINDING CONSTRAINT) — a page that cannot be certified carries
#   its typed per-page reason and neither blocks sibling pages nor
#   aggregates anywhere. Below-threshold magnitudes are attributed
#   `certified-unsensitive`: NOT certified as detectable — never claimed
#   caught, never silently assumed. Certificates are pure functions of the
#   recorded inputs: identical inputs produce identical records across
#   processes (no wall-clock, no iteration-order or hash-order dependence).
# Rationale: document-visual-oracles "Mutation-validated sensitivity",
#   "Scoped property claims", "Calibrated thresholds with per-page outcomes",
#   "No silent resolution"; design D4 (the recorded ink-dilation
#   simplification IS the oracle's tolerance — margins are measured on the
#   simplified surface, the comparison surface the oracle actually judges)
#   and D5 (typed unknowns; unknown is an answer). Oracle semantics are
#   never re-implemented: the certified `agree` baseline is the caller's
#   outcome, thresholds derive from the oracles' published decision rules
#   and measured fractions via the shared pixel gate, and the shift class is
#   verified through a real oracle run on a synthesized mutated render
#   (disagreement converts the certificate to typed `unknown`, never a
#   softened claim).
"""Per-page sensitivity certificates for oracle outcomes (sunset-7b4.5)."""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from dsc03.visual import coverage, frames, masks, render
from dsc03.visual._pixels import MaskUnavailable, comparison_mask, parse_dilation
# Private helpers reused exactly as masks.py reuses them: one convention,
# no duplicated rect-mapping or calibration validation (rule-of-5 EXCL-001).
from dsc03.visual.coverage import _pixel_rect, _region_fraction
from dsc03.visual.coverage import _usable_calibration
from dsc03.visual.masks import _usable_region_calibration

CERTIFIED = "certified"
UNKNOWN = "unknown"

# Typed refusal reason for every page this mechanism cannot certify; the
# failing condition is carried beside it, verbatim from the recorded inputs.
CERTIFICATE_UNSUPPORTED = "certificate-unsupported"

# Seeded mutation classes (deployed spec "Mutation-validated sensitivity").
CLASS_OMISSION = "omission"
CLASS_DUPLICATION = "duplication"
CLASS_SHIFT = "shift"
CLASS_WRONG_FRAME = "wrong-frame"

# Threshold units. Omission/duplication magnitudes are simplified-ink pixel
# counts (the surface the oracle judges; see design D4 above). Shift
# magnitudes follow the seeded class's defect shape: a diagonal (+s, +s) px
# translation of the page ink relative to the claimed rects.
UNIT_INK_PX = "simplified-ink-px"
UNIT_SHIFT_PX = "px-diagonal"

# Attribution emitted for every positive threshold: defects strictly below
# it are NOT certified as detectable by this outcome.
UNSENSITIVE_ATTRIBUTION = "certified-unsensitive"

_STATUS_VOCABULARY = frozenset({"certified", "unknown"})


@dataclass(frozen=True)
class SensitivityCertificate:
    """Typed PER-PAGE sensitivity certificate (sunset-7b4.5).

    ``status`` is ``certified`` or ``unknown``; ``outcome_status`` echoes
    the certified oracle outcome's vocabulary value (agree / differ /
    unknown / unavailable — never a new verdict vocabulary). ``thresholds``
    holds one entry per claimed seeded class,
    ``{"class", "unit", "threshold", "governing-scope", "scopes"}`` (plus
    ``"derived": True`` for the wrong-frame entry, whose threshold is
    inherited from shift): the minimal defect magnitude that the oracle's
    decision rule is GUARANTEED to detect on this page, with the binding
    scope named and every scope's margin listed. ``unsensitive_below``
    attributes the complementary band: defects strictly below the threshold
    are ``certified-unsensitive`` — not certified as detectable. For
    ``unknown`` records ``reason`` is ``certificate-unsupported`` and
    ``condition`` carries the failing condition verbatim (e.g.
    ``uncalibrated``, a render refusal reason, ``class-scoped-claims-
    unsupported``); ``thresholds`` is then empty. Records are per-page:
    nothing here aggregates, blocks, or carries across pages.
    """

    status: str
    property: str
    page: int
    carrier: str
    evidence_class: str
    outcome_status: str
    thresholds: tuple = ()
    unsensitive_below: tuple = ()
    reason: str | None = None
    condition: str | None = None


def _unknown(config, carrier, outcome_status, condition):
    return SensitivityCertificate(
        status=UNKNOWN, property=None, page=config.page, carrier=carrier,
        evidence_class=config.evidence_class, outcome_status=outcome_status,
        thresholds=(), unsensitive_below=(),
        reason=CERTIFICATE_UNSUPPORTED, condition=condition,
    )


def _class_entry(class_name, unit, scopes, derived=False):
    """One threshold entry: minimal margin with its binding scope named.

    ``scopes`` is a list of ``(scope-name, margin)`` pairs; ties on the
    minimal margin resolve by scope name — fully deterministic, no
    iteration-order dependence.
    """
    ordered = tuple(sorted(scopes))
    threshold = min(margin for _name, margin in ordered)
    governing = next(name for name, margin in ordered if margin == threshold)
    entry = {"class": class_name, "unit": unit, "threshold": threshold,
             "governing-scope": governing, "scopes": ordered}
    if derived:
        entry["derived"] = True
    return entry


def _finish(config, carrier, property_name, outcome_status, entries):
    entries = tuple(sorted(entries, key=lambda entry: entry["class"]))
    unsensitive = tuple(
        {"class": entry["class"], "unit": entry["unit"],
         "threshold": entry["threshold"],
         "attribution": UNSENSITIVE_ATTRIBUTION}
        for entry in entries if entry["threshold"] > 0
    )
    return SensitivityCertificate(
        status=CERTIFIED, property=property_name, page=config.page,
        carrier=carrier, evidence_class=config.evidence_class,
        outcome_status=outcome_status, thresholds=entries,
        unsensitive_below=unsensitive, reason=None, condition=None,
    )


def _png_bytes(mask, width, height):
    """Deterministic 8-bit grayscale PNG bytes (mask px 1 -> gray 0 = ink).

    Used to feed a synthesized mutated render through the REAL oracle for
    the shift verification probe; byte-identical for identical masks (pinned
    zlib level), so the probe is reproducible across processes.
    """
    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    table = bytes.maketrans(b"\x00\x01", b"\xff\x00")  # ink -> 0, paper -> 255
    scanlines = b"".join(
        b"\x00" + mask[y * width:(y + 1) * width].translate(table)
        for y in range(height)
    )
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(scanlines, 9))
            + chunk(b"IEND", b""))


def _translate_diagonal(raw, width, height, s):
    """Translate a packed mask by (+s, +s) px (the seeded shift defect shape).

    Ink pushed past the raster edges disappears, exactly as a real shifted
    render would lose it. (Chebyshev dilation commutes with translation in
    the page interior, so measuring the translated raw mask through the
    oracle's own simplification reproduces the oracle's judgment.)
    """
    out = bytearray(len(raw))
    for y in range(height - s):
        src = y * width
        dst = (y + s) * width + s
        out[dst:dst + width - s] = raw[src:src + width - s]
    return out


def _shift_threshold(rect, low, dilation):
    """Minimal diagonal shift (px) that forces this rect's measured fraction
    below the recorded floor.

    The post-shift simplified ink inside the rect is bounded by the rect's
    own pre-shift ink: a translated rect's overlap after dilation is
    ``(w - s + d) x (h - s + d)`` px, so `differ` is guaranteed once that
    product falls below ``low * w * h`` — the same arithmetic the committed
    shift fixture demonstrates (300x24 strip, d=2: a 12 px diagonal shift
    leaves ~0.56 < 0.95). Pure integer arithmetic, deterministic.
    """
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    floor = low * w * h
    for s in range(1, w + h + dilation + 2):
        if (w - s + dilation) * (h - s + dilation) < floor:
            return s
    return None  # unreachable for low >= 0; kept typed rather than guessed


def sensitivity_certificate(
    outcome,
    *,
    render_result,
    regions,
    calibration,
    geometry,
    frame_name,
) -> SensitivityCertificate:
    """Derive the per-page sensitivity certificate for one oracle outcome.

    ``outcome`` is the page's ``CoverageOutcome``/``AlignmentOutcome``;
    ``render_result`` and the remaining keyword arguments are the SAME
    recorded inputs that produced it. Pure and deterministic: identical
    inputs give identical records across processes. Never aggregates: one
    page, one typed record — an uncertifiable page yields ``unknown`` with
    reason ``certificate-unsupported`` and its failing condition, and says
    nothing about any other page (EDGE-002).

    Margin semantics (the oracle's decision rule, measured on the recorded
    simplified surface):

    - ink-coverage (claims: omission, duplication). Whole-page window
      ``[min, max]`` and per-region windows: removing k px of simplified ink
      drops page and region fractions by at most k px / scope-area, so the
      outcome provably stays `agree` while k is below the minimal margin
      ``(fraction - min) * area`` over page and claimed-ink scopes
      (omission) or ``(min - fraction) * area`` / ``(max - page) * area``
      over page and claimed-no-ink scopes (duplication). Monotone: no probe
      is needed for these classes.
    - region-alignment (claims: shift, wrong frame). The shift threshold per
      claimed-ink rect is ``_shift_threshold`` (guaranteed band; neighboring
      ink dilating into the rect can only weaken detection, which is why an
      `agree` baseline is verified against the REAL oracle on a synthesized
      shifted render — disagreement yields typed ``unknown`` with condition
      ``oracle-ladder-mismatch:shift``, never a softened claim). The
      wrong-frame threshold is derived from shift: any frame misdeclaration
      that displaces the claimed rects by at least the shift threshold lands
      them off their ink under the same guarantee (the committed
      rot180-vs-rot90 fixture demonstrates the class). Only claimed-ink
      rects bound these classes; shift-direction sensitivity of no-ink
      claims is not certified (conservative, never invented).
    """
    config = render_result.config
    carrier = str(outcome.carrier)
    property_name = getattr(outcome, "property", None)
    if property_name not in (coverage.PROPERTY, masks.PROPERTY):
        return _unknown(config, carrier, outcome.status,
                        f"unsupported-property:{property_name}")
    if outcome.status == "unavailable":
        return _unknown(config, carrier, outcome.status, outcome.reason)
    if outcome.status == "unknown":
        return _unknown(config, carrier, outcome.status, outcome.reason)

    try:
        width, height, raw, simplified = comparison_mask(render_result, config)
    except MaskUnavailable as unavailable:
        return _unknown(config, carrier, outcome.status, unavailable.reason)

    mapping = frames.frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, frames.UnknownMapping):
        return _unknown(config, carrier, outcome.status, mapping.reason)

    if property_name == coverage.PROPERTY:
        bounds = _usable_calibration(calibration, carrier, config.page)
    else:
        bounds = _usable_region_calibration(calibration, carrier, config.page)
    if bounds is None:
        return _unknown(config, carrier, outcome.status, "uncalibrated")
    low, high = bounds

    # Class-scoped claims are measured against content-class masks, whose
    # margins this mechanism does not ladder: typed per-page refusal, never
    # a guessed fall back to the undifferentiated surface.
    if any(isinstance(region, dict)
           and region.get("class") in coverage.CONTENT_CLASSES
           for region in regions):
        return _unknown(config, carrier, outcome.status,
                        "class-scoped-claims-unsupported")

    measured = []
    for region in regions:
        rect = _pixel_rect(mapping, region)
        expected = region.get("expected") if isinstance(region, dict) else None
        if rect is None or expected not in coverage.EXPECTED_VALUES:
            # A contradictory claim set (unmappable rect, out-of-vocabulary
            # expectation) means the page's oracle verdict is not fully
            # attributable: refused, per-page, never silently skipped.
            return _unknown(config, carrier, outcome.status, "unusable-claims")
        measured.append((f"region:{region['id']}", rect, expected,
                         _region_fraction(simplified, width, rect)))

    page_area = float(width * height)
    page_fraction = simplified.count(1) / page_area

    entries = []
    if property_name == coverage.PROPERTY:
        omission_scopes = [("page", max(0.0, (page_fraction - low) * page_area))]
        duplication_scopes = [("page", max(0.0, (high - page_fraction) * page_area))]
        for scope, rect, expected, fraction in measured:
            area = float((rect[2] - rect[0]) * (rect[3] - rect[1]))
            if expected == "ink":
                omission_scopes.append(
                    (scope, max(0.0, (fraction - low) * area)))
            else:
                duplication_scopes.append(
                    (scope, max(0.0, (low - fraction) * area)))
        entries.append(_class_entry(CLASS_OMISSION, UNIT_INK_PX, omission_scopes))
        entries.append(_class_entry(CLASS_DUPLICATION, UNIT_INK_PX,
                                    duplication_scopes))
        return _finish(config, carrier, property_name, outcome.status, entries)

    dilation = parse_dilation(config.source_simplification)
    shift_scopes = []
    for scope, rect, expected, _fraction in measured:
        if expected != "ink":
            continue
        threshold = _shift_threshold(rect, low, dilation)
        if threshold is None:
            return _unknown(config, carrier, outcome.status,
                            "shift-threshold-unreachable")
        shift_scopes.append((scope, threshold))
    if not shift_scopes:
        # No claimed-ink rect: neither shift nor wrong frame has a scope on
        # this page — typed refusal, never an invented unconditional claim.
        return _unknown(config, carrier, outcome.status, "no-ink-claims")

    shift_threshold = min(threshold for _scope, threshold in shift_scopes)
    if outcome.status == "agree":
        # The guarantee above counts the rect's own ink; ink dilating in
        # from neighbors can only weaken detection. Verify the certified
        # edge through the REAL oracle on the synthesized shifted render.
        shifted = _translate_diagonal(raw, width, height, shift_threshold)
        probe = masks.masks_outcome(
            render.Rendered(config=config,
                            data=_png_bytes(shifted, width, height)),
            carrier=carrier, regions=regions, calibration=calibration,
            geometry=geometry, frame_name=frame_name,
        )
        if probe.status != "differ":
            return _unknown(config, carrier, outcome.status,
                            "oracle-ladder-mismatch:shift")

    entries.append(_class_entry(CLASS_SHIFT, UNIT_SHIFT_PX, shift_scopes))
    # Derived class: a wrong declared frame displaces the mapped rects
    # exactly as a shift does; the same displacement threshold applies
    # (seeded demonstration: committed rot180-vs-rot90 fixture).
    entries.append(_class_entry(CLASS_WRONG_FRAME, UNIT_SHIFT_PX, shift_scopes,
                                derived=True))
    return _finish(config, carrier, property_name, outcome.status, entries)
