# Purpose: Diagnose the six-page candidate route's zero continuation edges (sunset-rmx.21).
# Responsibilities: Pin the frozen-input absence — the frozen run configurations supply
#   no structure proposals at all, so no continues-to edges can exist downstream — and
#   pin that the proposed-edge machinery is intact end to end: a supplied continues-to
#   proposal survives structure.collect and is counted by the evaluator relationship
#   join, ruling out validation or evaluation-join loss as the cause.
# Rationale: sunset-rmx.21 must distinguish "configuration never proposes" from
#   "validation drops edges" or "evaluation loses edges" before a continuation review
#   stage can be decided. Engineering-only: no quality/economy/scaling claims.
"""Continuation-edge diagnosis evidence (sunset-rmx.21)."""
import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from digitization.evaluation import relationship_metrics
from digitization.inspection import inspect_run
from digitization.pipeline import run

FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures' / 'digitization'
RUNS = ('baseline', 'loop-1', 'loop-2', 'replay-loop-1')
PAGES = [1, 2, 3, 4, 5, 6]


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _page_text(run_name, content_id):
    descriptor = _load(FIXTURES / 'six-page-runs' / run_name / 'descriptor.json')
    return next(c.get('value', '') for c in descriptor['contents'] if c['id'] == content_id)


@pytest.mark.parametrize('name', RUNS)
def test_frozen_six_page_configs_supply_zero_structure_proposals(name):
    """Hypothesis (a) input side: no pages.*.structure proposals exist in any frozen config."""
    config = _load(FIXTURES / 'six-page-runs' / name / 'config.json')
    assert 'pages' not in config


@pytest.mark.parametrize('name', RUNS)
def test_frozen_six_page_structures_record_zero_continuation_edges(name):
    """Hypothesis (a) output side: every observation on all six pages carries relations []."""
    structure = _load(FIXTURES / 'six-page-runs' / name / 'structure.json')
    assert structure['diagnostics'] == []
    for page in PAGES:
        observed = [o for o in structure['observations']
                    if o['region_id'].startswith(f'page-{page}-')]
        assert observed, f'run {name} has no observations for page {page}'
        assert all(o['relations'] == [] for o in observed)


def test_frozen_six_page_runs_record_explicit_continuation_markers_without_edges():
    """Both frozen routes saw printed continuation markers, yet emitted zero edges."""
    baseline_lead = _page_text('baseline', 'text-page-1-baseline')
    assert '(Sigue en pág. 2)' in baseline_lead  # page 1 -> page 2, inside the excerpt
    regional_ginsberg = _page_text('loop-1', 'text-page-1-det-71')
    assert '(sigue en pág. 37)' in regional_ginsberg  # page 1 -> page 37, outside it
    baseline_structure = _load(FIXTURES / 'six-page-runs' / 'baseline' / 'structure.json')
    candidate_structure = _load(FIXTURES / 'six-page-runs' / 'loop-1' / 'structure.json')
    assert not any(o['relations'] for o in baseline_structure['observations'])
    assert not any(o['relations'] for o in candidate_structure['observations'])


def test_six_page_evaluation_pins_degenerate_relationship_metrics():
    """The evaluator join is honestly empty: reference_count 0, missing_rate null."""
    report = _load(FIXTURES / 'six-page-evaluation' / 'evaluation.json')
    assert report['metrics']['relationships'] == {
        'matched': 0, 'missing': [], 'missing_rate': None,
        'reference_count': 0, 'spurious': [], 'spurious_count': 0}
    assert report['thresholds'] == {}
    assert 'continuation-relationships' in report['missing_scopes']


PAGE1_TEXT = 'lead ends mid sentence (continues)'
PAGE2_TEXT = 'sumario text continues here'


def _two_page_config(source_bytes):
    detection = {'id': 'p1', 'kind': 'poem', 'bbox': [30, 60, 200, 100]}
    config = {
        'version': '1', 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'provider': {'kind': 'recorded', 'id': 'fixture-ocr', 'version': '1'},
        'render': {'dpi': 72},
        'pages': {str(number): {
            'detections': [dict(detection)],
            'recognitions': {'p1': {'raw_text': text, 'unresolved': []}}}
            for number, text in ((1, PAGE1_TEXT), (2, PAGE2_TEXT))}}
    config['pages']['1']['structure'] = [{
        'id': 'cont-page-1', 'kind': 'ocr', 'region_id': 'page-1-p1',
        'producer': {'id': 'fixture-structure', 'version': '1', 'config': {}},
        'text': PAGE1_TEXT,
        'relations': [{'kind': 'continues-to', 'target': 'page-2-p1'}]}]
    return config


def _two_page_source(root):
    source = root / 'two-pages.pdf'
    with pymupdf.open() as pdf:
        for number in (1, 2):
            page = pdf.new_page(width=300, height=400)
            page.insert_text((30, 40), f'synthetic page {number}')
        pdf.save(source)
    return source


def _observed_edges(observations):
    return [{'source': o['region_id'], 'kind': relation['kind'], 'target': relation['target']}
            for o in observations for relation in o.get('relations', [])]


@pytest.fixture(scope='module')
def two_page_run(tmp_path_factory):
    """Minimal synthetic two-page descriptor proposing one cross-page continuation."""
    root = tmp_path_factory.mktemp('continuation')
    source = _two_page_source(root)
    config_path = root / 'recorded.json'
    config_path.write_text(json.dumps(_two_page_config(source.read_bytes())))
    out = root / 'continuation'
    run(source, [1, 2], config_path, out)
    observations = inspect_run(out)['structure']['observations']
    return observations, _observed_edges(observations)


def test_proposed_continuation_edge_survives_collect(two_page_run):
    """Ruling out (b): structure._validate keeps a supplied continues-to relation."""
    observations, edges = two_page_run
    assert edges == [
        {'source': 'page-1-p1', 'kind': 'continues-to', 'target': 'page-2-p1'}]
    proposal = next(o for o in observations if o['id'] == 'cont-page-1')
    assert proposal['status'] == 'unresolved'


def test_proposed_continuation_edge_counts_in_evaluation_join(two_page_run):
    """Ruling out (c): the evaluator join counts a surviving edge as matched."""
    _, edges = two_page_run
    candidate_map = {'ref-page-1': 'page-1-p1', 'ref-page-2': 'page-2-p1'}
    reference = [{'source': 'ref-page-1', 'kind': 'continues-to', 'target': 'ref-page-2'}]
    metrics = relationship_metrics(reference, edges, candidate_map)
    assert metrics['matched'] == 1 and metrics['missing_rate'] == 0.0
    assert metrics['spurious_count'] == 0 and metrics['reference_count'] == 1
