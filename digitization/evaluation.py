# Purpose: Score recorded digitization runs against a frozen human reference.
# Responsibilities: Validate stage policy, compute deterministic text/geometry/
#   layout/relationship metrics, and bind reports to all input digests.
# Rationale: Pilot claims must follow reviewed evidence and reproducible rules.
import hashlib
import json
import math
import re
from pathlib import Path

from digitization.budget import validate_policy
from digitization.inspection import inspect_run
from digitization.pipeline import json_bytes


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def validate_stage(path):
    try:
        raw = Path(path).read_bytes()
        stage = json.loads(raw)
        required = {'version', 'stage_id', 'mode', 'approval', 'source_sha256', 'pages',
                    'reference_sha256', 'baseline_configuration_sha256',
                    'candidate_configuration_sha256', 'engine', 'budget', 'policy', 'exclusions'}
        if not isinstance(stage, dict) or not required <= set(stage) or stage['version'] != '1':
            raise ValueError
        if stage['mode'] not in ('assessment', 'engineering-only'):
            raise ValueError
        approval = stage['approval']
        if (not isinstance(approval, dict) or approval.get('approved') is not True
                or not isinstance(approval.get('owner'), str) or not approval['owner'].strip()):
            raise ValueError
        if not _sha(stage['source_sha256']) or not isinstance(stage['pages'], list) or not stage['pages']:
            raise ValueError
        if any(type(page) is not int or page < 1 for page in stage['pages']):
            raise ValueError
        for key in ('baseline_configuration_sha256', 'candidate_configuration_sha256'):
            if not _sha(stage[key]):
                raise ValueError
        engine = stage['engine']
        if (not isinstance(engine, dict) or not all(isinstance(engine.get(k), str) and engine[k]
                for k in ('id', 'version')) or not _sha(engine.get('configuration_sha256'))
                or not _sha(engine.get('price_schedule_sha256'))):
            raise ValueError
        validate_policy(stage['budget'])
        policy = stage['policy']
        if (not isinstance(policy, dict) or policy.get('version') != '1'
                or policy.get('normalization') != 'identity'
                or policy.get('tie_break') != 'canonical-geometry-then-recorded-id'
                or type(policy.get('region_iou_threshold')) not in (int, float)
                or not 0 <= policy['region_iou_threshold'] <= 1
                or not isinstance(policy.get('required_scopes'), list)
                or not isinstance(policy.get('thresholds'), dict)):
            raise ValueError
        if any(not isinstance(k, str) or type(v) not in (int, float) or not math.isfinite(v)
               or v < 0 for k, v in policy['thresholds'].items()):
            raise ValueError
        if not isinstance(stage['exclusions'], list):
            raise ValueError
        missing = stage.get('missing_scopes', [])
        if stage['mode'] == 'assessment':
            if not _sha(stage['reference_sha256']) or missing:
                raise ValueError
        elif (stage['reference_sha256'] is not None or not isinstance(missing, list)
              or not missing or any(not isinstance(x, str) or not x for x in missing)):
            raise ValueError
        return {'stage': stage, 'sha256': hashlib.sha256(raw).hexdigest(),
                'missing_scopes': missing,
                'positive_conclusions_allowed': stage['mode'] == 'assessment' and not missing}
    except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError) as error:
        raise ValueError('invalid-stage-manifest') from error


def character_error(reference, candidate):
    if not isinstance(reference, str) or not isinstance(candidate, str):
        return {'status': 'UNKNOWN', 'errors': 0, 'reference_characters': 0, 'value': None}
    n, m = len(reference), len(candidate)
    if n == 0:
        return {'status': 'UNKNOWN', 'errors': 0, 'reference_characters': 0, 'value': None}
    previous = list(range(m + 1))
    for i, a in enumerate(reference, 1):
        current = [i]
        for j, b in enumerate(candidate, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (a != b)))
        previous = current
    errors = previous[-1]
    return {'status': 'measured', 'errors': errors, 'reference_characters': n, 'value': errors / n}


def _iou(a, b):
    if a.get('page') != b.get('page'):
        return 0.0
    ax, ay, aw, ah = a['bbox']; bx, by, bw, bh = b['bbox']
    if not all(math.isfinite(float(x)) for x in (ax, ay, aw, ah, bx, by, bw, bh)) or min(aw, ah, bw, bh) <= 0:
        return 0.0
    intersection = max(0, min(ax+aw, bx+bw)-max(ax,bx)) * max(0, min(ay+ah, by+bh)-max(ay,by))
    return intersection / (aw*ah + bw*bh - intersection)


def match_regions(references, candidates, minimum_iou=0.5):
    refs = sorted(references, key=lambda x: (tuple(x['bbox']), str(x.get('id', x.get('region_id', '')))))
    cands = sorted(candidates, key=lambda x: (tuple(x['bbox']), str(x.get('region_id', x.get('id', '')))))
    # Dynamic programming over candidate subsets gives maximum total IoU, with stable traversal ties.
    states = {0: (0.0, ())}
    for ri, ref in enumerate(refs):
        nxt = dict(states)
        for mask, (score, pairs) in states.items():
            for ci, cand in enumerate(cands):
                overlap = _iou(ref, cand)
                if mask & (1 << ci) or overlap < minimum_iou:
                    continue
                new_mask = mask | (1 << ci); proposal = (score + overlap, pairs + ((ri, ci, overlap),))
                old = nxt.get(new_mask)
                if old is None or proposal[0] > old[0] + 1e-12:
                    nxt[new_mask] = proposal
        states = nxt
    best = max(states.values(), key=lambda item: item[0])[1]
    used_r = {x[0] for x in best}; used_c = {x[1] for x in best}
    matches = [{'reference_id': str(refs[r].get('id', refs[r].get('region_id'))),
                'candidate_id': str(cands[c].get('region_id', cands[c].get('id'))), 'iou': overlap}
               for r, c, overlap in best]
    precision = len(best)/len(cands) if cands else None
    recall = len(best)/len(refs) if refs else None
    return {'matches': matches, 'missing': [str(x.get('id', x.get('region_id'))) for i,x in enumerate(refs) if i not in used_r],
            'spurious': [str(x.get('region_id', x.get('id'))) for i,x in enumerate(cands) if i not in used_c],
            'precision': precision, 'recall': recall, 'reference_count': len(refs), 'candidate_count': len(cands)}


def _set_error(reference, candidate):
    if not reference:
        return {'status': 'UNKNOWN', 'missing': 0, 'spurious': len(candidate), 'denominator': 0, 'value': None}
    missing = [x for x in reference if x not in candidate]
    spurious = [x for x in candidate if x not in reference]
    return {'status': 'measured', 'missing': len(missing), 'spurious': len(spurious),
            'denominator': len(reference), 'value': len(missing)/len(reference),
            'missing_witnesses': missing, 'spurious_witnesses': spurious}


def layout_metrics(reference, candidate_text):
    lines = [i for i, char in enumerate(candidate_text) if char == '\n']
    line = _set_error(reference.get('line_breaks', []), lines)
    stanza = _set_error(reference.get('stanza_boundaries', []), lines)
    expected = reference.get('indentation', [])
    actual = [len(x) - len(x.lstrip(' ')) for x in candidate_text.splitlines()]
    count = min(len(expected), len(actual))
    if not expected:
        indent = {'status': 'UNKNOWN', 'missing': 0, 'spurious': len(actual), 'denominator': 0, 'value': None}
    else:
        errors = sum(expected[i] != actual[i] for i in range(count)) + abs(len(expected)-len(actual))
        indent = {'status': 'measured', 'missing': errors, 'spurious': 0,
                  'denominator': len(expected), 'value': errors/len(expected)}
    return {'line_boundary_error': line, 'stanza_boundary_error': stanza, 'indentation_error': indent}


def relationship_metrics(reference, candidate, mapping):
    mapped = {(mapping.get(x['source']), x['kind'], mapping.get(x['target'])) for x in reference}
    actual = {(x['source'], x['kind'], x['target']) for x in candidate}
    matched = mapped & actual
    missing = [x for x in reference if (mapping.get(x['source']), x['kind'], mapping.get(x['target'])) not in actual]
    spurious = [x for x in candidate if (x['source'], x['kind'], x['target']) not in mapped]
    return {'matched': len(matched), 'missing': missing, 'spurious': spurious,
            'reference_count': len(reference), 'missing_rate': len(missing)/len(reference) if reference else None,
            'spurious_count': len(spurious)}


def evaluate(baseline_run, candidate_run, reference_path, policy_path, output):
    stage_info = validate_stage(policy_path); stage = stage_info['stage']
    reference_raw = Path(reference_path).read_bytes(); reference = json.loads(reference_raw)
    baseline = inspect_run(baseline_run); candidate = inspect_run(candidate_run)
    if baseline['source']['sha256'] != stage['source_sha256'] or candidate['source']['sha256'] != stage['source_sha256']:
        raise ValueError('stage-source-digest-mismatch')
    if baseline['configuration']['sha256'] != stage['baseline_configuration_sha256'] or candidate['configuration']['sha256'] != stage['candidate_configuration_sha256']:
        raise ValueError('stage-configuration-digest-mismatch')
    for run_path in (baseline_run, candidate_run):
        run_manifest = json.loads((Path(run_path) / 'manifest.json').read_text(encoding='utf-8'))
        if run_manifest.get('pages') != stage['pages']:
            raise ValueError('stage-page-selection-mismatch')
    if stage['reference_sha256'] and hashlib.sha256(reference_raw).hexdigest() != stage['reference_sha256']:
        raise ValueError('stage-reference-digest-mismatch')
    result = {'version': '1', 'stage_id': stage['stage_id'], 'status': 'evaluation-incomplete' if not stage_info['positive_conclusions_allowed'] else 'measured',
              'positive_conclusions_allowed': stage_info['positive_conclusions_allowed'],
              'digests': {'stage': stage_info['sha256'], 'reference': hashlib.sha256(reference_raw).hexdigest(),
                          'baseline_manifest': hashlib.sha256((Path(baseline_run)/'manifest.json').read_bytes()).hexdigest(),
                          'candidate_manifest': hashlib.sha256((Path(candidate_run)/'manifest.json').read_bytes()).hexdigest()},
              'metrics': {}, 'exclusions': stage['exclusions'],
              'execution': {'baseline_usage': baseline['usage'], 'candidate_usage': candidate['usage'],
                            'provider_calls': {'baseline': baseline['usage'].get('provider_calls'),
                                               'candidate': candidate['usage'].get('provider_calls')},
                            'correction_effort': 'UNKNOWN', 'setup_effort': 'UNKNOWN'},
              'unknown_claims': ['correction-effort', 'setup-effort', 'total-cost']}
    refs = reference.get('regions', [])
    base_regions = baseline['regions']; cand_regions = candidate['regions']
    result['metrics']['regions'] = {'baseline': match_regions(refs, base_regions, stage['policy']['region_iou_threshold']),
                                    'candidate': match_regions(refs, cand_regions, stage['policy']['region_iou_threshold'])}
    text_ref = reference.get('text', {})
    for label, run in (('baseline', baseline), ('candidate', candidate)):
        region_scores = result['metrics']['regions'][label]
        id_map = {item['reference_id']: item['candidate_id'] for item in region_scores['matches']}
        text_by_id = {r['region_id']: r.get('raw_text', '') for r in run['regions']}
        expected_text = ''.join(text_ref.values()) if isinstance(text_ref, dict) else ''
        output_text = ''.join(text_by_id.get(id_map.get(item, ''), '') for item in text_ref)
        result['metrics'].setdefault('cer', {})[label] = character_error(expected_text, output_text)
    result['metrics']['layout'] = layout_metrics(reference.get('layout', {}), '\n'.join(r.get('raw_text','') for r in cand_regions))
    candidate_map = {item['reference_id']: item['candidate_id']
                     for item in result['metrics']['regions']['candidate']['matches']}
    observed_edges = []
    for observation in candidate.get('structure', {}).get('observations', []):
        for relation in observation.get('relations', []):
            observed_edges.append({'source': observation.get('region_id'),
                                   'kind': relation['kind'], 'target': relation['target']})
    result['metrics']['relationships'] = relationship_metrics(
        reference.get('relationships', []), observed_edges, candidate_map)
    gates = {}
    thresholds = stage['policy']['thresholds']
    scalar_metrics = {'cer': result['metrics']['cer'].get('candidate', {}).get('value'),
                      'region_precision': result['metrics']['regions']['candidate']['precision'],
                      'region_recall': result['metrics']['regions']['candidate']['recall'],
                      'line_boundary_error': result['metrics']['layout']['line_boundary_error']['value'],
                      'stanza_boundary_error': result['metrics']['layout']['stanza_boundary_error']['value'],
                      'indentation_error': result['metrics']['layout']['indentation_error']['value'],
                      'continuation_error': result['metrics']['relationships']['missing_rate']}
    for name, limit in thresholds.items():
        measured = scalar_metrics.get(name)
        if measured is None:
            gates[name] = 'UNKNOWN'
        else:
            passes = measured >= limit if name in ('region_precision', 'region_recall') else measured <= limit
            gates[name] = 'pass' if passes else 'reject'
    result['thresholds'] = gates
    complete = stage_info['positive_conclusions_allowed'] and all(v != 'UNKNOWN' for v in gates.values())
    result['status'] = 'measured' if complete else 'evaluation-incomplete'
    result['quality_conclusion'] = ('pass' if all(v == 'pass' for v in gates.values()) else
                                    'reject' if complete else 'UNKNOWN')
    result['positive_economy_conclusion_allowed'] = False
    result['positive_scaling_conclusion_allowed'] = False
    if stage_info['missing_scopes']:
        result['missing_scopes'] = stage_info['missing_scopes']
    payload = json_bytes(result); Path(output).mkdir(parents=True, exist_ok=False)
    (Path(output)/'evaluation.json').write_bytes(payload)
    lines = [f"Evaluation {result['status']} for {stage['stage_id']}", f"Stage SHA256: {stage_info['sha256']}",
             'Positive conclusions allowed: ' + str(result['positive_conclusions_allowed']).lower(),
             json.dumps(result['metrics'], ensure_ascii=False, sort_keys=True)]
    (Path(output)/'evaluation.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    result['report_sha256'] = hashlib.sha256(payload).hexdigest()
    return result
