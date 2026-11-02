# Purpose: dsc03.visual — raster visual-oracle package (sunset-xzy.1).
# Responsibilities: Re-export the public render surface: the pinned
#   RenderConfig record, Binarization settings, typed outcomes
#   (Rendered / RenderUnavailable), the pdftoppm runner, version detection,
#   and evidence-class labeling/predicate.
# Rationale: document-visual-oracles capability; keeps oracle-render imports
#   stable for later slices (frame mapping 3.2, oracle properties 4.x).
"""Raster visual oracles: pinned rendering infrastructure."""
from dsc03.visual.render import (
    Binarization,
    RenderConfig,
    RenderCommandError,
    RenderUnavailable,
    Rendered,
    detect_renderer_version,
    evidence_class,
    render_page,
    supports_accuracy_claim,
)

__all__ = [
    "Binarization",
    "RenderConfig",
    "RenderCommandError",
    "RenderUnavailable",
    "Rendered",
    "detect_renderer_version",
    "evidence_class",
    "render_page",
    "supports_accuracy_claim",
]
