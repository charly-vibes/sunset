"""Contract tests for the local provider route (sunset-rmx.15 slice C).

Route selection: a config with provider.kind='local' runs the public run
journey over REAL dispatch — image-based region proposals (no OCR
prerequisite), per-crop recognition through digitization.crop_ocr behind
providers.dispatch, attributed DSC/text and inspect source mapping. The
whole-page baseline route uses the same pinned engine with its own recorded
configuration (one dispatch per page, no crops). Deterministic fake runners
replace the engine at the same seam the real smoke uses; the default suite
never launches a real engine or opens a socket. An engine failure must stop
the run without a manifest (nothing may look completed) while preserving the
durable ledger so the dispatch-uncertain attempt stays reconcilable.
"""

import json
import socket
import subprocess
from pathlib import Path

import pymupdf
import pytest

from digitization.inspection import inspect_run
from digitization.pipeline import run

ROOT = Path(__file__).resolve().parents[2]

POLICY = {'version': '1', 'currency': 'USD', 'max_refinement_rounds': 2,
          'max_provider_attempts': 8, 'max_estimated_cost_microunits': 100,
          'max_request_bytes': 1 << 20, 'max_output_bytes': 1 << 20,
          'price_schedule_sha256': 'c' * 64}

IDENTITY = {'kind': 'local', 'id': 'tesseract-ocr', 'version': '5.5.1',
            'language': 'spa', 'route': 'regional'}


def sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def for_real(request):
    def forbidden(*args, **kwargs):
        pytest.fail(f'{request} must not happen in the default suite')
    return forbidden


@pytest.fixture
def two_blocks(tmp_path):
    """A 300x400pt page with two well-separated text blocks."""
    source = tmp_path / 'two-blocks.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=300, height=400)
        page.insert_text((30, 40), 'Primer parrafo con contenido real')
        page.insert_text((30, 300), 'Segundo parrafo distante abajo')
        pdf.save(source)
    return source


@pytest.fixture
def no_engines(monkeypatch):
    monkeypatch.setattr(subprocess, 'Popen', for_real('real engine'))
    monkeypatch.setattr(subprocess, 'run', for_real('real engine'))
    monkeypatch.setattr(socket, 'socket', for_real('network'))


def fake_engine(texts, exit_after=None):
    """Runner writing one txt per invocation; records (payload, argv)."""
    calls = []
    counter = {'n': 0}

    def runner(cmd, timeout):
        counter['n'] += 1
        if exit_after is not None and counter['n'] > exit_after:
            return '', 3
        payload = Path(cmd[1]).read_bytes()
        calls.append({'payload': payload, 'argv': list(cmd)})
        Path(cmd[2] + '.txt').write_bytes(texts[counter['n'] - 1])
        return '', 0
    runner.calls = calls
    return runner


def local_config(source, route='regional', dpi=96, **provider_extra):
    provider = {**IDENTITY, 'route': route, **provider_extra}
    return {'version': '1', 'source_sha256': sha(Path(source).read_bytes()),
            'provider': provider, 'render': {'dpi': dpi}, 'pages': {},
            'budget': POLICY}


def test_local_regional_route_discovers_regions_and_ocrs_each_crop(
        two_blocks, tmp_path, no_engines):
    texts = [b'  primer bloque\n', b'\nsegundo bloque\n']
    runner = fake_engine(texts)
    config_path = tmp_path / 'local.json'
    config_path.write_text(json.dumps(local_config(two_blocks)))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    assert result['status'] == 'completed' and result['provider_calls'] == 2
    assert len(runner.calls) == 2
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['mode'] == 'local'
    descriptor = json.loads((output / manifest['descriptor']['path']).read_text())
    recognized = [region for region in descriptor['regions']
                  if region['id'].startswith('page-1-det-')]
    assert len(recognized) == 2
    assert all(region['kind'] == 'ink-block' for region in recognized)
    values = {content['id']: content['value']
              for content in descriptor['contents'] if content['kind'] == 'text'}
    # raw layout is preserved verbatim — no stripping or word-joining
    assert sorted(values.values()) == ['\nsegundo bloque\n', '  primer bloque\n']


def test_local_route_pins_provider_identity_transforms_and_raw_bytes(
        two_blocks, tmp_path, no_engines):
    texts = [b'linea una\n\nlinea dos\n', b'otro\n']
    runner = fake_engine(texts)
    config_path = tmp_path / 'local.json'
    config_path.write_text(json.dumps(local_config(two_blocks, dpi=72)))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    assert result['status'] == 'completed'
    manifest = json.loads((output / 'manifest.json').read_text())
    descriptor = json.loads((output / manifest['descriptor']['path']).read_text())
    evidence = [item for item in descriptor['evidence'] if item['origin'] == 'extracted']
    assert all(item['transform']['id'] == 'local-crop-ocr' for item in evidence)
    assert all(item['transform']['dependencies'][0] == 'local:tesseract-ocr@5.5.1'
               for item in evidence)
    assert all(item['transform']['dependencies'][1].startswith('PyMuPDF@')
               for item in evidence)
    assert all(item['transform']['config_sha256'] for item in evidence)
    # selectors keep the source-linked page/rect locator
    assert all(item['locator'].startswith('page:1 rect:') for item in descriptor['selectors'])
    regions = json.loads((output / 'regions.json').read_text())
    assert all(region['raw_text'] == region['layout_text'] for region in regions)
    search = (output / 'search.txt').read_text()
    assert 'linea una linea dos' in search  # search index joins, raw does not
    assert any('\n\n' in region['raw_text'] for region in regions)


def test_local_regions_are_proposed_without_any_configured_detections(
        two_blocks, tmp_path, no_engines):
    """No OCR prerequisite: pages dict stays empty; the detector proposes."""
    runner = fake_engine([b'a\n', b'b\n', b'c\n'])
    config_path = tmp_path / 'local.json'
    config_path.write_text(json.dumps(local_config(two_blocks)))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    assert result['status'] == 'completed'
    history = json.loads((output / 'history.json').read_text())
    detect_events = [event for event in history if event['operation'] == 'detect']
    assert detect_events and detect_events[0]['mode'] == 'image-proposals'
    regions = json.loads((output / 'regions.json').read_text())
    assert [region['local_id'] for region in regions] == ['det-1', 'det-2']


def test_baseline_route_ocrs_each_whole_page_once(two_blocks, tmp_path, no_engines):
    from digitization.render import render_page
    png, meta = render_page(Path(two_blocks).read_bytes(), 1, 96)
    runner = fake_engine([b'todo el texto\n'])
    config_path = tmp_path / 'baseline.json'
    config_path.write_text(json.dumps(local_config(two_blocks, route='baseline')))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    assert result['status'] == 'completed' and result['provider_calls'] == 1
    assert len(runner.calls) == 1
    assert runner.calls[0]['payload'] == png  # whole rendered page is the payload
    manifest = json.loads((output / 'manifest.json').read_text())
    descriptor = json.loads((output / manifest['descriptor']['path']).read_text())
    region = [item for item in descriptor['regions'] if item['id'] == 'page-1-baseline']
    assert region and region[0]['kind'] == 'page-block'


def test_provider_failure_stops_without_manifest_and_preserves_ledger(
        two_blocks, tmp_path, no_engines):
    runner = fake_engine([b'primer texto\n'], exit_after=1)
    config_path = tmp_path / 'local.json'
    config_path.write_text(json.dumps(local_config(two_blocks)))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    assert result['status'] == 'stopped-with-unresolved-work'
    assert result['reason'] == 'provider-failure'
    assert not (output / 'manifest.json').exists()  # nothing may look completed
    from digitization.budget import BudgetLedger
    ledger = BudgetLedger.open(output / 'budget-state.json')
    states = {attempt['id']: attempt['state'] for attempt in ledger.attempts}
    assert 'dispatch-uncertain' in states.values()
    # resume surfaces the unreconciled attempts without new dispatch
    from digitization.pipeline import resume
    resumed = resume(output)
    assert resumed['status'] == 'stopped-with-unresolved-work'
    assert resumed['reason'] == 'dispatch-uncertain'
    assert resumed['unresolved_attempts'] == [key for key, state in states.items()
                                              if state == 'dispatch-uncertain']


def test_inspect_maps_local_regions_to_sources(two_blocks, tmp_path, no_engines):
    runner = fake_engine([b'  texto uno\n', b'texto dos\n'])
    config_path = tmp_path / 'local.json'
    config_path.write_text(json.dumps(local_config(two_blocks)))
    output = tmp_path / 'run'
    result = run(two_blocks, [1], config_path, output, runner=runner)
    report = inspect_run(output)
    assert report['status'] == 'completed'
    for region in report['regions']:
        assert region['source_resolution'] == 'resolved'
        assert region['selector']['locator'].startswith('page:1 rect:')
        assert region['producer']['kind'] == 'local'
    usage = report['usage']
    assert usage['mode'] == 'local' and usage['provider_calls'] == 2
    assert usage['estimated_charge_microunits'] == 0
    assert report['unresolved'] == []
    assert report['coverage'] == 'unexamined-outside-recorded-regions'
