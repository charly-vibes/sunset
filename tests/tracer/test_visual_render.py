# Purpose: Pinned render configuration tests (sunset-xzy.1, tasks.md 3.1).
# Responsibilities: Pin the oracle-render contract from
#   document-visual-oracles "Pinned render configuration" and "Labeled evidence
#   class": (a) identical configurations over one fixture PDF reproduce
#   byte-identical poppler renders; (b) a missing renderer executable yields a
#   typed `unavailable` outcome — never bytes, never a silent skip, never a
#   bare exception; (c) the frozen config record round-trips every recorded
#   field (renderer name/version, DPI, page selection, binarization, source
#   simplification, lineages); (d) lineage declarations label results
#   correlated (shared lineage) vs independent (distinct renderer), and
#   correlated results can never support accuracy claims.
# Rationale: design D2 (poppler pdftoppm, recording + byte-identity), D4
#   (source simplification recorded per config), D5 (typed unavailable outcome).
"""Pinned oracle-render config + evidence-class tests (sunset-xzy.1)."""
import dataclasses
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dsc03.visual import render

FIXTURE_PDF = (
    Path(__file__).resolve().parents[2]
    / "fixtures" / "carriers" / "bank-statement-ca-excerpt.pdf"
)


def _poppler_executable():
    exe = shutil.which("pdftoppm") or "/usr/bin/pdftoppm"
    return exe


def _poppler_version(exe):
    version = render.detect_renderer_version(exe)
    assert version, "pdftoppm -v must yield a version string"
    return version


def _poppler_config(page=1, dpi=72):
    exe = _poppler_executable()
    return render.RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable=exe,
        renderer_version=_poppler_version(exe),
        dpi=dpi,
        page=page,
        binarization=render.Binarization(enabled=False),
        source_simplification="none",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )


def test_identical_config_renders_byte_identical():
    """Spec 'Reproducible render': same page twice from one config → equal bytes."""
    config = _poppler_config()
    first = render.render_page(config, FIXTURE_PDF)
    second = render.render_page(config, FIXTURE_PDF)
    assert isinstance(first, render.Rendered)
    assert first.status == "rendered"
    assert isinstance(first.data, bytes) and first.data, "render must yield bytes"
    assert second.data == first.data, "identical configs must render byte-identical"
    assert second.config == first.config


def test_missing_renderer_yields_typed_unavailable():
    """Spec 'Renderer unavailable': missing executable → typed unavailable, not agree/bytes."""
    config = _poppler_config()
    missing = dataclasses.replace(config, renderer_executable="/nonexistent/pdftoppm-nope")
    result = render.render_page(missing, FIXTURE_PDF)
    assert isinstance(result, render.RenderUnavailable)
    assert result.status == "unavailable"
    assert result.reason, "unavailable must carry a reason"
    assert not isinstance(result, render.Rendered)
    assert getattr(result, "data", None) is None


def test_config_record_round_trips_all_fields():
    """Every recorded field survives to_dict/from_dict; the record stays frozen."""
    config = render.RenderConfig(
        renderer_name="pdftoppm",
        renderer_executable="/usr/bin/pdftoppm",
        renderer_version="26.01.0",
        dpi=150,
        page=3,
        binarization=render.Binarization(enabled=True, method="fixed-threshold", threshold=180),
        source_simplification="ink-dilation-2px",
        extractor_lineage="pymupdf",
        renderer_lineage="poppler",
    )
    record = config.to_dict()
    for field in (
        "renderer_name", "renderer_executable", "renderer_version",
        "dpi", "page", "binarization", "source_simplification",
        "extractor_lineage", "renderer_lineage",
    ):
        assert field in record, f"config must record {field}"
    assert record["dpi"] == 150 and record["page"] == 3
    assert record["binarization"] == {
        "enabled": True, "method": "fixed-threshold", "threshold": 180
    }
    assert render.RenderConfig.from_dict(record) == config
    try:
        config.dpi = 300  # frozen: must raise
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("RenderConfig must be immutable (frozen)")


def test_lineage_labels_evidence_class():
    """Spec 'Labeled evidence class': shared lineage → correlated; distinct → independent."""
    correlated = render.evidence_class("pymupdf", "pymupdf")
    independent = render.evidence_class("pymupdf", "poppler")
    assert correlated == "correlated"
    assert independent == "independent"
    assert _poppler_config().evidence_class == "independent"

    shared = render.RenderConfig(
        renderer_name="pymupdf", renderer_executable="pymupdf", renderer_version="1.0",
        dpi=72, page=1, binarization=render.Binarization(), source_simplification="none",
        extractor_lineage="pymupdf", renderer_lineage="pymupdf",
    )
    assert shared.evidence_class == "correlated"
    # Correlated results support sensitivity demonstrations only — never accuracy.
    assert render.supports_accuracy_claim(correlated) is False
    assert render.supports_accuracy_claim(independent) is True
