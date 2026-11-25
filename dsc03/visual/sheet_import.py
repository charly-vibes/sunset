# Purpose: Attributed human-sheet import — typed ingest of HITL observation
#   sheets (the sunset-905.3 corpus) into DSC 0.3 region records.
# Responsibilities: Import existing region observations without modifying
#   source sheets or requiring DSC core wire changes; preserve every input
#   region with pinned sheet/source provenance OR account for it with an
#   explicitly typed ImportRefusal (zero silent drops); scope local region
#   ids to the originating sheet; bind each recorded page frame ONLY
#   through frames.resolve_pixel_mapping — the recorded viewport extent as
#   the raster extent, the carrier CropBox pt dims for the declared
#   px-per-pt scale — never a guessed coordinate convention; retain blank
#   and machine-inferred type provenance and derived-order provenance so
#   they never become independent human judgments.
# Rationale: document-adapters "Attributed human region import" (scenarios
#   "Preserve the accepted human geometry corpus", "Refuse unsupported
#   frame conversion"). Provenance pinning follows the repo's established
#   905.3 conventions (run_composition.py): a sheet's carrier resolves by
#   name under the sheet bundle's pristine copies (bundle/carriers), the
#   source root, or fixtures/carriers; the pinned digest comes from the
#   bundle's SHA256SUMS.txt, and an actual carrier file that digests
#   differently is a typed `source-digest-mismatch`, never a silent import
#   of unverified geometry. Recorded page frames declare the page rectangle
#   as fractions of the recorded viewport (the committed corpus records the
#   full-bleed 0/0/1/1 frame); the sheet's viewport dims are the raster
#   extent supplied to frames.resolve_pixel_mapping (the recorded viewport,
#   not a dpi recomputation, is what the reader actually saw, so the frame
#   declares NO source_dimensions and the frames.py extent check is
#   skipped), the px-per-pt scale is derived from that viewport and the
#   carrier CropBox at the identity dpi (72), and the page-rect offset
#   becomes the frame's declared crop — exactly the frames.py crop
#   semantics (crop positions the descriptor's local origin on the page;
#   the y component is negative for a page rect that sits above the
#   viewport bottom, which the frames.py crop validation permits). An
#   UnknownMapping becomes `frame-binding-refused`; a carrier file that
#   cannot be resolved at all also refuses `frame-binding-refused` (sheet
#   provenance cannot be bound — the nearest typed reason in the closed
#   refusal vocabulary). Machine-prefilled types are recognized via the
#   additive `prefill_provenance` marker key `types` (INSTRUCTIONS.md:
#   accepted pre-fills are marked in an additive prefill_provenance
#   object; `order_ranks` is the established sibling marker).
"""Human observation-sheet import: attributed ingest of HITL region sheets."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from dsc03.visual.frames import UnknownMapping, resolve_pixel_mapping

# The closed refusal vocabulary (document-adapters "Refuse unsupported
# frame conversion" + the shared import contract).
REFUSAL_REASONS = frozenset(
    {
        "source-digest-mismatch",
        "invalid-box",
        "missing-frame",
        "frame-binding-refused",
    }
)

# Identity dpi for frame binding: unit pt converts 1:1 at 72 dpi, so the
# frame's declared scale IS the recorded px-per-pt zoom of the viewport.
_FRAME_DPI = 72

# Fraction slack for the viewport-containment bound (float noise only).
_BOX_EPS = 1e-9

# Pinned aspect tolerance for the declared px-per-pt scale: a recorded
# viewport whose x/y zoom disagrees by more than this cannot be the CropBox
# page displayed unrotated (the committed corpus deviates < 0.1% — bank
# 1.000094, diario 1.000738, agentic 0.99970; a rotated/swapped recording
# deviates by tens of percent). Reuses the frames.py extent vocabulary:
# typed `page-extent-mismatch`, never a silent misalignment.
_ASPECT_TOLERANCE = 0.01

# prefill_provenance marker key that flags machine-prefilled region types
# (mirrors the established `order_ranks` marker).
_TYPE_PREFILL_KEY = "types"

_SHEET_SUFFIX = ".observations.json"


@dataclass(frozen=True)
class ImportRefusal:
    """One input region accounted for as explicitly unresolved.

    Every input region lands either in SheetImportResult.regions or in
    .refusals with one of REFUSAL_REASONS — never silently dropped.
    """

    region_key: str
    reason: str
    detail: str


@dataclass(frozen=True)
class SheetImportResult:
    """Whole-run accounting: sheet provenance, imported regions, refusals."""

    sheets: list
    regions: list
    refusals: list


@dataclass(frozen=True)
class _SheetViewport:
    """Minimal render-config stand-in for frame binding: dpi + declared page.

    frames.resolve_pixel_mapping reads exactly `dpi` and `page` off the
    render config; the sheet viewport contributes nothing else.
    """

    dpi: int
    page: int


def import_sheets(sheet_paths, *, source_root):
    """Import human observation sheets into region records.

    `sheet_paths` are sheet JSON paths; `source_root` is the sheet bundle
    root the sheets were returned under (carriers resolve beneath it, with
    the repo fixtures as the last resort; pinned digests come from its
    SHA256SUMS.txt). Returns a SheetImportResult in which every input
    region across all sheets is either imported with pinned provenance or
    accounted for by an ImportRefusal.
    """
    result = SheetImportResult(sheets=[], regions=[], refusals=[])
    for raw_path in sheet_paths:
        _import_one(Path(raw_path), Path(source_root), result)
    return result


def _import_one(path, source_root, result):
    """Import one sheet: pin provenance, then per-region resolve or refuse."""
    sheet = json.loads(path.read_text(encoding="utf-8"))
    sheet_id = _sheet_id(path)
    page_frames = sheet.get("page_frames") or {}
    prefill = sheet.get("prefill_provenance") or {}
    carrier = sheet.get("carrier")
    carrier_path = _resolve_carrier(source_root, carrier) if carrier else None
    pinned = _pinned_digest(source_root, carrier) if carrier else None
    actual = _sha256_file(carrier_path) if carrier_path is not None else None

    # Sheet-level provenance gate, checked before any geometry: a carrier
    # that no longer digests to the sheet's pinned sha invalidates every
    # region of the sheet; an unresolvable carrier cannot bind provenance.
    sheet_state = None
    if pinned is not None and actual is not None and actual != pinned:
        sheet_state = (
            "source-digest-mismatch",
            f"sheet pins sha256:{pinned} but carrier file {carrier_path} "
            f"digests to sha256:{actual}",
        )
    elif carrier_path is None:
        sheet_state = (
            "frame-binding-refused",
            f"carrier {carrier!r} not found under {source_root} (bundle/"
            "carriers, carriers/, bundle root, repo fixtures); sheet "
            "provenance cannot be bound to a file",
        )

    result.sheets.append(
        {
            "sheet_id": sheet_id,
            "reader": sheet.get("reader"),
            "carrier": carrier,
            "source_sha256": pinned,
            "page_frames": page_frames,
            "prefill_provenance": prefill,
        }
    )

    carrier_pages = _CarrierPages(carrier_path) if carrier_path is not None else None
    try:
        for index, entry in enumerate(sheet.get("structure") or [], start=1):
            if not isinstance(entry, dict):
                result.refusals.append(
                    ImportRefusal(
                        f"{sheet_id}:{index}",
                        "invalid-box",
                        f"structure entry {index} is not a mapping: {type(entry).__name__}",
                    )
                )
                continue
            label = entry.get("label")
            region_key = f"{sheet_id}:{label if isinstance(label, str) and label else index}"
            if sheet_state is not None:
                result.refusals.append(ImportRefusal(region_key, sheet_state[0], sheet_state[1]))
                continue
            page = entry.get("page")
            frame_record = page_frames.get(str(page))
            if frame_record is None:
                result.refusals.append(
                    ImportRefusal(
                        region_key,
                        "missing-frame",
                        f"page_frames lacks page {page!r}; no declared frame to "
                        "convert the box through",
                    )
                )
                continue
            box_problem = _invalid_box_reason(entry.get("bbox"))
            if box_problem is not None:
                result.refusals.append(ImportRefusal(region_key, "invalid-box", box_problem))
                continue
            bound = _bind_page_frame(page, frame_record, sheet_id, carrier_pages)
            if isinstance(bound, UnknownMapping):
                result.refusals.append(
                    ImportRefusal(
                        region_key,
                        "frame-binding-refused",
                        f"declared page frame did not resolve: {bound.reason}: {bound.detail}",
                    )
                )
                continue
            mapping, dims = bound
            result.regions.append(
                _region(
                    entry,
                    sheet_id,
                    region_key,
                    sheet.get("reader"),
                    page,
                    mapping,
                    dims,
                    actual,
                    prefill,
                )
            )
    finally:
        if carrier_pages is not None:
            carrier_pages.close()


def _sheet_id(path):
    """The originating sheet's local id: file name without the sheet suffix."""
    name = path.name
    if name.endswith(_SHEET_SUFFIX):
        return name[: -len(_SHEET_SUFFIX)]
    return name


def _resolve_carrier(source_root, carrier):
    """Resolve a sheet's carrier by name: bundle pristine copies first, then
    the source root's own carriers/ and root, then the repo fixtures."""
    name = f"{carrier}.pdf"
    for directory in (
        source_root / "bundle" / "carriers",
        source_root / "carriers",
        source_root,
        Path(__file__).resolve().parents[2] / "fixtures" / "carriers",
    ):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _pinned_digest(source_root, carrier):
    """The carrier digest pinned beside the sheets (SHA256SUMS.txt), or None.

    Entries match by file name; the bundle records bare names for its
    pristine carrier copies.
    """
    name = f"{carrier}.pdf"
    for sums_path in (source_root / "bundle" / "SHA256SUMS.txt", source_root / "SHA256SUMS.txt"):
        if not sums_path.is_file():
            continue
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].rsplit("/", 1)[-1] == name:
                return parts[0]
    return None


def _sha256_file(path):
    """Hex sha256 of a file's bytes, streamed (reuse-safe digest helper)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _CarrierPages:
    """One open carrier per sheet: page pt dims served without re-parsing.

    Holds the pymupdf document open for the sheet's whole import (one xref
    parse per carrier, not one per page); `close` releases it. Unreadable
    pages yield None — the caller converts that into a typed refusal.
    """

    def __init__(self, carrier_path):
        self._path = carrier_path
        self._doc = None
        self._dims = {}

    def page_pt(self, page):
        """Declared pt extent (CropBox) of one carrier page, or None."""
        if page not in self._dims:
            self._dims[page] = self._read(page)
        return self._dims[page]

    def _read(self, page):
        try:
            index = int(page) - 1
            if self._doc is None:
                self._doc = pymupdf.open(filename=str(self._path))
            if not 0 <= index < self._doc.page_count:
                return None
            box = self._doc[index].cropbox
        except Exception:
            return None
        if box is None or box.width <= 0 or box.height <= 0:
            return None
        return (float(box.width), float(box.height))

    def close(self):
        if self._doc is not None:
            self._doc.close()
            self._doc = None


def _bind_page_frame(page, frame_record, sheet_id, carrier_pages):
    """Bind one recorded page frame through resolve_pixel_mapping.

    Declares: canonical descriptor space, unit pt at the identity dpi, the
    px-per-pt scale derived from the recorded viewport extent and the
    carrier CropBox dims, rotation 0 (sheet viewports are unrotated), and
    the recorded page-rect offset as the frame's crop (frames.py semantics:
    crop positions the descriptor's local origin on the page — so a page
    rect at viewport fraction (fx, fy, fw, fh) crops by (fx·vw/sx,
    (1−fy−fh)·vh/sy)). No source_dimensions: the recorded viewport is the
    authoritative raster extent — which also skips frames.py's dpi
    recomputation check, so a pinned aspect guard stands in for it: a
    scale whose x/y zoom disagrees beyond _ASPECT_TOLERANCE is typed
    `page-extent-mismatch` (a rotated/swapped recording must refuse, not
    silently mis-map). Returns (PixelMapping, (w_pt, h_pt)) or
    UnknownMapping — never a guessed mapping.
    """
    vw = frame_record.get("viewport_w")
    vh = frame_record.get("viewport_h")
    if not (
        isinstance(vw, int)
        and not isinstance(vw, bool)
        and vw > 0
        and isinstance(vh, int)
        and not isinstance(vh, bool)
        and vh > 0
    ):
        return UnknownMapping(
            "invalid_page_extent",
            f"recorded viewport extent {(vw, vh)!r} is not two positive integers",
        )
    dims = carrier_pages.page_pt(page)
    if dims is None:
        return UnknownMapping(
            "invalid_geometry_frame",
            f"carrier page {page!r} pt dimensions unreadable from {carrier_pages._path}",
        )
    w_pt, h_pt = dims

    fx = frame_record.get("x", 0.0)
    fy = frame_record.get("y", 0.0)
    fw = frame_record.get("w", 1.0)
    fh = frame_record.get("h", 1.0)
    if not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        for v in (fx, fy, fw, fh)
    ):
        return UnknownMapping(
            "malformed_frame",
            f"page rect {(fx, fy, fw, fh)!r} must be finite viewport fractions",
        )
    scale = (fw * vw / w_pt, fh * vh / h_pt)
    if scale[0] > 0 and scale[1] > 0:
        ratio = min(scale) / max(scale)
        if ratio < 1 - _ASPECT_TOLERANCE:
            return UnknownMapping(
                "page-extent-mismatch",
                f"declared px-per-pt scale {scale!r} is nonuniform beyond the "
                f"pinned aspect tolerance {_ASPECT_TOLERANCE} (ratio {ratio:.6f}); "
                "the recorded viewport cannot be the CropBox page displayed "
                "unrotated",
            )
    crop = {"x": fx * vw / scale[0], "y": (1 - fy - fh) * vh / scale[1]}
    frame = {
        "name": f"{sheet_id}:page:{page}",
        "source_scope": f"page:{page}",
        "unit": "pt",
        "origin": "bottom-left",
        "axes": "x-right-y-up",
        "scale": scale,
        "rotation": 0,
    }
    if crop["x"] != 0.0 or crop["y"] != 0.0:
        frame["crop"] = crop
    mapping = resolve_pixel_mapping(
        frame, _SheetViewport(dpi=_FRAME_DPI, page=page), (vw, vh)
    )
    if isinstance(mapping, UnknownMapping):
        return mapping
    return mapping, dims


def _invalid_box_reason(bbox):
    """Typed invalid-box detail, or None when the box is structurally valid.

    A valid box has four finite, non-negative numbers, positive area, and
    stays within the recorded page viewport (fractions of it).
    """
    if not isinstance(bbox, dict):
        return f"bbox record is not a mapping: {bbox!r}"
    values = {}
    for key in ("x", "y", "w", "h"):
        value = bbox.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            return f"bbox {key!r} is not a finite number: {value!r}"
        values[key] = float(value)
    if min(values.values()) < 0:
        negative = {k: v for k, v in values.items() if v < 0}
        return f"bbox has negative components: {negative}"
    if values["w"] <= 0 or values["h"] <= 0:
        return f"bbox is degenerate (zero-area): w={values['w']!r} h={values['h']!r}"
    if values["x"] + values["w"] > 1 + _BOX_EPS or values["y"] + values["h"] > 1 + _BOX_EPS:
        return (
            "bbox extends past the recorded page viewport: "
            f"x+w={values['x'] + values['w']!r} y+h={values['y'] + values['h']!r}"
        )
    return None


def _region(entry, sheet_id, region_key, reader, page, mapping, dims, carrier_sha, prefill):
    """One imported region dict: contract keys, provenance pinned verbatim."""
    bbox = entry["bbox"]
    w_pt, h_pt = dims
    # Box corners in descriptor pt (y-up bottom-left): the recorded y is a
    # top-origin fraction, so top edge = (1 − y)·H, bottom edge = (1 − y − h)·H.
    x1, y1 = mapping.descriptor_to_pixel(bbox["x"] * w_pt, (1 - bbox["y"]) * h_pt)
    x2, y2 = mapping.descriptor_to_pixel(
        (bbox["x"] + bbox["w"]) * w_pt, (1 - bbox["y"] - bbox["h"]) * h_pt
    )
    return {
        "sheet_id": sheet_id,
        "region_id": region_key,
        "reader": reader,
        "page": page,
        "bbox_px": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1},
        "bbox_relative": dict(bbox),
        "viewport_w": bbox.get("viewport_w"),
        "viewport_h": bbox.get("viewport_h"),
        "carrier_sha256": carrier_sha,
        "type": entry.get("type", ""),
        "type_provenance": _type_provenance(entry.get("type"), prefill),
        "order_rank": entry.get("order_rank"),
        "order_alternatives": list(entry.get("order_alternatives") or []),
        "evidence": entry.get("evidence"),
    }


def _type_provenance(type_value, prefill):
    """blank / machine-inferred / human — never promotes a non-human entry."""
    if not isinstance(type_value, str) or not type_value.strip():
        return "blank"
    if prefill.get(_TYPE_PREFILL_KEY):
        return "machine-inferred"
    return "human"
