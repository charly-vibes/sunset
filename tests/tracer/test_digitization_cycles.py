# Purpose: Verify refinement cycle equality ignores allocation and execution IDs.
# Responsibilities: Pin semantic projection inclusions, exclusions and multiplicity.
# Rationale: sunset-rmx.6 must stop stable and repeated states without redefining DSC identity.
import copy
import json

import pytest

from digitization.state import semantic_projection
from digitization.pipeline import run
from digitization.inspection import inspect_run
from test_digitization_first_page import inputs
from test_digitization_structure import proposal


def state():
    config = {
        'source_sha256': 'source',
        'provider': {'id': 'recorded', 'version': '1', 'model': {'id': 'm', 'revision': None}},
    }
    report = {
        'regions': [{
            'region_id': 'allocated-a', 'page': 1, 'frame': 'page-1-pt',
            'bbox': [1, 2, 30, 40], 'kind': 'poem', 'producer': {'id': 'ocr', 'version': '1'},
            'raw_text': 'luna\n', 'layout_text': 'luna\n', 'search_text': 'luna',
            'alternatives': [], 'revision': 'revision-1', 'selected_attempt': 'attempt-1',
        }],
        'structure': {'observations': [], 'diagnostics': []},
        'unresolved': [], 'coverage': 'unexamined-outside-recorded-regions',
    }
    return config, [1], report


def project(value):
    return semantic_projection(*value)


def test_projection_ignores_allocations_history_and_resource_envelopes():
    original = state()
    changed = copy.deepcopy(original)
    region = changed[2]['regions'][0]
    region.update(region_id='new-allocation', revision='revision-99', selected_attempt='attempt-42')
    changed[2]['usage'] = {'runtime_seconds': 999, 'provider_calls': 8}
    changed[2]['history'] = [{'revision': 'revision-99', 'timestamp': 'later'}]
    assert project(original) == project(changed)


@pytest.mark.parametrize('field,value', [
    ('raw_text', 'luna'), ('layout_text', 'luna'), ('search_text', 'luna!'),
    ('kind', 'caption'), ('producer', {'id': 'ocr', 'version': '2'}),
    ('bbox', [1, 2, 31, 40]),
])
def test_projection_includes_selected_content_geometry_and_attribution(field, value):
    original = state()
    changed = copy.deepcopy(original)
    changed[2]['regions'][0][field] = value
    assert project(original) != project(changed)


def test_projection_preserves_equal_geometry_node_multiplicity():
    original = state()
    duplicated = copy.deepcopy(original)
    second = copy.deepcopy(duplicated[2]['regions'][0])
    second.update(region_id='allocated-b', revision='revision-2', selected_attempt='attempt-2')
    duplicated[2]['regions'].append(second)
    assert project(original) != project(duplicated)


def test_projection_includes_attributed_relationships_and_alternatives():
    original = state()
    changed = copy.deepcopy(original)
    changed[2]['regions'][0]['alternatives'] = [
        {'kind': 'caption-of', 'target': 'external-target', 'producer': {'id': 'model', 'version': '1'}}
    ]
    assert project(original) != project(changed)


def test_projection_canonicalizes_allocated_graph_labels_and_keeps_relationships():
    original = state()
    second = copy.deepcopy(original[2]['regions'][0])
    second.update(region_id='allocated-b', revision='revision-2', selected_attempt='attempt-2')
    original[2]['regions'].append(second)
    original[2]['structure']['observations'] = [{
        'id': 'obs-a', 'region_id': 'allocated-a', 'kind': 'model',
        'producer': {'id': 'reader', 'version': '1', 'config': {}},
        'text': 'same', 'lines': [], 'status': 'unresolved',
        'relations': [{'kind': 'continues-to', 'target': 'allocated-b'}],
    }]
    relabeled = copy.deepcopy(original)
    by_id = {r['region_id']: r for r in relabeled[2]['regions']}
    by_id['allocated-a']['region_id'] = 'new-left'
    by_id['allocated-b']['region_id'] = 'new-right'
    observation = relabeled[2]['structure']['observations'][0]
    observation.update(id='fresh-observation', region_id='new-left')
    observation['relations'][0]['target'] = 'new-right'
    assert project(original) == project(relabeled)
    relabeled[2]['structure']['observations'][0]['relations'][0]['target'] = 'new-left'
    assert project(original) != project(relabeled)


def _rule(identifier, *, structure=()):
    return {'id': identifier, 'priority': 1, 'check': {'kind': 'always'},
            'action': {'kind': 'restructure', 'inputs': ['page-2-p1'],
                       'outputs': [], 'structure': list(structure)}}


def _write_policy(path, config, rules):
    config['refinement'] = {'version': '1', 'rules': rules}
    path.write_text(json.dumps(config))


def test_public_refinement_stops_immediate_semantic_repeat(inputs, tmp_path):
    source, path, config = inputs
    _write_policy(path, config, [_rule('no-op')])
    output = tmp_path / 'stable'
    run(source, [2], path, output)
    report = inspect_run(output)
    assert report['refinement']['stop_reason'] == 'stable-state'
    assert len(report['refinement']['states']) == 2
    assert report['refinement']['steps'][0]['revision'] == 'state-1'
    assert report['reason'] == 'stable-state'


def test_public_refinement_stops_nonadjacent_repeat_and_keeps_every_revision(inputs, tmp_path):
    source, path, config = inputs
    alternate = proposal('model', id='cycle-model', lines=[])
    _write_policy(path, config, [
        _rule('add-reading', structure=[alternate]),
        _rule('remove-reading'),
    ])
    output = tmp_path / 'cycle'
    run(source, [2], path, output)
    report = inspect_run(output)
    refinement = report['refinement']
    assert refinement['stop_reason'] == 'repeated-state'
    assert len(refinement['states']) == 3
    assert len(refinement['steps']) == 2
    assert report['reason'] == 'repeated-state'
    assert (output / 'revisions/state-0/manifest.json').exists()
    assert (output / 'revisions/state-1/manifest.json').exists()
    assert (output / 'revisions/state-2/manifest.json').exists()

