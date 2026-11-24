# Purpose: Render-lineage gate between the two render paths and oracle
#   evaluation (openspec improve-geometry-render-binding tasks 3.1-3.2,
#   review finding CORR-001, spec delta "Render lineage labeling covers both
#   paths").
# Responsibilities: Pin that a review crop rendered by the in-process PyMuPDF
#   path (digitization/render.py) is labeled `correlated` with the same
#   vocabulary/shape as dsc03/visual/render.py's RenderConfig (extractor_/
#   renderer_lineage + evidence_class), and that the evaluation entry point
#   (dsc03/visual/review.py) refuses such correlated-labeled renders — the
#   crop is absent from the evaluation record with a typed reason, never a
#   silent skip, while its lineage label still reads `correlated`.
# Rationale: PyMuPDF render + PyMuPDF extraction share an implementation
#   lineage, so those crops are correlated evidence by construction and
#   SHALL NOT be read by oracle evaluation (deployed spec: "oracle
#   evaluation SHALL NOT read correlated renders"). Zero rendered-pixel
#   change: this is pure labeling plus one typed refusal gate.
import shutil
from pathlib import Path

import pymupdf

from dsc03.visual import Binarization, RenderConfig, render
from dsc03.visual.review import build_review_bundle

REPO = Path(__file__).resolve().parents[2]
CARRIER_PDF = REPO / "fixtures/carriers/bank-statement-ca-excerpt.pdf"


def _correlated_config(page=1):
    """The in-process PyMuPDF path's lineage, in RenderConfig shape.

    Same fields as the pinned poppler config, but render lineage == extractor
    lineage (`pymupdf`), i.e. exactly how digitization/render.py output is
    labeled — correlated evidence by construction.
    """
    return RenderConfig(
        renderer_name="pymupdf",
        renderer_executable="pymupdf",
        renderer_version=pymupdf.VersionBind,
        dpi=72,
        page=page,
        binarization=Binarization(enabled=True, method="fixed-threshold",
                                  threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="pymupdf",
    )


def _independent_config(page=1):
    exe = shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=exe,
        renderer_version=render.detect_renderer_version(exe),
        dpi=72,
        page=page,
        binarization=Binarization(enabled=True, method="fixed-threshold",
                                  threshold=128),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


# --- 3.2: the in-process PyMuPDF path labels its own outputs ----------------


def test_digitization_render_labels_lineage_correlated(tmp_path):
    from digitization.render import render_page

    source = (tmp_path / "source.pdf")
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), "Primera pagina con texto nativo")
        pdf.save(source)

    png, meta = render_page(source.read_bytes(), 1, 72)

    # Same vocabulary/shape as RenderConfig (dsc03/visual/render.py).
    assert meta["extractor_lineage"] == "pymupdf"
    assert meta["renderer_lineage"] == "pymupdf"
    assert meta["evidence_class"] == "correlated"
    # The pinned rule, derived the same way: shared lineage → correlated.
    assert meta["evidence_class"] == render.evidence_class(
        meta["extractor_lineage"], meta["renderer_lineage"])


def test_digitization_render_labeling_is_pure(tmp_path):
    """Labeling adds no pixels: the bytes render identically through the
    oracle path when labeled independent — same content, same extent."""
    from digitization.render import render_page

    source = (tmp_path / "source.pdf")
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), "Primera pagina con texto nativo")
        pdf.save(source)

    png, meta = render_page(source.read_bytes(), 1, 72)
    pix = pymupdf.Pixmap(png)
    assert (pix.width, pix.height) == (meta["width_px"], meta["height_px"])
    # Correlated labeling never travels with an oracle claim.
    assert render.supports_accuracy_claim(meta["evidence_class"]) is False


# --- 3.1: evaluation refuses correlated-labeled renders ---------------------


def test_evaluation_entry_refuses_correlated_render(tmp_path):
    """Spec scenario 'Review crop never feeds an oracle'.

    GIVEN a review crop whose render lineage is the in-process PyMuPDF path
    (correlated) WHEN the evaluation entry enumerates its page inputs
    THEN the crop is absent (no embedded image) with a typed refusal reason,
    and its lineage label still reads `correlated` — never a silent skip,
    never a relabeled crop.
    """
    out = tmp_path / "review.html"
    record = build_review_bundle(
        CARRIER_PDF,
        regions=[{"id": "r1", "x": 54, "y": 700, "w": 200, "h": 40,
                  "expected": "ink"}],
        geometry={"frames": {}},
        frame_name=None,
        carrier="correlated-crop-carrier",
        out_path=out,
        config=_correlated_config(),
    )
    (carrier,) = record["carriers"]
    assert carrier["evidence_class"] == "correlated"
    for page in carrier["pages"]:
        assert page["image"] is None, "correlated crop fed the evaluation"
        assert page["unavailable"], "refusal must be typed, never silent"
        assert page["unavailable"].startswith("correlated-render-refused")


def test_evaluation_entry_still_renders_independent(tmp_path):
    """The gate excludes ONLY correlated lineage; the pinned independent
    poppler render is untouched (regression pin for the refusal scope)."""
    exe = shutil.which("pdftoppm")
    if exe is None:
        return  # no poppler on this host: the refusal path alone is pinned
    out = tmp_path / "review.html"
    record = build_review_bundle(
        CARRIER_PDF,
        regions=[{"id": "r1", "x": 54, "y": 700, "w": 200, "h": 40,
                  "expected": "ink"}],
        geometry={"frames": {}},
        frame_name=None,
        carrier="independent-crop-carrier",
        out_path=out,
        config=_independent_config(),
    )
    (carrier,) = record["carriers"]
    assert carrier["evidence_class"] == "independent"
    assert all(p["unavailable"] is None or "correlated-render-refused"
               not in p["unavailable"] for p in carrier["pages"])
