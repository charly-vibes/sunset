# Purpose: Render selected PDF pages with explicit coordinate provenance.
# Responsibilities: Read pinned bytes, validate page/box coordinates, render
#   PNG evidence with dimensions, rotation and pixel-to-page transforms, and
#   label every render with its extractor/renderer lineage and evidence class.
# Rationale: sunset-rmx.2 uses existing PyMuPDF with no OCR prerequisite;
#   improve-geometry-render-binding D5 labels this in-process path
#   `correlated` (PyMuPDF render + PyMuPDF extraction share a lineage).
import pymupdf
from dsc03.visual.render import evidence_class

# Two-path labeling (design D5): this path renders in-process with PyMuPDF —
# the same implementation lineage as the extraction — so its crops are
# correlated evidence by construction and never feed oracle evaluation.
EXTRACTOR_LINEAGE = 'pymupdf'
RENDERER_LINEAGE = 'pymupdf'


def page_frames(source, pages):
    try:
        document = pymupdf.open(stream=source, filetype='pdf')
    except pymupdf.FileDataError as error:
        raise ValueError('source is not a readable PDF') from error
    with document:
        if document.needs_pass or not pages or len(set(pages)) != len(pages):
            raise ValueError('invalid page selection or encrypted source')
        if any(type(p) is not int or p < 1 or p > document.page_count for p in pages):
            raise ValueError('page outside source')
        return {p: {'width': document[p - 1].rect.width,
                    'height': document[p - 1].rect.height,
                    'rotation': document[p - 1].rotation} for p in pages}


def render_page(source, page_number, dpi):
    with pymupdf.open(stream=source, filetype='pdf') as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        return pixmap.tobytes('png'), {
            'width_px': pixmap.width, 'height_px': pixmap.height,
            'width_pt': page.rect.width, 'height_pt': page.rect.height,
            'rotation': page.rotation, 'dpi': dpi,
            'frame': f'page-{page_number}-pt',
            'pixel_to_page': [72 / dpi, 0, 0, 72 / dpi, 0, 0],
            'renderer': f'PyMuPDF@{pymupdf.VersionBind}',
            'extractor_lineage': EXTRACTOR_LINEAGE,
            'renderer_lineage': RENDERER_LINEAGE,
            'evidence_class': evidence_class(EXTRACTOR_LINEAGE,
                                             RENDERER_LINEAGE),
        }
