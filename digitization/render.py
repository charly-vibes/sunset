# Purpose: Render selected PDF pages with explicit coordinate provenance.
# Responsibilities: Read pinned bytes, validate page/box coordinates and render
#   PNG evidence with dimensions, rotation and pixel-to-page transforms.
# Rationale: sunset-rmx.2 uses existing PyMuPDF with no OCR prerequisite.
import pymupdf


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
        }
