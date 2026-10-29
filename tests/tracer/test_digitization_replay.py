# Purpose: Verify offline reconstruction of selected digitization artifacts.
# Responsibilities: Pin replay equality, failure classification, run isolation,
#   and provenance for original execution data and separate fresh comparisons.
# Rationale: sunset-rmx.8 must reconstruct only verified recorded outputs without
#   inference, network access, source mutation or invented measurements.
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[2]


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
