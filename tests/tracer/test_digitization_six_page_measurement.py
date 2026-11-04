# Purpose: Pin the six-page measurement evidence for sunset-rmx.12 (checkpoint 3.3 measurement half).
# Responsibilities: Assert the committed runs cover all six pages under the frozen
#   engineering-only stage, replay is zero-inference and fresh-run-comparable, the
#   shared .9 evaluate operation's machine-readable report is digest-bound and
#   evaluation-incomplete with honest degenerate denominators, and the results
#   record retains exact commands plus a rejection-grounded scaling recommendation.
# Rationale: Measurement tickets must bind to reproducible source-digested
#   artifacts, not prose — the run manifests, replay report and evaluation.json
#   are the only admissible evidence, and positive conclusions must remain
#   structurally impossible while references are missing.
"""Six-page measurement evidence (sunset-rmx.12)."""
import hashlib
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures' / 'digitization'
SOURCE_SHA = '42292cc690f4c10f88f8b9768eb491e7accb31704c897d47769ea54758093ad4'
BASELINE_CONFIG_SHA = '30f5df7adb18af012010e641c489c00bddbddb2df43ecd3edbafcfaed3f1c679'
CANDIDATE_SHA = '1a1ae286e597a248cd37b5a452c916225d82aa0470d246274185c1f9ae6483a4'
CANDIDATE_CONFIG_SHA = '29c031bfafa21b61fec01fb70b420d940ec3615ce8c07f03cebf3d12d2b80c25'
STAGE_SHA = '31bf682e0e99ec8ca5c3cfb040fb6ba66580ea158c66a58c2eaa36fcec443e35'
PAGES = [1, 2, 3, 4, 5, 6]
RUNS = FIXTURES / 'six-page-runs'


def _sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name,config_sha', [
    ('baseline', BASELINE_CONFIG_SHA),
    ('loop-1', CANDIDATE_SHA),
    ('loop-2', CANDIDATE_SHA),
])
def test_six_page_run_is_pinned_and_complete(name, config_sha):
    manifest = _load(RUNS / name / 'manifest.json')
    assert manifest['pages'] == PAGES
    assert manifest['source']['sha256'] == SOURCE_SHA
    assert manifest['configuration']['sha256'] == config_sha
    usage = manifest['usage']
    assert usage['mode'] == 'local'
    assert usage['provider_calls'] >= 1
    assert usage['estimated_charge_microunits'] == 0


def test_six_page_replay_is_zero_inference_and_matches_fresh_loop():
    replay = _load(RUNS / 'replay-loop-1' / 'replay-report.json')
    assert replay['status'] == 'replayed'
    assert replay['provider_calls'] == 0
    assert replay['fresh_comparison']['differences'] == []


def test_six_page_evaluation_is_digest_bound_and_evaluation_incomplete():
    report = _load(FIXTURES / 'six-page-evaluation' / 'evaluation.json')
    assert report['version'] == '1'
    assert report['stage_id'] == 'diario-six-page-r2'
    assert report['status'] == 'evaluation-incomplete'
    assert report['positive_conclusions_allowed'] is False
    digests = report['digests']
    assert digests['stage'] == STAGE_SHA
    assert digests['stage'] == _sha_file(FIXTURES / 'six-page-pilot.json')
    assert digests['reference'] == _sha_file(FIXTURES / 'six-page-reference.json')
    assert digests['baseline_manifest'] == _sha_file(RUNS / 'baseline' / 'manifest.json')
    assert digests['candidate_manifest'] == _sha_file(RUNS / 'loop-1' / 'manifest.json')
    metrics = report['metrics']
    assert metrics['regions']['baseline']['reference_count'] == 0
    assert metrics['regions']['candidate']['reference_count'] == 0
    for label in ('baseline', 'candidate'):
        assert metrics['cer'][label]['status'] == 'UNKNOWN', label
    for label in ('indentation_error', 'line_boundary_error', 'stanza_boundary_error'):
        assert metrics['layout'][label]['status'] == 'UNKNOWN', label
    assert metrics['relationships']['reference_count'] == 0
    assert metrics['relationships']['missing_rate'] is None
    execution = report['execution']
    assert execution['correction_effort'] == 'UNKNOWN'
    assert execution['baseline_usage']['estimated_charge_microunits'] == 0
    assert execution['candidate_usage']['estimated_charge_microunits'] == 0
    assert report['unknown_claims']


def test_six_page_results_org_retains_commands_and_grounded_scaling():
    org = (FIXTURES / 'six-page-results.org').read_text(encoding='utf-8')
    assert 'six-page-evaluation/evaluation.json' in org
    assert STAGE_SHA in org
    assert 'evaluation-incomplete' in org
    for command in ('run --source fixtures/carriers/diario-de-poesia-excerpt.pdf',
                    'replay --run fixtures/digitization/six-page-runs/loop-1',
                    'evaluate --baseline fixtures/digitization/six-page-runs/baseline'):
        assert command in org
    for pages_token in ('--pages 1,2,3,4,5,6',):
        assert pages_token in org
    assert 'rejection' in org.lower()
