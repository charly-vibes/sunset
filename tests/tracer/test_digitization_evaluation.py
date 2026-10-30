# Purpose: Verify pilot metrics and stage-policy validation with known answers.
# Responsibilities: Pin exact text, region, layout and directed-edge scoring;
#   ensure missing evidence remains UNKNOWN and approval limits are enforced.
# Rationale: sunset-rmx.9 must reject unsupported quality/economy conclusions
#   before either stage uses the shared evaluator.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 2,
          'max_provider_attempts': 8, 'max_estimated_cost_microunits': 500000,
          'max_request_bytes': 1000000, 'max_output_bytes': 2000000,
          'price_schedule_sha256': 'd' * 64}
THRESHOLDS = {'cer': 0.1, 'region_precision': 0.5, 'region_recall': 0.5,
              'line_boundary_error': 0.5, 'stanza_boundary_error': 0.5,
              'indentation_error': 0.5, 'continuation_error': 0.5}


@pytest.fixture
def stage():
    return {'version': '1', 'stage_id': 'fixture-stage', 'mode': 'assessment',
            'approval': {'owner': 'fixture-reviewer', 'approved': True},
            'source_sha256': 'a' * 64, 'pages': [1],
            'reference_sha256': 'b' * 64,
            'baseline_configuration_sha256': 'c' * 64,
            'candidate_configuration_sha256': 'e' * 64,
            'engine': {'id': 'fixture-ocr', 'version': '1',
                       'configuration_sha256': 'f' * 64, 'price_schedule_sha256': 'd' * 64},
            'budget': dict(POLICY),
            'policy': {'version': '1', 'normalization': 'identity',
                       'region_iou_threshold': 0.5,
                       'tie_break': 'canonical-geometry-then-recorded-id',
                       'required_scopes': ['text', 'regions', 'lines', 'stanzas',
                                           'indentation', 'continuations'],
                       'thresholds': dict(THRESHOLDS)},
            'exclusions': []}


def test_character_error_uses_identity_unicode_and_preserves_whitespace():
    from digitization.evaluation import character_error

    assert character_error('ab', 'ac') == {
        'status': 'measured', 'errors': 1, 'reference_characters': 2, 'value': 0.5}
    assert character_error('ab', 'ab') == {
        'status': 'measured', 'errors': 0, 'reference_characters': 2, 'value': 0.0}
    assert character_error('a b', 'ab')['value'] == pytest.approx(1 / 3)
    assert character_error('é', 'e\u0301')['errors'] == 2
    assert character_error('', 'anything') == {
        'status': 'UNKNOWN', 'errors': 0, 'reference_characters': 0, 'value': None}


def test_region_matching_is_one_to_one_and_keeps_misses_and_spurious_boxes():
    from digitization.evaluation import match_regions

    references = [
        {'id': 'r1', 'page': 1, 'bbox': [0, 0, 10, 10]},
        {'id': 'r2', 'page': 1, 'bbox': [20, 0, 10, 10]},
    ]
    candidates = [
        {'region_id': 'c1', 'page': 1, 'bbox': [0, 0, 10, 10]},
        {'region_id': 'c2', 'page': 1, 'bbox': [40, 0, 10, 10]},
    ]
    result = match_regions(references, candidates, minimum_iou=0.5)
    assert result['matches'] == [{'reference_id': 'r1', 'candidate_id': 'c1', 'iou': 1.0}]
    assert result['missing'] == ['r2']
    assert result['spurious'] == ['c2']
    assert result['precision'] == result['recall'] == 0.5

    competing = candidates + [{'region_id': 'c3', 'page': 1, 'bbox': [0, 0, 10, 10]}]
    result = match_regions([references[0]], competing, minimum_iou=0.5)
    assert len(result['matches']) == 1
    assert len(result['spurious']) == 2


def test_layout_metrics_count_missing_line_stanza_and_indent_units():
    from digitization.evaluation import layout_metrics

    reference = {'line_breaks': [1, 3], 'stanza_boundaries': [3],
                 'indentation': [0, 2, 0]}
    metrics = layout_metrics(reference, 'a\nbc')
    assert {k: metrics['line_boundary_error'][k] for k in
            ('status', 'missing', 'spurious', 'denominator', 'value')} == {
        'status': 'measured', 'missing': 1, 'spurious': 0, 'denominator': 2, 'value': 0.5}
    assert metrics['stanza_boundary_error']['status'] == 'measured'
    assert metrics['stanza_boundary_error']['value'] == 1.0
    assert metrics['indentation_error']['value'] == pytest.approx(2 / 3)


def test_directed_continuation_edges_keep_wrong_and_reversed_endpoints_visible():
    from digitization.evaluation import relationship_metrics

    reference = [{'source': 'r1', 'kind': 'continues-to', 'target': 'r2'},
                 {'source': 'r2', 'kind': 'continues-to', 'target': 'r3'}]
    candidate = [{'source': 'c1', 'kind': 'continues-to', 'target': 'c2'},
                 {'source': 'c3', 'kind': 'continues-to', 'target': 'c2'}]
    result = relationship_metrics(reference, candidate,
                                  {'r1': 'c1', 'r2': 'c2', 'r3': 'c3'})
    assert result['matched'] == 1
    assert result['missing'] == [reference[1]]
    assert result['spurious'] == [candidate[1]]
    assert result['missing_rate'] == 0.5


def test_stage_validation_requires_pinned_approval_engine_budget_and_thresholds(stage, tmp_path):
    from digitization.evaluation import validate_stage

    path = tmp_path / 'stage.json'
    path.write_text(json.dumps(stage))
    result = validate_stage(path)
    assert result['stage']['stage_id'] == 'fixture-stage'
    for field in ('source_sha256', 'pages', 'engine', 'budget', 'policy',
                  'reference_sha256', 'approval'):
        invalid = dict(stage)
        del invalid[field]
        path.write_text(json.dumps(invalid))
        with pytest.raises(ValueError, match='invalid-stage-manifest'):
            validate_stage(path)


def test_engineering_only_stage_can_be_validated_but_not_promoted(stage, tmp_path):
    from digitization.evaluation import validate_stage

    stage.update(mode='engineering-only', reference_sha256=None,
                 missing_scopes=['text', 'lines'])
    path = tmp_path / 'engineering.json'
    path.write_text(json.dumps(stage))
    result = validate_stage(path)
    assert result['positive_conclusions_allowed'] is False
    assert set(result['missing_scopes']) == {'text', 'lines'}


def test_public_evaluate_scores_verified_runs_without_provider_calls(stage, tmp_path):
    source = tmp_path / 'source.pdf'
    with pymupdf.open() as pdf:
        pdf.new_page(width=300, height=400)
        pdf.save(source)
    config = {'version': '1', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'provider': {'kind': 'recorded', 'id': 'fixture', 'version': '1',
                           'model': {'id': 'alias', 'revision': None}}, 'render': {'dpi': 72},
              'pages': {'1': {'detections': [{'id': 'p1', 'kind': 'text',
                                               'bbox': [20, 30, 120, 100]}],
                              'recognitions': {'p1': {'raw_text': 'ab', 'unresolved': []}}}}}
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(config))
    runs = []
    for name in ('baseline', 'candidate'):
        run_dir = tmp_path / name
        completed = subprocess.run([sys.executable, '-m', 'digitization', 'run',
            '--source', str(source), '--pages', '1', '--config', str(config_path),
            '--output', str(run_dir)], cwd=ROOT, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        runs.append(run_dir)
    manifests = [json.loads((path / 'manifest.json').read_text()) for path in runs]
    stage.update(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), pages=[1],
                 baseline_configuration_sha256=manifests[0]['configuration']['sha256'],
                 candidate_configuration_sha256=manifests[1]['configuration']['sha256'],
                 policy={**stage['policy'], 'thresholds': {'cer': 0.1,
                     'region_precision': 1.0, 'region_recall': 1.0}})
    reference = {'regions': [{'id': 'ref-p1', 'page': 1, 'bbox': [20, 30, 120, 100]}],
                 'text': {'ref-p1': 'ab'}, 'layout': {}, 'relationships': []}
    reference_path = tmp_path / 'reference.json'
    reference_path.write_text(json.dumps(reference))
    stage['reference_sha256'] = hashlib.sha256(reference_path.read_bytes()).hexdigest()
    policy_path = tmp_path / 'policy.json'
    policy_path.write_text(json.dumps(stage))
    output = tmp_path / 'evaluation'
    completed = subprocess.run([sys.executable, '-m', 'digitization', 'evaluate',
        '--baseline', str(runs[0]), '--candidate', str(runs[1]), '--reference',
        str(reference_path), '--policy', str(policy_path), '--output', str(output)],
        cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    report = json.loads((output / 'evaluation.json').read_text())
    assert result['status'] == 'measured'
    assert result['report_sha256'] == hashlib.sha256((output / 'evaluation.json').read_bytes()).hexdigest()
    assert report['quality_conclusion'] == 'pass'
    assert report['positive_economy_conclusion_allowed'] is False
    assert report['execution']['candidate_usage']['provider_calls'] == 0
