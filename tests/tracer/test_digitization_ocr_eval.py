"""Contract tests for OCR-vs-truth region evaluation (sunset-9op).

Matching math and measurement sheet: OCR descriptor regions against native
truth descriptor regions, per page, by IoU, with text similarity on matches.
Descriptors are the recorded-run outputs (canonical y-up geometry via
``space: page-N-pt``, region->text through has-content relations).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def make_descriptor(page_regions):
    """page_regions: {page: [(region_id, x, y, w, h, text), ...]} (canonical y-up)."""
    descriptor = {
        'version': '0.3', 'id': 'eval-fixture',
        'source': {'format': 'application/pdf', 'sha256': '0' * 64, 'locator': 'source.pdf'},
        'views': [{'id': 'physical', 'kind': 'physical', 'root': 'document'},
                  {'id': 'logical', 'kind': 'logical', 'root': 'logical-root'}],
        'regions': [{'id': 'document', 'view_id': 'physical', 'kind': 'document'},
                    {'id': 'logical-root', 'view_id': 'logical', 'kind': 'document'}],
        'contents': [], 'relations': [], 'annotations': [], 'evidence': [],
        'selectors': [], 'interpretations': [], 'coverage': [], 'vocabularies': [],
        'profiles': [],
    }
    for page, regions in page_regions.items():
        page_id = f'page-{page}'
        descriptor['regions'].append({'id': page_id, 'view_id': 'physical', 'kind': 'page'})
        descriptor['relations'].append({'id': f'c-{page_id}', 'kind': 'contains',
                                        'from': 'document', 'to': page_id})
        for rid, x, y, w, h, text in regions:
            descriptor['regions'].append({
                'id': rid, 'view_id': 'physical', 'kind': 'text-line',
                'geometry': {'profile_id': 'geometry', 'space': f'page-{page}-pt',
                             'x': x, 'y': y, 'width': w, 'height': h}})
            cid = f'{rid}-text'
            descriptor['contents'].append({'id': cid, 'kind': 'text', 'value': text})
            descriptor['relations'].append({'id': f'hc-{rid}', 'kind': 'has-content',
                                            'from': rid, 'to': cid})
    return descriptor


def cli(*args):
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization.ocr_eval', *map(str, args)],
        cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def test_perfect_ocr_matches_truth_and_scores_full(tmp_path):
    truth = make_descriptor({1: [('t1', 30, 350, 200, 12, 'Resumen Caja'),
                                 ('t2', 30, 330, 200, 12, 'SALDO ANTERIOR')]})
    ocr = make_descriptor({1: [('o1', 31, 350, 199, 11, 'Resumen Caja'),
                               ('o2', 30, 330, 200, 12, 'saldo anterior')]})
    (tmp_path / 't.json').write_text(json.dumps(truth))
    (tmp_path / 'o.json').write_text(json.dumps(ocr))
    code, result = cli('--true', tmp_path / 't.json', '--ocr', tmp_path / 'o.json',
                       '--output', tmp_path / 'sheet.json')
    assert code == 0 and result['status'] == 'measured'
    page = result['pages']['1']
    assert page['true_regions'] == 2 and page['ocr_regions'] == 2
    assert page['matched'] == 2 and page['false_positives'] == 0
    assert page['false_negatives'] == 0
    assert page['exact_text_matches'] == 2  # both match after normalization
    assert page['mean_iou'] > 0.9
    sheet = json.loads((tmp_path / 'sheet.json').read_text())
    assert sheet['totals']['matched'] == 2


def test_shifted_and_missing_ocr_regions_count_fp_fn(tmp_path):
    truth = make_descriptor({1: [('t1', 30, 350, 200, 12, 'alpha'),
                                 ('t2', 30, 200, 200, 12, 'beta')]})
    ocr = make_descriptor({1: [('o1', 30, 350, 200, 12, 'alpha'),
                               ('o2', 250, 30, 40, 10, 'ghost')]})  # t2 missed, o2 spurious
    (tmp_path / 't.json').write_text(json.dumps(truth))
    (tmp_path / 'o.json').write_text(json.dumps(ocr))
    code, result = cli('--true', tmp_path / 't.json', '--ocr', tmp_path / 'o.json',
                       '--output', tmp_path / 'sheet.json', '--iou', '0.5')
    assert code == 2  # measured with discrepancies
    page = result['pages']['1']
    assert page['matched'] == 1
    assert page['false_positives'] == 1 and page['false_negatives'] == 1
    assert result['totals']['mean_iou'] >= 0.99


def test_low_iou_matches_stay_unmatched(tmp_path):
    truth = make_descriptor({1: [('t1', 0, 0, 200, 100, 'big')]})
    ocr = make_descriptor({1: [('o1', 0, 0, 40, 20, 'big')]})  # IoU = 40*20/(200*100) = 0.04
    (tmp_path / 't.json').write_text(json.dumps(truth))
    (tmp_path / 'o.json').write_text(json.dumps(ocr))
    code, result = cli('--true', tmp_path / 't.json', '--ocr', tmp_path / 'o.json',
                       '--output', tmp_path / 'sheet.json', '--iou', '0.5')
    page = result['pages']['1']
    assert page['matched'] == 0
    assert page['false_positives'] == 1 and page['false_negatives'] == 1
