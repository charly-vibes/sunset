# Purpose: Verify offline reconstruction of selected digitization artifacts.
# Responsibilities: Pin replay equality, failure classification, run isolation,
#   and provenance for original execution data and separate fresh comparisons.
# Rationale: sunset-rmx.8 must reconstruct only verified recorded outputs without
#   inference, network access, source mutation or invented measurements.
import copy
import hashlib
import json
import contextlib
from pathlib import Path
import socket
import subprocess
import sys

import pymupdf
import pytest

from digitization.pipeline import run
from digitization.replay import replay as replay_run

ROOT = Path(__file__).resolve().parents[2]

LOCAL_POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 2,
                'max_provider_attempts': 8, 'max_estimated_cost_microunits': 100,
                'max_request_bytes': 1 << 20, 'max_output_bytes': 1 << 20,
                'price_schedule_sha256': 'c' * 64}

LOCAL_IDENTITY = {'kind': 'local', 'id': 'tesseract-ocr', 'version': '5.5.1',
                  'language': 'spa', 'route': 'regional'}


def fake_engine(texts):
    """Runner writing one txt per invocation; records every invocation."""
    calls = []
    counter = {'n': 0}

    def runner(cmd, timeout):
        counter['n'] += 1
        payload = Path(cmd[1]).read_bytes()
        calls.append({'payload': payload, 'argv': list(cmd)})
        Path(cmd[2] + '.txt').write_bytes(texts[counter['n'] - 1])
        return '', 0
    runner.calls = calls
    return runner


@contextlib.contextmanager
def forbid_engines():
    """Context failing the test on any engine or network attempt."""
    mp = pytest.MonkeyPatch()

    def forbidden(name):
        def trip(*args, **kwargs):
            pytest.fail(f'{name} must not happen during replay')
        return trip
    mp.setattr(subprocess, 'Popen', forbidden('real engine'))
    mp.setattr(subprocess, 'run', forbidden('real engine'))
    mp.setattr(socket, 'socket', forbidden('network'))
    try:
        yield
    finally:
        mp.undo()


@pytest.fixture
def local_setup(tmp_path):
    """A two-block source page plus a builder producing completed local runs."""
    source = tmp_path / 'two-blocks.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Primer parrafo con contenido real')
        page.insert_text((30, 300), 'Segundo parrafo distante abajo')
        pdf.save(source)

    def build(texts, name):
        runner = fake_engine(texts)
        config_path = tmp_path / f'{name}-config.json'
        config_path.write_text(json.dumps(local_config(source)))
        output = tmp_path / name
        result = run(source, [1], config_path, output, runner=runner)
        assert result['status'] == 'completed' and result['provider_calls'] == len(texts), result
        return output, runner
    return build


def local_config(source):
    return {'version': '1',
            'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            'provider': LOCAL_IDENTITY, 'render': {'dpi': 96}, 'pages': {},
            'budget': LOCAL_POLICY}


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.fixture
def make_run(tmp_path):
    source = tmp_path / 'source.pdf'
    with pymupdf.open() as pdf:
        pdf.new_page(width=300, height=400)
        pdf.save(source)
    cache = tmp_path / 'cache'
    config = {'version': '1', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'provider': {'kind': 'recorded', 'id': 'fixture', 'version': '1',
                           'model': {'id': 'alias', 'revision': None}},
              'render': {'dpi': 72},
              'pages': {'1': {'detections': [{'id': 'p1', 'kind': 'poem',
                                              'bbox': [20, 30, 120, 100]}],
                              'recognitions': {'p1': {'raw_text': 'luna', 'unresolved': []}}}}}

    def create(name, raw_text='luna', *, fresh=False):
        value = copy.deepcopy(config)
        value['pages']['1']['recognitions']['p1']['raw_text'] = raw_text
        config_path = tmp_path / f'{name}.json'
        config_path.write_text(json.dumps(value))
        output = tmp_path / name
        flags = ['--fresh', 'page-1-p1'] if fresh else []
        code, result = cli('run', '--source', source, '--pages', '1', '--config', config_path,
                           '--output', output, '--cache', cache, *flags)
        assert code == 0, result
        return output

    return create


def files(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def test_replay_reconstructs_verified_outputs_and_keeps_resume_available(make_run, tmp_path):
    original = make_run('original')
    before = files(original)
    output = tmp_path / 'replayed'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 0 and result['status'] == 'replayed'
    assert result['provider_calls'] == 0
    manifest = json.loads((original / 'manifest.json').read_text())
    for relative in manifest['artifacts']:
        assert (output / relative).read_bytes() == (original / relative).read_bytes()
    assert json.loads((output / 'replay-report.json').read_text())['status'] == 'replayed'
    assert files(original) == before
    code, resumed = cli('resume', '--run', original)
    assert code == 0 and resumed['status'] == 'completed'


def test_missing_response_is_incomplete_without_creating_output(make_run, tmp_path):
    original = make_run('original')
    manifest = json.loads((original / 'manifest.json').read_text())
    response = manifest['operations']['page-1-p1']['attempts'][0]['output']['path']
    (original / response).unlink()
    output = tmp_path / 'incomplete'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 2 and result['status'] == 'incomplete-artifacts'
    assert result['reason'] == 'incomplete-artifacts' and result['provider_calls'] == 0
    assert not output.exists()


def test_corrupt_artifact_is_integrity_failure_without_repair(make_run, tmp_path):
    original = make_run('original')
    damaged = original / 'search.txt'
    damaged.write_text('tampered')
    before = files(original)
    output = tmp_path / 'corrupt-replay'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 5 and result['reason'] == 'integrity-failure'
    assert result['provider_calls'] == 0 and not output.exists()
    assert files(original) == before


def test_unknown_manifest_version_is_unsupported(make_run, tmp_path):
    original = make_run('original')
    path = original / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['version'] = 'future'
    path.write_text(json.dumps(manifest))
    output = tmp_path / 'future-replay'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 4 and result['status'] == 'unsupported-version'
    assert result['provider_calls'] == 0 and not output.exists()


def test_original_envelope_is_retained_and_fresh_change_is_reported(make_run, tmp_path):
    original = make_run('original')
    manifest_path = original / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    usage = dict(manifest['usage'], estimated_charge_microunits=70, runtime_seconds=0.3)
    ledger_bytes = (json.dumps(usage, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False) + '\n').encode()
    (original / 'ledger.json').write_bytes(ledger_bytes)
    manifest['usage'] = usage
    manifest['artifacts']['ledger.json']['sha256'] = hashlib.sha256(ledger_bytes).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':')) + '\n')
    fresh = make_run('fresh', 'una', fresh=True)
    before = files(original)
    output = tmp_path / 'comparison'
    code, result = cli('replay', '--run', original, '--output', output, '--compare', fresh)
    assert code == 0 and result['status'] == 'replayed'
    report = json.loads((output / 'replay-report.json').read_text())
    assert report['execution_envelope']['origin'] == 'original-run'
    assert report['execution_envelope']['usage']['estimated_charge_microunits'] == 70
    assert report['execution_envelope']['usage']['runtime_seconds'] == 0.3
    assert report['fresh_comparison']['differences'] == [
        {'region_id': 'page-1-p1', 'recorded': 'luna', 'fresh': 'una', 'status': 'different'}]
    assert files(original) == before


def test_local_run_replays_without_inference(local_setup, tmp_path):
    original, runner = local_setup([b'  primer bloque\n', b'\nsegundo bloque\n'], 'local-original')
    invocations = len(runner.calls)
    before = files(original)
    replayed = tmp_path / 'local-replayed'
    with forbid_engines():
        result = replay_run(original, replayed)
    assert result['status'] == 'replayed' and result['reason'] == 'replay-verified'
    assert result['provider_calls'] == 0
    manifest = json.loads((original / 'manifest.json').read_text())
    for relative in manifest['artifacts']:
        assert (replayed / relative).read_bytes() == (original / relative).read_bytes()
    report = json.loads((replayed / 'replay-report.json').read_text())
    assert report['status'] == 'replayed'
    assert report['execution_envelope']['origin'] == 'original-run'
    assert report['execution_envelope']['fresh_measurement'] is False
    assert report['execution_envelope']['usage']['mode'] == 'local'
    assert 'ledger.json' not in report['semantic_artifacts']
    assert report['semantic_sha256'] == result['semantic_sha256']
    assert files(original) == before
    assert len(runner.calls) == invocations


def test_local_replay_reports_fresh_differences_separately(local_setup, tmp_path):
    recorded_run, _ = local_setup([b'  primer bloque\n', b'\nsegundo bloque\n'], 'local-a')
    fresh_run, _ = local_setup([b'otra lectura\n', b'\nlectura distinta\n'], 'local-b')
    before = files(recorded_run)
    replayed = tmp_path / 'local-comparison'
    with forbid_engines():
        result = replay_run(recorded_run, replayed, compare=fresh_run)
    assert result['status'] == 'replayed' and result['provider_calls'] == 0
    differences = result['fresh_comparison']['differences']
    assert {difference['region_id'] for difference in differences} == {'page-1-det-1', 'page-1-det-2'}
    assert all(difference['status'] == 'different' for difference in differences)
    assert sorted(difference['recorded'] for difference in differences) == ['\nsegundo bloque\n', '  primer bloque\n']
    assert sorted(difference['fresh'] for difference in differences) == ['\nlectura distinta\n', 'otra lectura\n']
    report = json.loads((replayed / 'replay-report.json').read_text())
    assert report['fresh_comparison']['fresh_run_manifest'] == str((fresh_run / 'manifest.json').resolve())
    assert files(recorded_run) == before


def test_local_corrupt_artifact_is_integrity_failure(local_setup, tmp_path):
    original, _ = local_setup([b'  primer bloque\n', b'\nsegundo bloque\n'], 'local-corrupt')
    blob = next((original / 'artifacts').iterdir())
    blob.write_bytes(b'tampered')
    output = tmp_path / 'local-corrupt-replay'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 5 and result['reason'] == 'integrity-failure'
    assert result['provider_calls'] == 0 and not output.exists()


def test_local_missing_artifact_is_incomplete(local_setup, tmp_path):
    original, _ = local_setup([b'  primer bloque\n', b'\nsegundo bloque\n'], 'local-missing')
    blob = next((original / 'artifacts').iterdir())
    blob.unlink()
    output = tmp_path / 'local-missing-replay'
    code, result = cli('replay', '--run', original, '--output', output)
    assert code == 2 and result['status'] == 'incomplete-artifacts'
    assert result['provider_calls'] == 0 and not output.exists()
