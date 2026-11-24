# Purpose: Pin exact quantized geometry for native extraction artifacts.
# Responsibilities: Assert word-map/line-map box coordinates are JSON integers
#   in the declared quantum, that the run carries an explicit quantization
#   transform record (quantum, rounding rule, extractor version) picked up by
#   the manifest artifact scan, and that quantization is deterministic
#   (byte-identical word-map.json across runs).
# Rationale: add-anchor-derived-identity Decision 4 / spec requirement
#   "Exact quantized geometry": geometry loss is declared, not silent, and
#   round-trips through declared frame transforms with tolerance zero.
import json

import pymupdf

from digitization.native import extract
from dsc03.substrate.space import QUANTUM, ROUNDING_RULE, quantization_transform_record


def layout_pdf(path):
    import pymupdf
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 50), 'echo echo café', fontsize=12, fontname='japan')
        page.set_cropbox(pymupdf.Rect(10, 20, 290, 380))
        page.set_rotation(90)
        pdf.save(path)


def _extract(tmp_path, name):
    source = tmp_path / f'{name}.pdf'
    layout_pdf(source)
    output = tmp_path / name
    extract(source, output)
    return output


def test_word_and_line_boxes_are_json_integers(tmp_path):
    output = _extract(tmp_path, 'run')
    for name in ('word-map.json', 'line-map.json'):
        records = json.loads((output / name).read_text(encoding='utf-8'))
        assert records
        for record in records:
            assert all(type(v) is int for v in record['box']), (name, record['box'])


def test_run_carries_quantization_transform_record(tmp_path):
    output = _extract(tmp_path, 'run')
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert 'carrier/quantization.json' in manifest['artifacts']
    record = json.loads((output / 'carrier/quantization.json').read_text(encoding='utf-8'))
    assert record['quantum'] == QUANTUM == '1/1000 pt'
    assert record['rounding'] == ROUNDING_RULE == 'round-half-even'
    assert record['extractor_version'] == pymupdf.VersionBind
    assert record == quantization_transform_record(
        record['config_sha256'], record['dependencies'], record['inputs'], record['outputs'])


def test_word_map_bytes_are_deterministic_across_runs(tmp_path):
    # Two separate extract runs of the SAME source: quantization must make
    # word-map.json byte-identical (it also pins float noise out).
    source = tmp_path / 'same.pdf'
    layout_pdf(source)
    first, second = tmp_path / 'run-a', tmp_path / 'run-b'
    extract(source, first)
    extract(source, second)
    assert (first / 'word-map.json').read_bytes() == (second / 'word-map.json').read_bytes()


def test_genuinely_wrong_mapping_still_refuses_after_quantized_compare(tmp_path):
    import hashlib
    import pytest
    from digitization.inspection import IntegrityError, inspect_run
    output = _extract(tmp_path, 'run')
    words = json.loads((output / 'word-map.json').read_text(encoding='utf-8'))
    words[0]['box'][0] += 1  # a real mismatch, far beyond one quantum of noise
    data = json.dumps(words).encode('utf-8')
    (output / 'word-map.json').write_bytes(data)
    # Refresh integrity bindings so the refusal is the transform mismatch
    # itself, not a digest error.
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    manifest['artifacts']['word-map.json']['sha256'] = hashlib.sha256(data).hexdigest()
    semantic = {name: ref['sha256'] for name, ref in sorted(manifest['artifacts'].items())}
    manifest['semantic_artifacts'] = semantic
    manifest['semantic_sha256'] = hashlib.sha256(
        (json.dumps(semantic, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()).hexdigest()
    (output / 'manifest.json').write_bytes(json.dumps(manifest).encode('utf-8'))
    with pytest.raises(IntegrityError, match='native word transform mismatch'):
        inspect_run(output)
