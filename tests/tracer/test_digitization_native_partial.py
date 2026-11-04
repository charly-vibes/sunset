# Purpose: Pin native partial coverage and safe refusal of invalid PDF requests.
# Responsibilities: Exercise page selection, textless/image/blank observations,
#   expected failures, and read-only native inspection through fresh CLI processes.
# Rationale: Native text extraction cannot establish visual completeness or that
#   a page with no text is blank; excluded and unsupported scopes stay explicit.
import json
from pathlib import Path
import subprocess
import sys

import pytest
import pymupdf

from dsc03 import validator

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def fixture(path):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 3, 3), False)
    pix.clear_with(200)
    png = pix.tobytes('png')
    with pymupdf.open() as doc:
        page = doc.new_page(width=300, height=400)
        page.insert_text((30, 60), 'native words')
        page.insert_image(pymupdf.Rect(200, 200, 230, 230), stream=png)
        page = doc.new_page(width=300, height=400)
        page.insert_image(pymupdf.Rect(20, 20, 280, 380), stream=png)
        doc.new_page(width=300, height=400)  # Textless and featureless is still unexamined.
        doc.save(path)


def test_partial_native_result_keeps_scopes_and_inspects_without_claiming_completeness(tmp_path):
    source, output = tmp_path / 'mixed.pdf', tmp_path / 'run'
    fixture(source)
    code, result = cli('native', '--source', source, '--output', output)
    assert code == 2 and result['status'] == 'text-with-gaps'
    assert result['reason'] == 'native-extraction-text-with-gaps' and result['provider_calls'] == 0
    manifest = json.loads((output / 'manifest.json').read_text())
    descriptor = validator.load(output / manifest['descriptor']['path'])
    assert validator.validate(descriptor) == []
    assert [r['id'] for r in descriptor['regions'] if r['id'].startswith('pg')] == ['pg1', 'pg2', 'pg3']
    by_scope = {(c['feature'], c['scope']): c for c in descriptor['coverage']}
    assert by_scope['pdf:glyphs', 'page:2']['status'] == 'unexamined'
    assert 'no native text' in by_scope['pdf:glyphs', 'page:2']['reason']
    assert by_scope['pdf:glyphs', 'page:3']['status'] == 'unexamined'
    assert by_scope['pdf:glyphs', 'page:1']['status'] == 'preserved'
    assert by_scope['pdf:images', 'page:1']['status'] == 'approximated'
    assert by_scope['pdf:images', 'page:2']['status'] == 'approximated'
    code, report = cli('inspect', '--run', output, '--json')
    assert code == 0 and report['status'] == 'text-with-gaps'
    assert report['coverage']['visual_completeness'] == 'not-established'
    assert report['coverage']['unexamined_pages'] == [2, 3]
    assert [w['text'] for w in report['words']] == ['native', 'words']


def test_zero_text_only_run_reads_no_text_and_stays_inspectable(tmp_path):
    source, output = tmp_path / 'textless.pdf', tmp_path / 'run'
    with pymupdf.open() as doc:
        doc.new_page(width=300, height=400)
        doc.save(source)
    code, result = cli('native', '--source', source, '--output', output)
    assert code == 2
    assert result['status'] == 'no-text-read'
    assert result['reason'] == 'native-extraction-no-text-read'
    code, report = cli('inspect', '--run', output, '--json')
    assert code == 0
    assert report['status'] == 'no-text-read'
    assert report['words'] == [] and report['lines'] == []
    assert report['coverage']['unexamined_pages'] == [1]
    assert report['coverage']['visual_completeness'] == 'not-established'


def test_logo_only_approximation_stays_text_complete(tmp_path):
    source, output = tmp_path / 'native-only.pdf', tmp_path / 'run'
    with pymupdf.open() as doc:
        page = doc.new_page(width=300, height=400)
        page.insert_text((30, 60), 'native text')
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 3, 3), False)
        pix.clear_with(200)
        page.insert_image(pymupdf.Rect(200, 200, 230, 230), stream=pix.tobytes('png'))
        doc.save(source)
    code, result = cli('native', '--source', source, '--output', output)
    assert code == 0
    assert result['status'] == 'text-complete'
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['version'] == '2'
    descriptor = validator.load(output / manifest['descriptor']['path'])
    approximated = [c for c in descriptor['coverage'] if c['status'] == 'approximated']
    assert approximated
    assert all(c['feature'] != 'pdf:glyphs' for c in approximated)
    code, report = cli('inspect', '--run', output, '--json')
    assert code == 0
    assert report['status'] == 'text-complete'
    assert report['coverage']['visual_completeness'] == 'not-established'


def test_outcome_classifier_is_pure_over_page_retention():
    from digitization.native import classify_outcome
    assert classify_outcome({1: True}) == 'text-complete'
    assert classify_outcome({1: True, 2: True, 3: True}) == 'text-complete'
    assert classify_outcome({1: True, 2: False}) == 'text-with-gaps'
    assert classify_outcome({1: False, 2: True}) == 'text-with-gaps'
    assert classify_outcome({1: False}) == 'no-text-read'
    assert classify_outcome({1: False, 2: False}) == 'no-text-read'
    with pytest.raises(ValueError):
        classify_outcome({})


def test_page_selection_excludes_unselected_text_but_preserves_inventory(tmp_path):
    source, output = tmp_path / 'two.pdf', tmp_path / 'selected'
    with pymupdf.open() as doc:
        for text in ('secret first page', 'selected second page'):
            page = doc.new_page()
            page.insert_text((30, 60), text)
        doc.save(source)
    code, result = cli('native', '--source', source, '--pages', '2', '--output', output)
    assert code == 0 and result['status'] == 'text-complete'
    manifest = json.loads((output / 'manifest.json').read_text())
    descriptor = validator.load(output / manifest['descriptor']['path'])
    assert validator.validate(descriptor) == []
    assert 'secret first page' not in (output / 'raw.txt').read_text()
    assert all('secret' not in c.get('value', '') for c in descriptor['contents'])
    assert [r['id'] for r in descriptor['regions'] if r['id'].startswith('pg')] == ['pg1', 'pg2']
    excluded = [c for c in descriptor['coverage'] if c['scope'] == 'page:1']
    assert excluded and all(c['status'] == 'unexamined' and 'excluded' in c['reason'] for c in excluded)
    code, report = cli('inspect', '--run', output, '--json')
    assert code == 0 and report['pages'] == [2]
    assert report['coverage']['excluded_pages'] == [1]


def test_invalid_pdf_inputs_selections_and_outputs_are_refused_without_tracebacks(tmp_path):
    valid = tmp_path / 'valid.pdf'
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(valid)
    malformed = tmp_path / 'malformed.pdf'
    malformed.write_bytes(b'not pdf bytes')
    encrypted = tmp_path / 'encrypted.pdf'
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='user')
    missing = tmp_path / 'missing.pdf'
    cases = [(missing, None), (malformed, None), (encrypted, None),
             (valid, '0'), (valid, '2'), (valid, '1,1'), (valid, 'x'), (valid, '')]
    for index, (source, pages) in enumerate(cases):
        output = tmp_path / f'out-{index}'
        args = ['native', '--source', source, '--output', output]
        if pages is not None:
            args += ['--pages', pages]
        code, result = cli(*args)
        assert code == 3 and result['status'] == 'invalid-input'
        expected = ('source-unreadable' if source == missing else
                    'malformed-pdf' if source == malformed else
                    'encrypted-pdf-unsupported' if source == encrypted else
                    'invalid-input' if pages in {'x', ''} else 'invalid-pages')
        assert result['reason'] == expected
        assert not output.exists()
    for kind in ('empty-dir', 'file'):
        output = tmp_path / kind
        if kind == 'empty-dir': output.mkdir()
        else: output.write_text('keep')
        before = (output.is_dir(), list(output.iterdir()) if output.is_dir() else output.read_bytes())
        code, result = cli('native', '--source', valid, '--output', output)
        assert code == 3 and result['status'] == 'invalid-input'
        assert (output.is_dir(), list(output.iterdir()) if output.is_dir() else output.read_bytes()) == before
    target = tmp_path / 'symlink-target'
    dangling = tmp_path / 'dangling-output'
    dangling.symlink_to(target, target_is_directory=True)
    code, result = cli('native', '--source', valid, '--output', dangling)
    assert code == 3 and result['reason'] == 'output-already-exists'
    assert dangling.is_symlink() and not target.exists()
    linked_output = tmp_path / 'linked-output'
    linked_target = tmp_path / 'linked-target'
    linked_target.mkdir()
    linked_output.symlink_to(linked_target, target_is_directory=True)
    code, result = cli('native', '--source', valid, '--output', linked_output)
    assert code == 3 and result['reason'] == 'output-already-exists'
    assert list(linked_target.iterdir()) == []
