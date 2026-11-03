# Purpose: Rasterize a text PDF into an image-only derivative (sunset-9op).
# Responsibilities: Render every selected page through the pinned pdftoppm
#   configuration at the requested dpi, keep the page PNGs, and assemble an
#   image-only PDF with identical page geometry — no text layer, images only.
#   This is the controlled "image PDF" side of ground-truth OCR experiments:
#   the native text stays in the original, so OCR claims over the raster can
#   be compared against true regions.
# Rationale: Reuses the pinned render path (dsc03.demo.run_pinned, same
#   poppler renderer the oracles and review bundles use) so every artifact
#   traces to declared tooling. Text-free by construction: pages are rebuilt
#   from pixel images only.
"""Text PDF -> pinned page PNGs + image-only PDF."""
import argparse
import json
import sys
from pathlib import Path

import pymupdf

from dsc03.demo import run_pinned



DEFAULT_DPI = 200


def rasterize(source_path, output_dir, dpi=DEFAULT_DPI, pages=None):
    """Render pages to PNGs and assemble the image-only PDF.

    Returns {'status', 'dpi', 'pages': {str(n): {'path','sha256'}},
    'image_pdf', 'image_pdf_sha256'} with paths relative to output_dir.
    """
    import hashlib

    source_path = Path(source_path)
    output_dir = Path(output_dir)
    data = source_path.read_bytes()
    document = pymupdf.open(stream=data, filetype='pdf')
    with document:
        if document.needs_pass:
            raise ValueError('encrypted source')
        selected = pages or list(range(1, document.page_count + 1))
        if (not selected or len(set(selected)) != len(selected)
                or any(type(p) is not int or p < 1 or p > document.page_count
                       for p in selected)):
            raise ValueError('invalid page selection')
        frames = {p: {'width': document[p - 1].rect.width,
                      'height': document[p - 1].rect.height} for p in selected}
        output_dir.mkdir(parents=True, exist_ok=True)
        pages_out = {}
        png_paths = []
        for number in selected:
            prefix = output_dir / f'page-{number}'
            proc = run_pinned(['pdftoppm', '-r', str(dpi), '-png',
                               '-f', str(number), '-l', str(number),
                               '-singlefile', str(source_path), str(prefix)])
            png = Path(str(prefix) + '.png')
            if not png.is_file():
                raise ValueError(f'renderer produced no output for page {number}')
            png_paths.append(png)
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            pages_out[str(number)] = {'path': png.relative_to(output_dir).as_posix(),
                                      'sha256': digest}
        image_pdf = output_dir / 'image.pdf'
        with pymupdf.open() as target:
            for number, png in zip(selected, png_paths):
                page = target.new_page(width=frames[number]['width'],
                                       height=frames[number]['height'])
                page.insert_image(page.rect, filename=str(png))
            target.save(str(image_pdf))
    image_bytes = image_pdf.read_bytes()
    return {
        'status': 'rasterized',
        'dpi': dpi,
        'pages': pages_out,
        'image_pdf': image_pdf.relative_to(output_dir).as_posix(),
        'image_pdf_sha256': hashlib.sha256(image_bytes).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--dpi', type=int, default=DEFAULT_DPI)
    parser.add_argument('--pages', default=None,
                        help='comma-separated 1-based page numbers (default: all)')
    args = parser.parse_args(argv)
    try:
        pages = None if args.pages is None else [int(p) for p in args.pages.split(',')]
        result = rasterize(args.source, args.output_dir, dpi=args.dpi, pages=pages)
    except (ValueError, OSError, pymupdf.FileDataError) as error:
        print(json.dumps({'status': 'invalid-input', 'reason': 'invalid-input',
                          'detail': str(error)}, ensure_ascii=False, sort_keys=True))
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
