# Purpose: Human visual-review bundle generator (sunset-e8t, sunset-fgg) —
#   the bridge between the raster visual oracles and a human
#   side-by-side/overlay comparison pass.
# Responsibilities: Render pinned carrier pages through the same
#   pinned-render configuration the oracles use, resolve the declared
#   geometry frames, map claimed descriptor region rects into pixel space,
#   and embed renders + mapped regions + render configuration + evidence
#   class into the offline review SPA template
#   (hitl/visual-review/templates/visual-review-spa.html). Correlated-lineage
#   render configs are refused per page with a typed reason
#   (CORRELATED_RENDER_REFUSED): oracle evaluation reads only independent
#   renders, so a correlated crop is absent from the record, never silently
#   skipped. Walks every
#   unique render target recorded in fixtures/visual/calibration.json for
#   the all-examples bundle, and walks every page of a DSC 0.3 descriptor
#   (as produced by `python3 -m digitization run`) for the
#   descriptor-sourced bundle. Missing renderers and unresolvable frames stay
#   typed (unavailable / unknown); regions are never silently dropped and
#   verdicts are never fabricated. `python -m dsc03.visual.review` builds
#   and optionally serves the bundle over loopback.
# Rationale: The oracles prove sensitivity mechanically; the deployed spec
#   keeps the human pass supreme. This module makes that pass concrete:
#   the human sees exactly what the oracle pipeline sees (same render, same
#   frame math) and records agree/differ/unknown verdicts with the same
#   no-winner-election, no-smoothing rules.
"""Build self-contained human review bundles for visual-oracle regions."""

import argparse
import base64
import hashlib
import json
import re
import shutil
import sys
from dataclasses import replace
from pathlib import Path

from dsc03.visual import Binarization, RenderConfig, render
from dsc03.visual.frames import PixelMapping, UnknownMapping, frame_mapping

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "hitl" / "visual-review" / "templates" / "visual-review-spa.html"
)

RULES = "no winner election, no smoothing; unknown is an answer"

# Design D5: oracle evaluation reads ONLY independent renders. A correlated
# config (render lineage == extractor lineage, e.g. the in-process PyMuPDF
# review-crop path) is refused with this typed reason — the crop is absent
# from the record, never silently skipped and never relabeled. The refusal
# is carried structurally in page_record["refusal"] = {code, reason}
# ("unavailable" keeps the prefixed display string for the review SPA).
CORRELATED_RENDER_REFUSED = "correlated-render-refused"

# Provenance label for verdicts ingested from a human (or human-supervised
# agent) review pass: every report, counterexample and evaluation summary
# this module emits carries it, so downstream consumers never mistake
# ingested verdicts for mechanical oracle outcomes.
PROVENANCE_LABEL = "AGENT-INGESTED-HUMAN-VERDICTS"

# Sunset-9rg caveat carried verbatim in every missed-ink report entry:
# missed-ink boxes are a proxy metric, not a measurement. Decorative and
# graphic ink can be invisible to native text observation (transcript
# 6ae4669e: on BORA gazettes the decorative heading band is invisible to
# native text objects; ink-coverage 71.89% -> 99.55% once graphic-region
# candidates are counted), so the count underestimates missed ink.
MISSING_INK_CAVEAT = (
    "ESTIMATE: proxy metric per sunset-9rg (transcript 6ae4669e): decorative/"
    "graphic ink can be invisible to native text observation (BORA gazettes: "
    "ink-coverage 71.89% -> 99.55% once graphic-region candidates are "
    "counted), so missed-ink boxes understate ink and are not a measurement."
)

# Typed refusal when the verdicts bundle was built against a different
# calibration record (record sha256 or base_commit mismatch). FP/FN
# statistics must never be attributed to the wrong record version, so this
# is a typed error, never a warning.
RECORD_MISMATCH = "record-version-mismatch"


class RecordVersionMismatch(ValueError):
    """Verdicts bundle does not pin the calibration record being compared
    against (record sha256 or base_commit mismatch). Refusal is typed and
    non-negotiable: ingest produces no statistics on a mismatch."""

    code = RECORD_MISMATCH

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason

# Declared geometry artifacts the calibration record names, mirroring the
# mapping in tests/tracer/test_visual_calibration.py.
_ROOT = Path(__file__).resolve().parents[2]
_GEOMETRY_ARTIFACTS = {
    "geometry-page-pt": _ROOT / "tests/tracer/profiles/geometry-page-pt.json",
    "geometry-rotated-strip": _ROOT / "tests/tracer/fixtures/visual/geometry-rotated-strip.json",
}
_CALIBRATION_PATH = _ROOT / "fixtures/visual/calibration.json"


def _pixmap_extent(data: bytes):
    """Decode rendered PNG bytes to the (width, height) raster extent."""
    import pymupdf

    pix = pymupdf.Pixmap(data)
    return pix.width, pix.height


def _pixel_rect(mapping: PixelMapping, region: dict):
    """Map a descriptor pt rect (bottom-left y-up) to a raster pixel rect."""
    px1 = mapping.descriptor_to_pixel(region["x"], region["y"])
    px2 = mapping.descriptor_to_pixel(region["x"] + region["w"], region["y"] + region["h"])
    x0, x1 = sorted((px1[0], px2[0]))
    y0, y1 = sorted((px1[1], px2[1]))
    return [round(x0), round(y0), round(x1 - x0), round(y1 - y0)]


def _default_config():
    executable = shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=executable,
        renderer_version=render.detect_renderer_version(executable),
        dpi=72,
        page=1,
        binarization=Binarization(enabled=True, method="fixed-threshold", threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


def _maybe_render(config, source_path):
    """Render unless correlated: refusal precedes rendering (Design D5).

    The typed refusal itself is constructed in _page_record; this helper is
    the single statement of "a correlated config never invokes a renderer".
    """
    if config.evidence_class == "correlated":
        return None
    return render.render_page(config, source_path)


def _regions_for(calibration, carrier_id):
    matches = [c for c in calibration["carriers"] if c["id"] == carrier_id]
    assert len(matches) == 1, f"carrier {carrier_id!r} not uniquely recorded"
    return [dict(r) for r in matches[0]["regions"]]


def _page_record(page_number, regions, config, rendered, geometry, frame_name,
                 file=None):
    """One page entry: pinned render + frame-mapped claimed regions."""
    record = {"page": page_number, "file": file, "unavailable": None,
              "refusal": None,
              "regions": [], "image": None, "width": None, "height": None,
              "frame": frame_name}
    if config.evidence_class == "correlated":
        # Spec "Render lineage labeling covers both paths": oracle evaluation
        # SHALL NOT read correlated renders. The crop stays absent and the
        # carrier entry still records evidence_class `correlated`.
        refusal_reason = ("evaluation reads only independent renders; this "
                          "in-process PyMuPDF crop is correlated evidence "
                          "(extractor_lineage == renderer_lineage) and never "
                          "enters oracle evaluation")
        # Structured refusal (rule-of-5 CLAR-001): machine-readable code and
        # reason, so consumers never prefix-match the display string.
        record["refusal"] = {"code": CORRELATED_RENDER_REFUSED,
                             "reason": refusal_reason}
        record["unavailable"] = CORRELATED_RENDER_REFUSED + ": " + refusal_reason
        return record
    if isinstance(rendered, render.RenderUnavailable):
        record["unavailable"] = rendered.reason
        return record
    width, height = _pixmap_extent(rendered.data)
    record["image"] = "data:image/png;base64," + base64.b64encode(
        rendered.data).decode("ascii")
    record["width"] = width
    record["height"] = height
    if not regions:
        return record  # nothing claimed on this page; no frame question
    if frame_name is None:
        mapping = UnknownMapping(
            "invalid_geometry_frame", "page has no single declared space")
    else:
        mapping = frame_mapping(geometry, frame_name, config, (width, height))
    if isinstance(mapping, UnknownMapping):
        record["unavailable"] = (
            f"frame unknown: {mapping.reason}: {mapping.detail}")
        record["regions"] = [
            {"id": r["id"], "rect_px": None, "expected": r.get("expected")}
            for r in regions
        ]
    else:
        record["regions"] = [
            {"id": r["id"], "rect_px": _pixel_rect(mapping, r),
             "expected": r.get("expected")}
            for r in regions
        ]
    return record


def _bundle_record(carriers):
    return {
        "kind": "visual-review-bundle",
        "version": 2,
        "rules": RULES,
        "carriers": carriers,
    }


def build_review_bundle(
    pdf_path,
    *,
    regions,
    geometry,
    frame_name,
    carrier,
    out_path,
    config=None,
):
    """Render one pinned page, map claimed regions, embed the review SPA.

    ``regions`` are claimed descriptor rects (``{id, x, y, w, h}``, optional
    ``expected``) in descriptor coordinates. ``geometry`` is the declared
    geometry artifact; ``frame_name`` the frame to resolve. ``out_path``
    receives the self-contained HTML bundle. Returns the embedded record.
    """
    config = config or _default_config()
    # Refusal precedes rendering: a correlated config never invokes a
    # renderer at all — the crop is absent, typed, before any pixels exist.
    rendered = _maybe_render(config, pdf_path)
    page_record = _page_record(config.page, regions, config, rendered,
                               geometry, frame_name)
    record = _bundle_record([{
        "carrier": carrier,
        "evidence_class": config.evidence_class,
        "render_config": config.to_dict(),
        "pages": [page_record],
    }])
    _write_bundle(out_path, record)
    return record


def build_calibration_review_bundle(out_path, record_path=None, config=None):
    """Walk every unique render target recorded in the calibration record.

    Each recorded carrier contributes one page entry per unique (file,
    page, geometry, frame) render target, so the human reviews exactly the
    pages the oracles were calibrated on — including both rotated-strip
    frames. Returns the embedded v2 record.
    """
    record_path = Path(record_path or _CALIBRATION_PATH)
    calibration = json.loads(record_path.read_text())
    config = config or _default_config()

    # first-seen unique render targets per carrier, in record order
    targets = []
    seen = set()
    for run in calibration["per_page_outcomes"]:
        key = (run["carrier"], run["file"], run["page"],
               run.get("geometry"), run.get("frame"))
        if key not in seen:
            seen.add(key)
            targets.append(key)

    entries = {}
    for (carrier, file_rel, page, geometry_name, frame_name) in targets:
        entry_config = replace(config, page=page)
        geometry = json.loads(_GEOMETRY_ARTIFACTS[geometry_name].read_text())
        rendered = _maybe_render(entry_config, _ROOT / file_rel)
        page_record = _page_record(page, _regions_for(calibration, carrier),
                                   entry_config, rendered, geometry,
                                   frame_name, file=file_rel)
        entries.setdefault(carrier, []).append(page_record)

    carriers = []
    for recorded in calibration["carriers"]:
        carrier = recorded["id"]
        carriers.append({
            "carrier": carrier,
            "evidence_class": config.evidence_class,
            "render_config": config.to_dict(),
            "pages": entries[carrier],
        })
    record = _bundle_record(carriers)
    _write_bundle(out_path, record)
    return record


_PAGE_ID_RE = re.compile(r"^(?:pg|page-)(\d+)$")


def _descriptor_geometry(descriptor, base_dir):
    """Load the descriptor's declared geometry profile artifact (or None).

    The profile uri resolves relative to the descriptor file, exactly like
    the digitization run layout (blobs/, carrier/). A declared-but-unreadable
    profile returns None — every frame then stays typed unknown downstream,
    never a guessed convention.
    """
    for profile in descriptor.get("profiles", []):
        if profile.get("kind") != "geometry":
            continue
        try:
            return json.loads((Path(base_dir) / profile["uri"]).read_text())
        except (OSError, ValueError, KeyError):
            return None
    return None


def _descriptor_page_targets(descriptor):
    """Enumerate (page_region, regions, spaces) targets from a descriptor.

    Pages are the descriptor's ``kind: page`` regions, ordered by their
    derivable page number (``pgN``/``page-N``); claimed regions attach
    through ``contains`` relations and keep their ids verbatim. ``spaces``
    are each region's declared geometry ``space`` — the frame name the
    declared geometry profile must resolve.
    """
    region_by_id = {r["id"]: r for r in descriptor.get("regions", [])}
    contained = {}
    for rel in descriptor.get("relations", []):
        if rel.get("kind") == "contains":
            contained.setdefault(rel["from"], []).append(rel["to"])

    pages = [r for r in descriptor.get("regions", []) if r.get("kind") == "page"]
    pages.sort(key=lambda p: (
        (int(m.group(1)), 0) if (m := _PAGE_ID_RE.match(p["id"])) else (10**9, 0)))

    targets = []
    for page in pages:
        regions, spaces = [], []
        for rid in contained.get(page["id"], []):
            region = region_by_id.get(rid)
            if region is None or "geometry" not in region:
                continue
            box = region["geometry"]
            regions.append({
                "id": region["id"],
                "x": box["x"],
                "y": box["y"],
                "w": box.get("w", box.get("width")),
                "h": box.get("h", box.get("height")),
            })
            spaces.append(box.get("space"))
        targets.append((page, regions, spaces))
    return targets


def build_descriptor_review_bundle(descriptor_path, out_path, config=None):
    """Render every page of a digitization descriptor for human review.

    ``descriptor_path`` is a DSC 0.3 descriptor as produced by
    ``python3 -m digitization run`` (artifact ``descriptor.json``, whose
    ``source.locator`` resolves relative to the descriptor's directory).
    One page entry per descriptor page — never truncated; a page whose
    claimed regions declare no single resolvable space stays typed unknown
    with regions kept (rect_px null), through the same declared-frame math
    the oracles use. Returns the embedded v2 record.
    """
    config = config or _default_config()
    descriptor_path = Path(descriptor_path)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    base_dir = descriptor_path.parent
    source = base_dir / descriptor["source"]["locator"]
    geometry = _descriptor_geometry(descriptor, base_dir)

    page_records = []
    for page, regions, spaces in _descriptor_page_targets(descriptor):
        frame_name = spaces[0] if spaces and len(set(spaces)) == 1 else None
        matched = _PAGE_ID_RE.match(page["id"])
        if matched is None:
            page_records.append({
                "page": None, "file": descriptor["source"]["locator"],
                "unavailable": (
                    f"page number not derivable from region id {page['id']!r}"),
                "regions": [
                    {"id": r["id"], "rect_px": None, "expected": None}
                    for r in regions],
                "image": None, "width": None, "height": None,
                "frame": None,
            })
            continue
        entry_config = replace(config, page=int(matched.group(1)))
        try:
            rendered = _maybe_render(entry_config, source)
        except render.RenderCommandError as exc:
            rendered = render.RenderUnavailable(config=entry_config,
                                                reason=str(exc))
        page_records.append(_page_record(
            entry_config.page, regions, entry_config, rendered, geometry,
            frame_name, file=descriptor["source"]["locator"]))

    record = _bundle_record([{
        "carrier": descriptor["id"],
        "evidence_class": config.evidence_class,
        "render_config": config.to_dict(),
        "pages": page_records,
    }])
    _write_bundle(out_path, record)
    return record


def _write_bundle(out_path, record):
    template = TEMPLATE_PATH.read_text()
    embedded = json.dumps(record, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__REVIEW_DATA_ISLAND__", embedded)
    assert "__REVIEW_DATA_ISLAND__" not in html
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


# -- verdicts ingest -------------------------------------------------------------------


_VERDICT_VOCABULARY = ("agree", "differ", "unknown")

# Ingest compares human verdicts against the derivation rows the review
# bundle was built from (build_calibration_review_bundle walks every unique
# (carrier, file, page, geometry, frame) target across all recorded runs);
# detection-run outcomes are a different oracle pass and are not attributed
# to the human pass.
_INGEST_RUN = "derivation"


def _record_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _oracle_rows(calibration):
    """derivation-run oracle outcomes keyed by (carrier, page, property)."""
    return {(row["carrier"], row["page"], row["property"]): row
            for row in calibration["per_page_outcomes"]
            if row.get("run", _INGEST_RUN) == _INGEST_RUN}


def _refuse(bundle, record_path):
    """Version pinning (typed refusal, never a warning)."""
    actual = _record_sha(record_path)
    if bundle.get("record_sha256") != actual:
        raise RecordVersionMismatch(
            f"verdicts bundle pins record sha256 "
            f"{bundle.get('record_sha256')!r} but {record_path} hashes to "
            f"{actual!r}; FP/FN statistics are never attributed to the "
            f"wrong record version")
    if bundle.get("base_commit") != _BASE_COMMIT:
        raise RecordVersionMismatch(
            f"verdicts bundle pins base_commit {bundle.get('base_commit')!r} "
            f"but ingest runs against {_BASE_COMMIT!r}; refusing to "
            f"attribute verdicts across commits")


def _base_commit():
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(_ROOT),
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 — provenance degrades to typed unknown
        return None


_BASE_COMMIT = _base_commit()


def _counterexample(row, record_sha, bundle_sha):
    """One differ row in the dsc03 counterexample format.

    replayable=false per existing convention (human verdicts are not
    machine-replayable); dsc03.compare.replay refuses the bundle."""
    return {
        "witness": {
            "rule_id": "visual-review-verdict-differ",
            "outcome": "differ",
            "comparator": {"id": "human-visual-review", "version": "1"},
            "endpoint_types": ["calibration-oracle", "human-verdict"],
            "observable_scope": ["carrier", "page", "region", "property"],
            "input_hashes": {
                "calibration_record": record_sha,
                "verdicts_bundle": bundle_sha,
            },
            "expected": "oracle agree",
            "observed": "human differ",
            "message": (f"human verdicts differ on region "
                        f"{row['region']!r} where the oracle recorded agree "
                        f"({row['carrier']} page {row['page']} "
                        f"{row['property']})"),
            "replayable": False,
            "redaction": {
                "omitted": ["rendered page pixels", "human review session"],
                "limitation": "human visual verdicts cannot be "
                              "machine-replayed; rerun requires the pinned "
                              "review bundle and a fresh human pass",
            },
            "replay_limitations": ["human verdicts are not machine-replayable"],
        },
        "inputs": {
            "carrier": row["carrier"],
            "page": row["page"],
            "region": row["region"],
            "property": row["property"],
        },
    }


def ingest_verdicts(verdicts_path, record_path=None, evaluation_record=None):
    """Ingest a review-verdicts bundle against the pinned calibration record.

    Returns the ingest report: per carrier × page × property agreement
    counts (human agree/differ/unknown vs the recorded derivation oracle
    outcome; oracle false-negative = human differ where oracle agree; human
    unknown never resolves — no winner election, no smoothing), per-page
    missed-ink accounting (labeled ESTIMATE with the sunset-9rg caveat), and
    the differ rows exported in the dsc03 counterexample format with
    replayable=false. Refuses with RecordVersionMismatch when the bundle
    does not pin ``record_path`` (record sha256) and the ingest commit
    (base_commit). Never modifies thresholds; when ``evaluation_record`` is
    a dict, the summary is appended to it via
    digitization.evaluation.append_visual_review_summary.
    """
    import copy

    from digitization.evaluation import append_visual_review_summary

    record_path = Path(record_path or _CALIBRATION_PATH)
    bundle = json.loads(Path(verdicts_path).read_text(encoding="utf-8"))
    if bundle.get("provenance") not in (None, PROVENANCE_LABEL):
        raise RecordVersionMismatch(
            f"unexpected bundle provenance {bundle.get('provenance')!r}; "
            f"ingest only accepts {PROVENANCE_LABEL} bundles")
    _refuse(bundle, record_path)

    calibration = json.loads(record_path.read_text(encoding="utf-8"))
    record_sha = _record_sha(record_path)
    bundle_sha = _record_sha(verdicts_path)
    oracle = _oracle_rows(calibration)

    agreement, missed_ink, unavailable_pages, counterexamples = [], [], [], []
    unknown_total = 0
    oracle_fn_total = 0

    for carrier_entry in bundle["verdicts"]["carriers"]:
        carrier = carrier_entry["carrier"]
        for page_entry in carrier_entry["pages"]:
            page = page_entry["page"]
            if page_entry.get("unavailable"):
                unavailable_pages.append({
                    "carrier": carrier,
                    "page": page,
                    "reason": page_entry["unavailable"],
                })
            # tri-state tally; verdicts outside the vocabulary are refused,
            # never coerced
            human = {"agree": 0, "differ": 0, "unknown": 0, "pending": 0}
            region_rows = []
            differs_here = []
            for region in page_entry.get("regions", []):
                verdict = region.get("verdict")
                if verdict is None:
                    human["pending"] += 1
                elif verdict not in _VERDICT_VOCABULARY:
                    raise RecordVersionMismatch(
                        f"verdict {verdict!r} outside the "
                        f"agree/differ/unknown vocabulary "
                        f"({carrier} page {page} region {region.get('id')!r})")
                else:
                    human[verdict] += 1
                    if verdict == "unknown":
                        unknown_total += 1
                    region_rows.append({"id": region["id"], "verdict": verdict})
                    if verdict == "differ":
                        differs_here.append(region["id"])

            properties = sorted(
                prop for (c, _p, prop) in oracle
                if c == carrier and _p == page)
            for prop in properties:
                oracle_status = oracle[(carrier, page, prop)]["status"]
                confusion = dict(human)
                confusion.pop("pending")
                oracle_fn = human["differ"] if oracle_status == "agree" else 0
                oracle_fn_total += oracle_fn
                row = {
                    "carrier": carrier,
                    "page": page,
                    "property": prop,
                    "oracle_status": oracle_status,
                    "human": dict(human),
                    "confusion": confusion,
                    "oracle_false_negatives": oracle_fn,
                    "regions": [dict(r) for r in region_rows],
                }
                if page_entry.get("unavailable"):
                    row["unavailable"] = page_entry["unavailable"]
                agreement.append(row)
            # one counterexample per differing region — the human verdict is
            # region-level, never re-counted per property
            for region_id in differs_here:
                counterexamples.append(_counterexample(
                    {"carrier": carrier, "page": page,
                     "region": region_id, "property": properties},
                    record_sha, bundle_sha))

            # missed-ink accounting: per page, count + total box area vs
            # page area — a proxy ESTIMATE, never a measurement
            page_size = page_entry.get("page_size_px") or None
            boxes = page_entry.get("missed_ink", [])
            total_area = sum(b["rect_px"][2] * b["rect_px"][3] for b in boxes)
            page_area = page_size[0] * page_size[1] if page_size else None
            missed_ink.append({
                "carrier": carrier,
                "page": page,
                "label": "ESTIMATE",
                "caveat": MISSING_INK_CAVEAT,
                "count": len(boxes),
                "total_area_px": total_area,
                "page_area_px": page_area,
                "area_fraction": (total_area / page_area
                                  if page_area else None),
            })

    report = {
        "kind": "visual-review-ingest-report",
        "version": 1,
        "provenance": PROVENANCE_LABEL,
        "record_path": str(record_path),
        "record_sha256": record_sha,
        "base_commit": bundle.get("base_commit"),
        "agreement": agreement,
        "missed_ink": missed_ink,
        "unavailable_pages": unavailable_pages,
        "counterexamples": counterexamples,
        "evaluation_summary": {
            "provenance": PROVENANCE_LABEL,
            "record_sha256": record_sha,
            "base_commit": bundle.get("base_commit"),
            "oracle_false_negatives": oracle_fn_total,
            "human_unknown_total": unknown_total,
            "missed_ink_pages": [
                {"carrier": m["carrier"], "page": m["page"],
                 "count": m["count"], "total_area_px": m["total_area_px"],
                 "area_fraction": m["area_fraction"]}
                for m in missed_ink if m["count"]],
            "differ_counterexamples": len(counterexamples),
        },
        "thresholds_modified": False,
        "recorded_thresholds": copy.deepcopy(calibration.get("thresholds")),
    }
    if isinstance(evaluation_record, dict):
        append_visual_review_summary(evaluation_record,
                                     report["evaluation_summary"])
    return report


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=".visual-review/index.html")
    parser.add_argument("--record", default=None,
                        help="calibration record (default fixtures/visual/calibration.json)")
    parser.add_argument("--descriptor", default=None,
                        help="DSC 0.3 descriptor (e.g. a digitization run output); "
                             "mutually exclusive with --record")
    parser.add_argument("--serve", nargs="?", const="8123", default=None,
                        metavar="PORT")
    sub = parser.add_subparsers(dest="command")
    ingest = sub.add_parser(
        "ingest", help="ingest a review-verdicts bundle against the pinned "
                       "calibration record; prints the ingest report JSON")
    ingest.add_argument("verdicts", help="verdicts JSON from the review SPA pass")
    ingest.add_argument("--record", default=None,
                        help="calibration record the bundle must pin "
                             "(default fixtures/visual/calibration.json)")
    ingest.add_argument("--counterexamples", default=None,
                        help="write differ rows (dsc03 counterexample format, "
                             "replayable=false) to this JSON path")
    return parser


def main(argv=None):
    """Build (and optionally serve) the all-examples review bundle.

    ``--out`` writes the self-contained HTML; ``--serve [port]`` then serves
    the output directory over loopback-only http.server and opens the page.
    ``ingest <verdicts.json> [--record RECORD]`` ingests a verdicts bundle
    (typed refusal on record-version mismatch) and prints the report JSON.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        report = ingest_verdicts(args.verdicts, record_path=args.record)
        if args.counterexamples:
            out = Path(args.counterexamples)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(report["counterexamples"], indent=1,
                           ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True))
        return 0
    if args.descriptor and args.record:
        parser.error("--descriptor and --record are mutually exclusive")

    if args.descriptor:
        record = build_descriptor_review_bundle(args.descriptor, args.out)
        n_pages = sum(len(c["pages"]) for c in record["carriers"])
        print(f"built {args.out}: {record['carriers'][0]['carrier']} — "
              f"{n_pages} descriptor pages")
    else:
        record = build_calibration_review_bundle(args.out, record_path=args.record)
        n_pages = sum(len(c["pages"]) for c in record["carriers"])
        print(f"built {args.out}: {len(record['carriers'])} carriers, "
              f"{n_pages} render targets")

    if args.serve:
        port = int(args.serve)
        out_dir = Path(args.out).resolve().parent
        url = f"http://localhost:{port}/{Path(args.out).name}"
        print(f"serving {url} (Ctrl-C to stop)")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        import http.server
        import socketserver

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(out_dir), **kw)

            def log_message(self, fmt, *log_args):
                pass

        with socketserver.TCPServer(("127.0.0.1", port), _Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
