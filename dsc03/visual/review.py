# Purpose: Human visual-review bundle generator (sunset-e8t, sunset-fgg) —
#   the bridge between the raster visual oracles and a human
#   side-by-side/overlay comparison pass.
# Responsibilities: Render pinned carrier pages through the same
#   pinned-render configuration the oracles use, resolve the declared
#   geometry frames, map claimed descriptor region rects into pixel space,
#   and embed renders + mapped regions + render configuration + evidence
#   class into the offline review SPA template
#   (hitl/visual-review/templates/visual-review-spa.html). Walks every
#   unique render target recorded in fixtures/visual/calibration.json for
#   the all-examples bundle. Missing renderers and unresolvable frames stay
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
import json
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


def _regions_for(calibration, carrier_id):
    matches = [c for c in calibration["carriers"] if c["id"] == carrier_id]
    assert len(matches) == 1, f"carrier {carrier_id!r} not uniquely recorded"
    return [dict(r) for r in matches[0]["regions"]]


def _page_record(page_number, regions, config, rendered, geometry, frame_name,
                 file=None):
    """One page entry: pinned render + frame-mapped claimed regions."""
    record = {"page": page_number, "file": file, "unavailable": None,
              "regions": [], "image": None, "width": None, "height": None,
              "frame": frame_name}
    if isinstance(rendered, render.RenderUnavailable):
        record["unavailable"] = rendered.reason
        return record
    width, height = _pixmap_extent(rendered.data)
    record["image"] = "data:image/png;base64," + base64.b64encode(
        rendered.data).decode("ascii")
    record["width"] = width
    record["height"] = height
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
    rendered = render.render_page(config, pdf_path)
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
        rendered = render.render_page(entry_config, _ROOT / file_rel)
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


def _write_bundle(out_path, record):
    template = TEMPLATE_PATH.read_text()
    embedded = json.dumps(record, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__REVIEW_DATA_ISLAND__", embedded)
    assert "__REVIEW_DATA_ISLAND__" not in html
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


def main(argv=None):
    """Build (and optionally serve) the all-examples review bundle.

    ``--out`` writes the self-contained HTML; ``--serve [port]`` then serves
    the output directory over loopback-only http.server and opens the page.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=".visual-review/index.html")
    parser.add_argument("--record", default=None,
                        help="calibration record (default fixtures/visual/calibration.json)")
    parser.add_argument("--serve", nargs="?", const="8123", default=None,
                        metavar="PORT")
    args = parser.parse_args(argv)

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
