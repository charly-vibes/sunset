# Purpose: Verify durable reservation accounting and safe public run resume.
# Responsibilities: Exercise atomic attempt state transitions and fresh-process
#   recovery without network calls, duplicate dispatch or settlement.
# Rationale: sunset-rmx.7 requires uncertain requests to remain encumbered across
#   process restarts until provider evidence resolves their outcome.
import json
from pathlib import Path
import subprocess
import sys

import pytest
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def test_resume_missing_run_is_invalid_and_does_not_create_a_run(tmp_path):
    missing = tmp_path / 'missing'
    code, result = cli('resume', '--run', missing)
    assert code == 3
    assert result == {'status': 'invalid-input', 'reason': 'invalid-input',
                      'detail': 'run directory does not exist', 'provider_calls': 0}
    assert not missing.exists()


def test_budget_ledger_retains_uncertain_reservation_and_refuses_new_attempt(tmp_path):
    from digitization.budget import BudgetLedger

    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD')
    attempt = ledger.reserve(request_key='request-1', payload_sha256='a' * 64, maximum_charge=70)
    ledger.mark_dispatch_uncertain(attempt['id'])
    with pytest.raises(ValueError, match='budget-exceeded'):
        ledger.reserve(request_key='request-2', payload_sha256='b' * 64, maximum_charge=40)
    reopened = BudgetLedger.open(tmp_path / 'ledger.json')
    assert reopened.available == 30
    assert reopened.attempts[0]['state'] == 'dispatch-uncertain'


def test_budget_ledger_refuses_attempt_without_a_safe_charge_bound(tmp_path):
    from digitization.budget import BudgetLedger

    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD')
    with pytest.raises(ValueError, match='unbounded-cost'):
        ledger.reserve(request_key='request-1', payload_sha256='a' * 64, maximum_charge=None)


def test_settlement_releases_reservation_once_even_for_duplicate_receipt(tmp_path):
    from digitization.budget import BudgetLedger

    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD')
    attempt = ledger.reserve(request_key='request-1', payload_sha256='a' * 64, maximum_charge=70)
    receipt = {'receipt_id': 'receipt-1', 'attempt_id': attempt['id'],
               'charge': 60, 'outcome': 'completed'}
    ledger.settle(receipt)
    ledger.settle(receipt)
    reopened = BudgetLedger.open(tmp_path / 'ledger.json')
    assert reopened.available == 40
    assert reopened.settled == 60
    assert len(reopened.receipts) == 1


def test_charged_failure_settles_usage_and_attempt_once(tmp_path):
    from digitization.budget import BudgetLedger

    ledger = BudgetLedger.create(tmp_path / 'ledger.json', cap=100, currency='USD')
    attempt = ledger.reserve(request_key='request-1', payload_sha256='a' * 64, maximum_charge=70)
    receipt = {'receipt_id': 'receipt-1', 'attempt_id': attempt['id'],
               'charge': 12, 'outcome': 'charged-failed'}
    ledger.settle(receipt)
    reopened = BudgetLedger.open(tmp_path / 'ledger.json')
    assert reopened.attempts[0]['state'] == 'charged-failed'
    assert reopened.settled == 12
    assert reopened.available == 88


def test_fresh_process_resume_retains_run_and_stops_uncertain_attempt(tmp_path):
    from digitization.budget import BudgetLedger

    source = tmp_path / 'source.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Fixture')
        pdf.save(source)
    import hashlib
    config = {'version': '1', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'provider': {'kind': 'recorded', 'id': 'fixture', 'version': '1'},
              'render': {'dpi': 72},
              'pages': {'1': {'detections': [{'id': 'r1', 'kind': 'poem', 'bbox': [20, 60, 100, 50]}],
                              'recognitions': {'r1': {'raw_text': 'line', 'unresolved': []}}}}}
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(config))
    run = tmp_path / 'run'
    code, result = cli('run', '--source', source, '--pages', '1', '--config', config_path, '--output', run)
    assert code == 0 and result['status'] == 'completed'
    ledger = BudgetLedger.create(run / 'budget-state.json', cap=100, currency='USD')
    attempt = ledger.reserve(request_key='request-1', payload_sha256='a' * 64, maximum_charge=70)
    ledger.mark_dispatch_uncertain(attempt['id'])
    retained = {name: (run / name).read_bytes() for name in
                ('manifest.json', 'history.json', 'ledger.json', 'descriptor.json')}
    state_before = (run / 'budget-state.json').read_bytes()

    code, resumed = cli('resume', '--run', run)

    assert code == 2
    assert resumed == {'manifest': str(run / 'manifest.json'),
                       'status': 'stopped-with-unresolved-work',
                       'reason': 'dispatch-uncertain', 'provider_calls': 0,
                       'unresolved_attempts': ['attempt-1']}
    assert {name: (run / name).read_bytes() for name in retained} == retained
    assert (run / 'budget-state.json').read_bytes() == state_before
    assert {p.name for p in tmp_path.iterdir()} == {'source.pdf', 'config.json', 'run'}
