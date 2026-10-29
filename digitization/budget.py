# Purpose: Persist provider attempt reservations and settlement evidence.
# Responsibilities: Atomically account for bounded charges and prevent duplicate
#   settlement or budget reuse after an interrupted provider call.
# Rationale: sunset-rmx.7 requires reservations and consumed attempts to survive
#   process crashes before any provider dispatch can be safely retried.
import json
import fcntl
import os
from pathlib import Path
import re
import tempfile
from contextlib import contextmanager


@contextmanager
def _locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / (path.name + '.lock')).open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class BudgetLedger:
    """A small atomically replaced ledger; callers persist uncertainty before I/O."""

    def __init__(self, path, state):
        self.path = Path(path)
        self.state = state

    @classmethod
    def create(cls, path, *, cap, currency):
        path = Path(path)
        if type(cap) is not int or cap < 0 or not isinstance(currency, str) or not currency:
            raise ValueError('invalid-budget-configuration')
        ledger = cls(path, {'version': '1', 'cap': cap, 'currency': currency,
                            'attempts': [], 'receipts': []})
        with _locked(path):
            if path.exists():
                raise ValueError('budget-ledger-already-exists')
            ledger._save()
        return ledger

    @classmethod
    def open(cls, path):
        path = Path(path)
        state = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(state, dict) or set(state) !=
                {'version', 'cap', 'currency', 'attempts', 'receipts'}
                or state['version'] != '1' or type(state['cap']) is not int
                or state['cap'] < 0 or not isinstance(state['currency'], str)
                or not state['currency'] or not isinstance(state['attempts'], list)
                or not isinstance(state['receipts'], list)):
            raise ValueError('invalid-budget-ledger')
        if not cls._valid_records(state):
            raise ValueError('invalid-budget-ledger-records')
        return cls(path, state)

    @staticmethod
    def _valid_records(state):
        attempts, receipts = state['attempts'], state['receipts']
        if any(not isinstance(item, dict) or set(item) !=
               {'id', 'request_key', 'payload_sha256', 'maximum_charge', 'state'}
               or not isinstance(item['id'], str) or not item['id']
               or not isinstance(item['request_key'], str) or not item['request_key']
               or not isinstance(item['payload_sha256'], str)
               or not re.fullmatch(r'[0-9a-f]{64}', item['payload_sha256'])
               or type(item['maximum_charge']) is not int or item['maximum_charge'] < 0
               or item['state'] not in ('reserved', 'dispatch-uncertain', 'completed', 'charged-failed')
               for item in attempts):
            return False
        if len({item['id'] for item in attempts}) != len(attempts):
            return False
        if any(not isinstance(item, dict) or set(item) !=
               {'receipt_id', 'attempt_id', 'charge', 'outcome'}
               or not isinstance(item['receipt_id'], str) or not item['receipt_id']
               or not isinstance(item['attempt_id'], str)
               or type(item['charge']) is not int or item['charge'] < 0
               or item['outcome'] not in ('completed', 'charged-failed')
               for item in receipts):
            return False
        return (len({item['receipt_id'] for item in receipts}) == len(receipts)
                and len({item['attempt_id'] for item in receipts}) == len(receipts)
                and all(any(attempt['id'] == receipt['attempt_id']
                       and attempt['state'] == receipt['outcome']
                       and receipt['charge'] <= attempt['maximum_charge'] for attempt in attempts)
                   for receipt in receipts)
                and all((attempt['state'] in ('completed', 'charged-failed')) ==
                        (attempt['id'] in {item['attempt_id'] for item in receipts})
                        for attempt in attempts))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(self.state, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False, allow_nan=False) + '\n').encode()
        fd, temporary = tempfile.mkstemp(prefix='.budget-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @property
    def attempts(self):
        return self.state['attempts']

    @property
    def receipts(self):
        return self.state['receipts']

    @property
    def settled(self):
        return sum(receipt['charge'] for receipt in self.receipts)

    @property
    def outstanding(self):
        return sum(attempt['maximum_charge'] for attempt in self.attempts
                   if attempt['state'] in ('reserved', 'dispatch-uncertain'))

    @property
    def available(self):
        return self.state['cap'] - self.settled - self.outstanding

    def reserve(self, *, request_key, payload_sha256, maximum_charge):
        if maximum_charge is None:
            raise ValueError('unbounded-cost')
        if (not isinstance(request_key, str) or not request_key
                or not isinstance(payload_sha256, str)
                or not re.fullmatch(r'[0-9a-f]{64}', payload_sha256)
                or type(maximum_charge) is not int or maximum_charge < 0):
            raise ValueError('invalid-attempt-reservation')
        with _locked(self.path):
            self.state = self.open(self.path).state
            for attempt in self.attempts:
                if attempt['request_key'] == request_key:
                    if attempt['payload_sha256'] != payload_sha256:
                        raise ValueError('request-key-payload-mismatch')
                    raise ValueError('request-key-already-reserved')
            if maximum_charge > self.available:
                raise ValueError('budget-exceeded')
            attempt = {'id': f"attempt-{len(self.attempts) + 1}", 'request_key': request_key,
                       'payload_sha256': payload_sha256, 'maximum_charge': maximum_charge,
                       'state': 'reserved'}
            self.state['attempts'].append(attempt)
            self._save()
            return dict(attempt)

    def mark_dispatch_uncertain(self, attempt_id):
        with _locked(self.path):
            self.state = self.open(self.path).state
            attempt = self._attempt(attempt_id)
            if attempt['state'] != 'reserved':
                raise ValueError('attempt-not-reserved')
            attempt['state'] = 'dispatch-uncertain'
            self._save()

    def settle(self, receipt):
        if (not isinstance(receipt, dict) or set(receipt) !=
                {'receipt_id', 'attempt_id', 'charge', 'outcome'}
                or not isinstance(receipt['receipt_id'], str) or not receipt['receipt_id']
                or type(receipt['charge']) is not int or receipt['charge'] < 0
                or receipt['outcome'] not in ('completed', 'charged-failed')):
            raise ValueError('invalid-settlement-receipt')
        with _locked(self.path):
            self.state = self.open(self.path).state
            for previous in self.receipts:
                if previous['receipt_id'] == receipt['receipt_id']:
                    if previous != receipt:
                        raise ValueError('receipt-id-conflict')
                    return
            attempt = self._attempt(receipt['attempt_id'])
            if attempt['state'] not in ('reserved', 'dispatch-uncertain'):
                raise ValueError('attempt-already-settled')
            if receipt['charge'] > attempt['maximum_charge']:
                raise ValueError('charge-exceeds-reservation')
            attempt['state'] = receipt['outcome']
            self.state['receipts'].append(dict(receipt))
            self._save()

    def _attempt(self, attempt_id):
        for attempt in self.attempts:
            if attempt['id'] == attempt_id:
                return attempt
        raise ValueError('unknown-attempt')
