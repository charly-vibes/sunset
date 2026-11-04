# Purpose: Verify the complete stubbed digitization pilot journey through the public CLI.
# Responsibilities: Pin the interrupt-then-fresh-process-resume continuity proof, the
#   shared evaluate command over baseline/regional fakes, attribution/loss inspection,
#   the committed .15 local-smoke evidence identity, and the recorded quality ledger.
# Rationale: sunset-rmx.13 (checkpoint 3.4) integrates one stubbed journey into the
#   existing gates without broadening conformance: the stage stays engineering-only,
#   resume never dispatches, and real smoke evidence is only inspected, never re-run.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'fixtures' / 'digitization'
SOURCE_SHA = '42292cc690f4c10f88f8b9768eb491e7accb31704c897d47769ea54758093ad4'
ENGINE_CONFIG_SHA = 'ee2c4d8ee6d1e5066343397ebdd686937af09901deea3e44dfd3d7b7ad883db4'
SCOPES = ['regions', 'text-cer', 'line-boundary', 'stanza-boundary',
          'indentation', 'continuation-relationships']
POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 2,
          'max_provider_attempts': 8, 'max_estimated_cost_microunits': 500000,
          'max_request_bytes': 1000000, 'max_output_bytes': 2000000,
          'price_schedule_sha256': 'd' * 64}
REGION_KEYS = {'region_id', 'producer', 'revision', 'alternatives', 'raw_text', 'selector'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def stub_source(tmp_path, pages=('2', '5')):
    source = tmp_path / 'pilot-source.pdf'
    with pymupdf.open() as pdf:
        for number in range(1, max(int(p) for p in pages) + 1):
            page = pdf.new_page(width=300, height=400)
            page.insert_text((30, 40), f'Pilot fixture page {number}')
        pdf.save(source)
    return source


def _spec(detections, recognitions):
    page = {'detections': [{'id': rid, 'kind': kind, 'bbox': bbox}
                           for rid, kind, bbox in detections],
            'recognitions': {rid: {'raw_text': text, 'unresolved': list(unresolved)}
                             for rid, text, unresolved in recognitions}}
    return page


WHOLE = _spec([('whole', 'text', [20, 30, 120, 100])], [('whole', 'ab', [])])
REGIONAL = _spec([('p1', 'poem', [20, 30, 120, 50]), ('c1', 'caption', [20, 200, 120, 20])],
                 [('p1', 'ab', []), ('c1', 'cd', [])])
LOSS = _spec([('p1', 'poem', [20, 30, 120, 50]), ('c1', 'caption', [20, 200, 120, 20])],
             [('p1', 'ab', []), ('c1', '?', ['caption-uncertain'])])
PAGE_SPECS = {'fixture-journey': {'2': WHOLE, '5': WHOLE},
              'fixture-baseline': {'2': WHOLE, '5': WHOLE},
              'fixture-regional': {'2': REGIONAL, '5': REGIONAL},
              'fixture-loss': {'2': LOSS}}


def stub_config(source, provider_id):
    config = {'version': '1', 'source_sha256': sha(source.read_bytes()),
              'provider': {'kind': 'recorded', 'id': provider_id, 'version': '1'},
              'render': {'dpi': 72}, 'budget': dict(POLICY),
              'pages': PAGE_SPECS[provider_id]}
    path = source.parent / f'config-{provider_id}.json'
    path.write_text(json.dumps(config))
    return path


def engineering_stage(baseline_manifest, candidate_manifest):
    return {'version': '1', 'stage_id': 'pilot-journey-fixture', 'mode': 'engineering-only',
            'approval': {'owner': 'pilot-journey-fixture — engineering-only (sunset-rmx.13)',
                         'approved': True},
            'source_sha256': baseline_manifest['source']['sha256'], 'pages': [2, 5],
            'reference_sha256': None,
            'baseline_configuration_sha256': baseline_manifest['configuration']['sha256'],
            'candidate_configuration_sha256': candidate_manifest['configuration']['sha256'],
            'engine': {'id': 'fixture-ocr', 'version': '1',
                       'configuration_sha256': 'f' * 64, 'price_schedule_sha256': 'd' * 64},
            'budget': dict(POLICY),
            'policy': {'version': '1', 'normalization': 'identity',
                       'region_iou_threshold': 0.5,
                       'tie_break': 'canonical-geometry-then-recorded-id',
                       'required_scopes': list(SCOPES), 'thresholds': {}},
            'exclusions': [], 'missing_scopes': list(SCOPES)}


def run_both_routes(source, tmp_path):
    runs, manifests = [], []
    for name, provider_id in (('baseline', 'fixture-baseline'), ('candidate', 'fixture-regional')):
        run_dir = tmp_path / name
        code, result = cli('run', '--source', source, '--pages', '2,5',
                           '--config', stub_config(source, provider_id), '--output', run_dir)
        assert code == 0
        assert result['status'] == 'completed'
        runs.append(run_dir)
        manifests.append(json.loads((run_dir / 'manifest.json').read_text()))
    return runs, manifests


def interrupt_run(run, marker):
    crash = '''
import os, sys
from pathlib import Path
from digitization.budget import BudgetLedger
from digitization.providers import dispatch
ledger = BudgetLedger.open(Path(sys.argv[1]) / 'budget-state.json')
def provider(request_key, payload):
    Path(sys.argv[2]).write_text(request_key)
    os._exit(73)
dispatch(ledger, request_key='request-1', payload=b'fixture',
         maximum_charge=70, provider=provider)
'''
    crashed = subprocess.run([sys.executable, '-B', '-c', crash, str(run), str(marker)],
                             cwd=ROOT, capture_output=True, text=True)
    assert crashed.returncode == 73
    assert marker.read_text() == 'request-1'
    return (run / 'budget-state.json').read_bytes()


@pytest.fixture
def both_routes(tmp_path):
    source = stub_source(tmp_path)
    runs, manifests = run_both_routes(source, tmp_path)
    return source, runs, manifests


def test_pilot_journey_interrupt_then_fresh_process_resume_preserves_continuity(tmp_path):
    source = stub_source(tmp_path)
    run = tmp_path / 'run'
    code, result = cli('run', '--source', source, '--pages', '2,5',
                       '--config', stub_config(source, 'fixture-journey'), '--output', run)
    assert code == 0
    assert result['status'] == 'completed'
    retained = {name: (run / name).read_bytes() for name in
                ('manifest.json', 'history.json', 'ledger.json', 'descriptor.json')}
    ledger_after_crash = interrupt_run(run, tmp_path / 'provider-entered')

    code, resumed = cli('resume', '--run', run)

    assert code == 2
    assert resumed == {'manifest': str(run / 'manifest.json'),
                       'status': 'stopped-with-unresolved-work',
                       'reason': 'dispatch-uncertain', 'provider_calls': 0,
                       'unresolved_attempts': ['attempt-1']}
    assert {name: (run / name).read_bytes() for name in retained} == retained
    assert (run / 'budget-state.json').read_bytes() == ledger_after_crash
    code, report = cli('inspect', '--run', run, '--json')
    assert code == 0
    assert report['status'] == 'completed'
    assert report['usage']['provider_calls'] == 0
    assert {path.name for path in tmp_path.iterdir()} == {
        'pilot-source.pdf', 'config-fixture-journey.json', 'run', 'provider-entered'}


def test_pilot_journey_evaluate_shared_operation_with_fakes(both_routes, tmp_path):
    source, runs, manifests = both_routes
    stage = engineering_stage(manifests[0], manifests[1])
    stage_path = tmp_path / 'stage.json'
    stage_path.write_text(json.dumps(stage))
    reference_path = tmp_path / 'reference.json'
    reference_path.write_text('{}')
    output = tmp_path / 'evaluation'

    code, result = cli('evaluate', '--baseline', runs[0], '--candidate', runs[1],
                       '--reference', reference_path, '--policy', stage_path,
                       '--output', output)

    assert code == 2
    assert result['status'] == 'evaluation-incomplete'
    report = json.loads((output / 'evaluation.json').read_text())
    assert report['stage_id'] == 'pilot-journey-fixture'
    assert report['status'] == 'evaluation-incomplete'
    assert report['quality_conclusion'] == 'UNKNOWN'
    assert report['positive_conclusions_allowed'] is False
    assert report['positive_economy_conclusion_allowed'] is False
    assert report['positive_scaling_conclusion_allowed'] is False
    assert report['digests'] == {'stage': sha(stage_path.read_bytes()),
                                 'reference': sha(reference_path.read_bytes()),
                                 'baseline_manifest': sha((runs[0] / 'manifest.json').read_bytes()),
                                 'candidate_manifest': sha((runs[1] / 'manifest.json').read_bytes())}
    assert report['execution']['provider_calls'] == {'baseline': 0, 'candidate': 0}
    assert report['unknown_claims'] == ['correction-effort', 'setup-effort', 'total-cost']


def test_pilot_journey_inspection_reports_attribution(both_routes):
    _, runs, _ = both_routes
    code, report = cli('inspect', '--run', runs[1], '--json')
    assert code == 0
    assert report['status'] == 'completed'
    assert [region['region_id'] for region in report['regions']] == [
        'page-2-p1', 'page-2-c1', 'page-5-p1', 'page-5-c1']
    assert REGION_KEYS <= set(report['regions'][0])
    assert report['unresolved'] == []
    assert report['coverage'] == 'unexamined-outside-recorded-regions'
    assert report['usage']['provider_calls'] == 0


def test_pilot_loss_report_lists_unresolved_regions_with_attribution_kept(tmp_path):
    source = stub_source(tmp_path, pages=('2',))
    run = tmp_path / 'run'
    code, result = cli('run', '--source', source, '--pages', '2',
                       '--config', stub_config(source, 'fixture-loss'), '--output', run)
    assert code == 2
    assert result['status'] == 'stopped-with-unresolved-work'
    code, report = cli('inspect', '--run', run, '--json')
    assert code == 0
    assert report['unresolved'] == [{'region_id': 'page-2-c1', 'reason': 'caption-uncertain'}]
    assert [region['region_id'] for region in report['regions']] == ['page-2-p1', 'page-2-c1']
    resolved = report['regions'][0]
    assert resolved['revision'] == 'recognized-page-2-p1'
    assert resolved['alternatives'] == []


@pytest.mark.parametrize('name,region_count', [('baseline', 2), ('regional', 121)])
def test_real_local_smoke_evidence_inspected_without_inference(name, region_count):
    run_dir = FIXTURES / 'local-smoke' / name
    code, report = cli('inspect', '--run', run_dir, '--json')
    assert code == 0
    assert report['status'] == 'completed'
    assert report['source']['sha256'] == SOURCE_SHA
    assert json.loads((run_dir / 'manifest.json').read_text())['pages'] == [2, 5]
    usage = report['usage']
    assert usage['mode'] == 'local'
    assert usage['estimated_charge_microunits'] == 0
    assert len(report['regions']) == region_count
    assert report['unresolved'] == []
    assert report['coverage'] == 'unexamined-outside-recorded-regions'


def test_pilot_stage_binds_committed_local_configs_and_stays_engineering_only():
    stage = json.loads((FIXTURES / 'pilot.json').read_text())
    assert stage['stage_id'] == 'diario-difficult-page-r1'
    assert stage['pages'] == [2, 5]
    assert stage['source_sha256'] == SOURCE_SHA
    assert stage['mode'] == 'engineering-only'
    assert stage['reference_sha256'] is None
    assert len(stage['missing_scopes']) == 6
    assert stage['approval']['approved'] is True
    assert 'ruling 2026-11-03' in stage['approval']['owner']
    assert stage['baseline_configuration_sha256'] == sha((FIXTURES / 'local-baseline.json').read_bytes())
    assert stage['candidate_configuration_sha256'] == sha((FIXTURES / 'local-regional.json').read_bytes())
    engine = stage['engine']
    assert engine['id'] == 'tesseract-ocr'
    assert engine['version'] == '5.5.3'
    assert engine['configuration_sha256'] == ENGINE_CONFIG_SHA
    assert stage['budget']['max_provider_attempts'] == 160
    smoke = json.loads((FIXTURES / 'local-smoke' / 'manifest.json').read_text())
    assert smoke['configuration']['baseline']['sha256'] == stage['baseline_configuration_sha256']
    assert smoke['configuration']['candidate']['sha256'] == stage['candidate_configuration_sha256']


def test_pilot_quality_ledger_records_the_journey():
    ledger = (FIXTURES / 'quality-ledger.org').read_text(encoding='utf-8')
    assert 'diario-difficult-page-r1' in ledger
    assert 'engineering-only' in ledger
    assert 'evaluation-incomplete' in ledger
    assert SOURCE_SHA[:12] in ledger
    assert 'dispatch-uncertain' in ledger
    assert 'provider_calls: 0' in ledger
    assert 'no duplicate dispatch' in ledger
    assert 'just spec-check' in ledger
    assert 'No positive quality' in ledger
