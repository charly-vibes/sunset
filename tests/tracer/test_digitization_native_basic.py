# Purpose: Pin the public native PDF extraction journey for simple embedded text.
# Responsibilities: Exercise fresh-process extraction and inspection, including
#   source-bound word/line geometry and read-only artifact integrity.
# Rationale: sunset-jbb.1 establishes the native extraction baseline; sunset-jbb.3
#   distinguishes native-scope completion from visual completeness.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pymupdf

from dsc03 import validator
from dsc03.inspect import build_index
from dsc03.locators import resolve
from dsc03.profiles import Registry, resolve as resolve_profile, resolve_frame

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def pdf_fixture(path):
    with pymupdf.open() as pdf:
        for text in ('Alpha beta', 'Gamma delta'):
            page = pdf.new_page(width=300, height=400)
            page.insert_text((30, 60), text, fontsize=12)
        pdf.save(path)


def test_native_cli_extracts_and_inspects_source_attributed_words(tmp_path):
    source = tmp_path / 'two-pages.pdf'
    output = tmp_path / 'native-run'
    pdf_fixture(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    code, result = cli('native', '--source', source, '--output', output)
    assert code == 0 and result['status'] == 'complete', result
    assert result['provider_calls'] == 0
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['source']['sha256'] == source_hash
    assert manifest['mode'] == 'native'
    descriptor = validator.load(output / manifest['descriptor']['path'])
    assert validator.validate(descriptor) == []
    assert descriptor['source']['sha256'] == source_hash
    for profile in descriptor['profiles']:
        assert resolve_profile(profile, Registry(output))[0] == 'resolved'
    geometry = next(profile for profile in descriptor['profiles'] if profile['kind'] == 'geometry')
    geometry_status, geometry_artifact = resolve_profile(geometry, Registry(output))
    assert geometry_status == 'resolved'
    assert [resolve_frame(geometry_artifact, f'page-{page}-pt')[0] for page in (1, 2)] == [
        'resolved', 'resolved']
    assert resolve(build_index(descriptor), 'pg1').status == 'resolved'

    raw = (output / 'raw.txt').read_text()
    search = (output / 'search.txt').read_text()
    assert raw == 'Alpha beta\nGamma delta\n'
    # Native search text applies NFC and collapses layout whitespace between tokens.
    assert search == 'Alpha beta Gamma delta'
    mappings = json.loads((output / 'word-map.json').read_text())
    assert [item['text'] for item in mappings] == ['Alpha', 'beta', 'Gamma', 'delta']
    assert [item['page'] for item in mappings] == [1, 1, 2, 2]
    for item in mappings:
        assert item['source_sha256'] == source_hash
        assert item['frame'] == f"page-{item['page']}-pt"
        assert item['box'][2] > item['box'][0] and item['box'][3] > item['box'][1]
        assert raw[item['raw_start']:item['raw_end']] == item['text']
    lines = json.loads((output / 'line-map.json').read_text())
    assert all(item['source_sha256'] == source_hash and item['frame'] == f"page-{item['page']}-pt"
               for item in lines)
    assert [raw[item['raw_start']:item['raw_end']] for item in lines] == [
        'Alpha beta', 'Gamma delta']

    before = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    code, report = cli('inspect', '--run', output, '--json')
    assert code == 0 and report['mode'] == 'native'
    assert report['source']['sha256'] == source_hash
    assert [word['text'] for word in report['words']] == ['Alpha', 'beta', 'Gamma', 'delta']
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    human = subprocess.run([sys.executable, '-B', '-m', 'digitization', 'inspect', '--run', str(output)],
                           cwd=ROOT, capture_output=True, text=True)
    assert human.returncode == 0 and 'Alpha' in human.stdout and 'pymupdf' in human.stdout

    selected_output = tmp_path / 'selected-run'
    code, selected = cli('native', '--source', source, '--pages', '2', '--output', selected_output)
    assert code == 2 and selected['status'] == 'partial'
    selected_manifest = json.loads((selected_output / 'manifest.json').read_text())
    assert selected_manifest['pages'] == [2]
    assert [word['page'] for word in json.loads((selected_output / 'word-map.json').read_text())] == [2, 2]
