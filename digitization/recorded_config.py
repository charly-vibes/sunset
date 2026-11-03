# Purpose: Generate recorded digitization configs from a PDF's native text
#   layer (sunset-bv4).
# Responsibilities: Derive per-page detections (text-block bboxes in y-down
#   page points, the native reader's own report) and recorded recognitions
#   (the extracted text) under a pinned pymupdf recorded-provider identity,
#   so `digitization run` can produce geometry-bearing descriptors for real
#   documents without hand-authored configs or live OCR.
# Rationale: The recorded pipeline already validates inputs, renders pinned
#   pages, attributes observations and exports validator-passing descriptors;
#   the only missing piece was the config. Text-only by construction: page
#   pixels, images and vectors stay with the native extractor path and the
#   visual oracles — nothing here fabricates claims the source does not
#   carry. Config bboxes stay y-down; the pipeline converts to the canonical
#   descriptor space at emission.
"""Recorded digitization configs derived mechanically from native text."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import pymupdf

PROVIDER_ID = 'pymupdf-native-text'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def build_config(source_path, pages=None):
    """Build a recorded-run config from the source's native text layer.

    ``pages`` is an optional list of 1-based page numbers (default: every
    page). Blocks are pymupdf text blocks; bboxes are nonnegative integer
    page points, top-left origin, y-down — the pipeline's preflight contract.
    """
    data = Path(source_path).read_bytes()
    try:
        document = pymupdf.open(stream=data, filetype='pdf')
    except pymupdf.FileDataError as error:
        raise ValueError('source is not a readable PDF') from error
    with document:
        if document.needs_pass:
            raise ValueError('encrypted source')
        if pages is None:
            pages = list(range(1, document.page_count + 1))
        if (not pages or len(set(pages)) != len(pages)
                or any(type(p) is not int or p < 1 or p > document.page_count
                       for p in pages)):
            raise ValueError('invalid page selection')
        pages_config = {}
        for number in pages:
            page = document[number - 1]
            width, height = int(page.rect.width), int(page.rect.height)
            detections, recognitions = [], {}
            for x0, y0, x1, y1, text, *_rest in page.get_text('blocks'):
                if not text.strip():
                    continue
                bx0, by0 = max(0, math.floor(x0)), max(0, math.floor(y0))
                bx1 = min(width, math.ceil(x1))
                by1 = min(height, math.ceil(y1))
                box = [bx0, by0, bx1 - bx0, by1 - by0]
                if box[2] <= 0 or box[3] <= 0:
                    continue
                did = f'block-{len(detections)}'
                detections.append({'id': did, 'kind': 'text-block', 'bbox': box})
                recognitions[did] = {'raw_text': text.strip(), 'unresolved': []}
            pages_config[str(number)] = {'detections': detections,
                                         'recognitions': recognitions}
    return {
        'version': '1',
        'source_sha256': _sha(data),
        'provider': {'kind': 'recorded', 'id': PROVIDER_ID,
                     'version': pymupdf.__version__},
        'render': {'dpi': 72},
        'pages': pages_config,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--pages', default=None,
                        help='comma-separated 1-based page numbers (default: all)')
    args = parser.parse_args(argv)
    try:
        pages = None if args.pages is None else [int(p) for p in args.pages.split(',')]
        config = build_config(args.source, pages)
    except ValueError as error:
        print(json.dumps({'status': 'invalid-input', 'reason': 'invalid-input',
                          'detail': str(error), 'provider_calls': 0},
                         ensure_ascii=False, sort_keys=True))
        return 3
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True),
                      encoding='utf-8')
    blocks = sum(len(p['detections']) for p in config['pages'].values())
    print(json.dumps({'status': 'recorded-config', 'provider': PROVIDER_ID,
                      'pages': [int(p) for p in sorted(config['pages'], key=int)],
                      'blocks': blocks, 'provider_calls': 0},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
