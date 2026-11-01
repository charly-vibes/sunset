# Purpose: Pin deterministic native artifacts and offline replay integrity.
# Responsibilities: Exercise public native extraction, read-only inspection,
#   deterministic semantic identities, replay copies and malformed artifact refusal.
# Rationale: sunset-jbb.4 makes retained native runs reproducible without
#   invoking extraction again and keeps run-specific metadata outside semantics.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import pymupdf

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout) if result.stdout else result.stderr


def pdf_fixture(path):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 60), 'Alpha beta', fontsize=12)
        pdf.save(path)


def semantic_files(run):
    manifest = json.loads((run / 'manifest.json').read_text())
    names = ('descriptor.json', 'raw.txt', 'search.txt', 'word-map.json', 'line-map.json',
             'page-map.json', 'configuration.json')
    return {name: (run / name).read_bytes() for name in names}, manifest


def refresh_semantic_manifest(run, manifest):
    semantic = {name: ref['sha256'] for name, ref in sorted(manifest['artifacts'].items())}
    manifest['semantic_artifacts'] = semantic
    manifest['semantic_sha256'] = hashlib.sha256(
        (json.dumps(semantic, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()).hexdigest()
    (run / 'manifest.json').write_text(json.dumps(manifest))


def test_renamed_identical_sources_have_identical_declared_semantics_and_replay(tmp_path):
    first_source, second_source = tmp_path / 'one.pdf', tmp_path / 'renamed.pdf'
    pdf_fixture(first_source)
    second_source.write_bytes(first_source.read_bytes())
    first, second = tmp_path / 'first', tmp_path / 'second'
    assert cli('native', '--source', first_source, '--output', first)[0] == 0
    assert cli('native', '--source', second_source, '--output', second)[0] == 0
    first_files, first_manifest = semantic_files(first)
    second_files, second_manifest = semantic_files(second)
    assert first_files == second_files
    assert first_manifest['semantic_artifacts'] == second_manifest['semantic_artifacts']
    assert first_manifest['semantic_sha256'] == second_manifest['semantic_sha256']
    configuration = json.loads((first / 'configuration.json').read_text())
    assert configuration['extractor']['version'] == pymupdf.VersionBind == '1.28.2'
    assert configuration['extractor']['mupdf_version'] == pymupdf.VersionFitz == '1.28.2'
    assert 'PyMuPDF==1.28.2' in (ROOT / 'requirements-native.txt').read_text()
    descriptor = json.loads((first / 'descriptor.json').read_text())
    native_transform = next(e['transform'] for e in descriptor['evidence']
                            if e['id'] == 'native-evidence-1')
    assert 'MuPDF@1.28.2' in native_transform['dependencies']
    replayed = tmp_path / 'replayed'
    code, result = cli('replay', '--run', first, '--output', replayed)
    assert code == 0 and result['status'] == 'replayed'
    assert semantic_files(replayed)[0] == first_files
    code, inspected = cli('inspect', '--run', replayed, '--json')
    assert code == 0 and inspected['mode'] == 'native'


def test_missing_native_semantic_artifact_fails_inspection_and_replay(tmp_path):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    assert cli('native', '--source', source, '--output', run)[0] == 0
    (run / 'word-map.json').unlink()
    code, report = cli('inspect', '--run', run, '--json')
    assert code == 5 and report['status'] == 'inspection-failed'
    code, report = cli('replay', '--run', run, '--output', tmp_path / 'out')
    assert code == 5 and report['status'] == 'inspection-failed'


def test_removing_artifact_reference_and_malformed_manifest_are_typed_failures(tmp_path):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    assert cli('native', '--source', source, '--output', run)[0] == 0
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    del manifest['artifacts']['word-map.json']
    manifest_path.write_text(json.dumps(manifest))
    code, result = cli('inspect', '--run', run, '--json')
    assert code == 5 and result['status'] == 'inspection-failed'
    manifest_path.write_text('[]')
    code, result = cli('inspect', '--run', run, '--json')
    assert code == 5 and result['status'] == 'inspection-failed'
    code, report = cli('replay', '--run', run, '--output', tmp_path / 'out')
    assert code == 5 and report['status'] == 'inspection-failed'


@pytest.mark.parametrize('corruption', ['short-box', 'bad-source', 'path-traversal', 'symlink'])
def test_replay_rejects_refreshed_hash_corruptions(tmp_path, corruption):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    assert cli('native', '--source', source, '--output', run)[0] == 0
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if corruption in {'short-box', 'bad-source'}:
        name, key = ('word-map.json', 'box') if corruption == 'short-box' else ('line-map.json', 'source_sha256')
        mapping_path = run / name
        mapping = json.loads(mapping_path.read_text())
        mapping[0][key] = [1, 2] if corruption == 'short-box' else '0' * 64
        data = (json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()
        mapping_path.write_bytes(data)
        manifest['artifacts'][name]['sha256'] = hashlib.sha256(data).hexdigest()
    elif corruption == 'path-traversal':
        manifest['artifacts']['word-map.json']['path'] = '../outside.json'
    else:
        outside = tmp_path / 'outside.json'
        outside.write_text('[]')
        (run / 'word-map.json').unlink()
        (run / 'word-map.json').symlink_to(outside)
    semantic = {name: ref['sha256'] for name, ref in sorted(manifest['artifacts'].items())}
    manifest['semantic_artifacts'] = semantic
    manifest['semantic_sha256'] = hashlib.sha256(
        (json.dumps(semantic, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    code, result = cli('replay', '--run', run, '--output', tmp_path / 'out')
    assert code == 5 and result['status'] == 'inspection-failed'


@pytest.mark.parametrize('partial', [False, True])
def test_native_resume_is_read_only_and_preserves_complete_or_partial_status(tmp_path, partial):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    args = ['native', '--source', source]
    if partial:
        args += ['--pages', '1']
        with pymupdf.open() as pdf:
            pdf.new_page(width=300, height=400)
            pdf.new_page(width=300, height=400).insert_text((30, 60), 'Alpha beta', fontsize=12)
            pdf.save(source)
    assert cli(*args, '--output', run)[0] == (2 if partial else 0)
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    code, result = cli('resume', '--run', run)
    assert code == (2 if partial else 0)
    assert result['status'] == ('partial' if partial else 'complete')
    assert before == {p.relative_to(run): p.read_bytes() for p in run.rglob('*') if p.is_file()}


def test_native_replay_does_not_call_extractor_or_open_pdf(tmp_path, monkeypatch):
    from digitization import native
    from digitization.replay import replay

    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    assert cli('native', '--source', source, '--output', run)[0] == 0
    monkeypatch.setattr(native, 'extract', lambda *args, **kwargs: pytest.fail('extract called'))
    monkeypatch.setattr(native.pymupdf, 'open', lambda *args, **kwargs: pytest.fail('PDF opened'))
    assert replay(run, tmp_path / 'replayed')['status'] == 'replayed'


def test_native_unknown_manifest_version_is_unsupported(tmp_path):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    assert cli('native', '--source', source, '--output', run)[0] == 0
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['version'] = 'future'
    manifest_path.write_text(json.dumps(manifest))
    code, result = cli('inspect', '--run', run, '--json')
    assert code == 4 and result['status'] == 'unsupported-version'
    code, result = cli('replay', '--run', run, '--output', tmp_path / 'replayed')
    assert code == 4 and result['status'] == 'unsupported-version'


@pytest.mark.parametrize('corruption', ['remove-selector', 'descriptor-profile-hash', 'status'])
def test_native_inspection_rejects_unbound_profiles_and_coverage_status(tmp_path, corruption):
    source, run = tmp_path / 'source.pdf', tmp_path / 'run'
    pdf_fixture(source)
    if corruption == 'status':
        with pymupdf.open() as pdf:
            pdf.new_page(width=300, height=400)
            pdf.new_page(width=300, height=400).insert_text((30, 60), 'Alpha beta', fontsize=12)
            pdf.save(source)
    assert cli('native', '--source', source, '--output', run)[0] == (2 if corruption == 'status' else 0)
    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if corruption == 'remove-selector':
        del manifest['artifacts']['carrier/selector.json']
    elif corruption == 'descriptor-profile-hash':
        descriptor = json.loads((run / 'descriptor.json').read_text())
        next(profile for profile in descriptor['profiles'] if profile['id'] == 'selector')['sha256'] = '0' * 64
        data = (json.dumps(descriptor, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()
        (run / 'descriptor.json').write_bytes(data)
        manifest['artifacts']['descriptor.json']['sha256'] = hashlib.sha256(data).hexdigest()
        manifest['descriptor']['sha256'] = hashlib.sha256(data).hexdigest()
    else:
        manifest['status'] = 'complete'
        manifest['reason'] = 'native-extraction-complete'
    refresh_semantic_manifest(run, manifest)
    code, result = cli('inspect', '--run', run, '--json')
    assert code == 5 and result['status'] == 'inspection-failed'
