# Purpose: Recorded OCR configs for image-only PDFs (sunset-9op).
# Responsibilities: Run pinned tesseract (spa) in TSV mode over the page PNGs
#   produced by digitization.rasterize, aggregate word rows into line boxes,
#   convert pixel boxes to y-down page points via the declared dpi, and emit
#   a recorded config for the image-only PDF — so the tested recorded
#   pipeline renders, attributes and exports geometry-bearing OCR descriptors.
# Rationale: The region-recognition half of the ground-truth loop: OCR claims
#   over image PDFs can then be compared against native truth (ocr_eval) and
#   reviewed in the visual-review SPA over the rasterized render. Reuses
#   dsc03.demo.run_pinned (ALIGN-001: reuse the demo's pinned tesseract path).
#   Provider identity is pinned as tesseract-ocr with the reported version.
"""Pinned tesseract -> recorded config for image-only PDFs."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from dsc03.demo import run_pinned

PROVIDER_ID = 'tesseract-ocr'
DEFAULT_LANG = 'spa'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _tesseract_version():
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    first = (result.stdout or result.stderr).splitlines()[0]
    return first.split()[-1]


def _line_rows(tsv_text):
    """Aggregate TSV word rows (level 5) into line boxes with joined text.

    Yields (left, top, right, bottom, text, mean_conf) in pixel space,
    y-down, grouped by (page, block, par, line).
    """
    rows = {}
    lines = tsv_text.splitlines()
    header = lines[0].split('\t')
    idx = {name: i for i, name in enumerate(header)}
    for line in lines[1:]:
        cols = line.split('\t')
        if len(cols) != len(header):
            continue
        if cols[idx['level']] != '5':
            continue
        text = cols[idx['text']].strip()
        if not text:
            continue
        key = (cols[idx['page_num']], cols[idx['block_num']],
               cols[idx['par_num']], cols[idx['line_num']])
        left = int(cols[idx['left']])
        top = int(cols[idx['top']])
        width = int(cols[idx['width']])
        height = int(cols[idx['height']])
        conf = float(cols[idx['conf']])
        box, texts, confs = rows.get(key, ([None, None, None, None], [], []))
        if box[0] is None:
            box = [left, top, left + width, top + height]
        else:
            box = [min(box[0], left), min(box[1], top),
                   max(box[2], left + width), max(box[3], top + height)]
        texts.append(text)
        confs.append(conf)
        rows[key] = (box, texts, confs)
    return [(box, ' '.join(texts), sum(confs) / len(confs))
            for box, texts, confs in rows.values()]


def build_config(image_pdf_path, pages_dir, dpi=200, lang=DEFAULT_LANG, pages=None):
    """Build a recorded-run config from pinned OCR over the page PNGs.

    ``pages_dir`` holds the rasterize output (page-N.png per page). Boxes are
    converted from PNG pixels to y-down page points via ``dpi`` — the same
    declared scale the recorded pipeline's frames use.
    """
    import pymupdf

    image_pdf_path = Path(image_pdf_path)
    pages_dir = Path(pages_dir)
    data = image_pdf_path.read_bytes()
    try:
        document = pymupdf.open(stream=data, filetype='pdf')
    except pymupdf.FileDataError as error:
        raise ValueError('image PDF is not readable') from error
    with document:
        if document.needs_pass:
            raise ValueError('encrypted source')
        selected = pages or list(range(1, document.page_count + 1))
        if (not selected or len(set(selected)) != len(selected)
                or any(type(p) is not int or p < 1 or p > document.page_count
                       for p in selected)):
            raise ValueError('invalid page selection')
        points_per_px = 72.0 / dpi
        pages_config = {}
        for number in selected:
            png = pages_dir / f'page-{number}.png'
            if not png.is_file():
                raise ValueError(f'missing rasterized page PNG: {png.name}')
            # this tesseract install ships no 'tsv' config file; request TSV
            # via tessedit_create_tsv with a file output base, then read it
            with tempfile.TemporaryDirectory(prefix='sunset-ocr-') as tmp:
                base = str(Path(tmp) / 'ocr')
                run_pinned(['tesseract', str(png), base, '-l', lang,
                            '-c', 'tessedit_create_tsv=1'])
                tsv_path = Path(base + '.tsv')
                if not tsv_path.is_file():
                    raise ValueError(f'tesseract produced no TSV for page {number}')
                tsv_text = tsv_path.read_text(encoding='utf-8', errors='replace')
            width, height = int(document[number - 1].rect.width), int(document[number - 1].rect.height)
            detections, recognitions = [], {}
            for box, text, _conf in _line_rows(tsv_text):
                x = max(0, int(box[0] * points_per_px))
                y = max(0, int(box[1] * points_per_px))
                w = min(width - x, int(round((box[2] - box[0]) * points_per_px)))
                h = min(height - y, int(round((box[3] - box[1]) * points_per_px)))
                if w <= 0 or h <= 0:
                    continue
                did = f'ocr-{len(detections)}'
                detections.append({'id': did, 'kind': 'text-line',
                                   'bbox': [x, y, w, h]})
                recognitions[did] = {'raw_text': text, 'unresolved': []}
            pages_config[str(number)] = {'detections': detections,
                                         'recognitions': recognitions}
    return {
        'version': '1',
        'source_sha256': _sha(data),
        'provider': {'kind': 'recorded', 'id': PROVIDER_ID,
                     'version': _tesseract_version()},
        'render': {'dpi': dpi},
        'pages': pages_config,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--image-pdf', required=True,
                        help='image-only PDF the config targets (rasterize output)')
    parser.add_argument('--pages-dir', required=True,
                        help='rasterize output dir holding page-N.png renders')
    parser.add_argument('--dpi', type=int, default=200,
                        help='dpi the PNGs were rasterized at (px -> pt scale)')
    parser.add_argument('--lang', default=DEFAULT_LANG)
    parser.add_argument('--pages', default=None,
                        help='comma-separated 1-based page numbers (default: all)')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        pages = None if args.pages is None else [int(p) for p in args.pages.split(',')]
        config = build_config(args.image_pdf, args.pages_dir, dpi=args.dpi,
                              lang=args.lang, pages=pages)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'invalid-input', 'reason': 'invalid-input',
                          'detail': str(error)}, ensure_ascii=False, sort_keys=True))
        return 3
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True),
                      encoding='utf-8')
    blocks = sum(len(p['detections']) for p in config['pages'].values())
    print(json.dumps({'status': 'ocr-config', 'provider': PROVIDER_ID,
                      'pages': [int(p) for p in sorted(config['pages'], key=int)],
                      'blocks': blocks, 'provider_calls': 0},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
