# Purpose: Run one provider attempt behind the durable budget boundary.
# Responsibilities: Reserve one bounded attempt and persist dispatch uncertainty
#   before invoking an adapter; settle only when the adapter returns a receipt.
# Rationale: A process loss or adapter exception after dispatch cannot establish
#   whether work was performed, so the same request must not be retried here.
import hashlib


def dispatch(ledger, *, request_key, payload, maximum_charge, provider):
    """Invoke once after durable reservation and uncertainty recording.

    The injected provider receives the stable request key and exact payload. It
    returns a receipt containing receipt_id, attempt_id, charge and outcome.
    Exceptions leave the full reservation uncertain for explicit reconciliation.
    """
    if not isinstance(payload, bytes):
        raise ValueError('provider-payload-must-be-bytes')
    policy = ledger.state.get('policy')
    if policy is not None and len(payload) > policy['max_request_bytes']:
        raise ValueError('request-limit-exceeded')
    attempt = ledger.reserve(request_key=request_key,
                             payload_sha256=hashlib.sha256(payload).hexdigest(),
                             maximum_charge=maximum_charge)
    ledger.mark_dispatch_uncertain(attempt['id'])
    response = provider(request_key, payload)
    if policy is not None:
        if (not isinstance(response, tuple) or len(response) != 2
                or not isinstance(response[0], bytes)):
            raise ValueError('provider-output-must-be-bytes-with-receipt')
        output, receipt = response
        if len(output) > policy['max_output_bytes']:
            raise ValueError('output-limit-exceeded')
    else:
        receipt = response
    if not isinstance(receipt, dict) or receipt.get('attempt_id') != attempt['id']:
        raise ValueError('provider-receipt-attempt-mismatch')
    ledger.settle(receipt)
    return receipt
