# Purpose: Independent box-agreement statistic (sunset-7b4.3, deferred from
#   improve-geometry-render-binding Non-goals; unblocked by
#   add-anchor-derived-identity quantized boxes and add-scale-complete-regions
#   word-level regions).
# Responsibilities: Compare two INDEPENDENT box sources on ONE carrier page —
#   the native word/line descriptor regions (manifest v3, quantized 1/1000pt
#   integer boxes; word-map raw source_box floats are provenance only) vs
#   observation-derived boxes (content-class-observations records, rect_pt
#   quantized through the same declared quantum) — and report, per
#   carrier x page: the symmetric agreement fraction, every disagreement as a
#   typed pair, and a typed outcome in the family vocabulary
#   (agree/differ/unknown/unavailable, unchanged from the coverage oracle).
#   Matching is one-to-many enumeration, one-to-one greedy assignment over
#   quantized-IoU-eligible pairs with EXACT integer ordering (cross-multiplied
#   fractions; the reported IoU float never decides anything). Seeded defects
#   must degrade the fraction with attribution: a shifted region lands
#   below-threshold/no-overlap, an omitted region vacates its observation
#   (unmatched-observation), a duplicated region is typed duplicate-of the
#   matched claim. Loaders are typed (Loaded), never guessed, never silent:
#   v1/v2 manifests are refused, degenerate zero-area observed rects are
#   skipped but disclosed, provenance binds by the quantized box (a diverging
#   word-map box is provenance-mismatch; a poisoned raw source_box cannot
#   change any outcome). Decode and measure only — never modify inputs, never
#   elect a winner, never smooth differences, never guess a coordinate
#   convention.
# Rationale: improve-geometry-render-binding proposal Non-goals ("Independent
#   box agreement ... depend on add-anchor-derived-identity (quantized boxes)
#   and add-scale-complete-regions (word-level regions)"); PROPOSAL-SET.md
#   necessity cuts; document-visual-oracles outcome vocabulary (design D5) and
#   "No silent resolution"; O-A01 (hypothesis entries stay render-derived
#   evidence — disclosed through the record's evidence_class so correlated
#   comparisons can never support accuracy claims). Pure integer core:
#   identical inputs give identical outcomes across processes.
"""Independent box-agreement statistic between native and observed boxes.

Pinned semantics (every verdict below is derived from declared inputs alone
— no defaults, no fallbacks):

- Property: this oracle evaluates exactly one property, "box-agreement"
  (``PROPERTY``). Every outcome carries it as a field.

- Operative boxes: BOTH sides are compared as quantized integer boxes
  (counts of the declared 1/1000 pt quantum, ``dsc03.substrate.space``).
  Native word/line boxes arrive already quantized in the manifest v3
  descriptor locators; the raw extractor floats (word-map ``source_box``)
  are provenance and are NEVER read for comparison — poisoning them cannot
  change any outcome. Observation ``rect_pt`` floats are quantized here with
  the same sanctioned quantizer. A box is valid iff it is four integers
  (bools excluded) with x1 > x0 and y1 > y0; anything else is a typed
  ``unknown`` (``native-regions-invalid`` / ``observation-boxes-invalid``) —
  never clipped, never skipped.

- Match rule: a region matches an observation iff their quantized IoU is at
  least the declared threshold (``MIN_IOU`` = 1/2, overridable per call and
  echoed on the outcome; an out-of-range threshold is ``unknown``,
  ``match-threshold-invalid``). Assignment is ONE-TO-ONE: candidate pairs
  (positive intersection, IoU >= threshold) are visited in exact descending
  IoU order — cross-multiplied integer comparison, ties broken by input
  index — and each region/observation matches at most once. Because matching
  is one-to-one, genuine duplicates on BOTH sides still agree fully.

- Agreement fraction: symmetric, ``2 * matched / (len(regions) +
  len(observations))`` (rounded to 6 decimal places). The observation side
  is in the denominator so an OMITTED region — one that vacates its
  observation — degrades the fraction exactly like a shift or duplicate does.

- Seeded-defect attribution (each region keeps a verdict in input order,
  "No silent resolution"): a region with an overlapping-but-sub-threshold
  candidate is ``differ`` with reason ``below-threshold`` and a disagreement
  pair naming the best candidate and its IoU; a region with no overlap at
  all is ``differ``/``no-overlap``; an unmatched region whose quantized box
  equals a MATCHED region's box is ``differ``/``duplicate-of:<id>``; an
  observation no region matched yields ``unmatched-observation``. The page
  agrees iff there are NO disagreement entries of any kind.

- Typed emptiness: zero native regions on the page is ``unknown`` (reason
  ``no-native-regions``) — agreement over nothing claims nothing. An empty
  observation side over claimed regions is a measured result: every region
  disagrees and the fraction is 0.0 (``differ``), never a silent pass.

- Observations: a ``content-class-observations`` record (kind/version/status
  pinned by ``dsc03.visual.content_classes``) is loaded through
  ``observation_boxes``. A ``None`` record is ``observations-missing``; a
  record of the wrong kind/version/status, a requested class outside the
  carrier classes + ``graphic-hypothesis``, a missing requested section, or
  a malformed entry is ``observations-invalid``; a different page is
  ``page-mismatch``; a different frame name is ``frame-mismatch``; an
  unresolved frame is ``frame-unresolved`` (the coordinate equivalence to
  the native quantized boxes is undeclared — never guessed). Hypothesis
  boxes are render-derived: a requested ``graphic-hypothesis`` section that
  did not derive is ``unknown`` (``hypotheses-not-derived``), and one
  blocked by an unavailable render is ``unavailable`` with the render's
  reason carried. Zero-area observed rects (e.g. stroked hairlines) are not
  boxes: skipped, counted, and disclosed on the outcome
  (``degenerate_observations``) — never silently dropped. An observed
  record that measured zero boxes is a measured EMPTY side (``differ``),
  not a missing record.

- Provenance: ``native_regions`` optionally binds each word region to its
  word-map entry by (page, raw interval) and requires the declared quantized
  boxes to be identical; divergence is ``unknown``
  (``provenance-mismatch``) — the raw ``source_box`` floats are never read.
  A manifest passed alongside the descriptor must declare version 3
  (v1/v2 predate descriptor regions and are refused,
  ``manifest-version-unsupported``), mirroring the native extractor's own
  refusal.

- Evidence class: the outcome carries the caller-declared evidence class
  (the observation record's ``evidence_class`` — ``independent`` for a
  poppler render vs PyMuPDF extraction, ``correlated`` otherwise).
  ``supports_accuracy_claim`` reuses the render.py semantics: correlated
  agreement demonstrates sensitivity only and can never support an accuracy
  claim.

- SCOPED CLAIM: an agreeing box-agreement result establishes NOTHING about
  text correctness, reading order, semantic grouping or visual
  completeness; it covers only geometric agreement between the two declared
  box sources at the recorded match threshold.

- Aggregation: ``aggregate`` mirrors the coverage oracle — ``pass`` ONLY if
  every carrier-page outcome agrees; any ``unknown``/``unavailable``/
  ``differ`` outcome, or an empty outcome set, is ``blocked`` with reasons.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from functools import cmp_to_key

# Sanctioned substrate import (add-anchor-derived-identity Decision 4): the
# exact declared quantum used by BOTH sides of the comparison.
from dsc03.substrate.space import quantize_scalar
from dsc03.visual import render
from dsc03.visual.content_classes import KIND as OBSERVATIONS_KIND
from dsc03.visual.content_classes import OBJECT_CLASSES, VERSION as OBSERVATIONS_VERSION

PROPERTY = "box-agreement"

# The declared outcome vocabulary — unchanged from the coverage oracle (D5).
STATUSES = ("agree", "differ", "unknown", "unavailable")

SCOPED_CLAIM = (
    "A passing box-agreement result establishes NOTHING about text "
    "correctness, reading order, semantic grouping or visual completeness; "
    "it covers only geometric agreement between the two declared box sources "
    "at the recorded match threshold."
)

# Declared match threshold: quantized IoU at or above MIN_IOU matches.
MIN_IOU = 0.5

# Manifest version carrying descriptor word/line regions (native v3); v1/v2
# manifests predate descriptor regions and are refused, never guessed.
MANIFEST_VERSION = "3"

# Descriptor region kinds loaded as native box sources (blocks are unions of
# lines; the assignment scope is the word/line ladder).
REGION_KINDS = ("word", "line")

# The render-derived observation class (content_classes emits this literal
# for pinned-render morphology candidates).
HYPOTHESIS_CLASS = "graphic-hypothesis"

# The default observation side: render-derived boxes are the independent
# source the deferred proposal names; carrier classes (text/vector/raster)
# share the extractor's lineage and stay available (labeled correlated).
DEFAULT_CLASSES = (HYPOTHESIS_CLASS,)

# Descriptor region anchor locator (identity-rotated v3 shape):
# page:N/kind:[raw_start,raw_end)/box=[x0,y0,x1,y1] — quantized integers.
_LOCATOR = re.compile(
    r"^page:(\d+)/(word|line|block):\[(\-?\d+),(\-?\d+)\)"
    r"/box=\[(-?\d+),(-?\d+),(-?\d+),(-?\d+)\]$")


@dataclass(frozen=True)
class AgreementOutcome:
    """Typed per-carrier, per-page agreement outcome (design D5 vocabulary).

    ``regions`` retains one verdict dict per native region in input order —
    ``{"id", "status": "agree"|"differ"}`` plus ``matched``/``iou`` for a
    match and ``reason`` for an attributed disagreement — never smoothed.
    ``disagreements`` retains the typed pairs (``below-threshold`` with the
    best candidate and its IoU, ``no-overlap``, ``duplicate`` with the
    matched claim it duplicates, ``unmatched-observation``). Page-level
    ``unknown``/``unavailable`` outcomes carry ``agreement=None`` and no
    verdicts, with ``reason`` explaining why.
    """

    status: str
    property: str = PROPERTY
    page: int = 0
    carrier: str = ""
    evidence_class: str = ""
    agreement: float | None = None
    regions: tuple = ()
    disagreements: tuple = ()
    min_iou: float = MIN_IOU
    degenerate_observations: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class AggregateOutcome:
    """Typed aggregate over carrier-page outcomes: ``pass``/``blocked``."""

    status: str
    reasons: tuple = ()


@dataclass(frozen=True)
class Loaded:
    """Typed loader result: ``items``, or a vocabulary status + reason.

    ``items`` is a tuple of ``{"id", "kind"|"class", "page", "box"}`` dicts
    with quantized integer boxes. ``degenerate`` counts zero-area observed
    rects skipped while loading (disclosed, never silent).
    """

    items: tuple = ()
    status: str = "ok"
    reason: str | None = None
    degenerate: int = 0


def _valid_page(page) -> bool:
    return type(page) is int and page >= 1


def _valid_box(box) -> bool:
    """A quantized operative box: four true integers, strictly positive area."""
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(type(v) is int for v in box)
            and box[2] > box[0] and box[3] > box[1])


def _usable_threshold(min_iou):
    """Declared threshold: a real number in (0, 1]; bools are not numbers."""
    if isinstance(min_iou, bool) or not isinstance(min_iou, (int, float)):
        return None
    if not 0 < min_iou <= 1:
        return None
    return Fraction(min_iou)


def _area(box) -> int:
    return (box[2] - box[0]) * (box[3] - box[1])


def _intersection(a, b) -> int:
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    return width * height if width > 0 and height > 0 else 0


def _before(a, b) -> int:
    """Exact descending-IoU order for (inter, union, ri, oi) candidates.

    Cross-multiplied integer comparison — no float ever decides an order;
    ties break by region then observation input index.
    """
    left, right = a[0] * b[1], b[0] * a[1]
    if left != right:
        return -1 if left > right else 1
    return -1 if a[2:] < b[2:] else (1 if a[2:] > b[2:] else 0)


def agreement_outcome(*, carrier, page, regions, observations,
                      min_iou=MIN_IOU, evidence_class="",
                      degenerate_observations=0) -> AgreementOutcome:
    """Evaluate box agreement between one page's two loaded box sources.

    ``regions`` are native region dicts (``native_regions`` items);
    ``observations`` are observation box dicts (``observation_boxes`` items).
    Pure integer computation — identical inputs give identical outcomes
    across processes.
    """
    carrier = str(carrier)
    if not _valid_page(page):
        return AgreementOutcome(status="unknown", carrier=carrier,
                                reason="page-invalid")
    threshold = _usable_threshold(min_iou)
    if threshold is None:
        return AgreementOutcome(status="unknown", page=page, carrier=carrier,
                                reason="match-threshold-invalid")
    regions = list(regions)
    observations = list(observations)
    for region in regions:
        if not (isinstance(region, dict) and isinstance(region.get("id"), str)
                and _valid_box(region.get("box"))):
            return AgreementOutcome(status="unknown", page=page,
                                    carrier=carrier,
                                    reason="native-regions-invalid")
    if len({region["id"] for region in regions}) != len(regions):
        return AgreementOutcome(status="unknown", page=page, carrier=carrier,
                                reason="native-regions-invalid")
    for observation in observations:
        if not (isinstance(observation, dict)
                and isinstance(observation.get("id"), str)
                and _valid_box(observation.get("box"))):
            return AgreementOutcome(status="unknown", page=page,
                                    carrier=carrier,
                                    reason="observation-boxes-invalid")
    if not regions:
        # Agreement over nothing claims nothing — never a silent pass.
        return AgreementOutcome(status="unknown", page=page, carrier=carrier,
                                reason="no-native-regions")

    # One-to-one greedy assignment over exact-ordered eligible pairs.
    eligible = []
    for ri, region in enumerate(regions):
        for oi, observation in enumerate(observations):
            inter = _intersection(region["box"], observation["box"])
            if inter <= 0:
                continue
            union = _area(region["box"]) + _area(observation["box"]) - inter
            if inter * threshold.denominator >= threshold.numerator * union:
                eligible.append((inter, union, ri, oi))
    eligible.sort(key=cmp_to_key(_before))
    matched_region, matched_observation, pairs = {}, {}, {}
    for inter, union, ri, oi in eligible:
        if ri not in matched_region and oi not in matched_observation:
            matched_region[ri] = oi
            matched_observation[oi] = ri
            pairs[(ri, oi)] = round(inter / union, 6)

    verdicts, disagreements = [], []
    for ri, region in enumerate(regions):
        entry = {"id": region["id"]}
        if ri in matched_region:
            oi = matched_region[ri]
            entry["status"] = "agree"
            entry["matched"] = observations[oi]["id"]
            entry["iou"] = pairs[(ri, oi)]
        else:
            box = region["box"]
            duplicate_of = next(
                (regions[other]["id"] for other in sorted(matched_region)
                 if regions[other]["box"] == box), None)
            if duplicate_of is not None:
                # A second claim on an already-matched quantized box.
                entry["status"] = "differ"
                entry["reason"] = f"duplicate-of:{duplicate_of}"
                disagreements.append({"kind": "duplicate",
                                      "region": region["id"],
                                      "of": duplicate_of})
            else:
                best = None  # (inter, union, oi) — best overlapping candidate
                for oi, observation in enumerate(observations):
                    inter = _intersection(box, observation["box"])
                    if inter <= 0:
                        continue
                    union = (_area(box) + _area(observation["box"]) - inter)
                    if best is None or _before((inter, union, ri, oi),
                                               (best[0], best[1], ri, best[2])):
                        best = (inter, union, oi)
                if best is None:
                    entry["status"] = "differ"
                    entry["reason"] = "no-overlap"
                    disagreements.append({"kind": "no-overlap",
                                          "region": region["id"]})
                else:
                    entry["status"] = "differ"
                    entry["reason"] = "below-threshold"
                    disagreements.append({
                        "kind": "below-threshold", "region": region["id"],
                        "observation": observations[best[2]]["id"],
                        "iou": round(best[0] / best[1], 6)})
        verdicts.append(entry)
    for oi, observation in enumerate(observations):
        if oi not in matched_observation:
            # The region that used to claim this box is gone (or drifted).
            disagreements.append({"kind": "unmatched-observation",
                                  "observation": observation["id"]})

    matched = len(matched_region)
    fraction = round(2 * matched / (len(regions) + len(observations)), 6)
    status = "agree" if not disagreements else "differ"
    return AgreementOutcome(
        status=status, page=page, carrier=carrier,
        evidence_class=str(evidence_class), agreement=fraction,
        regions=tuple(verdicts), disagreements=tuple(disagreements),
        min_iou=float(min_iou),
        degenerate_observations=int(degenerate_observations), reason=None)


def _provenance_index(word_map):
    """(page, raw interval) -> quantized box from word-map entries.

    The raw ``source_box`` floats are provenance only and are NEVER read
    here. Malformed or ambiguous provenance returns ({}, False).
    """
    if word_map is None:
        return {}, True
    index = {}
    if not isinstance(word_map, list):
        return {}, False
    for entry in word_map:
        if not isinstance(entry, dict):
            return {}, False
        page, start, end = (entry.get("page"), entry.get("raw_start"),
                            entry.get("raw_end"))
        box = entry.get("box")
        if not (type(page) is int and type(start) is int and type(end) is int
                and _valid_box(box)):
            return {}, False
        key = (page, start, end)
        if key in index:
            return {}, False  # ambiguous provenance
        index[key] = list(box)
    return index, True


def native_regions(descriptor, page, manifest=None, word_map=None) -> Loaded:
    """Load a page's native word/line descriptor regions (manifest v3).

    Boxes are the quantized integers pinned in each region's anchor locator
    (the operative geometry; raw source_box floats are never consulted).
    ``manifest`` pins the v3 refusal; ``word_map`` binds word-region
    provenance by (page, raw interval) — a diverging quantized box is
    ``provenance-mismatch``. Typed ``unknown`` on every refusal.
    """
    if not _valid_page(page):
        return Loaded(status="unknown", reason="page-invalid")
    if manifest is not None:
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if version != MANIFEST_VERSION:
            return Loaded(status="unknown",
                          reason="manifest-version-unsupported")
    regions = descriptor.get("regions") if isinstance(descriptor, dict) else None
    if not isinstance(regions, list):
        return Loaded(status="unknown", reason="native-regions-invalid")
    provenance, provenance_ok = _provenance_index(word_map)
    if word_map is not None and not provenance_ok:
        return Loaded(status="unknown", reason="provenance-mismatch")
    items = []
    for region in regions:
        if not isinstance(region, dict) or region.get("kind") not in REGION_KINDS:
            continue
        anchor = region.get("anchor")
        locator = anchor.get("locator_path") if isinstance(anchor, dict) else None
        match = _LOCATOR.match(locator) if isinstance(locator, str) else None
        rid = region.get("id")
        if match is None or not isinstance(rid, str):
            return Loaded(status="unknown", reason="native-regions-invalid")
        if int(match.group(1)) != page:
            continue  # anchored on another page of the same document
        box = [int(match.group(i)) for i in (5, 6, 7, 8)]
        if not _valid_box(box):
            return Loaded(status="unknown", reason="native-regions-invalid")
        if region["kind"] == "word" and provenance:
            key = (page, int(match.group(3)), int(match.group(4)))
            if provenance.get(key) != box:
                return Loaded(status="unknown", reason="provenance-mismatch")
        items.append({"id": rid, "kind": region["kind"], "page": page,
                      "box": box})
    if len({item["id"] for item in items}) != len(items):
        return Loaded(status="unknown", reason="native-regions-invalid")
    if not items:
        return Loaded(status="unknown", reason="no-native-regions")
    return Loaded(items=tuple(items))


def observation_boxes(record, page, frame,
                      classes=DEFAULT_CLASSES) -> Loaded:
    """Load quantized observation boxes from a content-class-observations record.

    ``classes`` selects the record's sections in given order (carrier
    classes text/vector/raster and/or the render-derived
    ``graphic-hypothesis``). Entry ``rect_pt`` (canonical descriptor pt) is
    quantized with the declared quantum — the same operative representation
    as the native side. Zero-area rects are skipped and disclosed; every
    refusal is typed, nothing is guessed.
    """
    if record is None:
        return Loaded(status="unknown", reason="observations-missing")
    if (not isinstance(record, dict) or record.get("kind") != OBSERVATIONS_KIND
            or record.get("version") != OBSERVATIONS_VERSION
            or record.get("status") != "observed"):
        return Loaded(status="unknown", reason="observations-invalid")
    if record.get("page") != page:
        return Loaded(status="unknown", reason="page-mismatch")
    frame_record = record.get("frame")
    if (not isinstance(frame_record, dict) or frame_record.get("name") != frame):
        return Loaded(status="unknown", reason="frame-mismatch")
    if frame_record.get("status") != "resolved":
        # The coordinate equivalence to the native boxes is undeclared.
        return Loaded(status="unknown", reason="frame-unresolved")
    classes = tuple(dict.fromkeys(classes))
    known = set(OBJECT_CLASSES) | {HYPOTHESIS_CLASS}
    if not classes or any(name not in known for name in classes):
        return Loaded(status="unknown", reason="observations-invalid")
    sections = record.get("classes")
    if not isinstance(sections, dict) or any(
            name != HYPOTHESIS_CLASS and name not in sections
            for name in classes):
        return Loaded(status="unknown", reason="observations-invalid")
    if HYPOTHESIS_CLASS in classes:
        section = sections.get(HYPOTHESIS_CLASS)
        status = section.get("status") if isinstance(section, dict) else None
        if status != "derived":
            render_record = record.get("render")
            if (status == "render-unavailable"
                    and isinstance(render_record, dict)
                    and render_record.get("status") == "unavailable"):
                return Loaded(status="unavailable",
                              reason=render_record.get("reason"))
            return Loaded(status="unknown", reason="hypotheses-not-derived")
    items, degenerate = [], 0
    for name in classes:
        section = sections[name]
        entries = (section.get("entries")
                   if isinstance(section, dict) else None)
        if not isinstance(entries, list):
            return Loaded(status="unknown", reason="observations-invalid")
        for index, entry in enumerate(entries):
            if (not isinstance(entry, dict) or entry.get("class") != name):
                return Loaded(status="unknown", reason="observations-invalid")
            rect = entry.get("rect_pt")
            if not (isinstance(rect, (list, tuple)) and len(rect) == 4
                    and all(isinstance(v, (int, float))
                            and not isinstance(v, bool) for v in rect)):
                return Loaded(status="unknown", reason="observations-invalid")
            try:
                box = [quantize_scalar(v) for v in rect]
            except (TypeError, ValueError):
                return Loaded(status="unknown", reason="observations-invalid")
            if box[2] <= box[0] or box[3] <= box[1]:
                # A zero-area observed rect (e.g. a hairline stroke) is not
                # a box: skipped AND disclosed, never guessed into one.
                degenerate += 1
                continue
            items.append({"id": f"{name}:{index}", "class": name, "box": box})
    return Loaded(items=tuple(items), degenerate=degenerate)


def supports_accuracy_claim(outcome) -> bool:
    """Whether an agreement outcome MAY support an accuracy claim.

    Reuses render.py semantics at the oracle level: ``correlated`` evidence
    (observation side sharing the extractor's implementation lineage)
    demonstrates sensitivity only and can never support an accuracy claim.
    """
    return render.supports_accuracy_claim(outcome.evidence_class)


def aggregate(outcomes) -> AggregateOutcome:
    """Aggregate carrier-page outcomes: ``pass`` ONLY if every page agrees.

    Any ``unknown``, ``unavailable`` or ``differ`` outcome blocks, with its
    blocking reason listed; an empty outcome set is blocked too (an
    aggregate over nothing must never claim a pass).
    """
    outcomes = list(outcomes)
    if not outcomes:
        return AggregateOutcome(status="blocked", reasons=("no-page-outcomes",))
    reasons = []
    for outcome in outcomes:
        if outcome.status == "agree":
            continue
        detail = f"{outcome.carrier} page {outcome.page}: {outcome.status}"
        if outcome.reason:
            detail += f" ({outcome.reason})"
        reasons.append(detail)
    if reasons:
        return AggregateOutcome(status="blocked", reasons=tuple(reasons))
    return AggregateOutcome(status="pass", reasons=())
