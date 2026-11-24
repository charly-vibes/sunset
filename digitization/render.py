# Purpose: Render selected PDF pages with explicit coordinate provenance.
# Responsibilities: Read pinned bytes, validate page/box coordinates, render
#   PNG evidence with dimensions, rotation and pixel-to-page transforms, and
#   label every render with its extractor/renderer lineage and evidence class.
# Rationale: sunset-rmx.2 uses existing PyMuPDF with no OCR prerequisite;
#   improve-geometry-render-binding D5 labels this in-process path
#   `correlated` (PyMuPDF render + PyMuPDF extraction share a lineage).
import hashlib
import json

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


def render_crop(source, page_number, dpi, box):
    """Render a page and derive the pixel-space crop record for ``box``
    (a page-pt frame box). sunset-3oq 2.3: the same lineage labels as the
    page render — a review crop is correlated evidence (PyMuPDF render +
    PyMuPDF extraction) and never feeds oracle evaluation."""
    png, meta = render_page(source, page_number, dpi)
    scale = dpi / 72.0
    record = dict(meta)
    record['box_pt'] = {k: box[k] for k in ('page', 'x', 'y', 'w', 'h') if k in box}
    record['page_frame'] = meta['frame']
    record['pixel_box'] = [round(box['x'] * scale), round(box['y'] * scale),
                           round(box['w'] * scale), round(box['h'] * scale)]
    return png, record


def crop_reference(profile_digest, render_record, box):
    """The pinned crop reference of a queue item: render profile digest,
    page frame, box, and a digest binding all three."""
    reference = {
        'render_profile_digest': profile_digest,
        'page_frame': render_record['page_frame'],
        'box': {k: box[k] for k in ('page', 'x', 'y', 'w', 'h') if k in box},
    }
    reference['digest'] = 'crop:' + hashlib.sha256(
        json.dumps(reference, sort_keys=True).encode('utf-8')).hexdigest()[:32]
    return reference


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
