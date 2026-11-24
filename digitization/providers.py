# Purpose: Run one provider attempt behind the durable budget boundary, and
#   host the model adapter beside the OCR/local route.
# Responsibilities: Reserve one bounded attempt and persist dispatch uncertainty
#   before invoking an adapter; settle only when the adapter returns a receipt.
#   For model calls: pin identity before any dispatch, derive the exact call
#   key, validate output against the declared schema, and record one replayable
#   model run reusing the ledger, artifact and replay machinery unchanged.
# Rationale: A process loss or adapter exception after dispatch cannot establish
#   whether work was performed, so the same request must not be retried here.
#   Model calls add §4 determinism requirements: floating aliases refuse before
#   any request is dispatched, every call-key component is digest-bound, and
#   schema-invalid output settles as a charged-failed attempt that admits
#   nothing into the semantic state.
import hashlib
import os
from pathlib import Path
import re
import tempfile
import time

from dsc03 import validator
from digitization.artifacts import encoded, sha, validate_response
from digitization.budget import BudgetExhausted, BudgetLedger, validate_policy


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


# --- Model adapter (tasks 4.1-4.6, add-iterative-document-digitization §4) ---
#
# Sits beside the per-crop OCR adapter (digitization.crop_ocr.local_provider)
# behind the same dispatch boundary, reusing the durable budget ledger, the
# artifact identity machinery and recorded replay unchanged. No live model
# transport exists in this repository: the transport seam is injected by the
# caller, so the default suite runs synthetic responses only (owner ruling G5,
# 2026-11-24: recorded model I/O is retained locally, never exported).

FLOATING_ALIASES = frozenset({'latest', 'stable', 'nightly', 'unstable',
                              'preview', 'dev', 'edge'})


class FloatingModelAlias(ValueError):
    """Typed refusal: the model identity names a floating alias instead of a
    versioned or dated snapshot. Raised before any reservation or dispatch."""


class ModelSchemaViolation(ValueError):
    """Typed refusal: a model response failed its declared output schema."""


class ModelTransportDisabled(RuntimeError):
    """Typed refusal: this repository enables no live model transport."""


def pinned_model_identity(provider):
    """Validate the model identity pins a snapshot; refuse aliases pre-dispatch.

    A provider that exposes no revision identifier is allowed but recorded
    unavailable (`revision_available` False): fresh outputs are never claimed
    deterministic from that alone (Fresh inference variability).
    """
    if (not isinstance(provider, dict) or not isinstance(provider.get('id'), str)
            or not provider['id']):
        raise FloatingModelAlias('model provider must pin a nonempty id')
    model = provider.get('model', {'id': provider['id'], 'revision': None})
    if (not isinstance(model, dict) or not isinstance(model.get('id'), str)
            or not model['id']):
        raise FloatingModelAlias('model identity must pin a nonempty model id')
    revision = model.get('revision')
    if revision is not None:
        if not isinstance(revision, str) or not revision:
            raise FloatingModelAlias(
                'model revision must be a nonempty snapshot identifier')
        if revision.strip().lower() in FLOATING_ALIASES:
            raise FloatingModelAlias(f'floating model alias refused: {revision!r}')
        return {'id': model['id'], 'revision': revision, 'revision_available': True}
    return {'id': model['id'], 'revision': None, 'revision_available': False}


def _component_digest(value):
    """Digest one call-key component: bytes, text or structured value."""
    if isinstance(value, bytes):
        return sha(value)
    if isinstance(value, str):
        return sha(value.encode('utf-8'))
    return sha(encoded(value))


def model_call_key(*, model_id, snapshot, template, rendered_input, schema, decoding):
    """Exact model call key: SHA256 over the canonical encoding of model id,
    snapshot, prompt-template digest, rendered-input digest, output-schema
    digest and decoding parameters. Changing any component changes the key.
    """
    if not isinstance(model_id, str) or not model_id:
        raise ValueError('model-call-key requires a pinned model id')
    identity = {'version': '1', 'model_id': model_id, 'snapshot': snapshot,
                'template_sha256': _component_digest(template),
                'rendered_input_sha256': _component_digest(rendered_input),
                'schema_sha256': _component_digest(schema),
                'decoding': decoding}
    return sha(encoded(identity))


def validate_model_output(raw, schema):
    """Validate raw model bytes against the declared output schema and return
    the normalized output. Unknown schemas fail closed; violations are typed.
    """
    if schema != 'recorded-recognition-v1':
        raise ModelSchemaViolation(f'unknown model output schema: {schema!r}')
    try:
        return validate_response(validator.loads(raw.decode('utf-8')))
    except (UnicodeDecodeError, ValueError, validator.Duplicate) as error:
        raise ModelSchemaViolation(
            f'model output rejected by {schema}: {error}') from error


def model_provider(ledger, *, identity, schema, transport, sink=None):
    """Dispatch-compatible model adapter beside the OCR adapter.

    Construction pins the model identity (floating aliases refuse before any
    reservation exists). The transport is injected: it receives the stable
    request key and exact payload bytes and returns {'raw': bytes, 'charge':
    int}. Every response is schema-validated before admission; invalid output
    settles the attempt charged-failed with its charge retained, the raw
    response handed back for evidence, and nothing admitted. When `sink` is a
    dict it receives per request key {'raw', 'normalized', 'detail', 'receipt'}.
    """
    pinned = pinned_model_identity(identity)

    def provider(request_key, payload):
        attempt = next((item for item in ledger.attempts
                        if item['request_key'] == request_key), None)
        if attempt is None:
            raise ValueError('unknown-request-key')
        response = transport(request_key, payload)
        if (not isinstance(response, dict) or not isinstance(response.get('raw'), bytes)
                or type(response.get('charge')) is not int or response['charge'] < 0):
            raise ModelSchemaViolation(
                'model transport must return raw bytes and a nonnegative charge')
        raw = response['raw']
        receipt_id = 'receipt-' + sha(request_key.encode('utf-8'))[:24]
        try:
            normalized = validate_model_output(raw, schema)
        except ModelSchemaViolation as error:
            receipt = {'receipt_id': receipt_id + '-rejected',
                       'attempt_id': attempt['id'], 'charge': response['charge'],
                       'outcome': 'charged-failed'}
            if sink is not None:
                sink[request_key] = {'raw': raw, 'normalized': None,
                                     'detail': str(error), 'receipt': dict(receipt)}
            return raw, receipt
        receipt = {'receipt_id': receipt_id, 'attempt_id': attempt['id'],
                   'charge': response['charge'], 'outcome': 'completed'}
        if sink is not None:
            sink[request_key] = {'raw': raw, 'normalized': normalized,
                                 'detail': '', 'receipt': dict(receipt)}
        return encoded(normalized), receipt
    return provider


def _preflight_model_run(source, config, pages):
    """Structural validation for a recorded model run; no dispatch yet."""
    from digitization.pipeline import InputError, digest, json_bytes
    from digitization.render import page_frames
    try:
        if config.get('version') != '1' or config.get('source_sha256') != digest(source):
            raise ValueError('unsupported configuration or source hash mismatch')
        provider = config.get('provider')
        if not isinstance(provider, dict) or provider.get('kind') != 'model':
            raise ValueError('model route requires an identified model provider')
        if (not isinstance(provider['id'], str) or not provider['id']
                or not isinstance(provider.get('version'), str) or not provider['version']):
            raise ValueError('providers must pin id and version')
        if 'budget' not in config:
            raise ValueError('model route requires a durable budget policy')
        config['budget'] = validate_policy(config['budget'])
        dpi = config['render']['dpi']
        if type(dpi) is not int or not 36 <= dpi <= 300:
            raise ValueError('DPI must be an integer between 36 and 300')
        frames = page_frames(source, pages)
        for page in pages:
            detections = config['pages'][str(page)]['detections']
            if not isinstance(detections, list) or not detections:
                raise ValueError('recorded detections required for model regions')
            for detection in detections:
                local_id, kind, box = detection['id'], detection['kind'], detection['bbox']
                if not isinstance(local_id, str) or not re.fullmatch(
                        r'[A-Za-z0-9][A-Za-z0-9_.:-]*', local_id):
                    raise ValueError('invalid local region identity')
                if not isinstance(kind, str) or not kind:
                    raise ValueError('missing attributed region kind')
                if (not isinstance(box, list) or len(box) != 4
                        or any(type(v) is not int or v < 0 for v in box)):
                    raise ValueError('boxes must use nonnegative integer page points')
                x, y, width, height = box
                if (not width or not height or x + width > frames[page]['width']
                        or y + height > frames[page]['height']):
                    raise ValueError('region outside page frame')
        json_bytes(config)  # Unicode and finite-number validation before any I/O.
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            validator.Duplicate) as error:
        raise InputError(str(error)) from error


def record_model_run(job, output, *, template, schema, decoding, transport=None,
                     maximum_charge=0):
    """Record one model-recognized run: pinned identity, exact call key,
    durable dispatch, schema-gated admission, replayable artifacts.

    job = (source_path, pages, config_path); the configuration pins a model
    provider (kind 'model'), a durable budget policy and the region proposals.
    The manifest is written in the recorded conventions, so replay and inspect
    reuse their existing machinery unchanged; replay of the finished run
    performs zero provider calls and a deleted response blob yields
    incomplete-artifacts. A transport crash after dispatch preserves the
    durable ledger as a dispatch-uncertain stop; nothing is retried here.
    """
    from digitization.pipeline import InputError, digest, json_bytes
    from digitization.render import render_page
    from digitization.structure import collect
    source_path, pages, config_path = job
    try:
        source = Path(source_path).read_bytes()
        config = validator.loads(Path(config_path).read_text(encoding='utf-8'))
    except (OSError, ValueError, validator.Duplicate) as error:
        raise InputError(str(error)) from error
    if not isinstance(config, dict):
        raise InputError('model configuration must be a JSON object')
    _preflight_model_run(source, config, pages)
    # §4.1: identity pinning precedes every reservation, dispatch and render.
    pinned = pinned_model_identity(config['provider'])
    if transport is None:
        raise ModelTransportDisabled(
            'model-transport-disabled: this repository has no live model route')
    if type(maximum_charge) is not int or maximum_charge < 0:
        raise InputError('maximum charge must be a nonnegative integer')
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise InputError('output directory already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='.digitization-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        policy = config['budget']
        ledger = BudgetLedger.create(stage / 'budget-state.json',
                                     cap=policy['max_estimated_cost_microunits'],
                                     currency=policy['currency'], policy=policy)
        artifacts = {}
        renders, regions, mappings = {}, [], []
        unresolved, trace, history = [], [], []
        operations, failed, recorded = {}, [], {}

        def save(name, data):
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            reference = {'path': name, 'sha256': digest(data)}
            artifacts[name] = reference
            return reference

        def blob(data):
            return save('artifacts/' + digest(data), data)

        adapter = model_provider(ledger, identity=config['provider'], schema=schema,
                                 transport=transport, sink=recorded)
        source_ref = save('source.pdf', source)
        config_ref = save('config.json', Path(config_path).read_bytes())
        geometry = {'kind': 'geometry', 'version': '1', 'frames': [
            {'name': f'page-{p}-pt', 'unit': 'pt', 'origin': 'bottom-left',
             'axes': 'x-right-y-up', 'scale': [1, 1], 'rotation': 0,
             'crop': None, 'source_scope': f'page:{p}'} for p in pages]}
        geometry_ref = blob(json_bytes(geometry))
        selector_ref = blob(json_bytes({'kind': 'selector', 'version': '1',
                                        'selector_kinds': ['pdf-area'],
                                        'offset_unit': 'unicode-scalar-values',
                                        'endpoints': 'half-open'}))
        descriptor = {
            'version': '0.3', 'id': 'digitization-' + digest(source)[:16],
            'source': {'format': 'application/pdf', 'sha256': digest(source),
                       'locator': 'source.pdf'},
            'views': [{'id': 'physical', 'kind': 'physical', 'root': 'document'},
                      {'id': 'logical', 'kind': 'logical', 'root': 'logical-root'}],
            'regions': [{'id': 'document', 'view_id': 'physical', 'kind': 'document'},
                        {'id': 'logical-root', 'view_id': 'logical', 'kind': 'document'}],
            'contents': [], 'relations': [], 'annotations': [], 'evidence': [],
            'selectors': [], 'interpretations': [], 'coverage': [], 'vocabularies': [],
            'profiles': [dict(id='geometry', kind='geometry', uri=geometry_ref['path'],
                              version='1', sha256=geometry_ref['sha256']),
                         dict(id='selector', kind='selector', uri=selector_ref['path'],
                              version='1', sha256=selector_ref['sha256'])],
        }
        provider_ref = config['provider']
        search = ''
        preloop_attempts = len(ledger.attempts)
        try:
            for page in pages:
                png, render = render_page(source, page, config['render']['dpi'])
                render_ref = blob(png)
                renders[str(page)] = {**render_ref, **render}
                trace.append({'operation': 'render', 'page': page,
                              'artifact': render_ref['sha256']})
                page_id, image_id = f'page-{page}', f'image-{page}'
                descriptor['regions'].append({'id': page_id, 'view_id': 'physical',
                                              'kind': 'page'})
                descriptor['relations'].extend([
                    {'id': f'contains-{page_id}', 'kind': 'contains',
                     'from': 'document', 'to': page_id},
                    {'id': f'has-{image_id}', 'kind': 'has-content',
                     'from': page_id, 'to': image_id}])
                descriptor['contents'].append({'id': image_id, 'kind': 'image',
                                               'value': render_ref['path']})
                descriptor['evidence'].append({
                    'id': f'evidence-{image_id}', 'origin': 'source',
                    'source_ref': f'sha256:{digest(source)}#page:{page}',
                    'content_ids': [image_id], 'selector_ids': []})
                detections = config['pages'][str(page)]['detections']
                detection_ref = blob(json_bytes(detections))
                trace.append({'operation': 'detect', 'page': page,
                              'artifact': detection_ref['sha256'], 'mode': 'recorded'})
                history.append({'operation': 'detect',
                                'revision': f'page-{page}-regions-0', 'parents': [],
                                'artifact': detection_ref['sha256'], 'mode': 'recorded'})
                for detection in detections:
                    local_id = detection['id']
                    rid = f'{page_id}-{local_id}'
                    sid, cid = f'sel-{rid}', f'text-{rid}'
                    # §4.2: the key digests every component of the call.
                    request_key = model_call_key(
                        model_id=pinned['id'], snapshot=pinned['revision'],
                        template=template, rendered_input=png, schema=schema,
                        decoding=decoding)
                    request = {'version': '1', 'operation': 'model-recognition',
                               'model': pinned,
                               'model_revision_available': pinned['revision_available'],
                               'template_sha256': _component_digest(template),
                               'rendered_input_sha256': digest(png),
                               'schema_sha256': _component_digest(schema),
                               'decoding': decoding, 'region_id': rid,
                               'region_kind': detection['kind'],
                               'inputs': [digest(source), render_ref['sha256']],
                               'transforms': {'page': page, 'bbox': detection['bbox'],
                                              'render': render}}
                    receipt = dispatch(ledger, request_key=request_key, payload=png,
                                       maximum_charge=maximum_charge, provider=adapter)
                    outcome = recorded[request_key]
                    if receipt['outcome'] != 'completed':
                        # §4.3: schema-invalid output settles charged-failed; the
                        # raw response is retained as evidence, nothing admitted.
                        record = {'attempt_id': receipt['attempt_id'],
                                  'request_key': request_key,
                                  'reason': 'model-output-schema-invalid',
                                  'detail': outcome['detail'],
                                  'charge': receipt['charge'],
                                  'raw_response': outcome['raw'].decode('utf-8', 'replace')}
                        failed.append({**record,
                                       'artifact': blob(json_bytes(record))})
                        unresolved.append({'region_id': rid,
                                           'reason': 'model-output-schema-invalid'})
                        trace.append({'operation': 'recognize', 'region_id': rid,
                                      'mode': 'model', 'status': 'charged-failed'})
                        history.append({'operation': 'recognize', 'region_id': rid,
                                        'mode': 'model', 'status': 'charged-failed',
                                        'attempt': receipt['attempt_id']})
                        continue
                    normalized = outcome['normalized']
                    response_bytes = encoded(normalized)
                    response_ref = save('blobs/' + sha(response_bytes), response_bytes)
                    attempt_id = receipt['attempt_id']
                    operations[rid] = {
                        'request': request, 'operation_key': request_key,
                        'attempts': [{'version': '1', 'id': attempt_id,
                                      'output': {'path': response_ref['path'],
                                                 'sha256': response_ref['sha256']},
                                      'state': 'completed',
                                      'charge': receipt['charge'],
                                      'receipt_id': receipt['receipt_id']}],
                        'selected_attempt': attempt_id, 'cache_hit': False,
                        'fresh_determinism': 'not-claimed'}
                    box = detection['bbox']
                    geometry_box = {'x': box[0],
                                    'y': int(render['height_pt'] - box[1] - box[3]),
                                    'width': box[2], 'height': box[3]}
                    descriptor['regions'].append({
                        'id': rid, 'kind': detection['kind'], 'view_id': 'physical',
                        'geometry': {'profile_id': 'geometry',
                                     'space': f'page-{page}-pt', **geometry_box}})
                    descriptor['selectors'].append({
                        'id': sid, 'kind': 'pdf-area', 'profile_id': 'selector',
                        'source_sha256': digest(source), 'target': rid,
                        'locator': f'page:{page} rect:' + ','.join(map(str, box))})
                    raw = normalized['raw_text']
                    search_text = ' '.join(raw.split())
                    descriptor['contents'].append({'id': cid, 'kind': 'text',
                                                   'value': raw})
                    descriptor['relations'].extend([
                        {'id': 'contains-' + rid, 'kind': 'contains',
                         'from': page_id, 'to': rid},
                        {'id': 'has-' + cid, 'kind': 'has-content', 'from': rid,
                         'to': cid},
                        {'id': 'derived-' + rid, 'kind': 'derived-from',
                         'from': 'evidence-' + rid, 'to': f'evidence-{image_id}'}])
                    descriptor['evidence'].append({
                        'id': 'evidence-' + rid, 'origin': 'extracted',
                        'source_ref': f'sha256:{digest(source)}#page:{page}',
                        'content_ids': [cid], 'selector_ids': [sid],
                        'transform': {'id': 'model-recognition', 'version': '1',
                                      'config_sha256': request_key,
                                      'dependencies': [
                                          f"model:{provider_ref['id']}@{provider_ref['version']}",
                                          render['renderer']],
                                      'inputs': [image_id], 'outputs': [cid]}})
                    revision = {'operation': 'recognize',
                                'revision': 'recognized-' + rid,
                                'parents': [f'page-{page}-regions-0'],
                                'region_id': rid,
                                'artifact': response_ref['sha256'], 'mode': 'model',
                                'operation_key': request_key,
                                'selected_attempt': attempt_id, 'cache_hit': False}
                    history.append(revision)
                    trace.append(revision)
                    regions.append({'region_id': rid, 'local_id': local_id,
                                    'page': page, 'bbox': box,
                                    'frame': f'page-{page}-pt', 'selector_id': sid,
                                    'raw_text': raw, 'layout_text': raw,
                                    'search_text': search_text,
                                    'producer': provider_ref,
                                    'kind': detection['kind'], 'alternatives': [],
                                    'revision': revision['revision'],
                                    'operation_key': request_key,
                                    'selected_attempt': attempt_id})
                    mappings.append({'region_id': rid, 'page': page,
                                     'selector_id': sid, 'start': len(search),
                                     'end': len(search) + len(search_text)})
                    search += search_text + '\n'
                    unresolved.extend({'region_id': rid, 'reason': reason}
                                      for reason in normalized['unresolved'])
        except BudgetExhausted as error:
            # Pre-dispatch refusal at reserve: no uncertainty, stop durably.
            os.rename(stage, output)
            return {'status': 'stopped-with-unresolved-work',
                    'reason': error.reason, 'detail': str(error),
                    'provider_calls': len(recorded), 'run': str(output),
                    'attempts_dispatched': len(ledger.attempts)}
        except Exception as error:
            # Transport loss after the uncertainty marker was persisted: the
            # whole reservation stays encumbered for explicit reconciliation.
            if len(ledger.attempts) == preloop_attempts:
                raise  # no attempt was reserved: a pre-I/O refusal, not uncertainty
            uncertain = [a['id'] for a in ledger.attempts
                         if a['state'] in ('reserved', 'dispatch-uncertain')]
            os.rename(stage, output)
            return {'status': 'stopped-with-unresolved-work',
                    'reason': 'dispatch-uncertain', 'detail': str(error),
                    'provider_calls': len(recorded), 'run': str(output),
                    'attempts_dispatched': len(ledger.attempts),
                    'unresolved_attempts': uncertain}
        structure, structural_unresolved = collect(config, pages, regions, mappings,
                                                   digest(source))
        unresolved.extend(structural_unresolved)
        structure_ref = save('structure.json', json_bytes(structure))
        errors = validator.validate(descriptor)
        if errors:
            raise ValueError('export violates DSC: ' + ', '.join(errors))
        descriptor_ref = save('descriptor.json', json_bytes(descriptor))
        save('search.txt', search.encode('utf-8'))
        save('search-map.json', json_bytes(mappings))
        save('regions.json', json_bytes(regions))
        save('unresolved.json', json_bytes({'regions': unresolved,
                                            'coverage': 'unexamined-outside-recorded-regions'}))
        save('history.json', json_bytes(history))
        if failed:
            save('failed-attempts.json', json_bytes(failed))
        trace.append({'operation': 'export', 'artifact': descriptor_ref['sha256']})
        save('trace.jsonl', b''.join(json_bytes(event) for event in trace))
        usage = {'mode': 'model', 'provider_calls': len(ledger.attempts),
                 'estimated_charge_microunits': ledger.settled,
                 'attempts': [attempt['id'] for attempt in ledger.attempts],
                 'runtime_seconds': time.monotonic() - started}
        save('ledger.json', json_bytes(usage))
        save('operations.json', json_bytes(operations))
        status = 'stopped-with-unresolved-work' if unresolved else 'completed'
        if failed:
            reason = 'model-output-rejected'
        elif unresolved:
            reason = 'model-unresolved'
        else:
            reason = 'model-inputs-consumed'
        manifest = {'version': '1', 'mode': 'recorded', 'status': status,
                    'reason': reason, 'source': source_ref, 'configuration': config_ref,
                    'pages': pages, 'descriptor': descriptor_ref, 'renders': renders,
                    'artifacts': artifacts, 'usage': usage, 'operations': operations,
                    'structure': structure_ref}
        (stage / 'manifest.json').write_bytes(json_bytes(manifest))
        os.rename(stage, output)
    return {'manifest': str(output / 'manifest.json'), 'status': status,
            'reason': reason, 'provider_calls': usage['provider_calls']}
