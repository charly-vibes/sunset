# Purpose: Freeze the six-page stage manifest for sunset-rmx.16 before any
#   six-page candidate inference (checkpoint 3.1b).
# Responsibilities: Assert the committed stage manifest validates under the
#   .9 evaluate/validation contract as engineering-only with nonempty missing
#   scopes, honest pins (source/config/engine/budget/policy digests), no
#   fabricated reference record, and untouched difficult-page evidence.
# Rationale: The approval gate is data, not prose — these tests pin the exact
#   frozen inputs so sunset-rmx.12 can only run against the approved stage,
#   and so positive quality/economy/scaling conclusions stay structurally
#   impossible while references are missing.
"""Six-page stage manifest freeze (sunset-rmx.16)."""
import hashlib
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures' / 'digitization'
SOURCE_SHA = '42292cc690f4c10f88f8b9768eb491e7accb31704c897d47769ea54758093ad4'
BASELINE_SHA = '30f5df7adb18af012010e641c489c00bddbddb2df43ecd3edbafcfaed3f1c679'
CANDIDATE_SHA = '1a1ae286e597a248cd37b5a452c916225d82aa0470d246274185c1f9ae6483a4'
ENGINE_CONFIG_SHA = 'ee2c4d8ee6d1e5066343397ebdd686937af09901deea3e44dfd3d7b7ad883db4'
PRICE_SCHEDULE_SHA = '357e4136d0bea16484bf016363d7c3f7295e39fb09276d7e7ab39143664bba9f'
REFERENCE_SCOPES = {'regions', 'text-cer', 'line-boundary', 'stanza-boundary',
                    'indentation', 'continuation-relationships'}


def _sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_six_page_stage_manifest_is_frozen_engineering_only():
    from digitization.evaluation import validate_stage

    result = validate_stage(FIXTURES / 'six-page-pilot.json')
    stage = result['stage']
    assert stage['version'] == '1'
    assert stage['stage_id'] == 'diario-six-page-r2'
    assert stage['mode'] == 'engineering-only'
    assert result['positive_conclusions_allowed'] is False
    assert stage['pages'] == [1, 2, 3, 4, 5, 6]
    assert stage['source_sha256'] == SOURCE_SHA
    assert stage['reference_sha256'] is None
    assert set(stage['missing_scopes']) == REFERENCE_SCOPES
    assert stage['exclusions'] == []
    assert stage['approval']['approved'] is True
    assert '2026-11-03' in stage['approval']['owner']


def test_six_page_config_and_engine_pins_match_committed_records():
    from digitization.evaluation import validate_stage

    stage = validate_stage(FIXTURES / 'six-page-pilot.json')['stage']
    assert stage['baseline_configuration_sha256'] == BASELINE_SHA
    assert stage['baseline_configuration_sha256'] == _sha_file(
        FIXTURES / 'local-baseline.json')
    assert stage['candidate_configuration_sha256'] == CANDIDATE_SHA
    assert stage['candidate_configuration_sha256'] == _sha_file(
        FIXTURES / 'local-regional-sixpage.json')
    assert stage['budget']['max_provider_attempts'] == 512
    engine = stage['engine']
    assert engine['id'] == 'tesseract-ocr'
    assert engine['version'] == '5.5.3'
    assert engine['configuration_sha256'] == ENGINE_CONFIG_SHA
    assert engine['price_schedule_sha256'] == PRICE_SCHEDULE_SHA
    assert stage['budget']['price_schedule_sha256'] == PRICE_SCHEDULE_SHA
    difficult = json.loads((FIXTURES / 'pilot.json').read_text(encoding='utf-8'))
    assert engine['configuration_sha256'] == difficult['engine']['configuration_sha256']


def test_six_page_reference_record_is_absence_not_fabrication():
    reference = json.loads(
        (FIXTURES / 'six-page-reference.json').read_text(encoding='utf-8'))
    assert reference == {}


def test_six_page_stage_digest_is_stable_and_recorded():
    digest = _sha_file(FIXTURES / 'six-page-pilot.json')
    org = (FIXTURES / 'six-page-references.org').read_text(encoding='utf-8')
    assert digest in org


def test_difficult_page_evidence_is_preserved():
    from digitization.evaluation import validate_stage

    result = validate_stage(FIXTURES / 'pilot.json')
    assert result['stage']['stage_id'] == 'diario-difficult-page-r1'
    assert result['stage']['pages'] == [2, 5]
    assert (FIXTURES / 'difficult-page-results.org').exists()
    for run in ('baseline', 'loop-1', 'loop-2', 'replay-loop-1'):
        assert (FIXTURES / 'difficult-page' / run).exists()


def test_six_page_manifest_rejects_unapproved_shapes(tmp_path):
    from digitization.evaluation import validate_stage

    stage = json.loads(
        (FIXTURES / 'six-page-pilot.json').read_text(encoding='utf-8'))
    path = tmp_path / 'mutant.json'
    mutant = dict(stage, approval=dict(stage['approval'], approved=False))
    path.write_text(json.dumps(mutant), encoding='utf-8')
    with pytest.raises(ValueError, match='invalid-stage-manifest'):
        validate_stage(path)
    mutant = dict(stage, mode='assessment')
    path.write_text(json.dumps(mutant), encoding='utf-8')
    with pytest.raises(ValueError, match='invalid-stage-manifest'):
        validate_stage(path)
