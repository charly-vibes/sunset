# Purpose: Verify recorded refinement retains lineage and selectively reuses work.
# Responsibilities: Exercise public run/inspect, dependency invalidation, stable
#   rule scheduling and rejection of malformed region transformations offline.
# Rationale: sunset-rmx.5 must preserve prior revisions and unrelated evidence.
import copy
import json
import socket
import subprocess

import pytest

from test_digitization_first_page import inputs, cli
from digitization.pipeline import run
from digitization.inspection import inspect_run
from dsc03 import validator


def output(name, box, text='column', page=2):
    return {'page': page, 'id': name, 'kind': 'text', 'bbox': box,
            'recognition': {'raw_text': text, 'unresolved': []}}


def rule(name='mixed-columns', kind='split', inputs=('page-2-p1',), outputs=None, priority=1):
    return {'id': name, 'priority': priority,
            'check': {'kind': 'text-contains', 'value': 'luna'},
            'action': {'kind': kind, 'inputs': list(inputs), 'outputs': outputs if outputs is not None else [
                output('r1a', [30, 60, 45, 100], 'left'),
                output('r1b', [80, 60, 50, 100], 'right')]}}


def configure(path, config, rules):
    config['refinement'] = {'version': '1', 'rules': rules}
    path.write_text(json.dumps(config))


def test_split_public_journey_retains_parent_and_unrelated_attempt(inputs, tmp_path):
    source, path, config = inputs
    configure(path, config, [rule()])
    before = source.read_bytes(), path.read_bytes()
    out = tmp_path / 'split'
    code, _ = cli('run', '--source', source, '--pages', '2', '--config', path, '--output', out)
    assert code == 2  # original caption uncertainty still visible
    code, report = cli('inspect', '--run', out, '--json')
    assert code == 0
    assert {r['region_id'] for r in report['regions']} == {'page-2-r1a', 'page-2-r1b', 'page-2-c1'}
    refinement = report['refinement']
    assert refinement['version'] == '1' and refinement['diagnostics'] == []
    step = refinement['steps'][0]
    assert step['rule_id'] == 'mixed-columns'
    assert step['parents'] == ['state-0'] and step['revision'] == 'state-1'
    assert step['mapping'] == {'page-2-p1': ['page-2-r1a', 'page-2-r1b']}
    assert step['transforms']['page-2-r1a']['bbox'] == [30, 60, 45, 100]
    assert step['transforms']['page-2-r1a']['source_sha256'] == config['source_sha256']
    old = inspect_run(out / 'revisions/state-0')
    assert old['regions'][0]['local_id'] == 'p1'
    assert old['operations']['page-2-c1']['selected_attempt'] == report['operations']['page-2-c1']['selected_attempt']
    assert report['operations']['page-2-c1']['cache_hit']
    assert report['usage']['recorded_observations'] == 4  # original2 + children2
    assert validator.validate(validator.load(out / 'descriptor.json')) == []
    assert before == (source.read_bytes(), path.read_bytes())
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['artifacts']['revisions/state-0/manifest.json']


@pytest.mark.parametrize('kind', ['merge', 'expand', 'rerecognize', 'restructure'])
def test_actions_recheck_neighbor_links_but_preserve_unrelated_cache(inputs, tmp_path, kind, monkeypatch):
    source, path, config = inputs
    config['pages']['3'] = copy.deepcopy(config['pages']['2'])
    config['pages']['3']['structure'] = [{'id': 'neighbor', 'kind': 'model',
        'region_id': 'page-3-p1', 'producer': {'id': 'fixture', 'version': '1', 'config': {}},
        'relations': [{'kind': 'continues-to', 'target': 'page-2-p1'}]}]
    chosen = rule(kind=kind)
    if kind == 'merge':
        chosen['action'].update(inputs=['page-2-p1', 'page-2-c1'], outputs=[output('merged', [30, 60, 100, 160])])
    elif kind == 'expand':
        chosen['action']['outputs'] = [output('expanded', [20, 50, 120, 120])]
    elif kind == 'rerecognize':
        chosen['action']['outputs'] = [{**output('p1', [30, 60, 100, 100], 'corrected'), 'kind': 'poem'}]
    else:
        chosen['action']['outputs'] = []
        chosen['action']['structure'] = []
    configure(path, config, [chosen])
    def forbidden(*args, **kwargs): pytest.fail('unexpected external IO')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    out = tmp_path / kind
    run(source, [2, 3], path, out)
    report, initial = inspect_run(out), inspect_run(out / 'revisions/state-0')
    step = report['refinement']['steps'][0]
    assert 'structure:neighbor' in step['invalidated']
    assert not any(o['id'] == 'neighbor' for o in report['structure']['observations'])
    assert any(u['reason'] == 'structure-recheck-required' for u in report['unresolved'])
    untouched = 'page-3-c1'
    assert report['operations'][untouched]['selected_attempt'] == initial['operations'][untouched]['selected_attempt']
    assert report['operations'][untouched]['selected_output'] == initial['operations'][untouched]['selected_output']
    assert report['usage']['provider_calls'] == 0


def test_shuffled_rule_arrival_has_identical_schedule_and_geometry_does_not_merge_identity(inputs, tmp_path):
    source, path, config = inputs
    # Two equal-geometry regions must remain two identities.
    config['pages']['2']['detections'].append({**config['pages']['2']['detections'][0], 'id': 'twin'})
    config['pages']['2']['recognitions']['twin'] = copy.deepcopy(config['pages']['2']['recognitions']['p1'])
    rules = [rule('z-rule', kind='restructure', outputs=[], priority=2),
             rule('a-rule', kind='restructure', inputs=['page-2-twin'], outputs=[], priority=1)]
    reports = []
    for name, pending in [('forward', rules), ('reverse', list(reversed(rules)))]:
        configure(path, config, pending)
        out = tmp_path / name
        run(source, [2], path, out)
        reports.append(inspect_run(out))
    steps = [r['refinement']['steps'] for r in reports]
    assert [s['rule_id'] for s in steps[0]] == ['a-rule', 'z-rule']
    assert steps[0] == steps[1]
    assert {r['region_id'] for r in reports[0]['regions']} == {'page-2-p1', 'page-2-c1', 'page-2-twin'}


@pytest.mark.parametrize('bad', [
    {'outputs': [output('bad', [295, 60, 100, 100])]},
    {'inputs': ['absent']}, {'outputs': [output('c1', [30, 60, 20, 100])]},
    {'outputs': [output('x', [30, 60, 45, 100])]}, {'kind': 'unknown'},
    {'outputs': [output('x', [30, 60, 45, 100]), output('x', [80, 60, 50, 100])]},
])
def test_invalid_action_retains_valid_state_with_diagnostic(inputs, tmp_path, bad):
    source, path, config = inputs
    candidate = rule()
    candidate['action'].update(bad)
    configure(path, config, [candidate])
    out = tmp_path / 'invalid'
    run(source, [2], path, out)
    report = inspect_run(out)
    assert report['regions'][0]['local_id'] == 'p1'
    assert report['refinement']['steps'] == []
    assert report['refinement']['diagnostics'][0]['reason'] == 'invalid-refinement'
    assert report['status'] == 'stopped-with-unresolved-work'


def test_nonmatching_rule_does_not_recognize_again(inputs, tmp_path):
    source, path, config = inputs
    candidate = rule()
    candidate['check']['value'] = 'not in recorded text'
    configure(path, config, [candidate])
    run(source, [2], path, tmp_path / 'no-match')
    report = inspect_run(tmp_path / 'no-match')
    assert report['refinement']['steps'] == [] and report['usage']['recorded_observations'] == 2


def test_transitive_structure_invalidation_and_replacement_recheck(inputs, tmp_path):
    source, path, config = inputs
    config['pages']['3'] = copy.deepcopy(config['pages']['2'])
    def observation(name, rid, target):
        return {'id': name, 'kind': 'model', 'region_id': rid,
                'producer': {'id': 'fixture', 'version': '1', 'config': {}},
                'relations': [{'kind': 'continues-to', 'target': target}]}
    config['pages']['3']['structure'] = [observation('raw-neighbor', 'page-3-p1', 'page-2-p1'),
                                        observation('transitive', 'page-3-c1', 'page-3-p1')]
    chosen = rule(kind='restructure', outputs=[])
    chosen['action']['structure'] = [observation('raw-neighbor', 'page-3-p1', 'page-2-c1')]
    configure(path, config, [chosen])
    out = tmp_path / 'replacement'
    run(source, [2, 3], path, out)
    report = inspect_run(out)
    assert set(report['refinement']['steps'][0]['invalidated']) == {'structure:raw-neighbor', 'structure:transitive'}
    assert next(o for o in report['structure']['observations'] if o['id'] == 'raw-neighbor')['relations'][0]['target'] == 'page-2-c1'
    assert not any(u['region_id'] == 'structure:raw-neighbor' and u['reason'] == 'structure-recheck-required'
                   for u in report['unresolved'])
    assert any(u['region_id'] == 'structure:transitive' and u['reason'] == 'structure-recheck-required'
               for u in report['unresolved'])


@pytest.mark.parametrize('kind,outputs', [
    ('expand', [output('smaller', [40, 70, 20, 20])]),
    ('split', [output('inside', [30, 60, 45, 100]), output('outside', [200, 60, 50, 100])]),
    ('merge', [output('too-small', [30, 60, 20, 20])]),
])
def test_geometric_action_must_mean_its_named_transform(inputs, tmp_path, kind, outputs):
    source, path, config = inputs
    chosen = rule(kind=kind, outputs=outputs)
    if kind == 'merge': chosen['action']['inputs'].append('page-2-c1')
    configure(path, config, [chosen])
    out = tmp_path / kind
    run(source, [2], path, out)
    report = inspect_run(out)
    assert report['refinement']['steps'] == []
    assert report['refinement']['diagnostics'][0]['reason'] == 'invalid-refinement'


def test_malformed_replacement_is_diagnosed_before_scheduling_can_crash(inputs, tmp_path):
    source, path, config = inputs
    chosen = rule(kind='restructure', outputs=[])
    chosen['action']['structure'] = [{'region_id': 'page-2-p1', 'relations': None}]
    configure(path, config, [chosen])
    out = tmp_path / 'malformed-structure'
    run(source, [2], path, out)
    report = inspect_run(out)
    assert report['refinement']['steps'] == []
    assert report['refinement']['diagnostics'][0]['reason'] == 'invalid-refinement'


def test_page_and_semantic_region_precede_rule_name_in_order(inputs, tmp_path):
    source, path, config = inputs
    config['pages']['3'] = copy.deepcopy(config['pages']['2'])
    rules = [rule('a-page3', kind='restructure', inputs=['page-3-p1'], outputs=[]),
             rule('a-poem', kind='restructure', outputs=[]),
             rule('z-caption', kind='restructure', inputs=['page-2-c1'], outputs=[])]
    for chosen in rules: chosen['check'] = {'kind': 'always'}
    configure(path, config, rules)
    out = tmp_path / 'order'
    run(source, [2, 3], path, out)
    steps = inspect_run(out)['refinement']['steps']
    # Canonical JSON orders bbox [...,200,...] before [...,60,...]; this is an
    # explicit encoding order, not a claimed reading order.
    assert [s['rule_id'] for s in steps] == ['z-caption', 'a-poem', 'a-page3']


def test_rerecognized_selection_survives_unrelated_revision(inputs, tmp_path):
    source, path, config = inputs
    correction = rule('correct', kind='rerecognize', outputs=[
        {**output('p1', [30, 60, 100, 100], 'corrected'), 'kind': 'poem'}])
    unrelated = rule('unrelated', kind='restructure', inputs=['page-2-c1'], outputs=[], priority=2)
    unrelated['check'] = {'kind': 'always'}
    configure(path, config, [correction, unrelated])
    out = tmp_path / 'selection'
    run(source, [2], path, out)
    first = inspect_run(out / 'revisions/state-1')
    final = inspect_run(out)
    assert next(r for r in final['regions'] if r['local_id'] == 'p1')['raw_text'] == 'corrected'
    assert final['operations']['page-2-p1']['selected_attempt'] == first['operations']['page-2-p1']['selected_attempt']
    assert final['operations']['page-2-p1']['cache_hit']


@pytest.mark.parametrize('selection_mode', ['fresh', 'select'])
def test_initial_explicit_selection_survives_refinement(inputs, tmp_path, selection_mode):
    source, path, config = inputs
    cache = tmp_path / 'cache'
    run(source, [2], path, tmp_path / 'original', cache_dir=cache)
    config['pages']['2']['recognitions']['p1']['raw_text'] = 'corrected'
    path.write_text(json.dumps(config))
    run(source, [2], path, tmp_path / 'fresh', cache_dir=cache, fresh=['page-2-p1'])
    selected = inspect_run(tmp_path / 'fresh')['operations']['page-2-p1']['selected_attempt']
    unrelated = rule('unrelated', kind='restructure', inputs=['page-2-c1'], outputs=[])
    unrelated['check'] = {'kind': 'always'}
    configure(path, config, [unrelated])
    kwargs = {'fresh': ['page-2-p1']} if selection_mode == 'fresh' else {'selections': {'page-2-p1': selected}}
    out = tmp_path / ('selected-' + selection_mode)
    run(source, [2], path, out, cache_dir=cache, **kwargs)
    initial, final = inspect_run(out / 'revisions/state-0'), inspect_run(out)
    assert next(r for r in final['regions'] if r['local_id'] == 'p1')['raw_text'] == 'corrected'
    assert final['operations']['page-2-p1']['selected_attempt'] == initial['operations']['page-2-p1']['selected_attempt']


def test_cached_candidate_layout_refusal_preserves_parent_and_attempt_evidence(inputs, tmp_path):
    source, path, config = inputs
    cache = tmp_path / 'cache'
    configure(path, config, [rule()])
    run(source, [2], path, tmp_path / 'warm', cache_dir=cache)
    config['refinement']['rules'][0]['action']['outputs'][0]['recognition']['raw_text'] = 'new'
    config['refinement']['rules'][0]['action']['structure'] = [{
        'id': 'child-layout', 'kind': 'ocr', 'region_id': 'page-2-r1a', 'text': 'new',
        'producer': {'id': 'fixture', 'version': '1', 'config': {}},
        'lines': [{'start': 0, 'end': 3, 'bbox': [30, 60, 45, 10]}]}]
    path.write_text(json.dumps(config))
    out = tmp_path / 'refused-layout'
    run(source, [2], path, out, cache_dir=cache)
    report = inspect_run(out)
    assert report['refinement']['steps'] == []
    assert {r['region_id'] for r in report['regions']} == {'page-2-p1', 'page-2-c1'}
    diagnostic = report['refinement']['diagnostics'][0]
    assert diagnostic['reason'] == 'invalid-refinement'
    rejected = out / diagnostic['candidate']
    rejected_report = inspect_run(rejected)
    assert rejected_report['structure']['diagnostics'][0]['reason'] == 'invalid-structure'
    assert report['operations']['page-2-p1']['selected_attempt'] == inspect_run(out / 'revisions/state-0')['operations']['page-2-p1']['selected_attempt']
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['artifacts'][diagnostic['candidate'] + '/manifest.json']
    assert report['usage']['cache_hits'] == 5  # initial2, rejected children2 and unchanged caption1


def test_resolved_valid_replacement_is_admitted(inputs, tmp_path):
    source, path, config = inputs
    chosen = rule()
    chosen['action']['structure'] = [{
        'id': 'child-layout', 'kind': 'ocr', 'region_id': 'page-2-r1a', 'text': 'left',
        'producer': {'id': 'fixture', 'version': '1', 'config': {}},
        'lines': [{'start': 0, 'end': 4, 'bbox': [30, 60, 45, 10]}]}]
    configure(path, config, [chosen])
    out = tmp_path / 'valid-layout'
    run(source, [2], path, out)
    report = inspect_run(out)
    assert len(report['refinement']['steps']) == 1
    assert report['refinement']['diagnostics'] == report['structure']['diagnostics'] == []
    assert next(o for o in report['structure']['observations'] if o['id'] == 'child-layout')['text'] == 'left'


def test_layout_matching_cached_selection_is_valid_despite_unselected_recording(inputs, tmp_path):
    source, path, config = inputs
    cache = tmp_path / 'cache'
    configure(path, config, [rule()])
    run(source, [2], path, tmp_path / 'warm', cache_dir=cache)
    action = config['refinement']['rules'][0]['action']
    action['outputs'][0]['recognition']['raw_text'] = 'different unselected recording'
    action['structure'] = [{
        'id': 'selected-layout', 'kind': 'ocr', 'region_id': 'page-2-r1a', 'text': 'left',
        'producer': {'id': 'fixture', 'version': '1', 'config': {}},
        'lines': [{'start': 0, 'end': 4, 'bbox': [30, 60, 45, 10]}]}]
    path.write_text(json.dumps(config))
    out = tmp_path / 'selected-layout'
    run(source, [2], path, out, cache_dir=cache)
    report = inspect_run(out)
    assert len(report['refinement']['steps']) == 1
    assert report['refinement']['diagnostics'] == report['structure']['diagnostics'] == []
    assert next(o for o in report['structure']['observations'] if o['id'] == 'selected-layout')['text'] == 'left'


@pytest.mark.parametrize('malformed', ['malformed', None, {}, 5])
def test_malformed_prior_envelope_plus_replacement_preserves_inspectable_state(inputs, tmp_path, malformed):
    source, path, config = inputs
    config['pages']['2']['structure'] = malformed
    chosen = rule(kind='restructure', outputs=[])
    chosen['action']['structure'] = [{'id': 'correction', 'kind': 'manual', 'region_id': 'page-2-p1',
        'producer': {'id': 'reviewer', 'version': '1', 'config': {}}, 'text': 'fixed'}]
    configure(path, config, [chosen])
    out = tmp_path / 'malformed-prior'
    code, _ = cli('run', '--source', source, '--pages', '2', '--config', path, '--output', out)
    assert code == 2
    code, report = cli('inspect', '--run', out, '--json')
    assert code == 0
    assert report['refinement']['steps'] == []
    assert report['refinement']['diagnostics'][0]['reason'] == 'invalid-refinement'
    assert report['regions'][0]['local_id'] == 'p1'
    assert report['structure']['diagnostics'][0]['reason'] == 'invalid-structure'
    initial = inspect_run(out / 'revisions/state-0')
    assert report['operations'] == initial['operations']


def test_changed_request_type_does_not_inherit_old_attempt(inputs, tmp_path):
    from digitization.pipeline import _run_once
    source, path, config = inputs
    cache = tmp_path / 'cache'
    config['recognition'] = {'policy': {'flag': 0}}
    path.write_text(json.dumps(config))
    _run_once(source, [2], path, tmp_path / 'integer-request', cache_dir=cache)
    old = inspect_run(tmp_path / 'integer-request')
    config['recognition']['policy']['flag'] = False
    config['pages']['2']['recognitions']['p1']['raw_text'] = 'new request'
    path.write_text(json.dumps(config))
    out = tmp_path / 'boolean-request'
    _run_once(source, [2], path, out, cache_dir=cache, inherited_operations=old['operations'])
    report = inspect_run(out)
    assert report['operations']['page-2-p1']['key'] != old['operations']['page-2-p1']['key']
    assert not report['operations']['page-2-p1']['cache_hit']
    assert next(r for r in report['regions'] if r['local_id'] == 'p1')['raw_text'] == 'new request'
