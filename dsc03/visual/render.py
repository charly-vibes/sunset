# Purpose: Pinned oracle-render infrastructure (sunset-xzy.1, tasks.md 3.1).
# Responsibilities: Provide the immutable RenderConfig record (renderer
#   name/version, DPI, page selection, binarization settings, source
#   simplification, extractor/renderer lineage declarations); render a PDF page
#   through poppler `pdftoppm` so identical configurations produce
#   byte-identical output; return typed render-level outcomes — Rendered
#   (bytes + config) or typed RenderUnavailable (reason) for a missing
#   renderer executable, never a silent skip, never `agree`, never a bare
#   exception; and derive the evidence class (correlated / independent) from
#   the declared lineages, with correlated results restricted to sensitivity
#   demonstrations only — they can never support accuracy claims.
# Rationale: document-visual-oracles "Pinned render configuration"
#   (reproducible render; renderer unavailable → typed `unavailable`) and
#   "Labeled evidence class"; design D2 (poppler pdftoppm as the initial
#   independent renderer, recorded + byte-identical), D4 (source
#   simplification recorded per config), D5 (outcome vocabulary with typed
#   `unavailable`). Applying binarization to rendered pixels is the ink-mask
#   oracle's concern (tasks 4.x); here it is recorded, not applied.
"""Pinned render configuration, pdftoppm runner, and evidence-class labeling."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory


class RenderCommandError(RuntimeError):
    """The pinned renderer ran but the render command failed (nonzero exit).

    Distinct from RenderUnavailable: the executable existed, the render
    itself did not. Callers must handle this explicitly; nothing is guessed.
    """


@dataclass(frozen=True)
class Binarization:
    """Binarization settings recorded per render configuration (design D2).

    Recorded only in this slice; applying a threshold to rendered pixels is
    the ink-mask oracle's concern (tasks 4.x).
    """

    enabled: bool = False
    method: str = "fixed-threshold"
    threshold: int | None = None

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "method": self.method,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, record):
        return cls(
            enabled=bool(record["enabled"]),
            method=str(record["method"]),
            threshold=None if record["threshold"] is None else int(record["threshold"]),
        )


@dataclass(frozen=True)
class RenderConfig:
    """Immutable record of exactly how one oracle render is produced.

    Records renderer name, version and executable, DPI, 1-based page
    selection, binarization settings and the source simplification (design
    D4: what the source image is simplified to before comparison), plus the
    declared extractor and renderer implementation lineages used for evidence
    labeling. Identical configs must reproduce byte-identical renders.
    """

    renderer_name: str
    renderer_executable: str
    renderer_version: str
    dpi: int
    page: int
    extractor_lineage: str
    renderer_lineage: str
    binarization: Binarization = field(default_factory=Binarization)
    source_simplification: str = "none"

    @property
    def evidence_class(self) -> str:
        """`correlated` when render and extraction share a lineage, else `independent`."""
        return evidence_class(self.extractor_lineage, self.renderer_lineage)

    def to_dict(self):
        """Plain-scalar record of every pinned field (suitable for JSON)."""
        return {
            "renderer_name": self.renderer_name,
            "renderer_executable": self.renderer_executable,
            "renderer_version": self.renderer_version,
            "dpi": self.dpi,
            "page": self.page,
            "binarization": self.binarization.to_dict(),
            "source_simplification": self.source_simplification,
            "extractor_lineage": self.extractor_lineage,
            "renderer_lineage": self.renderer_lineage,
        }

    @classmethod
    def from_dict(cls, record):
        return cls(
            renderer_name=str(record["renderer_name"]),
            renderer_executable=str(record["renderer_executable"]),
            renderer_version=str(record["renderer_version"]),
            dpi=int(record["dpi"]),
            page=int(record["page"]),
            binarization=Binarization.from_dict(record["binarization"]),
            source_simplification=str(record["source_simplification"]),
            extractor_lineage=str(record["extractor_lineage"]),
            renderer_lineage=str(record["renderer_lineage"]),
        )


@dataclass(frozen=True)
class Rendered:
    """Successful render: the produced bytes together with the pinned config."""

    config: RenderConfig
    data: bytes
    status: str = "rendered"


@dataclass(frozen=True)
class RenderUnavailable:
    """Typed unavailable outcome (design D5): the pinned renderer is missing.

    Behaves like `unknown` for aggregates — it never collapses to a pass, a
    fail, or a silent skip of the check.
    """

    config: RenderConfig
    reason: str
    status: str = "unavailable"


def evidence_class(extractor_lineage: str, renderer_lineage: str) -> str:
    """Label the evidence class from declared implementation lineages.

    `correlated` when extraction and rendering share a lineage (e.g. PyMuPDF
    render for PyMuPDF extraction); `independent` otherwise (poppler render
    vs PyMuPDF extraction).
    """
    return "correlated" if extractor_lineage == renderer_lineage else "independent"


def supports_accuracy_claim(evidence_label: str) -> bool:
    """Whether a labeled result MAY support an accuracy claim.

    Spec "Labeled evidence class": correlated results SHALL NOT support
    accuracy claims — they demonstrate sensitivity only (e.g. that a seeded
    defect shifts the outcome). Independent results may support accuracy
    claims, subject to the remaining gates (calibration, declared frames).
    """
    return evidence_label != "correlated"


def detect_renderer_version(executable: str) -> str:
    """Shell out to `<executable> -v` once and return its version string.

    poppler tools print their version banner on stderr; tolerate a nonzero
    exit. An empty string means the version could not be determined.
    """
    try:
        proc = subprocess.run(
            [executable, "-v"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    banner = (proc.stdout or "") + (proc.stderr or "")
    match = re.search(r"version\s+(\S+)", banner)
    return match.group(1) if match else ""


def render_page(config: RenderConfig, pdf_path) -> Rendered | RenderUnavailable:
    """Render one PDF page through the pinned renderer.

    Returns Rendered (bytes + config) on success, or a typed
    RenderUnavailable when the pinned renderer executable is missing —
    never bytes from a substitute renderer, never a silent skip. A renderer
    that exists but fails raises the typed RenderCommandError.
    """
    pdf_path = Path(pdf_path)
    resolved = shutil.which(config.renderer_executable) or (
        config.renderer_executable
        if "/" in config.renderer_executable and Path(config.renderer_executable).is_file()
        else None
    )
    if resolved is None:
        return RenderUnavailable(
            config=config,
            reason=(
                f"pinned renderer executable not found: {config.renderer_executable!r} "
                f"(renderer_name={config.renderer_name!r}, "
                f"version={config.renderer_version!r})"
            ),
        )
    with TemporaryDirectory(prefix="sunset-render-") as tmp:
        out_prefix = str(Path(tmp) / "page")
        command = [
            resolved,
            "-r", str(config.dpi),
            "-f", str(config.page),
            "-l", str(config.page),
            "-singlefile",
            "-png",
            str(pdf_path),
            out_prefix,
        ]
        try:
            proc = subprocess.run(
                command, capture_output=True, text=True, timeout=120, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RenderCommandError(f"render invocation failed: {exc}") from exc
        if proc.returncode != 0:
            raise RenderCommandError(
                f"renderer exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}"
            )
        rendered = Path(out_prefix + ".png")
        if not rendered.is_file():
            raise RenderCommandError("renderer produced no output file")
        return Rendered(config=config, data=rendered.read_bytes())
