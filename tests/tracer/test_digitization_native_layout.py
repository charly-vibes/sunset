# Purpose: Pin native text mapping across repetition, Unicode, whitespace and PDF frames.
# Responsibilities: Exercise the public fresh-process CLI and assert raw/search
#   span attribution, line grouping, and known page transform geometry.
# Rationale: sunset-jbb.2 extends native extraction; sunset-jbb.3 keeps native
#   scope completion separate from visual completeness.
import json
import subprocess
import sys
import unicodedata

import pymupdf
import pytest
from digitization.native import _align_raw_words

ROOT = __import__('pathlib').Path(__file__).resolve().parents[2]


def cli(*args):
    result = subprocess.run([sys.executable, '-B', '-m', 'digitization', *map(str, args)],
                           cwd=ROOT, capture_output=True, text=True)
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


def layout_pdf(path):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 50), 'echo echo café', fontsize=12, fontname='japan')
        page.insert_text((30, 80), 'again', fontsize=12, fontname='japan')
        page.insert_text((30, 110), 'cafe\u0301 repeated', fontsize=12, fontname='japan')
        page.set_cropbox(pymupdf.Rect(10, 20, 290, 380))
        page.set_rotation(90)
        pdf.save(path)


def test_native_layout_maps_every_normalized_token_and_explicit_page_frame(tmp_path):
    source, output = tmp_path / 'layout.pdf', tmp_path / 'run'
    layout_pdf(source)
    code, result = cli('native', '--source', source, '--output', output)
    assert code == 0 and result['status'] == 'text-complete', result

    raw = (output / 'raw.txt').read_text(encoding='utf-8')
    search = (output / 'search.txt').read_text(encoding='utf-8')
    words = json.loads((output / 'word-map.json').read_text(encoding='utf-8'))
    assert raw == 'echo echo café\n\nagain\n\ncafe\u0301  repeated\n'
    assert search == 'echo echo café again café repeated'
    assert [w['text'] for w in words] == ['echo', 'echo', 'café', 'again', 'cafe\u0301', 'repeated']
    for word in words:
        assert raw[word['raw_start']:word['raw_end']] == word['text']
        assert search[word['search_start']:word['search_end']] == unicodedata.normalize('NFC', word['text'])
        assert word['box'][2] > word['box'][0] and word['box'][3] > word['box'][1]
        assert word['frame'] == 'page-1-pt'
    assert len({(w['raw_start'], w['raw_end']) for w in words}) == 6
    lines = json.loads((output / 'line-map.json').read_text(encoding='utf-8'))
    assert len(lines) == 4  # PyMuPDF groups the wide two-space gap as separate layout lines.
    assert [raw[line['raw_start']:line['raw_end']] for line in lines] == [
        'echo echo café', 'again', 'cafe\u0301', 'repeated']

    frames = json.loads((output / 'page-map.json').read_text(encoding='utf-8'))
    frame = frames[0]
    assert frame['page'] == 1 and frame['rotation'] == 90
    assert frame['cropbox'] == [10, 20, 290, 380]
    assert frame['source_origin'] == [10, 20]
    assert frame['source_dimensions'] == [280, 360]
    assert frame['target_dimensions'] == [360, 280]
    assert frame['source_frame'] == 'unrotated-crop-page-pt'
    assert frame['target_frame'] == 'rotated-visible-page-pt'
    assert frame['source_to_page'] == [0, 1, -1, 0, 360, 0]
    for word in words:
        x0, y0, x1, y1 = word['source_box']
        assert word['box'] == pytest.approx([360 - y1, x0, 360 - y0, x1])

    code, inspected = cli('inspect', '--run', output, '--json')
    assert code == 0 and inspected['mode'] == 'native'
    assert inspected['words'] == words
    assert inspected['frames'] == frames


def test_adjacent_extractor_words_map_inside_one_raw_text_run():
    # Synthetic output shape observed in real PDFs: separate word boxes but no
    # whitespace in PyMuPDF's raw text serialization.
    tokens = ['(Art.', '9', 'de', 'la', 'Ley', '14967)']
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        x = 30
        for token in tokens:
            page.insert_text((x, 50), token, fontsize=11)
            x += pymupdf.get_text_length(token, fontname='helv', fontsize=11) + 1.3
        raw = page.get_text('text', sort=True, flags=0).rstrip('\n')
    assert raw == ''.join(tokens)
    spans = _align_raw_words(raw, tokens, 10)
    assert [raw[start:end] for start, end in spans] == tokens
    assert spans[0][1] == spans[1][0]
    assert spans[-1][1] == len(raw)
