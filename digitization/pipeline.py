# Purpose: Build source-linked runs with verified recorded-recognition reuse.
# Responsibilities: Preflight all inputs, render pages before consuming recorded
#   detections/recognitions, pin selected attempts and export valid DSC atomically.
# Rationale: sunset-rmx.17 preserves selected attempts across immutable revisions
#   only when the complete recognition request is unchanged; fresh remains explicit.
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import unicodedata

from dsc03 import validator
from digitization import __version__
from digitization.artifacts import OperationCache, CacheIntegrityError, validate_response
from digitization.render import page_frames, render_page
from digitization.structure import collect


class InputError(ValueError):
    """A refused run that has not dispatched any provider request."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def _preflight(source_path, pages, config_path, output):
    try:
        source = Path(source_path).read_bytes()
        config_raw = Path(config_path).read_bytes()
        config = validator.loads(config_raw.decode('utf-8'))
        if Path(output).exists():
            raise ValueError('output directory already exists')
        if config['version'] != '1' or config['source_sha256'] != digest(source):
            raise ValueError('unsupported configuration or source hash mismatch')
        provider = config['provider']
        if (provider['kind'] != 'recorded' or not isinstance(provider['id'], str)
                or not provider['id'] or not isinstance(provider['version'], str) or not provider['version']):
            raise ValueError('only identified recorded providers are enabled')
        model = provider.get('model', {'id': provider['id'], 'revision': None})
        if (not isinstance(model, dict) or not isinstance(model.get('id'), str) or not model['id']
                or model.get('revision') is not None and not isinstance(model['revision'], str)):
            raise ValueError('invalid model identity/revision availability')
        if not isinstance(config.get('recognition', {}), dict):
            raise ValueError('recognition request parameters must be an object')
        dpi = config['render']['dpi']
        if type(dpi) is not int or not 36 <= dpi <= 300:
            raise ValueError('DPI must be an integer between 36 and 300')
        frames = page_frames(source, pages)
        for page in pages:
            observations = config['pages'][str(page)]
            detections, recognitions = observations['detections'], observations['recognitions']
            if not isinstance(detections, list) or not detections or not isinstance(recognitions, dict):
                raise ValueError('recorded detections and recognitions required')
            ids = []
            for detection in detections:
                local_id, kind, box = detection['id'], detection['kind'], detection['bbox']
                if not isinstance(local_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', local_id):
                    raise ValueError('invalid local region identity')
                if not isinstance(kind, str) or not kind:
                    raise ValueError('missing attributed region kind')
                if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int or v < 0 for v in box):
                    raise ValueError('boxes must use nonnegative integer page points')
                x, y, width, height = box
                if not width or not height or x + width > frames[page]['width'] or y + height > frames[page]['height']:
                    raise ValueError('region outside page frame')
                recognition = recognitions[local_id]
                validate_response(recognition)
                ids.append(local_id)
            overrides = observations.get('recognition_overrides', {})
            if (not isinstance(overrides, dict) or not set(overrides).issubset(ids)
                    or any(not isinstance(value, dict) for value in overrides.values())):
                raise ValueError('recognition overrides must name detected regions')
            if len(set(ids)) != len(ids) or set(ids) != set(recognitions):
                raise ValueError('duplicate region or mismatched recognition identities')
        # Reject invalid Unicode/NaN before rendering or creating any output.
        json_bytes(config)
        return source, config_raw, config
    except (OSError, ValueError, KeyError, TypeError, AttributeError, validator.Duplicate) as error:
        raise InputError(str(error)) from error


def run(source_path, pages, config_path, output, *, cache_dir=None, fresh=(), selections=None):
    _, _, config = _preflight(source_path, pages, config_path, output)
    if 'refinement' in config:
        from digitization.refinement import refine_run
        return refine_run(source_path, pages, config_path, output, cache_dir=cache_dir,
                          fresh=fresh, selections=selections)
    return _run_once(source_path, pages, config_path, output, cache_dir=cache_dir,
                     fresh=fresh, selections=selections)


def _run_once(source_path, pages, config_path, output, *, cache_dir=None, fresh=(), selections=None,
              inherited_operations=None):
    source, config_raw, config = _preflight(source_path, pages, config_path, output)
    output = Path(output).absolute()
    selections = selections or {}
    known_regions = {f"page-{page}-{region['id']}" for page in pages
                     for region in config['pages'][str(page)]['detections']}
    if (not set(fresh).issubset(known_regions) or not set(selections).issubset(known_regions)
            or set(fresh) & set(selections)):
        raise InputError('unknown region or conflicting fresh/selection request')
    if cache_dir is not None and Path(cache_dir).resolve().is_relative_to(output.resolve()):
        raise InputError('shared cache must be outside the new run directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='.digitization-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        artifacts = {}
        cache = OperationCache(cache_dir if cache_dir is not None else Path(temporary) / 'cache')
        operations = {}

        def save(name, data):
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            reference = {'path': name, 'sha256': digest(data)}
            artifacts[name] = reference
            return reference

        def blob(data):
            return save('artifacts/' + digest(data), data)

        source_ref = save('source.pdf', source)
        config_ref = save('config.json', config_raw)
        implementation = {'consumer_version': __version__, 'unicode_version': unicodedata.unidata_version,
                          'modules': {name: digest((Path(__file__).parent / name).read_bytes())
                                      for name in ('pipeline.py', 'artifacts.py', 'render.py')}}
        geometry = {'kind': 'geometry', 'version': '1', 'frames': [
            {'name': f'page-{p}-pt', 'unit': 'pt', 'origin': 'top-left',
             'axes': 'x-right-y-down', 'scale': [1, 1], 'rotation': 0,
             'crop': None, 'source_scope': f'page:{p}'} for p in pages]}
        geometry_ref = blob(json_bytes(geometry))
        selector_ref = blob(json_bytes({'kind': 'selector', 'version': '1',
                                       'selector_kinds': ['pdf-area'],
                                       'offset_unit': 'unicode-scalar-values', 'endpoints': 'half-open'}))
        descriptor = {
            'version': '0.3', 'id': 'digitization-' + digest(source)[:16],
            'source': {'format': 'application/pdf', 'sha256': digest(source), 'locator': 'source.pdf'},
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
        regions, mappings, unresolved, trace, history, renders = [], [], [], [], [], {}
        search = ''
        for page in pages:
            png, render = render_page(source, page, config['render']['dpi'])
            renders[str(page)] = {**blob(png), **render}
            trace.append({'operation': 'render', 'page': page, 'artifact': renders[str(page)]['sha256']})
            page_id, image_id = f'page-{page}', f'image-{page}'
            descriptor['regions'].append({'id': page_id, 'view_id': 'physical', 'kind': 'page'})
            descriptor['relations'].extend([
                {'id': f'contains-{page_id}', 'kind': 'contains', 'from': 'document', 'to': page_id},
                {'id': f'has-{image_id}', 'kind': 'has-content', 'from': page_id, 'to': image_id}])
            descriptor['contents'].append({'id': image_id, 'kind': 'image', 'value': renders[str(page)]['path']})
            descriptor['evidence'].append({'id': f'evidence-{image_id}', 'origin': 'source',
                'source_ref': f'sha256:{digest(source)}#page:{page}', 'content_ids': [image_id], 'selector_ids': []})
            records = config['pages'][str(page)]
            detection_ref = blob(json_bytes(records['detections']))
            trace.append({'operation': 'detect', 'page': page, 'artifact': detection_ref['sha256'], 'mode': 'recorded'})
            history.append({'operation': 'detect', 'revision': f'page-{page}-regions-0',
                            'parents': [], 'artifact': detection_ref['sha256']})
            for detection in records['detections']:
                local_id = detection['id']
                rid, sid, cid = f'{page_id}-{local_id}', f'sel-{page_id}-{local_id}', f'text-{page_id}-{local_id}'
                parameters = {'schema': 'recorded-recognition-v1', 'prompt': '', 'language': 'und',
                              'preprocessing': {}, 'decoding': {}, 'policy': {}}
                parameters.update(config.get('recognition', {}))
                parameters.update(records.get('recognition_overrides', {}).get(local_id, {}))
                provider_identity = dict(config['provider'])
                provider_identity.setdefault('model', {'id': provider_identity['id'], 'revision': None})
                request = {'version': '1', 'operation': 'recorded-recognition',
                           'inputs': [digest(source), renders[str(page)]['sha256']],
                           'region_id': rid, 'region_kind': detection['kind'],
                           'transforms': {'page': page, 'bbox': detection['bbox'], 'render': render},
                           'implementation': implementation, 'provider': provider_identity,
                           'model_revision_available': bool(provider_identity['model'].get('revision')),
                           'parameters': parameters}
                selected = selections.get(rid)
                inherited = (inherited_operations or {}).get(rid)
                if (selected is None and rid not in fresh and inherited is not None
                        and inherited['key'] == digest(validator.canonical(request) + b'\n')):
                    selected = inherited['selected_attempt']
                try:
                    resolved = cache.resolve(request, lambda: records['recognitions'][local_id],
                                             fresh=rid in fresh, selected=selected)
                except CacheIntegrityError:
                    raise
                except ValueError as error:
                    raise InputError(str(error)) from error
                response = resolved.pop('response')
                for attempt in resolved['attempts']:
                    save(attempt['output']['path'], cache.response_bytes(attempt))
                    blob(json_bytes({key: value for key, value in attempt.items() if key != 'id'}))
                operations[rid] = resolved
                raw = response['raw_text']
                search_text = ' '.join(raw.split())
                box = detection['bbox']
                geometry_box = dict(zip(('x', 'y', 'width', 'height'), box))
                selector = {'id': sid, 'kind': 'pdf-area', 'profile_id': 'selector',
                            'source_sha256': digest(source), 'target': rid,
                            'locator': f'page:{page} rect:' + ','.join(map(str, box))}
                descriptor['regions'].append({'id': rid, 'kind': detection['kind'], 'view_id': 'physical',
                    'geometry': {'profile_id': 'geometry', 'space': f'page-{page}-pt', **geometry_box}})
                descriptor['selectors'].append(selector)
                descriptor['contents'].append({'id': cid, 'kind': 'text', 'value': raw})
                descriptor['relations'].extend([
                    {'id': 'contains-' + rid, 'kind': 'contains', 'from': page_id, 'to': rid},
                    {'id': 'has-' + cid, 'kind': 'has-content', 'from': rid, 'to': cid},
                    {'id': 'derived-' + rid, 'kind': 'derived-from',
                     'from': 'evidence-' + rid, 'to': f'evidence-{image_id}'}])
                descriptor['evidence'].append({'id': 'evidence-' + rid, 'origin': 'extracted',
                    'source_ref': f'sha256:{digest(source)}#page:{page}',
                    'content_ids': [cid], 'selector_ids': [sid],
                    'transform': {'id': 'recorded-recognition', 'version': '1',
                        'config_sha256': resolved['key'],
                        'dependencies': [f"recorded:{config['provider']['id']}@{config['provider']['version']}", render['renderer']],
                        'inputs': [image_id], 'outputs': [cid]}})
                response_ref = {'path': 'blobs/' + resolved['selected_output'], 'sha256': resolved['selected_output']}
                revision = {'operation': 'recognize', 'revision': 'recognized-' + rid,
                            'parents': [f'page-{page}-regions-0'], 'region_id': rid,
                            'artifact': response_ref['sha256'], 'mode': 'recorded',
                            'operation_key': resolved['key'], 'selected_attempt': resolved['selected_attempt'],
                            'cache_hit': resolved['cache_hit']}
                history.append(revision)
                trace.append(revision)
                regions.append({'region_id': rid, 'local_id': local_id, 'page': page,
                    'bbox': box, 'frame': f'page-{page}-pt', 'selector_id': sid,
                    'raw_text': raw, 'layout_text': raw, 'search_text': search_text,
                    'producer': config['provider'], 'kind': detection['kind'],
                    'alternatives': [], 'revision': revision['revision'],
                    'operation_key': resolved['key'], 'selected_attempt': resolved['selected_attempt']})
                mappings.append({'region_id': rid, 'page': page, 'selector_id': sid,
                                 'start': len(search), 'end': len(search) + len(search_text)})
                search += search_text + '\n'
                unresolved.extend({'region_id': rid, 'reason': reason} for reason in response['unresolved'])
        structure, structural_unresolved = collect(config, pages, regions, mappings, digest(source))
        unresolved.extend(structural_unresolved)
        structure_ref = save('structure.json', json_bytes(structure))
        if any('structure' in config['pages'][str(page)] for page in pages):
            event = {'operation': 'structure', 'artifact': structure_ref['sha256'],
                     'mode': 'recorded', 'accepted': len(structure['observations']) - len(regions),
                     'rejected': len(structure['diagnostics'])}
            history.append(event)
            trace.append(event)
        errors = validator.validate(descriptor)
        if errors:
            raise ValueError('export violates DSC: ' + ', '.join(errors))
        descriptor_ref = save('descriptor.json', json_bytes(descriptor))
        save('search.txt', search.encode('utf-8'))
        save('search-map.json', json_bytes(mappings))
        save('regions.json', json_bytes(regions))
        save('unresolved.json', json_bytes({'regions': unresolved, 'coverage': 'unexamined-outside-recorded-regions'}))
        save('history.json', json_bytes(history))
        trace.append({'operation': 'export', 'artifact': descriptor_ref['sha256']})
        save('trace.jsonl', b''.join(json_bytes(event) for event in trace))
        usage = {'mode': 'recorded', 'provider_calls': 0, 'recorded_observations': len(regions),
                 'estimated_charge_microunits': 0, 'attempts': [], 'runtime_seconds': time.monotonic() - started}
        usage['recorded_observations'] = sum(not op['cache_hit'] for op in operations.values())
        usage['cache_hits'] = sum(op['cache_hit'] for op in operations.values())
        usage['recorded_attempts'] = [op['selected_attempt'] for op in operations.values() if not op['cache_hit']]
        save('operations.json', json_bytes(operations))
        save('ledger.json', json_bytes(usage))
        status = 'stopped-with-unresolved-work' if unresolved else 'completed'
        reason = 'recorded-unresolved' if unresolved else 'recorded-inputs-consumed'
        manifest = {'version': '1', 'mode': 'recorded', 'status': status, 'reason': reason,
                    'source': source_ref, 'configuration': config_ref, 'pages': pages,
                    'descriptor': descriptor_ref, 'renders': renders, 'artifacts': artifacts, 'usage': usage,
                    'operations': operations, 'structure': structure_ref}
        (stage / 'manifest.json').write_bytes(json_bytes(manifest))
        os.rename(stage, output)
    return {'manifest': str(output / 'manifest.json'), 'status': status, 'reason': reason}
