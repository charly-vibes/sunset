# Purpose: OCR-vs-truth region evaluation over recorded descriptors
#   (sunset-9op).
# Responsibilities: Match OCR descriptor regions against native-truth
#   descriptor regions per page (greedy best-IoU above a declared threshold),
#   score matched pairs on normalized text equality and similarity ratio, and
#   emit a JSON measurement sheet (TP/FP/FN, mean IoU, text scores) — the
#   numeric side of the ground-truth OCR loop; the review SPA is the human
#   side.
# Rationale: Regions come from recorded-run descriptors (canonical y-up
#   geometry declared per ``space: page-N-pt``; region text resolved through
#   has-content relations). Matching is geometry-first so every number traces
#   to declared boxes; nothing here claims accuracy beyond the measured
#   sheet. Discrepancies exit nonzero so recipes and gates can branch.
"""Match OCR descriptor regions against native truth; emit a measurement sheet."""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

_PAGE_RE = re.compile(r'^page-(\d+)-pt$')


def _normalize(text):
    return ' '.join(text.lower().split())


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _regions_by_page(descriptor):
    """{page_number: [{'id','x','y','w','h','text'}]} from declared geometry."""
    texts = {c['id']: c.get('value', '') for c in descriptor.get('contents', [])}
    text_of = {}
    for rel in descriptor.get('relations', []):
        if rel.get('kind') == 'has-content':
            text_of.setdefault(rel['from'], []).append(rel['to'])
    pages = {}
    for region in descriptor.get('regions', []):
        geometry = region.get('geometry')
        if not geometry:
            continue
        match = _PAGE_RE.match(geometry.get('space', ''))
        if match is None:
            continue
        page = int(match.group(1))
        cids = text_of.get(region['id'], [])
        pages.setdefault(page, []).append({
            'id': region['id'],
            'x': geometry['x'], 'y': geometry['y'],
            'w': geometry['width'], 'h': geometry['height'],
            'text': ' '.join(texts.get(cid, '') for cid in cids).strip(),
        })
    return pages


def _iou(a, b):
    ix = max(0, min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x']))
    iy = max(0, min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y']))
    inter = ix * iy
    union = a['w'] * a['h'] + b['w'] * b['h'] - inter
    return inter / union if union else 0.0


def evaluate(truth_descriptor, ocr_descriptor, iou_threshold=0.5):
    """Greedy best-IoU matching per page; returns the measurement sheet dict."""
    truth_pages = _regions_by_page(truth_descriptor)
    ocr_pages = _regions_by_page(ocr_descriptor)
    sheet = {'status': 'measured', 'iou_threshold': iou_threshold, 'pages': {}}
    totals = {'true_regions': 0, 'ocr_regions': 0, 'matched': 0,
              'false_positives': 0, 'false_negatives': 0,
              'exact_text_matches': 0, 'mean_iou': None, 'mean_text_ratio': None}
    ious, ratios = [], []
    for page in sorted(set(truth_pages) | set(ocr_pages)):
        truths, ocrs = truth_pages.get(page, []), ocr_pages.get(page, [])
        pairs = []
        for ti, t in enumerate(truths):
            for oi, o in enumerate(ocrs):
                overlap = _iou(t, o)
                if overlap >= iou_threshold:
                    pairs.append((overlap, ti, oi))
        matched_t, matched_o, matches = set(), set(), []
        for overlap, ti, oi in sorted(pairs, reverse=True):
            if ti in matched_t or oi in matched_o:
                continue
            matched_t.add(ti)
            matched_o.add(oi)
            matches.append((truths[ti], ocrs[oi], overlap))
        t = truths[ti] if matches else None
        exact = sum(1 for t_, o_, _ in matches
                    if _normalize(t_['text']) == _normalize(o_['text']))
        page_ious = [overlap for _, _, overlap in matches]
        page_ratios = [difflib.SequenceMatcher(
            None, _normalize(t_['text']), _normalize(o_['text'])).ratio()
            for t_, o_, _ in matches]
        ious.extend(page_ious)
        ratios.extend(page_ratios)
        sheet['pages'][str(page)] = {
            'true_regions': len(truths),
            'ocr_regions': len(ocrs),
            'matched': len(matches),
            'false_positives': len(ocrs) - len(matches),
            'false_negatives': len(truths) - len(matches),
            'exact_text_matches': exact,
            'mean_iou': round(sum(page_ious) / len(page_ious), 4) if page_ious else None,
            'mean_text_ratio': round(sum(page_ratios) / len(page_ratios), 4) if page_ratios else None,
            'matches': [{'true': t_['id'], 'ocr': o_['id'], 'iou': round(overlap, 4),
                         'exact_text': _normalize(t_['text']) == _normalize(o_['text'])}
                        for t_, o_, overlap in matches],
        }
        totals['true_regions'] += len(truths)
        totals['ocr_regions'] += len(ocrs)
        totals['matched'] += len(matches)
        totals['false_positives'] += len(ocrs) - len(matches)
        totals['false_negatives'] += len(truths) - len(matches)
        totals['exact_text_matches'] += exact
    totals['mean_iou'] = round(sum(ious) / len(ious), 4) if ious else None
    totals['mean_text_ratio'] = round(sum(ratios) / len(ratios), 4) if ratios else None
    sheet['totals'] = totals
    discrepancies = (totals['false_positives'] or totals['false_negatives'])
    sheet['discrepancies'] = bool(discrepancies)
    return sheet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--true', required=True,
                        help='native-truth descriptor (recorded run on the text PDF)')
    parser.add_argument('--ocr', required=True,
                        help='OCR descriptor (recorded run on the image-only PDF)')
    parser.add_argument('--output', required=True)
    parser.add_argument('--iou', type=float, default=0.5)
    args = parser.parse_args(argv)
    sheet = evaluate(_load(args.true), _load(args.ocr), iou_threshold=args.iou)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sheet, ensure_ascii=False, sort_keys=True),
                      encoding='utf-8')
    totals = sheet['totals']
    print(json.dumps(sheet, ensure_ascii=False, sort_keys=True))
    return 2 if sheet['discrepancies'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
