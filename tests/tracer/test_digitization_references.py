# Purpose: Known-answer tests converting SPA review verdicts into reference
#   regions scopes (sunset-rmx.23, first slice of the staged DEFER re-entry).
# Responsibilities: Pin schema-v1 validation for review-verdicts.json and the
#   reference-regions-scope record; pin the agree/differ/missed-ink/unknown
#   mapping, source digests and page render frames, missing-scope honesty
#   (never a fabricated empty truth), and the golden fixture's compatibility
#   with the shared evaluate parser (match_regions).
# Rationale: The repo had no non-empty reference example (six-page-reference.json
#   is {}); the normative regions shape is the evaluate parser in
#   digitization/evaluation.py, so the golden fixture doubles as the repo's
#   first consumable reference example and every unknown stays recorded.
import hashlib
import json
import re
from pathlib import Path

import pytest

from digitization.evaluation import match_regions
from digitization.pipeline import json_bytes
from digitization.references import (
    VERDICTS,
    validate_reference,
    validate_verdicts,
    verdicts_to_reference,
)

ROOT = Path(__file__).resolve().parents[2]
SPA_TEMPLATE, GOLDEN, SIX_PAGE_BASELINE = (
    ROOT / 'hitl' / 'visual-review' / 'templates' / 'visual-review-spa.html',
    ROOT / 'fixtures' / 'digitization' / 'reference-regions-golden.json',
    ROOT / 'fixtures' / 'digitization' / 'six-page-runs' / 'baseline')
CARRIER = 'digitization-test'
RULES = 'no winner election, no smoothing; unknown is an answer'
DESCRIPTOR = {'id': CARRIER, 'version': '1', 'source': {'locator': 'source.pdf'}}
MISMATCH_RECORD = {'reviewer': 'test-reviewer', 'rules': RULES,
                   'carriers': [{'carrier': 'some-other-descriptor', 'pages': []}]}
GOLDEN_CONTENT = json.loads(GOLDEN.read_bytes())
RUN_REGIONS = [{'region_id': 'p1', 'page': 1, 'frame': 'page-1-pt'}]
RUN_REGIONS_FULL = [
    {'region_id': 'p1', 'page': 1, 'frame': 'page-1-pt'},
    {'region_id': 'p2', 'page': 2, 'frame': 'page-2-pt'},
    {'region_id': 'p3', 'page': 3, 'frame': 'page-3-pt'}]
WITNESS_R1 = {'id': 'r1', 'page': 1, 'bbox': [10, 10, 100, 50], 'origin': 'witness'}
COUNTEREXAMPLE_R1 = {'id': 'r1', 'page': 1, 'bbox': [190, 15, 95, 70],
                     'origin': 'counterexample', 'claim_bbox': [200, 20, 80, 60]}
DIFFERED_R1 = [{'id': 'r1', 'claim_bbox': [200, 20, 80, 60], 'correction_bbox': None}]
MISSING_OUT = [{'id': 'missed-ink-1-1', 'page': 1, 'bbox': [600, 60, 30, 30],
                'origin': 'missed-ink'},
               {'id': 'missed-ink-1-2', 'page': 1, 'bbox': [640, 60, 20, 20],
                'origin': 'missed-ink'}]
UNKNOWN_REVIEWED = [{'id': 'r1', 'reason': 'reviewer-unknown'}]
UNKNOWN_UNREVIEWED = [{'id': 'r1', 'reason': 'unreviewed'}]
UNKNOWN_UNMAPPED = [{'id': 'r1', 'reason': 'unmapped-rect'}]
UNKNOWN_GATED_NULL = [{'id': 'r1', 'reason': 'page-number-not-derivable'}]
UNKNOWN_GATED_UNAVAILABLE = [{'id': 'r1', 'reason': 'page-unavailable'}]
MISSING_PAGE_ONE = {'page': 1, 'status': 'missing', 'regions': None, 'witnesses': [],
                    'differed': [], 'missed_ink': [], 'unknown': []}
PARTIAL_PAGE_ONE = {'page': 1, 'status': 'partial', 'regions': None, 'witnesses': [],
                    'differed': [], 'missed_ink': [], 'unknown': []}
AGREE_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [10, 10, 100, 50], 'verdict': 'agree', 'note': ''}],
    'missed_ink': []}]
DIFFER_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [200, 20, 80, 60], 'verdict': 'differ', 'note': '',
     'correction_px': [190, 15, 95, 70]}], 'missed_ink': []}]
DIFFER_NC_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [200, 20, 80, 60], 'verdict': 'differ', 'note': ''}],
    'missed_ink': []}]
MISSED_PAGES = [{'page': 1, 'unavailable': None, 'regions': [],
                 'missed_ink': [{'rect_px': [600, 60, 30, 30]},
                                {'rect_px': [640, 60, 20, 20]}]}]
UNKNOWN_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [1, 2, 3, 4], 'verdict': 'unknown', 'note': ''}], 'missed_ink': []}]
UNREVIEWED_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [1, 2, 3, 4], 'verdict': None, 'note': ''}], 'missed_ink': []}]
UNMAPPED_PAGES = [{'page': 1, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': None, 'verdict': 'agree', 'note': ''}], 'missed_ink': []}]
GATED_NULL_PAGES = [{'page': None, 'unavailable': None, 'regions': [
    {'id': 'r1', 'rect_px': [1, 2, 3, 4], 'verdict': 'agree', 'note': ''}], 'missed_ink': []}]
GATED_UNAVAILABLE_PAGES = [{'page': 1, 'unavailable': 'frame unknown: invalid_geometry_frame',
                            'regions': [{'id': 'r1', 'rect_px': [1, 2, 3, 4],
                                         'verdict': 'agree', 'note': ''}], 'missed_ink': []}]
FULL_PAGES = [
    {'page': 1, 'unavailable': None, 'regions': [
        {'id': 'r-agree', 'rect_px': [10, 10, 100, 50], 'verdict': 'agree', 'note': 'box matches'},
        {'id': 'r-differ', 'rect_px': [200, 20, 80, 60], 'verdict': 'differ', 'note': 'clips stanza',
         'correction_px': [190, 15, 95, 70]},
        {'id': 'r-differ-nc', 'rect_px': [300, 30, 60, 40], 'verdict': 'differ', 'note': 'drift'},
        {'id': 'r-unknown', 'rect_px': [400, 40, 70, 30], 'verdict': 'unknown', 'note': 'faint'},
        {'id': 'r-unreviewed', 'rect_px': [500, 50, 40, 20], 'verdict': None, 'note': ''},
        {'id': 'r-unmapped', 'rect_px': None, 'verdict': 'agree', 'note': 'frame unknown'}],
     'missed_ink': [{'rect_px': [600, 60, 30, 30]}, {'rect_px': [640, 60, 20, 20]}]},
    {'page': 2, 'unavailable': None, 'regions': [
        {'id': 'q-unknown', 'rect_px': [5, 5, 50, 40], 'verdict': 'unknown', 'note': 'illegible'}],
     'missed_ink': []},
    {'page': None, 'unavailable': 'page number not derivable from region id z-page',
     'regions': [{'id': 'z-page', 'rect_px': None, 'verdict': None, 'note': ''}], 'missed_ink': []},
]
AGREE_OUT = [{**PARTIAL_PAGE_ONE, 'regions': [WITNESS_R1], 'witnesses': ['r1']}]
DIFFER_OUT = [{**PARTIAL_PAGE_ONE, 'regions': [COUNTEREXAMPLE_R1]}]
DIFFER_NC_OUT = [{**MISSING_PAGE_ONE, 'differed': DIFFERED_R1}]
MISSED_OUT_PAGE = [{**PARTIAL_PAGE_ONE, 'regions': MISSING_OUT, 'missed_ink': MISSING_OUT}]
UNKNOWN_OUT = [{**MISSING_PAGE_ONE, 'unknown': UNKNOWN_REVIEWED}]
UNREVIEWED_OUT = [dict(MISSING_PAGE_ONE, unknown=UNKNOWN_UNREVIEWED)]
UNMAPPED_OUT = [{**MISSING_PAGE_ONE, 'unknown': UNKNOWN_UNMAPPED}]
GATED_NULL_OUT = [
    {**MISSING_PAGE_ONE, 'page': None, 'unknown': UNKNOWN_GATED_NULL},
    MISSING_PAGE_ONE]
UNAVAILABLE_OUT = [{**MISSING_PAGE_ONE, 'unknown': UNKNOWN_GATED_UNAVAILABLE}]
UNCOVERED_OUT = [MISSING_PAGE_ONE]
_CASE_SPECS = [
    ('agree-becomes-witness',
     AGREE_PAGES, RUN_REGIONS, AGREE_OUT, []),
    ('differ-with-correction',
     DIFFER_PAGES, RUN_REGIONS, DIFFER_OUT, []),
    ('differ-without-correction',
     DIFFER_NC_PAGES, RUN_REGIONS, DIFFER_NC_OUT, [1]),
    ('missed-ink-human-only',
     MISSED_PAGES, RUN_REGIONS, MISSED_OUT_PAGE, []),
    ('unknown-recorded-not-truth',
     UNKNOWN_PAGES, RUN_REGIONS, UNKNOWN_OUT, [1]),
    ('unreviewed-recorded-not-truth',
     UNREVIEWED_PAGES, RUN_REGIONS, UNREVIEWED_OUT, [1]),
    ('unmapped-rect-recorded',
     UNMAPPED_PAGES, RUN_REGIONS, UNMAPPED_OUT, [1]),
    ('page-number-gates-truth',
     GATED_NULL_PAGES, RUN_REGIONS, GATED_NULL_OUT, [None, 1]),
    ('unavailable-page-gates-truth',
     GATED_UNAVAILABLE_PAGES, RUN_REGIONS, UNAVAILABLE_OUT, [1]),
    ('unreviewed-run-page-stays-missing',
     [], RUN_REGIONS, UNCOVERED_OUT, [1]),
    ('full-golden',
     FULL_PAGES, RUN_REGIONS_FULL, None, None),
]
VERDICT_REJECT_CASES = [
    ({'reviewer': None, 'rules': '', 'carriers': [{'carrier': CARRIER, 'pages': [
        {'page': 1, 'unavailable': None, 'regions': [
            {'id': 'r', 'rect_px': [1, 2, 3, 4], 'verdict': 'winner', 'note': ''}],
         'missed_ink': []}]}]}, 'vocabulary'),
    ({'reviewer': None, 'rules': '', 'carriers': [{'carrier': CARRIER, 'pages': [
        {'page': 1, 'unavailable': None, 'regions': [
            {'id': 'r', 'rect_px': [1, 2, 3], 'verdict': 'agree', 'note': ''}],
         'missed_ink': []}]}]}, 'rect'),
    ({'reviewer': None, 'rules': '', 'carriers': None}, 'carriers'),
    ({'reviewer': None, 'rules': '', 'carriers': [{'carrier': CARRIER, 'pages': [
        {'page': '1', 'unavailable': None, 'regions': [
            {'id': 'r', 'rect_px': [1, 2, 3, 4], 'verdict': 'agree', 'note': ''}],
         'missed_ink': []}]}]}, 'page-number'),
]
REFERENCE_REJECT_CASES = [
    ({'version': '1', 'kind': 'reference-regions-scope', 'regions': [],
      'pages': [{'page': 3, 'status': 'missing', 'regions': []}]}, 'fabricate'),
    ({'version': '1', 'kind': 'reference-regions-scope',
      'regions': [{'id': 'x', 'page': 1, 'bbox': [0, 0, 1, 1], 'origin': 'election'}],
      'pages': []}, 'origin'),
    ({'version': '2', 'kind': 'reference-regions-scope', 'regions': [], 'pages': []}, 'version'),
]


def _write_bytes(path, value):
    path.write_bytes(json_bytes(value))
    return path


def _write_run(tmp_path, regions):
    _write_bytes(tmp_path / 'descriptor.json', DESCRIPTOR)
    _write_bytes(tmp_path / 'regions.json', regions)
    return tmp_path


def _write_verdicts(tmp_path, record):
    return _write_bytes(tmp_path / 'review-verdicts.json', record)


def _verdicts(tmp_path, pages):
    record = {'reviewer': 'test-reviewer', 'rules': RULES,
              'carriers': [{'carrier': CARRIER, 'pages': pages}]}
    return _write_verdicts(tmp_path, record)


def _expected(pages_and_regions, pages_out_and_missing):
    pages, regions = pages_and_regions
    pages_out, missing = pages_out_and_missing
    record = {'reviewer': 'test-reviewer', 'rules': RULES,
              'carriers': [{'carrier': CARRIER, 'pages': pages}]}
    return {'version': '1', 'kind': 'reference-regions-scope',
            'source': {'carrier': CARRIER, 'reviewer': 'test-reviewer', 'rules': RULES,
                       'descriptor_sha256': hashlib.sha256(
                           json_bytes(DESCRIPTOR)).hexdigest(),
                       'verdicts_sha256': hashlib.sha256(json_bytes(record)).hexdigest(),
                       'frames': {str(region['page']): [region['frame']] for region in regions}},
            'regions': [r for p in pages_out for r in (p['regions'] or [])],
            'pages': pages_out, 'missing_pages': missing}


CONVERSION_CASES = [
    pytest.param(((pages, regions), GOLDEN_CONTENT if pages_out is None else
                  _expected((pages, regions), (pages_out, missing))), id=id_name)
    for id_name, pages, regions, pages_out, missing in _CASE_SPECS]


def test_verdict_vocabulary_matches_spa():
    template = SPA_TEMPLATE.read_text(encoding='utf-8')
    declared = re.search(r'const VERDICTS = \[(.*?)\];', template, re.S).group(1)
    assert tuple(VERDICTS) == tuple(re.findall(r'"(\w+)"', declared))


def test_validate_verdicts_accepts_spa_shape():
    assert validate_verdicts({'reviewer': None, 'rules': '', 'carriers': [
        {'carrier': CARRIER, 'pages': [{'page': 1, 'unavailable': None, 'regions': [
            {'id': 'r', 'rect_px': [1, 2, 3, 4], 'verdict': 'agree', 'note': ''}],
             'missed_ink': []}]}]}) is None


@pytest.mark.parametrize('record, fragment', VERDICT_REJECT_CASES)
def test_validate_verdicts_rejects(record, fragment):
    with pytest.raises(ValueError, match=fragment):
        validate_verdicts(record)


def test_validate_reference_accepts_golden():
    assert validate_reference(GOLDEN_CONTENT) is None


@pytest.mark.parametrize('record, fragment', REFERENCE_REJECT_CASES)
def test_validate_reference_rejects(record, fragment):
    with pytest.raises(ValueError) as raised:
        validate_reference(record)
    assert fragment in str(raised.value)


@pytest.mark.parametrize('case', CONVERSION_CASES)
def test_known_answer_mapping(tmp_path, case):
    (pages, regions), expected = case
    _write_run(tmp_path, regions)
    assert verdicts_to_reference(_verdicts(tmp_path, pages), tmp_path) == expected


def test_carrier_mismatch_is_typed(tmp_path):
    path = _write_verdicts(tmp_path, MISMATCH_RECORD)
    _write_run(tmp_path, RUN_REGIONS)
    with pytest.raises(ValueError, match='carrier-descriptor-mismatch'):
        verdicts_to_reference(path, tmp_path)


def test_golden_regions_feed_match_regions():
    validate_reference(GOLDEN_CONTENT)
    candidates = [{'region_id': region['id'], 'page': region['page'], 'bbox': region['bbox']}
                  for region in GOLDEN_CONTENT['regions']]
    candidates.append({'region_id': 'spurious', 'page': 1, 'bbox': [900, 900, 10, 10]})
    candidates.append({'region_id': 'page-gated', 'page': 2, 'bbox': [10, 10, 100, 50]})
    report = match_regions(GOLDEN_CONTENT['regions'], candidates, 0.5)
    assert (report['reference_count'], report['precision']) == (4, 4 / 6)
    assert (len(report['matches']), report['recall']) == (4, 1.0)


def test_real_run_digests_and_frames(tmp_path):
    descriptor = json.loads((SIX_PAGE_BASELINE / 'descriptor.json').read_bytes())
    record = {'reviewer': None, 'rules': '',
              'carriers': [{'carrier': descriptor['id'], 'pages': []}]}
    path = _write_verdicts(tmp_path, record)
    reference = verdicts_to_reference(path, SIX_PAGE_BASELINE)
    manifest = json.loads((SIX_PAGE_BASELINE / 'manifest.json').read_bytes())
    assert reference['source']['descriptor_sha256'] == manifest['descriptor']['sha256']
    assert (set(reference['source']['frames']), reference['missing_pages']) == (
        {'1', '2', '3', '4', '5', '6'}, [1, 2, 3, 4, 5, 6])
    assert all(page['status'] == 'missing' for page in reference['pages'])
