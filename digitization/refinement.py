# Purpose: Apply pinned recorded refinement rules through immutable run revisions.
# Responsibilities: Order actions by semantic inputs, validate transformations,
#   invalidate dependent structure, and retain source-bound revision snapshots.
# Rationale: sunset-rmx.18/.19 validate realized candidates and explicitly refuse
#   malformed prior envelopes, preserving the selected state and audit evidence.
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from dsc03 import validator


def encoded(value):
    return validator.canonical(value)


def regions(config, pages):
    return {f"page-{page}-{d['id']}": {**d, 'page': page,
            'response': config['pages'][str(page)]['recognitions'][d['id']]}
            for page in pages for d in config['pages'][str(page)]['detections']}


def semantic_labels(config, pages, report):
    """Canonical graph labels; automorphic nodes retain separate identities."""
    nodes = regions(config, pages)
    groups = {}
    for rid, node in nodes.items():
        attributes = {k: v for k, v in node.items() if k != 'id'}
        attributes['provider'] = config['provider']
        attributes['readings'] = sorted([{k: v for k, v in o.items() if k in ('kind', 'producer', 'text', 'lines')}
                                  for o in report['structure']['observations']
                                  if o['region_id'] == rid and o['kind'] != 'ocr'], key=encoded)
        groups.setdefault(encoded(attributes), []).append(rid)
    ordered = sorted(groups)
    edges = [(o['region_id'], relation['target'], encoded({'kind': relation['kind'], 'producer': o['producer']}))
             for o in report['structure']['observations'] for relation in o['relations']]
    best, labels = None, {}
    # Distinct attributes fix their label blocks. Only equal-attribute identities
    # require permutation; never collapse their cardinality or graph incidence.
    choices = [itertools.permutations(groups[key]) for key in ordered]
    for partition in itertools.product(*choices):
        sequence = [rid for block in partition for rid in block]
        mapping = {rid: i for i, rid in enumerate(sequence)}
        graph = encoded([[mapping[a], mapping[b], label.decode()] for a, b, label in
                         sorted(edges, key=lambda edge: (mapping[edge[0]], mapping[edge[1]], edge[2]))])
        if best is None or graph < best:
            best, labels = graph, {rid: index for rid, index in mapping.items()}
        elif graph == best:
            labels = {rid: min(labels[rid], mapping[rid]) for rid in mapping}
    return labels


def schedule(rules, config, pages, report):
    nodes, labels = regions(config, pages), semantic_labels(config, pages, report)
    def key(rule):
        action = copy.deepcopy(rule['action'])
        inputs = action.get('inputs', [])
        canonical_inputs = sorted(labels.get(rid, -1) for rid in inputs)
        action['inputs'] = canonical_inputs
        original_outputs = action.get('outputs', [])
        action['outputs'] = [{k: v for k, v in output.items() if k != 'id'}
                             if isinstance(output, dict) else output for output in original_outputs]
        output_labels = {encoded(value): i for i, value in enumerate(sorted(action['outputs'], key=encoded))}
        references = dict(labels)
        for output in original_outputs:
            if isinstance(output, dict) and isinstance(output.get('id'), str):
                value = {k: v for k, v in output.items() if k != 'id'}
                references[f"page-{output.get('page')}-{output['id']}"] = 'output-' + str(output_labels[encoded(value)])
        # Output allocation IDs cannot affect action ordering.
        for observation in action.get('structure', []):
            if isinstance(observation, dict):
                if observation.get('kind') != 'manual':
                    observation.pop('id', None)
                rid = observation.get('region_id')
                if isinstance(rid, str) and rid in references:
                    observation['region_id'] = references[rid]
                relations = observation.get('relations')
                for relation in relations if isinstance(relations, list) else []:
                    if isinstance(relation, dict) and isinstance(relation.get('target'), str) and relation['target'] in references:
                        relation['target'] = references[relation['target']]
        return (rule['priority'], min((nodes[rid]['page'] for rid in inputs if rid in nodes), default=0),
                canonical_inputs, rule['id'], hashlib.sha256(encoded(action)).hexdigest())
    return sorted(rules, key=key)


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {'version', 'rules'} or policy['version'] != '1':
        raise ValueError('unsupported refinement policy')
    if not isinstance(policy['rules'], list):
        raise ValueError('refinement rules must be a list')
    seen = set()
    for rule in policy['rules']:
        if (not isinstance(rule, dict) or set(rule) != {'id', 'priority', 'check', 'action'}
                or not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in seen
                or type(rule['priority']) is not int or rule['priority'] < 0):
            raise ValueError('rules require unique identities and nonnegative integer priority')
        seen.add(rule['id'])
        check, action = rule['check'], rule['action']
        if (not isinstance(check, dict) or check.get('kind') not in ('always', 'text-contains', 'unresolved')
                or set(check) != ({'kind'} if check['kind'] == 'always' else {'kind', 'value'})
                or check['kind'] != 'always' and (not isinstance(check['value'], str) or not check['value'])):
            raise ValueError('invalid recorded refinement check')
        if (not isinstance(action, dict) or not isinstance(action.get('inputs'), list)
                or not action['inputs'] or any(not isinstance(rid, str) for rid in action['inputs'])
                or not isinstance(action.get('outputs', []), list)
                or not isinstance(action.get('structure', []), list)):
            raise ValueError('invalid action envelope')


def matches(rule, nodes):
    inputs = rule['action']['inputs']
    if not set(inputs).issubset(nodes):
        raise ValueError('action references absent or retired input region')
    check = rule['check']
    if check['kind'] == 'always':
        return True
    if check['kind'] == 'text-contains':
        return any(check['value'] in nodes[rid]['response']['raw_text'] for rid in inputs)
    return any(check['value'] in nodes[rid]['response']['unresolved'] for rid in inputs)


def candidate(config, pages, rule, report, allocated):
    result, nodes = copy.deepcopy(config), regions(config, pages)
    action, kind = rule['action'], rule['action']['kind']
    inputs, outputs = action['inputs'], action.get('outputs', [])
    if set(action) - {'kind', 'inputs', 'outputs', 'structure'} or len(set(inputs)) != len(inputs):
        raise ValueError('unknown action fields or repeated input identity')
    if kind not in ('split', 'merge', 'expand', 'rerecognize', 'restructure'):
        raise ValueError('unknown refinement action')
    if (kind == 'split' and (len(inputs) != 1 or len(outputs) < 2)
            or kind == 'merge' and (len(inputs) < 2 or len(outputs) != 1)
            or kind in ('expand', 'rerecognize') and (len(inputs) != 1 or len(outputs) != 1)
            or kind == 'restructure' and outputs):
        raise ValueError('invalid transformation arity')
    source_pages = {nodes[rid]['page'] for rid in inputs}
    if len(source_pages) != 1:
        raise ValueError('geometric transformations require inputs on one page')
    ids, transforms = [], {}
    for output in outputs:
        if not isinstance(output, dict) or set(output) != {'page', 'id', 'kind', 'bbox', 'recognition'}:
            raise ValueError('outputs require page/id/kind/bbox/recognition')
        if type(output['page']) is not int or output['page'] not in source_pages:
            raise ValueError('output must share its input page frame')
        if not isinstance(output['id'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*', output['id']):
            raise ValueError('invalid output identity')
        rid = f"page-{output['page']}-{output['id']}"
        if rid in ids or rid in allocated and not (kind == 'rerecognize' and rid == inputs[0]):
            raise ValueError('output identity collides with an active or historical region')
        if kind == 'rerecognize' and (rid != inputs[0] or output['bbox'] != nodes[rid]['bbox']
                                    or output['kind'] != nodes[rid]['kind']):
            raise ValueError('rerecognition retains identity, role and geometry')
        ids.append(rid)
        transforms[rid] = {'page': output['page'], 'frame': f"page-{output['page']}-pt",
                           'bbox': output['bbox'], 'source_sha256': config['source_sha256'],
                           'mapping': 'identity-page-points',
                           'inputs': {rid: nodes[rid]['bbox'] for rid in inputs}}
    def contains(outer, inner):
        x, y, width, height = outer
        ix, iy, iw, ih = inner
        return x <= ix and y <= iy and ix + iw <= x + width and iy + ih <= y + height
    for output in outputs:
        box = output['bbox']
        if (not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box)
                or box[2] <= 0 or box[3] <= 0):
            raise ValueError('invalid output geometry')
        if kind == 'split' and not contains(nodes[inputs[0]]['bbox'], box):
            raise ValueError('split children must fit inside the parent')
        if kind in ('merge', 'expand') and not all(contains(box, nodes[rid]['bbox']) for rid in inputs):
            raise ValueError('merge/expansion must contain every input box')
        if kind == 'expand' and box == nodes[inputs[0]]['bbox']:
            raise ValueError('expansion must enlarge its input')
    for rid in inputs if kind != 'restructure' else []:
        node = nodes[rid]
        record = result['pages'][str(node['page'])]
        record['detections'] = [d for d in record['detections'] if d['id'] != node['id']]
        del record['recognitions'][node['id']]
        record.get('recognition_overrides', {}).pop(node['id'], None)
    for output in outputs:
        record = result['pages'][str(output['page'])]
        record['detections'].append({k: output[k] for k in ('id', 'kind', 'bbox')})
        record['recognitions'][output['id']] = output['recognition']
        # Preserve per-region request options when rerecognizing the same crop.
        if kind == 'rerecognize':
            options = config['pages'][str(output['page'])].get('recognition_overrides', {}).get(output['id'])
            if options is not None:
                record.setdefault('recognition_overrides', {})[output['id']] = copy.deepcopy(options)
    affected, invalidated = set(inputs), set()
    changed = True
    while changed:
        changed = False
        for observation in report['structure']['observations']:
            key = 'structure:' + observation['id']
            if 'selected_attempt' in observation or key in invalidated:
                continue
            dependencies = {observation['region_id']} | {r['target'] for r in observation['relations']}
            if dependencies & affected:
                invalidated.add(key)
                affected.add(observation['region_id'])
                changed = True
    for page in pages:
        record = result['pages'][str(page)]
        supplied = record.get('structure')
        if isinstance(supplied, list):
            record['structure'] = [o for o in supplied if not isinstance(o, dict)
                                    or 'structure:' + str(o.get('id')) not in invalidated]
    for observation in action.get('structure', []):
        if not isinstance(observation, dict):
            raise ValueError('replacement structure must be an observation object')
        rid = observation.get('region_id')
        updated = regions(result, pages)
        if rid not in updated:
            raise ValueError('replacement structure must target an active output')
        page = updated[rid]['page']
        record = result['pages'][str(page)]
        if not isinstance(record.get('structure', []), list):
            raise ValueError('cannot append replacement to malformed prior structure envelope')
        record.setdefault('structure', []).append(observation)
    mapping = {rid: ids if kind != 'restructure' else [rid] for rid in inputs}
    invalidated |= {'recognition:' + rid for rid in inputs} if kind != 'restructure' else set()
    return result, mapping, transforms, sorted(invalidated)


class CandidateRefusal(ValueError):
    """A realized candidate is invalid; preserve it without selecting its state."""

    def __init__(self, detail, candidate_path):
        super().__init__(detail)
        self.candidate = candidate_path


def refine_run(source_path, pages, config_path, output, *, cache_dir, fresh, selections):
    # Local imports avoid a pipeline/inspection cycle while preserving one public
    # run interface for plain recorded runs and revision snapshots.
    from digitization.pipeline import _preflight, _run_once, InputError, json_bytes, digest
    from digitization.inspection import inspect_run
    source, original_raw, config = _preflight(source_path, pages, config_path, output)
    try:
        validate_policy(config['refinement'])
    except (ValueError, TypeError, KeyError) as error:
        raise InputError(str(error)) from error
    output = Path(output).absolute()
    if cache_dir is not None and Path(cache_dir).resolve().is_relative_to(output):
        raise InputError('shared cache must be outside the new run directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.refinement-', dir=output.parent) as temporary:
        root = Path(temporary)
        stage = root / 'run'
        stage.mkdir()
        cache = Path(cache_dir) if cache_dir is not None else root / 'cache'
        active = copy.deepcopy(config)
        del active['refinement']
        pending = copy.deepcopy(config['refinement']['rules'])
        steps, diagnostics, states, histories, traces = [], [], [], [], []
        allocated = set(regions(active, pages))
        revision = 0
        total_usage = {'provider_calls': 0, 'recorded_observations': 0, 'cache_hits': 0,
                       'estimated_charge_microunits': 0, 'runtime_seconds': 0, 'recorded_attempts': []}

        def execute(value, number, fresh_regions=(), selected=None, inherited=None,
                    candidate_id=None, replacements=()):
            path = root / 'effective.json'
            path.write_bytes(json_bytes(value))
            accepted_path = stage / 'revisions' / f'state-{number}'
            destination = stage / 'candidates' / candidate_id if candidate_id else accepted_path
            _run_once(source_path, pages, path, destination, cache_dir=cache,
                      fresh=fresh_regions, selections=selected, inherited_operations=inherited)
            report = inspect_run(destination)
            manifest = validator.load(destination / 'manifest.json')
            for field in total_usage:
                total_usage[field] += report['usage'][field]
            histories.extend(report['history'])
            traces.extend(report['trace'])
            # Checks must use the selected cached response, not a conflicting
            # unselected recording in the caller's configuration.
            for rid, operation in report['operations'].items():
                region = next(r for r in report['regions'] if r['region_id'] == rid)
                attempt = next(a for a in operation['attempts'] if a['id'] == operation['selected_attempt'])
                value['pages'][str(region['page'])]['recognitions'][region['local_id']] = validator.load(destination / attempt['output']['path'])
            accepted_ids = {o['id'] for o in report['structure']['observations']}
            for observation in replacements:
                refused = any(d.get('proposal') == observation for d in report['structure']['diagnostics'])
                if refused or observation.get('id') not in accepted_ids:
                    raise CandidateRefusal('replacement structure does not validate against selected recognition',
                                           str(destination.relative_to(stage)))
            if candidate_id:
                accepted_path.parent.mkdir(parents=True, exist_ok=True)
                os.rename(destination, accepted_path)
                destination = accepted_path
            states.append({'revision': f'state-{number}', 'manifest': f'revisions/state-{number}/manifest.json'})
            return destination, report, manifest

        current, report, manifest = execute(active, 0, fresh, selections)
        while pending:
            rule = schedule(pending, active, pages, report)[0]
            pending.remove(rule)
            try:
                if not matches(rule, regions(active, pages)):
                    continue
                updated, mapping, transforms, invalidated = candidate(active, pages, rule, report, allocated)
                path = root / 'candidate.json'
                path.write_bytes(json_bytes(updated))
                _preflight(source_path, pages, path, stage / 'not-published')
                rerecognize = rule['action']['inputs'] if rule['action']['kind'] == 'rerecognize' else ()
                selected_candidate = execute(updated, revision + 1, rerecognize,
                    inherited=report['operations'], candidate_id='candidate-' + str(len(steps) + len(diagnostics) + 1),
                    replacements=rule['action'].get('structure', ()))
            except (ValueError, KeyError, TypeError) as error:
                diagnostic = {'rule_id': rule['id'], 'reason': 'invalid-refinement', 'detail': str(error)}
                if isinstance(error, CandidateRefusal):
                    diagnostic['candidate'] = error.candidate
                    traces.append({'operation': 'reject-refinement', **diagnostic})
                diagnostics.append(diagnostic)
                continue
            previous = revision
            revision += 1
            event = {'operation': rule['action']['kind'], 'rule_id': rule['id'],
                     'priority': rule['priority'], 'check': rule['check'],
                     'parents': [f'state-{previous}'], 'revision': f'state-{revision}',
                     'mapping': mapping, 'transforms': transforms, 'invalidated': invalidated}
            active = updated
            current, report, manifest = selected_candidate
            allocated.update(regions(active, pages))
            steps.append(event)
            histories.append(event)
            traces.append(event)
        # Publish selected semantic output at root and retain every earlier run.
        for path in current.rglob('*'):
            if path.is_file():
                target = stage / path.relative_to(current)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        manifest['artifacts'] = dict(manifest['artifacts'])
        def save(name, value):
            raw = value if isinstance(value, bytes) else json_bytes(value)
            (stage / name).write_bytes(raw)
            ref = {'path': name, 'sha256': digest(raw)}
            manifest['artifacts'][name] = ref
            return ref
        refinement = {'version': '1', 'policy': config['refinement'], 'states': states,
                      'steps': steps, 'diagnostics': diagnostics}
        manifest['refinement'] = save('refinement.json', refinement)
        save('original-config.json', original_raw)
        save('history.json', histories)
        save('trace.jsonl', b''.join(json_bytes(item) for item in traces))
        usage = {**manifest['usage'], **total_usage}
        save('ledger.json', usage)
        manifest['usage'] = usage
        unresolved = validator.load(stage / 'unresolved.json')
        unresolved['regions'].extend({'region_id': f"rule:{d['rule_id']}", 'reason': d['reason']} for d in diagnostics)
        accepted_structure = {o['id'] for o in report['structure']['observations']}
        for step in steps:
            unresolved['regions'].extend({'region_id': key, 'reason': 'structure-recheck-required'}
                                         for key in step['invalidated'] if key.startswith('structure:')
                                         and key.removeprefix('structure:') not in accepted_structure)
        save('unresolved.json', unresolved)
        if unresolved['regions']:
            manifest['status'], manifest['reason'] = 'stopped-with-unresolved-work', 'recorded-unresolved'
        for directory in ('revisions', 'candidates'):
            for path in (stage / directory).rglob('*'):
                if path.is_file():
                    relative = str(path.relative_to(stage))
                    manifest['artifacts'][relative] = {'path': relative, 'sha256': digest(path.read_bytes())}
        (stage / 'manifest.json').write_bytes(json_bytes(manifest))
        os.rename(stage, output)
    return {'manifest': str(output / 'manifest.json'), 'status': manifest['status'], 'reason': manifest['reason']}
