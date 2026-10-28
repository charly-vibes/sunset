# Purpose: Verify the first recorded digitization journey through the public CLI.
# Responsibilities: Pin source/text/geometry outputs, input refusals, attribution,
#   read-only inspection and explicit unsupported resume/replay behavior.
# Rationale: sunset-rmx.2 needs executable source-linked output before real OCR.
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pymupdf
import pytest

from dsc03 import validator
from dsc03.inspect import build_index
from dsc03.locators import resolve
from dsc03.profiles import Registry, resolve as resolve_profile

ROOT = Path(__file__).resolve().parents[2]
POEM = '  luna\nmar\n\n  sal'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.fixture
def inputs(tmp_path):
    source = tmp_path / 'six-pages.pdf'
    with pymupdf.open() as pdf:
        for n in range(6):
            page = pdf.new_page(width=300, height=400)
            page.insert_text((30, 40), f'Synthetic scan fixture page {n + 1}')
        pdf.save(source)
    config = {
        'version': '1', 'source_sha256': sha(source.read_bytes()),
        'provider': {'kind': 'recorded', 'id': 'fixture-ocr', 'version': '1'},
        'render': {'dpi': 72},
        'pages': {'2': {
            'detections': [
                {'id': 'p1', 'kind': 'poem', 'bbox': [30, 60, 100, 100]},
                {'id': 'c1', 'kind': 'caption', 'bbox': [30, 200, 100, 20]},
            ],
            'recognitions': {
                'p1': {'raw_text': POEM, 'unresolved': []},
                'c1': {'raw_text': '?', 'unresolved': ['caption-uncertain']},
            },
        }},
    }
    config_path = tmp_path / 'recorded.json'
    config_path.write_text(json.dumps(config))
    return source, config_path, config


def test_public_run_inspect_and_source_links(inputs, tmp_path):
    source, config_path, config = inputs
    before = source.read_bytes(), config_path.read_bytes()
    out = tmp_path / 'run'
    code, result = cli('run', '--source', source, '--pages', '2', '--config', config_path, '--output', out)
    assert code == 2
    assert result['status'] == 'stopped-with-unresolved-work'
    assert result['reason'] == 'recorded-unresolved'
    documentation = (ROOT / 'docs/src/digitization.org').read_text()
    snippet = re.search(r'\#\+name: partial-run-result\n\#\+begin_example\n(.*?)\n\#\+end_example', documentation, re.S).group(1)
    assert {**result, 'manifest': '<RUN>/manifest.json'} == json.loads(snippet)
    manifest_path = Path(result['manifest'])
    assert manifest_path == out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['source']['sha256'] == config['source_sha256']
    assert manifest['pages'] == [2]
    assert manifest['usage']['provider_calls'] == 0
    assert manifest['usage']['recorded_observations'] == 2
    assert manifest['usage']['estimated_charge_microunits'] == 0
    descriptor_path = out / manifest['descriptor']['path']
    descriptor = validator.load(descriptor_path)
    assert validator.validate(descriptor) == []
    assert 'attempts' not in descriptor
    for profile in descriptor['profiles']:
        assert resolve_profile(profile, Registry(out))[0] == 'resolved'
    selection = resolve(build_index(descriptor), 'page-2-p1')
    assert selection.status == 'resolved'
    assert selection.loci[0].page == 2
    assert selection.loci[0].rect == (30, 60, 100, 100)
    text = (out / 'search.txt').read_text()
    mappings = json.loads((out / 'search-map.json').read_text())
    poem_map = next(m for m in mappings if m['region_id'] == 'page-2-p1')
    assert text[poem_map['start']:poem_map['end']] == 'luna mar sal'
    assert poem_map['page'] == 2 and poem_map['selector_id'] == 'sel-page-2-p1'
    # Every pinned output is retained and its bytes actually match the digest.
    for artifact in manifest['artifacts'].values():
        assert sha((out / artifact['path']).read_bytes()) == artifact['sha256']
    render = manifest['renders']['2']
    with pymupdf.open(out / render['path']) as image:
        assert (image[0].rect.width, image[0].rect.height) == (300, 400)
    snapshot = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    code, report = cli('inspect', '--run', out, '--json')
    assert code == 0
    assert report['source']['sha256'] == config['source_sha256']
    poem = next(r for r in report['regions'] if r['local_id'] == 'p1')
    assert poem['raw_text'] == POEM and poem['layout_text'] == POEM
    assert poem['search_text'] == 'luna mar sal'
    assert poem['producer'] == config['provider']
    assert poem['selector']['locator'] == 'page:2 rect:30,60,100,100'
    assert poem['frame'] == 'page-2-pt'
    assert report['unresolved'][0]['region_id'] == 'page-2-c1'
    assert report['history'][0]['operation'] == 'detect'
    assert [e['operation'] for e in report['trace']] == ['render', 'detect', 'recognize', 'recognize', 'export']
    assert snapshot == {str(p.relative_to(out)): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    assert before == (source.read_bytes(), config_path.read_bytes())
    human = subprocess.run([sys.executable, '-m', 'digitization', 'inspect', '--run', str(out)],
                           cwd=ROOT, capture_output=True, text=True)
    assert human.returncode == 0 and 'caption-uncertain' in human.stdout and 'luna' in human.stdout


@pytest.mark.parametrize('case', ['page', 'config', 'nonempty', 'source-hash', 'geometry', 'provider', 'duplicate', 'missing-response'])
def test_invalid_inputs_never_dispatch_or_overwrite(inputs, tmp_path, case):
    source, config_path, config = inputs
    out = tmp_path / 'refused'
    pages = '2'
    if case == 'page': pages = '7'
    elif case == 'config': config_path = tmp_path / 'absent.json'
    elif case == 'nonempty':
        out.mkdir()
        (out / 'keep.txt').write_text('keep me')
    elif case == 'source-hash': config['source_sha256'] = '0' * 64
    elif case == 'geometry': config['pages']['2']['detections'][0]['bbox'] = [290, 60, 100, 100]
    elif case == 'provider': config['provider']['kind'] = 'remote'
    elif case == 'duplicate': config['pages']['2']['detections'].append(config['pages']['2']['detections'][0])
    elif case == 'missing-response': del config['pages']['2']['recognitions']['p1']
    if case not in {'config', 'nonempty', 'page'}: config_path.write_text(json.dumps(config))
    original_source = source.read_bytes()
    code, result = cli('run', '--source', source, '--pages', pages, '--config', config_path, '--output', out)
    assert code == 3 and result['status'] == 'invalid-input'
    assert result['provider_calls'] == 0
    assert source.read_bytes() == original_source
    assert not out.exists() or list(out.iterdir()) == [out / 'keep.txt']
    if out.exists(): assert (out / 'keep.txt').read_text() == 'keep me'


@pytest.mark.parametrize('operation', ['resume', 'replay'])
def test_unimplemented_operations_refuse_without_restarting(inputs, tmp_path, operation):
    source, config_path, _ = inputs
    run = tmp_path / 'original'
    cli('run', '--source', source, '--pages', '2', '--config', config_path, '--output', run)
    before = {str(p): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    args = [operation, '--run', run]
    if operation == 'replay': args += ['--output', tmp_path / 'replay']
    code, result = cli(*args)
    assert code == 4 and result['reason'] == 'unsupported-operation'
    assert result['provider_calls'] == 0
    assert before == {str(p): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    assert not (tmp_path / 'replay').exists()


def test_inspection_refuses_corrupted_evidence(inputs, tmp_path):
    source, config_path, _ = inputs
    out = tmp_path / 'run'
    cli('run', '--source', source, '--pages', '2', '--config', config_path, '--output', out)
    (out / 'search.txt').write_text('tampered')
    code, result = cli('inspect', '--run', out, '--json')
    assert code == 5 and result['reason'] == 'integrity-failure'


def test_recorded_journey_cannot_launch_inference_or_network(inputs, tmp_path, monkeypatch):
    import socket
    from digitization.pipeline import run
    from digitization.inspection import inspect_run

    def forbidden(*args, **kwargs):
        pytest.fail('recorded journey attempted external I/O')

    source, config_path, _ = inputs
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = run(source, [2], config_path, tmp_path / 'offline')
    report = inspect_run(Path(result['manifest']).parent)
    assert report['usage']['provider_calls'] == 0
    assert report['usage']['recorded_observations'] == 2


def test_invalid_pdf_is_classified_before_writing(inputs, tmp_path):
    source, config_path, config = inputs
    source.write_bytes(b'this is not a PDF')
    config['source_sha256'] = sha(source.read_bytes())
    config_path.write_text(json.dumps(config))
    out = tmp_path / 'bad-pdf'
    code, result = cli('run', '--source', source, '--pages', '2', '--config', config_path, '--output', out)
    assert code == 3 and result['status'] == 'invalid-input'
    assert not out.exists()


def test_complete_recorded_run_does_not_claim_quality(inputs, tmp_path):
    source, config_path, config = inputs
    config['pages']['2']['recognitions']['c1']['unresolved'] = []
    config_path.write_text(json.dumps(config))
    code, result = cli('run', '--source', source, '--pages', '2', '--config', config_path, '--output', tmp_path / 'complete')
    assert code == 0 and result['reason'] == 'recorded-inputs-consumed'
    _, report = cli('inspect', '--run', tmp_path / 'complete', '--json')
    assert report['coverage'] == 'unexamined-outside-recorded-regions'
    assert report['unresolved'] == []


@pytest.mark.parametrize('mutation', ['usage', 'usage-type', 'ledger-unbound'])
def test_inspection_rejects_manifest_ledger_disagreement(inputs, tmp_path, mutation):
    from digitization.pipeline import run
    from digitization.inspection import inspect_run, IntegrityError
    source, path, _ = inputs
    out = tmp_path / 'ledger'
    run(source, [2], path, out)
    assert inspect_run(out)['usage']['provider_calls'] == 0
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if mutation == 'usage':
        manifest['usage']['provider_calls'] = 999
    elif mutation == 'usage-type':
        manifest['usage']['provider_calls'] = False
    else:
        del manifest['artifacts']['ledger.json']
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(IntegrityError, match='ledger'):
        inspect_run(out)
