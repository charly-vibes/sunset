# Purpose: Verify selective recorded-operation reuse through the public digitizer.
# Responsibilities: Exercise request invalidation, integrity refusal, fresh output
#   retention, explicit selection and concurrent attempt preservation offline.
# Rationale: sunset-rmx.3 must never replace a selected reading on a silent miss.
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.fixture
def example(tmp_path):
    source = tmp_path / 'source.pdf'
    with pymupdf.open() as pdf:
        pdf.new_page(width=300, height=400)
        pdf.save(source)
    config = {'version': '1', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'provider': {'kind': 'recorded', 'id': 'fixture', 'version': '1',
                           'model': {'id': 'alias-only', 'revision': None}},
              'render': {'dpi': 72},
              'pages': {'1': {'detections': [
                  {'id': 'p1', 'kind': 'poem', 'bbox': [20, 20, 100, 80]},
                  {'id': 'c1', 'kind': 'caption', 'bbox': [20, 150, 100, 20]}],
                  'recognitions': {'p1': {'raw_text': 'luna', 'unresolved': []},
                                   'c1': {'raw_text': 'caption', 'unresolved': []}}}}}
    path = tmp_path / 'config.json'
    cache = tmp_path / 'cache'

    def start(name, configuration=None, *flags):
        path.write_text(json.dumps(config if configuration is None else configuration))
        out = tmp_path / name
        code, result = cli('run', '--source', source, '--pages', '1', '--config', path,
                           '--output', out, '--cache', cache, *flags)
        assert code == 0, result
        manifest = json.loads((out / 'manifest.json').read_text())
        return out, manifest
    return config, start, source, path, cache


def text_at(out, region):
    code, report = cli('inspect', '--run', out, '--json')
    assert code == 0, report
    return next(r['raw_text'] for r in report['regions'] if r['region_id'] == region)


def test_prompt_change_reuses_unrelated_region_and_pins_cache_hits(example):
    config, start, source, _, _ = example
    source_before = source.read_bytes()
    first, original = start('first')
    updated = copy.deepcopy(config)
    updated['pages']['1']['recognition_overrides'] = {'p1': {'prompt': 'retain poem whitespace'}}
    updated['pages']['1']['recognitions']['p1']['raw_text'] = '  luna\nmar'
    updated['pages']['1']['recognitions']['c1']['raw_text'] = 'must not silently replace caption'
    second, changed = start('second', updated)
    old, new = original['operations'], changed['operations']
    assert old['page-1-p1']['key'] != new['page-1-p1']['key']
    assert new['page-1-p1']['cache_hit'] is False
    assert old['page-1-c1']['key'] == new['page-1-c1']['key']
    assert new['page-1-c1']['cache_hit'] is True
    assert old['page-1-c1']['selected_attempt'] == new['page-1-c1']['selected_attempt']
    assert changed['usage']['cache_hits'] == 1 and changed['usage']['recorded_observations'] == 1
    assert text_at(second, 'page-1-p1') == '  luna\nmar'
    assert text_at(second, 'page-1-c1') == 'caption'
    assert text_at(first, 'page-1-p1') == 'luna'
    assert source.read_bytes() == source_before


def test_fresh_outputs_survive_and_selection_stays_explicit(example):
    config, start, _, _, _ = example
    first, original = start('original')
    changed = copy.deepcopy(config)
    changed['pages']['1']['recognitions']['p1']['raw_text'] = 'una'
    fresh, fresh_manifest = start('fresh', changed, '--fresh', 'page-1-p1')
    old = original['operations']['page-1-p1']
    new = fresh_manifest['operations']['page-1-p1']
    assert old['key'] == new['key']
    assert old['selected_attempt'] != new['selected_attempt']
    assert old['selected_output'] != new['selected_output']
    assert {a['output']['sha256'] for a in new['attempts']} == {old['selected_output'], new['selected_output']}
    assert text_at(first, 'page-1-p1') == 'luna' and text_at(fresh, 'page-1-p1') == 'una'
    default, default_manifest = start('default', changed)
    assert default_manifest['operations']['page-1-p1']['selected_attempt'] == old['selected_attempt']
    assert text_at(default, 'page-1-p1') == 'luna'
    selected, selected_manifest = start('selected', changed, '--select', 'page-1-p1=' + new['selected_attempt'])
    assert text_at(selected, 'page-1-p1') == 'una'
    assert selected_manifest['operations']['page-1-p1']['selected_attempt'] == new['selected_attempt']
    _, report = cli('inspect', '--run', fresh, '--json')
    request = report['operations']['page-1-p1']['request']
    assert request['provider']['model']['revision'] is None
    assert request['model_revision_available'] is False
    assert new['fresh_determinism'] == 'not-claimed'
    for attempt in new['attempts']:
        assert hashlib.sha256((fresh / attempt['output']['path']).read_bytes()).hexdigest() == attempt['output']['sha256']


def test_corrupt_cached_response_is_refused_without_replacement(example, tmp_path):
    _, start, source, path, cache = example
    original, manifest = start('original')
    op = manifest['operations']['page-1-p1']
    blob = cache / 'blobs' / op['selected_output']
    blob.write_bytes(b'corrupted')
    before = {str(p): p.read_bytes() for p in original.rglob('*') if p.is_file()}
    code, result = cli('run', '--source', source, '--pages', '1', '--config', path,
                       '--output', tmp_path / 'refused', '--cache', cache)
    assert code == 5 and result['reason'] == 'cache-integrity-failure'
    assert result['provider_calls'] == 0 and not (tmp_path / 'refused').exists()
    assert blob.read_bytes() == b'corrupted'
    assert before == {str(p): p.read_bytes() for p in original.rglob('*') if p.is_file()}


@pytest.mark.parametrize('field', ['prompt', 'schema', 'language', 'preprocessing', 'decoding', 'policy', 'provider', 'model', 'render', 'crop'])
def test_request_changes_invalidate_bound_operations(example, field):
    config, start, _, _, _ = example
    _, original = start('original')
    changed = copy.deepcopy(config)
    if field in {'prompt', 'schema', 'language', 'preprocessing', 'decoding', 'policy'}:
        changed['recognition'] = {field: 'changed' if field in {'prompt','schema','language'} else {'version': 'changed'}}
    elif field == 'provider': changed['provider']['version'] = '2'
    elif field == 'model': changed['provider']['model']['revision'] = 'revision-2'
    elif field == 'render': changed['render']['dpi'] = 144
    elif field == 'crop': changed['pages']['1']['detections'][0]['bbox'][0] += 1
    _, new = start('changed', changed)
    assert new['operations']['page-1-p1']['key'] != original['operations']['page-1-p1']['key']
    assert new['operations']['page-1-p1']['cache_hit'] is False
    if field == 'crop': assert new['operations']['page-1-c1']['cache_hit'] is True


def test_concurrent_fresh_attempts_are_both_retained(tmp_path):
    from digitization.artifacts import OperationCache
    cache = OperationCache(tmp_path / 'cache')
    request = {'version': '1', 'operation': 'recognize', 'inputs': ['source-and-crop'], 'policy': 'fixed'}
    def produce(word):
        return cache.resolve(request, lambda: {'raw_text': word, 'unresolved': []}, fresh=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(produce, ['luna', 'una']))
    assert len({r['selected_attempt'] for r in results}) == 2
    final = cache.resolve(request, lambda: pytest.fail('cache unexpectedly missed'))
    assert len(final['attempts']) == 2
    assert {cache.read_response(a)['raw_text'] for a in final['attempts']} == {'luna','una'}


def test_invalid_cached_output_shape_is_not_admitted(tmp_path):
    from digitization.artifacts import OperationCache
    cache = OperationCache(tmp_path / 'cache')
    with pytest.raises(ValueError):
        cache.resolve({'operation': 'recognize'}, lambda: {'raw_text': 7, 'unresolved': []})
    assert not list((tmp_path / 'cache').rglob('*.attempt.json'))


def test_corrupt_request_refuses_fresh_import_before_admission(example, tmp_path):
    config, start, source, path, cache = example
    _, manifest = start('original')
    key = manifest['operations']['page-1-p1']['key']
    (cache / 'operations' / key / 'request.json').write_text('{}')
    snapshot = {str(p): p.read_bytes() for p in cache.rglob('*') if p.is_file()}
    updated = copy.deepcopy(config)
    updated['pages']['1']['recognitions']['p1']['raw_text'] = 'new response must not be admitted'
    path.write_text(json.dumps(updated))
    code, result = cli('run', '--source', source, '--pages', '1', '--config', path,
                       '--output', tmp_path / 'refused-fresh', '--cache', cache, '--fresh', 'page-1-p1')
    assert code == 5 and result['reason'] == 'cache-integrity-failure'
    assert not (tmp_path / 'refused-fresh').exists()
    assert snapshot == {str(p): p.read_bytes() for p in cache.rglob('*') if p.is_file()}


@pytest.mark.parametrize('flags', [('--fresh', 'unknown'), ('--select', 'page-1-p1=missing'),
                                   ('--fresh', 'page-1-p1', '--select', 'page-1-p1=missing')])
def test_invalid_selection_cannot_publish_a_run(example, tmp_path, flags):
    _, start, source, path, cache = example
    start('original')
    code, result = cli('run', '--source', source, '--pages', '1', '--config', path,
                       '--output', tmp_path / 'bad-selection', '--cache', cache, *flags)
    assert code == 3 and result['provider_calls'] == 0
    assert not (tmp_path / 'bad-selection').exists()


def test_reused_and_fresh_attempts_need_no_network_or_provider_process(example, tmp_path, monkeypatch):
    import socket
    from digitization.pipeline import run
    from digitization.inspection import inspect_run
    config, start, source, path, cache = example
    start('original')
    def forbidden(*args, **kwargs):
        pytest.fail('recorded cache invoked external I/O')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = run(source, [1], path, tmp_path / 'offline', cache_dir=cache, fresh=['page-1-p1'])
    report = inspect_run(Path(result['manifest']).parent)
    assert report['usage']['provider_calls'] == 0 and report['usage']['cache_hits'] == 1
