"""Section 4 model-call determinism: pinned identity, exact call key,
schema-validated admission, replay without model calls and the durable spend
boundary (tasks 4.1-4.6 of add-iterative-document-digitization).

Owner ruling G5 (2026-11-24, sunset-gpd): recorded model I/O is retained
locally only, so every fixture here is synthetic — invented page geometry,
invented document text and invented model responses. No real document text,
no network and no live provider invocation happens anywhere in this module;
replay tests additionally trip-wire subprocess and socket creation.
"""

import contextlib
import hashlib
import json
import socket
import subprocess
from pathlib import Path

import pymupdf
import pytest

from digitization.budget import BudgetLedger
from digitization.pipeline import resume as resume_run
from digitization.providers import (FloatingModelAlias, ModelSchemaViolation,
                                    ModelTransportDisabled, model_call_key,
                                    model_provider, pinned_model_identity,
                                    record_model_run, validate_model_output)

MODEL_POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 1,
                'max_provider_attempts': 4, 'max_estimated_cost_microunits': 100,
                'max_request_bytes': 1 << 20, 'max_output_bytes': 1 << 20,
                'price_schedule_sha256': 'd' * 64}

MODEL_SCHEMA = 'recorded-recognition-v1'
TEMPLATE = 'Transcribe the pinned region verbatim; synthetic test template v1.'
DECODING = {'temperature': 0}


def synthetic_transport(responses):
    """Injected transport: returns each invented response once, in order.

    A raised exception simulates a process crash after dispatch. No real
    transport exists; the adapter seam is the only route.
    """
    calls = []
    counter = {'n': 0}

    def transport(request_key, payload):
        counter['n'] += 1
        calls.append({'request_key': request_key, 'payload': payload})
        item = responses[min(counter['n'], len(responses)) - 1]
        if isinstance(item, Exception):
            raise item
        return item
    transport.calls = calls
    transport.count = counter
    return transport


def response(raw_text, charge=40):
    return {'raw': json.dumps({'raw_text': raw_text, 'unresolved': []},
                              ensure_ascii=False).encode('utf-8'),
            'charge': charge}


@pytest.fixture
def model_setup(tmp_path):
    """A synthetic one-page source plus a model-config builder."""
    source = tmp_path / 'synthetic-source.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Parrafo inventado para la prueba')
        page.insert_text((30, 300), 'Segundo parrafo inventado abajo')
        pdf.save(source)

    def config(name, *, revision='2026-01-01',
               detections=(('p1', 'poem', [20, 30, 120, 100]),)):
        value = {'version': '1',
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                 'provider': {'kind': 'model', 'id': 'synthetic-model',
                              'version': '2026-01-01',
                              'model': {'id': 'synthetic-model', 'revision': revision}},
                 'render': {'dpi': 96},
                 'pages': {'1': {'detections': [{'id': rid, 'kind': kind, 'bbox': box}
                                                for rid, kind, box in detections]}},
                 'budget': MODEL_POLICY}
        path = tmp_path / f'{name}-model-config.json'
        path.write_text(json.dumps(value))
        return path
    return source, config


def run_model(model_setup, tmp_path, name, transport, *, revision='2026-01-01',
              maximum_charge=70):
    source, config = model_setup
    return record_model_run((source, [1], config(name, revision=revision)),
                            tmp_path / name, template=TEMPLATE, schema=MODEL_SCHEMA,
                            decoding=DECODING, transport=transport,
                            maximum_charge=maximum_charge)


@contextlib.contextmanager
def forbid_provider_io():
    """Trip-wire every engine and network seam during replay."""
    mp = pytest.MonkeyPatch()

    def forbidden(name):
        def trip(*args, **kwargs):
            pytest.fail(f'{name} must not happen during replay')
        return trip
    mp.setattr(subprocess, 'Popen', forbidden('real engine'))
    mp.setattr(subprocess, 'run', forbidden('real engine'))
    mp.setattr(socket, 'socket', forbidden('network'))
    try:
        yield
    finally:
        mp.undo()


# 4.1 floating alias refused before dispatch; unavailable revision recorded

def test_pinned_identity_refuses_aliases_and_records_unavailability():
    for alias in ('latest', 'stable', 'nightly', 'preview', 'dev', 'unstable'):
        provider = {'kind': 'model', 'id': 'm', 'version': '1',
                    'model': {'id': 'm', 'revision': alias}}
        with pytest.raises(FloatingModelAlias):
            pinned_model_identity(provider)
    pinned = pinned_model_identity({'kind': 'model', 'id': 'm', 'version': '1',
                                    'model': {'id': 'm', 'revision': '2026-01-01'}})
    assert pinned == {'id': 'm', 'revision': '2026-01-01', 'revision_available': True}
    unavailable = pinned_model_identity({'kind': 'model', 'id': 'm', 'version': '1'})
    assert unavailable == {'id': 'm', 'revision': None, 'revision_available': False}


def test_floating_alias_refused_before_any_dispatch(model_setup, tmp_path):
    transport = synthetic_transport([response('respuesta inventada')])
    with pytest.raises(FloatingModelAlias):
        run_model(model_setup, tmp_path, 'alias-run', transport, revision='latest')
    assert transport.calls == []
    assert not (tmp_path / 'alias-run').exists()
    assert not [p for p in tmp_path.rglob('*') if p.name == 'budget-state.json']


def test_unavailable_revision_is_recorded_and_never_claimed_deterministic(model_setup,
                                                                         tmp_path):
    transport = synthetic_transport([response('texto inventado uno')])
    result = run_model(model_setup, tmp_path, 'norev-run', transport, revision=None)
    assert result['status'] == 'completed', result
    manifest = json.loads((tmp_path / 'norev-run' / 'manifest.json').read_text())
    operation = manifest['operations']['page-1-p1']
    assert operation['request']['model_revision_available'] is False
    assert operation['fresh_determinism'] == 'not-claimed'


def test_model_route_without_transport_is_disabled_before_any_io(model_setup, tmp_path):
    with pytest.raises(ModelTransportDisabled):
        run_model(model_setup, tmp_path, 'notransport-run', None)
    assert not (tmp_path / 'notransport-run').exists()
    assert not [p for p in tmp_path.rglob('*') if p.name == 'budget-state.json']


# 4.2 exact model call key

def test_call_key_changes_on_any_component_change():
    def key(**override):
        base = dict(model_id='m', snapshot='2026-01-01', template='T',
                    rendered_input=b'png', schema=MODEL_SCHEMA,
                    decoding={'temperature': 0})
        return model_call_key(**{**base, **override})
    stable = key()
    assert stable == key()
    assert key(model_id='other') != stable
    assert key(snapshot='2026-02-01') != stable
    assert key(template='T2') != stable
    assert key(rendered_input=b'png!') != stable
    assert key(schema='other-schema-v1') != stable
    assert key(decoding={'temperature': 0.2}) != stable
    assert key(decoding={'temperature': 0, 'top_p': 1}) != stable
    # canonical encoding: key order inside decoding parameters is irrelevant
    assert key(decoding={'top_p': 1, 'temperature': 0}) == key(
        decoding={'temperature': 0, 'top_p': 1})


def test_recorded_operation_key_is_the_exact_component_digest(model_setup, tmp_path):
    transport = synthetic_transport([response('texto inventado dos')])
    result = run_model(model_setup, tmp_path, 'keybind-run', transport)
    assert result['status'] == 'completed', result
    root = tmp_path / 'keybind-run'
    manifest = json.loads((root / 'manifest.json').read_text())
    operation = manifest['operations']['page-1-p1']
    request = operation['request']
    key = model_call_key(model_id=request['model']['id'],
                         snapshot=request['model']['revision'],
                         template=TEMPLATE,
                         rendered_input=transport.calls[0]['payload'],
                         schema=MODEL_SCHEMA, decoding=DECODING)
    assert operation['operation_key'] == key
    region = json.loads((root / 'regions.json').read_text())[0]
    assert region['operation_key'] == key
    assert request['rendered_input_sha256'] == hashlib.sha256(
        transport.calls[0]['payload']).hexdigest()


# 4.3 schema-invalid output is a failed attempt admitting nothing

def test_schema_invalid_output_is_failed_attempt_and_admits_nothing(model_setup,
                                                                    tmp_path):
    invalid = {'raw': b'{"not_the_schema": true}', 'charge': 40}
    transport = synthetic_transport([invalid])
    result = run_model(model_setup, tmp_path, 'invalid-run', transport)
    assert result['status'] == 'stopped-with-unresolved-work'
    assert result['reason'] == 'model-output-rejected'
    root = tmp_path / 'invalid-run'
    ledger = BudgetLedger.open(root / 'budget-state.json')
    assert [a['state'] for a in ledger.attempts] == ['charged-failed']
    assert [r['charge'] for r in ledger.receipts] == [40]
    assert ledger.settled == 40
    failed = json.loads((root / 'failed-attempts.json').read_text())
    assert len(failed) == 1
    assert failed[0]['attempt_id'] == ledger.attempts[0]['id']
    assert failed[0]['reason'] == 'model-output-schema-invalid'
    assert failed[0]['raw_response'] == '{"not_the_schema": true}'
    manifest = json.loads((root / 'manifest.json').read_text())
    reference = manifest['artifacts']['failed-attempts.json']
    assert reference['sha256'] == hashlib.sha256(
        (root / 'failed-attempts.json').read_bytes()).hexdigest()
    # nothing admitted into the semantic state
    assert json.loads((root / 'regions.json').read_text()) == []
    assert (root / 'search.txt').read_bytes() == b''
    descriptor = json.loads((root / 'descriptor.json').read_text())
    assert [content['kind'] for content in descriptor['contents']] == ['image']
    unresolved = json.loads((root / 'unresolved.json').read_text())['regions']
    assert unresolved == [{'region_id': 'page-1-p1',
                           'reason': 'model-output-schema-invalid'}]
    assert transport.count['n'] == 1  # recorded once, never retried


def test_validate_model_output_fails_closed_on_unknown_schema():
    assert validate_model_output(b'{"raw_text": "x", "unresolved": []}',
                                 MODEL_SCHEMA) == {'raw_text': 'x', 'unresolved': []}
    with pytest.raises(ModelSchemaViolation):
        validate_model_output(b'{"nope": 1}', MODEL_SCHEMA)
    with pytest.raises(ModelSchemaViolation):
        validate_model_output(b'not json at all', MODEL_SCHEMA)
    with pytest.raises(ModelSchemaViolation):
        validate_model_output(b'{"raw_text": "x", "unresolved": []}', 'unknown-schema')


# 4.4 replay performs zero provider calls; missing record fails closed

def test_replay_performs_zero_provider_calls_and_missing_record_fails_closed(
        model_setup, tmp_path):
    transport = synthetic_transport([response('verso inventado uno')])
    result = run_model(model_setup, tmp_path, 'replayable-run', transport)
    assert result['status'] == 'completed'
    assert transport.count['n'] == 1
    from digitization.replay import replay as replay_run
    with forbid_provider_io():
        first = replay_run(tmp_path / 'replayable-run', tmp_path / 'replay-a')
        second = replay_run(tmp_path / 'replayable-run', tmp_path / 'replay-b')
    assert first['status'] == 'replayed' and first['provider_calls'] == 0
    assert second['provider_calls'] == 0
    assert first['semantic_sha256'] == second['semantic_sha256']

    def contents(name):
        return {str(p.relative_to(tmp_path / name)): p.read_bytes()
                for p in (tmp_path / name).rglob('*') if p.is_file()}
    assert contents('replay-a') == contents('replay-b')

    manifest = json.loads((tmp_path / 'replayable-run' / 'manifest.json').read_text())
    blob_ref = manifest['operations']['page-1-p1']['attempts'][0]['output']
    (tmp_path / 'replayable-run' / blob_ref['path']).unlink()
    with forbid_provider_io():
        outcome = replay_run(tmp_path / 'replayable-run', tmp_path / 'replay-c')
    assert outcome['status'] == 'incomplete-artifacts'
    assert outcome['reason'] == 'incomplete-artifacts'
    assert outcome['provider_calls'] == 0
    assert outcome['missing'] == blob_ref['path']
    assert not (tmp_path / 'replay-c').exists()
    assert transport.count['n'] == 1  # replay never resorted to a live call


# 4.5 uncertain dispatch survives resume; explicit settle recorded

def test_uncertain_dispatch_survives_resume_and_settles_explicitly(model_setup,
                                                                   tmp_path):
    transport = synthetic_transport([RuntimeError('connection lost after dispatch')])
    result = run_model(model_setup, tmp_path, 'crash-run', transport)
    assert result['status'] == 'stopped-with-unresolved-work'
    assert result['reason'] == 'dispatch-uncertain'
    root = tmp_path / 'crash-run'
    assert transport.count['n'] == 1
    assert not (root / 'manifest.json').exists()  # durable ledger preserved instead
    ledger = BudgetLedger.open(root / 'budget-state.json')
    assert [a['state'] for a in ledger.attempts] == ['dispatch-uncertain']
    assert ledger.available == 100 - 70  # reservation stays encumbered
    with pytest.raises(ValueError):
        ledger.reserve(request_key='another-key', payload_sha256='a' * 64,
                       maximum_charge=40)

    resumed = resume_run(root)
    assert resumed['status'] == 'stopped-with-unresolved-work'
    assert resumed['reason'] == 'dispatch-uncertain'
    assert resumed['provider_calls'] == 0
    assert resumed['unresolved_attempts'] == [ledger.attempts[0]['id']]
    assert transport.count['n'] == 1  # no implicit retry on resume

    # explicit, recorded settle (e.g. after provider status lookup); a
    # duplicate receipt cannot settle twice
    receipt = {'receipt_id': 'receipt-manual-reconcile-1',
               'attempt_id': ledger.attempts[0]['id'],
               'charge': 70, 'outcome': 'completed'}
    ledger.settle(receipt)
    ledger.settle(dict(receipt))
    reopened = BudgetLedger.open(root / 'budget-state.json')
    assert [a['state'] for a in reopened.attempts] == ['completed']
    assert len(reopened.receipts) == 1
    assert reopened.available == 100 - 70
    assert resume_run(root)['unresolved_attempts'] == []
