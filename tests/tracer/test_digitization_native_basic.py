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
from dsc03.identity import derive_id
from dsc03.inspect import build_index
from dsc03.locators import resolve
from dsc03.profiles import Registry, resolve as resolve_profile, resolve_frame

ROOT = Path(__file__).resolve().parents[2]
IDENTITY_PROFILE_ID = 'p-identity'
IDENTITY_PROFILE_VERSION = '1'


def native_id(source_hash, record_kind, locator_path):
    """The anchor-derived id native descriptors must carry for one record."""
    return derive_id((source_hash, record_kind, locator_path,
                      IDENTITY_PROFILE_ID, IDENTITY_PROFILE_VERSION))[1]


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
    assert code == 0 and result['status'] == 'text-complete', result
    assert result['provider_calls'] == 0
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['source']['sha256'] == source_hash
    assert manifest['mode'] == 'native'
    assert manifest['version'] == '2'
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
    page1_id = native_id(source_hash, 'region', 'page:1')
    assert resolve(build_index(descriptor), page1_id).status == 'resolved'

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
    assert code == 0 and selected['status'] == 'text-complete'
    selected_manifest = json.loads((selected_output / 'manifest.json').read_text())
    assert selected_manifest['pages'] == [2]
    assert [word['page'] for word in json.loads((selected_output / 'word-map.json').read_text())] == [2, 2]


def annotated_fixture(path):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 60), 'Alpha beta', fontsize=12)
        page.add_text_annot(pymupdf.Point(40, 70), 'first note')
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 60), 'Gamma delta', fontsize=12)
        page.add_text_annot(pymupdf.Point(40, 70), 'second note')
        pdf.save(path)


def test_native_emits_identity_profile_descriptors(tmp_path):
    """add-anchor-derived-identity task 5.2: record ids are anchor derivations
    under a declared identity profile, pinned like the selector/geometry pins."""
    source, output = tmp_path / 'identity.pdf', tmp_path / 'run'
    pdf_fixture(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    code, result = cli('native', '--source', source, '--output', output)
    assert code == 0 and result['status'] == 'text-complete', result
    descriptor = validator.load(output / 'descriptor.json')
    assert validator.validate(descriptor) == []

    identity_profile = next(p for p in descriptor['profiles'] if p['kind'] == 'identity')
    assert identity_profile['id'] == IDENTITY_PROFILE_ID
    assert identity_profile['version'] == IDENTITY_PROFILE_VERSION
    artifact_bytes = (output / 'carrier' / 'identity.json').read_bytes()
    assert identity_profile['sha256'] == hashlib.sha256(artifact_bytes).hexdigest()
    assert json.loads(artifact_bytes) == {
        'kind': 'identity', 'version': '1',
        'digest': {'algorithm': 'sha256', 'truncation_bits': 128, 'prefix': 'a:'}}
    status, artifact = resolve_profile(identity_profile, Registry(output))
    assert status == 'resolved' and artifact['digest']['truncation_bits'] == 128

    # every validated record id equals the derivation of its declared anchor;
    # selectors derive from their own source_sha256 field
    for section, kind in (('regions', 'region'), ('contents', 'content'),
                          ('selectors', 'selector'), ('evidence', 'evidence')):
        for record in descriptor[section]:
            anchor = record['anchor']
            assert anchor['record_kind'] == kind
            record_source = record['source_sha256'] if kind == 'selector' else source_hash
            assert record['id'] == native_id(record_source, kind, anchor['locator_path'])
            assert record['id'].startswith('a:')
    rotated_sections = ('regions', 'contents', 'selectors', 'evidence', 'annotations')
    assert all(record['id'].startswith('a:')
               for section in rotated_sections for record in descriptor[section])

    # page selection does not change ids (document-identity scenario):
    # page 2's region id survives a selection that drops page 1
    selected_output = tmp_path / 'selected'
    code, selected = cli('native', '--source', source, '--pages', '2', '--output', selected_output)
    assert code == 0 and selected['status'] == 'text-complete', selected
    selected_descriptor = validator.load(selected_output / 'descriptor.json')
    page2_id = native_id(source_hash, 'region', 'page:2')
    assert {r['id'] for r in descriptor['regions']
            if r['anchor']['locator_path'] == 'page:2'} == {page2_id}
    assert page2_id in {r['id'] for r in selected_descriptor['regions']}


def test_native_annotation_page_binding_comes_from_declared_target_anchor(tmp_path):
    """The an{page}- prefix match is gone: a source annotation whose target
    content was excluded demotes to its declared target page (from the
    annotation's own anchor), not from id spelling."""
    source, output = tmp_path / 'annotated.pdf', tmp_path / 'run'
    annotated_fixture(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    code, result = cli('native', '--source', source, '--pages', '1', '--output', output)
    assert code == 0, result
    descriptor = validator.load(output / 'descriptor.json')
    assert validator.validate(descriptor) == []
    assert len(descriptor['annotations']) == 2

    content1 = native_id(source_hash, 'content', 'page:1')
    page2 = native_id(source_hash, 'region', 'page:2')
    kept = next(a for a in descriptor['annotations'] if a['target'] == content1)
    demoted = next(a for a in descriptor['annotations'] if a['target'] == page2)
    assert kept['status'] == 'supported'
    assert kept['evidence'] == [native_id(source_hash, 'evidence', 'page:1')]
    assert demoted['status'] == 'asserted_without_evidence'
    assert demoted['evidence'] == []
    assert kept['id'] == derive_id((source_hash, 'annotation', 'page:1/annots:1',
                                    IDENTITY_PROFILE_ID, IDENTITY_PROFILE_VERSION))[1]
    assert demoted['id'] == derive_id((source_hash, 'annotation', 'page:2/annots:1',
                                       IDENTITY_PROFILE_ID, IDENTITY_PROFILE_VERSION))[1]


def test_native_descriptors_are_byte_identical_across_runs(tmp_path):
    """Independent-derivation determinism: two extractions of one carrier into
    two run directories emit identical descriptor bytes."""
    source = tmp_path / 'same.pdf'
    pdf_fixture(source)
    first, second = tmp_path / 'first', tmp_path / 'second'
    assert cli('native', '--source', source, '--output', first)[0] == 0
    assert cli('native', '--source', source, '--output', second)[0] == 0
    assert (first / 'descriptor.json').read_bytes() == (second / 'descriptor.json').read_bytes()
