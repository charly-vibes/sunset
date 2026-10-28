# Purpose: Verify attributed poetic layout and unresolved structural alternatives.
# Responsibilities: Exercise public run/inspect, token provenance and refusal of
#   malformed observations without replacing selected OCR or prior valid readings.
# Rationale: sunset-rmx.4 keeps competing readings visible without semantic winners.
import copy
import json
import socket
import subprocess

import pytest

from test_digitization_first_page import inputs, cli, POEM
from digitization.pipeline import run
from digitization.inspection import inspect_run, format_report
from dsc03 import validator


def proposal(kind='ocr', **changes):
    value = {'id': kind + '-poem', 'kind': kind, 'region_id': 'page-2-p1',
             'producer': {'id': 'fixture-' + kind, 'version': '1', 'config': {'language': 'es'}},
             'text': POEM,
             'lines': [{'start': 0, 'end': 6, 'bbox': [40, 60, 60, 10]},
                       {'start': 7, 'end': 10, 'bbox': [30, 75, 60, 10]},
                       {'start': 12, 'end': 17, 'bbox': [40, 105, 60, 10]}]}
    value.update(changes)
    return value


def write(config_path, config, observations):
    config['pages']['2']['structure'] = observations
    config_path.write_text(json.dumps(config))


def test_poem_and_three_attributed_readings_remain_source_linked(inputs, tmp_path, monkeypatch):
    source, path, config = inputs
    manual = proposal('manual', text=POEM.replace('luna', 'Luna'))
    write(path, config, [proposal(), proposal('model'), manual])
    before = source.read_bytes(), path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail('recorded structure attempted external IO')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    out = tmp_path / 'poem'
    run(source, [2], path, out)
    report = inspect_run(out)
    region = report['regions'][0]
    assert region['raw_text'] == region['layout_text'] == POEM
    assert region['search_text'] == 'luna mar sal'
    structure = report['structure']
    assert structure['version'] == '1' and structure['diagnostics'] == []
    readings = [o for o in structure['observations'] if o['region_id'] == 'page-2-p1']
    assert [o['kind'] for o in readings] == ['ocr', 'ocr', 'model', 'manual']
    assert readings[-1]['text'] == manual['text']
    for observation in readings:
        assert observation['source_sha256'] == config['source_sha256']
        assert observation['selector_id'] == 'sel-page-2-p1'
        assert observation['producer']['id']
    layout = readings[1]
    assert [line['indent'] for line in layout['lines']] == [2, 0, 2]
    assert [line['stanza'] for line in layout['lines']] == [0, 0, 1]
    mapping = json.loads((out / 'search-map.json').read_text())[0]
    assert [(t['raw_start'], t['raw_end']) for t in mapping['tokens']] == [(2, 6), (7, 10), (14, 17)]
    search = (out / 'search.txt').read_text()
    for token, line in zip(mapping['tokens'], layout['lines']):
        assert search[token['start']:token['end']] == POEM[token['raw_start']:token['raw_end']]
        assert token['bbox'] == line['bbox']
        assert token['observation_id'] == 'ocr-poem'
    assert before == (source.read_bytes(), path.read_bytes())
    assert report['usage']['provider_calls'] == 0
    assert validator.validate(validator.load(out / 'descriptor.json')) == []
    assert 'manual' in format_report(report) and 'stanza' in format_report(report)


def test_competing_caption_and_cross_page_continuations_are_not_selected(inputs, tmp_path):
    source, path, config = inputs
    for name in ('i1', 'i2'):
        config['pages']['2']['detections'].append({'id': name, 'kind': 'image', 'bbox': [150, 200, 20, 20]})
        config['pages']['2']['recognitions'][name] = {'raw_text': '', 'unresolved': []}
    config['pages']['3'] = copy.deepcopy(config['pages']['2'])
    alternatives = [proposal('model', id='caption-links', region_id='page-2-c1', text='?', lines=[],
                             relations=[{'kind': 'caption-of', 'target': 'page-2-i1'},
                                        {'kind': 'caption-of', 'target': 'page-2-i2'}]),
                    proposal('model', id='continuations', lines=[],
                             relations=[{'kind': 'continues-to', 'target': 'page-3-p1'},
                                        {'kind': 'continues-to', 'target': 'page-3-c1'}])]
    write(path, config, alternatives)
    out = tmp_path / 'alternatives'
    code, _ = cli('run', '--source', source, '--pages', '2,3', '--config', path, '--output', out)
    assert code == 2
    code, report = cli('inspect', '--run', out, '--json')
    assert code == 0
    observations = report['structure']['observations']
    for expected in alternatives:
        actual = next(o for o in observations if o['id'] == expected['id'])
        assert actual['relations'] == expected['relations'] and actual['status'] == 'unresolved'
        region = next(r for r in report['regions'] if r['region_id'] == expected['region_id'])
        assert len(region['alternatives']) == 2
        assert any(u['region_id'] == region['region_id'] and u['reason'] == 'structural-alternatives'
                   for u in report['unresolved'])
    descriptor = validator.load(out / 'descriptor.json')
    assert not any(r['kind'] in ('caption-of', 'continues-to') for r in descriptor['relations'])


@pytest.mark.parametrize('bad', [None, [], {'producer': {}}, {'text': 4}, {'lines': 'bad'},
    {'lines': [{'start': 0, 'end': 6, 'bbox': [290, 60, 60, 10]}]},
    {'lines': [{'start': 0, 'end': 999, 'bbox': [40, 60, 60, 10]}]},
    {'relations': [{'kind': 'continues-to', 'target': 'missing'}]},
    {'kind': 'unattributed'}, {'unexpected': True}, {'id': 'ocr-poem'}])
def test_bad_proposal_retains_last_valid_output_and_diagnostic(inputs, tmp_path, bad):
    source, path, config = inputs
    invalid = {**proposal('model'), **bad} if isinstance(bad, dict) else bad
    write(path, config, [proposal(), invalid])
    out = tmp_path / 'invalid-proposal'
    code, _ = cli('run', '--source', source, '--pages', '2', '--config', path, '--output', out)
    assert code == 2
    _, report = cli('inspect', '--run', out, '--json')
    assert report['regions'][0]['raw_text'] == POEM
    assert report['regions'][0]['layout_text'] == POEM
    assert [o['id'] for o in report['structure']['observations'] if o.get('lines')] == ['ocr-poem']
    diagnostic = report['structure']['diagnostics'][0]
    assert diagnostic['reason'] == 'invalid-structure' and diagnostic['detail']
    retained = next(o for o in report['structure']['observations'] if o['id'] == 'ocr-poem')
    assert retained['text'] == POEM and [line['bbox'] for line in retained['lines']] == [line['bbox'] for line in proposal()['lines']]
    assert any(u['reason'] == 'invalid-structure' for u in report['unresolved'])


def test_structure_only_change_reuses_ocr_and_corruption_refuses_inspection(inputs, tmp_path):
    from digitization.inspection import IntegrityError
    source, path, config = inputs
    write(path, config, [proposal()])
    cache = tmp_path / 'cache'
    first, second = tmp_path / 'first', tmp_path / 'second'
    run(source, [2], path, first, cache_dir=cache)
    write(path, config, [proposal(), proposal('manual')])
    run(source, [2], path, second, cache_dir=cache)
    report = inspect_run(second)
    assert report['usage']['recorded_observations'] == 0
    assert report['usage']['cache_hits'] == 2
    assert any(o['kind'] == 'manual' for o in report['structure']['observations'])
    (second / 'structure.json').write_text('{}')
    with pytest.raises(IntegrityError, match='digest'):
        inspect_run(second)


@pytest.mark.parametrize('invalid', [{}, None, 'invalid', 5])
def test_malformed_page_envelope_is_visible_even_without_ocr_uncertainty(inputs, tmp_path, invalid):
    source, path, config = inputs
    config['pages']['2']['recognitions']['c1']['unresolved'] = []
    write(path, config, invalid)
    out = tmp_path / 'bad-envelope'
    result = run(source, [2], path, out)
    assert result['status'] == 'stopped-with-unresolved-work'
    assert inspect_run(out)['structure']['diagnostics'][0]['reason'] == 'invalid-structure'
