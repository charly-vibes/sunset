"""Contract tests for recorded configs generated from native text (sunset-bv4).

The recorded digitization pipeline needs a per-document config (detections +
recorded recognitions). For a PDF with a native text layer that config can be
derived mechanically from the source itself: pymupdf text blocks become
detections (y-down page-point bboxes, the reader's own report), the extracted
text becomes the recorded recognitions, and the pinned pymupdf identity acts
as the recorded provider. No hand-authored configs, no live OCR — the
existing tested pipeline machinery then produces geometry-bearing descriptors
for real documents.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from dsc03 import validator
from dsc03.profiles import Registry, resolve as resolve_profile

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cli(*args):
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization.recorded_config', *map(str, args)],
        cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'native-text.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Resumen Caja de Ahorro')
        page.insert_text((30, 60), 'SALDO ANTERIOR 1.234,56')
        page2 = pdf.new_page(width=300, height=400)
        page2.insert_text((30, 40), 'Segunda pagina sin deudas')
        pdf.save(path)
    return path


def test_generated_config_shape_and_provider_pin(source, tmp_path):
    out = tmp_path / 'recorded.json'
    code, result = cli('--source', source, '--output', out)
    assert code == 0 and result['status'] == 'recorded-config'
    config = json.loads(out.read_text())
    assert config['version'] == '1'
    assert config['source_sha256'] == sha(source.read_bytes())
    assert config['provider'] == {'kind': 'recorded', 'id': 'pymupdf-native-text',
                                  'version': pymupdf.__version__}
    assert config['render'] == {'dpi': 72}
    assert sorted(config['pages']) == ['1', '2']
    for number, page in config['pages'].items():
        assert page['detections'], number
        for detection in page['detections']:
            x, y, w, h = detection['bbox']
            assert type(x) is int and type(y) is int and type(w) is int and type(h) is int
            assert 0 <= x and 0 <= y and w > 0 and h > 0
            assert x + w <= 300 and y + h <= 400
            assert detection['kind'] == 'text-block'
        assert set(page['recognitions']) == {d['id'] for d in page['detections']}
        assert all(r['raw_text'].strip() and r['unresolved'] == []
                   for r in page['recognitions'].values())
    first_page_text = ' '.join(r['raw_text'] for r in config['pages']['1']['recognitions'].values())
    assert 'Resumen Caja de Ahorro' in first_page_text
    assert 'SALDO ANTERIOR 1.234,56' in first_page_text


def test_generated_config_runs_the_real_pipeline(source, tmp_path):
    config_path = tmp_path / 'recorded.json'
    code, _ = cli('--source', source, '--output', config_path)
    assert code == 0
    out = tmp_path / 'run'
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'digitization', 'run', '--source', source,
         '--pages', '1,2', '--config', config_path, '--output', out],
        cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((out / 'manifest.json').read_text())
    descriptor = validator.load(out / manifest['descriptor']['path'])
    assert validator.validate(descriptor) == []
    geometry_profile = next(p for p in descriptor['profiles'] if p['kind'] == 'geometry')
    status, artifact = resolve_profile(geometry_profile, Registry(out))
    assert status == 'resolved'
    assert all(f['origin'] == 'bottom-left' and f['axes'] == 'x-right-y-up'
               for f in artifact['frames'])
    claimed = [r for r in descriptor['regions'] if 'geometry' in r]
    assert claimed, 'generated config must produce geometry-bearing claims'
    for region in claimed:
        x, y, w, h = (region['geometry']['x'], region['geometry']['y'],
                      region['geometry']['width'], region['geometry']['height'])
        assert x >= 0 and y >= 0 and w > 0 and h > 0
        assert x + w <= 300 and y + h <= 400
    texts = ' '.join(c['value'] for c in descriptor['contents'] if c['kind'] == 'text')
    assert 'SALDO ANTERIOR 1.234,56' in texts
    assert 'Segunda pagina sin deudas' in texts


def test_page_selection_restricts_the_config(source, tmp_path):
    out = tmp_path / 'recorded.json'
    code, result = cli('--source', source, '--output', out, '--pages', '2')
    assert code == 0
    config = json.loads(out.read_text())
    assert sorted(config['pages']) == ['2']


def test_unreadable_source_is_typed_invalid(tmp_path):
    bogus = tmp_path / 'bogus.pdf'
    bogus.write_bytes(b'not a pdf')
    code, result = cli('--source', bogus, '--output', tmp_path / 'c.json')
    assert code == 3
    assert result['status'] == 'invalid-input'
