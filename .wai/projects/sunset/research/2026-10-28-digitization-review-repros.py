# Purpose: Reproduce digitization review findings without production changes.
# Responsibilities: Probe multi-step selection, cache-bound proposal validation,
#   run ledger consistency and semantic scheduling using synthetic local inputs.
# Rationale: sunset-72d requires executable evidence before review conclusions.
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import pymupdf
from digitization.pipeline import run
from digitization.inspection import inspect_run

ROOT = Path(tempfile.mkdtemp(prefix='sunset-72d-review-'))
SOURCE = ROOT / 'source.pdf'
with pymupdf.open() as pdf:
    pdf.new_page(width=300, height=400)
    pdf.save(SOURCE)
BASE = {'version': '1', 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'provider': {'kind': 'recorded', 'id': 'fixture', 'version': '1'},
        'render': {'dpi': 72}, 'pages': {'1': {'detections': [
            {'id': 'p1', 'kind': 'text', 'bbox': [20, 20, 100, 80]},
            {'id': 'c1', 'kind': 'text', 'bbox': [20, 150, 100, 20]}],
        'recognitions': {'p1': {'raw_text': 'old', 'unresolved': []},
                         'c1': {'raw_text': 'caption', 'unresolved': []}}}}}

def start(name, config, **kwargs):
    path = ROOT / (name + '.json')
    path.write_text(json.dumps(config))
    out = ROOT / name
    run(SOURCE, [1], path, out, **kwargs)
    return out, inspect_run(out)

def rule(name, kind, inputs, outputs, priority=1, structure=None):
    action = {'kind': kind, 'inputs': inputs, 'outputs': outputs}
    if structure is not None: action['structure'] = structure
    return {'id': name, 'priority': priority, 'check': {'kind': 'always'}, 'action': action}

def output(name, bbox, text):
    return {'page': 1, 'id': name, 'kind': 'text', 'bbox': bbox,
            'recognition': {'raw_text': text, 'unresolved': []}}

# CORR-001: the next revision falls back to the shared cache's default.
config = copy.deepcopy(BASE)
config['refinement'] = {'version': '1', 'rules': [
    rule('correct', 'rerecognize', ['page-1-p1'], [output('p1', [20, 20, 100, 80], 'corrected')]),
    rule('unrelated', 'restructure', ['page-1-c1'], [], priority=2)]}
out, report = start('selection-rollback', config)
readings = [[r['raw_text'] for r in inspect_run(out / 'revisions' / f'state-{i}')['regions']
             if r['region_id'] == 'page-1-p1'][0] for i in range(3)]
assert readings == ['old', 'corrected', 'old'], readings
print(json.dumps({'finding': 'CORR-001', 'observed_snapshots': readings,
                  'expected_final': 'corrected'}))

# CORR-002: validation binds the supplied response, execution selects cached text.
config = copy.deepcopy(BASE)
outputs = [output('left', [20, 20, 40, 80], 'old'), output('right', [70, 20, 50, 80], 'right')]
config['refinement'] = {'version': '1', 'rules': [rule('split', 'split', ['page-1-p1'], outputs)]}
cache = ROOT / 'cache'
start('warm-child-cache', config, cache_dir=cache)
config['refinement']['rules'][0]['action']['outputs'][0]['recognition']['raw_text'] = 'new'
config['refinement']['rules'][0]['action']['structure'] = [{
    'id': 'child-layout', 'kind': 'ocr', 'region_id': 'page-1-left',
    'producer': {'id': 'fixture', 'version': '1', 'config': {}}, 'text': 'new',
    'lines': [{'start': 0, 'end': 3, 'bbox': [20, 20, 40, 10]}]}]
out2, report2 = start('invalid-resolved-proposal', config, cache_dir=cache)
assert len(report2['refinement']['steps']) == 1
assert report2['refinement']['diagnostics'] == []
assert report2['structure']['diagnostics'][0]['reason'] == 'invalid-structure'
assert 'page-1-p1' not in {r['region_id'] for r in report2['regions']}
print(json.dumps({'finding': 'CORR-002', 'admitted_steps': 1, 'parent_retained_active': False,
                  'structure_diagnostic': report2['structure']['diagnostics'][0]['detail']}))

# EDGE-001: invalid structure envelope crashes replacement admission, loses output.
config = copy.deepcopy(BASE)
config['pages']['1']['structure'] = 'malformed'
config['refinement'] = {'version': '1', 'rules': [rule('replace', 'restructure', ['page-1-p1'], [], structure=[{
    'id': 'correction', 'kind': 'manual', 'region_id': 'page-1-p1',
    'producer': {'id': 'reviewer', 'version': '1', 'config': {}}, 'text': 'fixed'}])]}
try:
    start('malformed-envelope', config)
except AttributeError as error:
    assert not (ROOT / 'malformed-envelope').exists()
    print(json.dumps({'finding': 'EDGE-001', 'exception': str(error), 'published_run': False}))
else:
    raise AssertionError('expected uncaught AttributeError')

# CORR-003: manifest accounting is not checked against its retained hashed ledger.
out3, _ = start('ledger-mismatch', copy.deepcopy(BASE))
manifest_path = out3 / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['usage']['provider_calls'] = 999
manifest_path.write_text(json.dumps(manifest))
report3 = inspect_run(out3)
ledger = json.loads((out3 / 'ledger.json').read_text())
assert ledger['provider_calls'] == 0 and report3['usage']['provider_calls'] == 999
print(json.dumps({'finding': 'CORR-003', 'verified_ledger_calls': 0,
                  'inspection_reported_calls': 999, 'inspection_refused': False}))
print('Evidence directory:', ROOT)
