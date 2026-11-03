# Purpose: Execute the local-provider route: real dispatch-bound recognition.
# Responsibilities: Branch a run configuration whose provider kind is 'local'
#   into image-based region proposals, per-crop (or whole-page baseline)
#   recognition behind providers.dispatch, attributed DSC/text export, and the
#   provider-failure stop that preserves the durable ledger.
# Rationale: sunset-rmx.15 (tasks 2.4) owns the real local vertical slice.
#   No OCR prerequisite: regional proposals come from the image detector, not
#   the config; the baseline route OCRs each whole page once with the same
#   pinned engine identity under its own recorded configuration. The engine
#   seam is the injected runner, so deterministic fakes prove the wiring while
#   the default suite never launches tesseract; the separately invoked real
#   smoke closes the ticket. An engine failure must never look completed: the
#   stop keeps budget-state.json (dispatch-uncertain attempts stay
#   reconcilable) and writes no manifest.
"""Local provider route: detect -> dispatch -> attributed DSC export."""
import os
import tempfile
import time
import unicodedata
from pathlib import Path

from dsc03 import validator
from digitization import __version__
from digitization.budget import BudgetLedger
from digitization.pipeline import InputError, _preflight, digest, json_bytes, render_page


class LocalRouteStopped(Exception):
    """Raised by run_local when the engine fails; carries the stop result."""


class _LocalRun:
    """One local-route run: staging, dispatch-bound recognition, attribution.

    Recognitions are real provider attempts behind the durable budget
    boundary (providers.dispatch -> digitization.crop_ocr); the engine seam
    is the injected runner, so deterministic fakes prove the wiring without
    launching tesseract.
    """

    def __init__(self, prepared, stage, runner):
        from digitization.crop_ocr import local_provider
        from digitization.providers import dispatch
        self.source, self.config_raw, self.config = prepared
        self.stage, self.runner, self.dispatch = stage, runner, dispatch
        self.provider = dict(self.config['provider'])
        self.route = self.provider.get('route', 'regional')
        self.language = self.provider['language']
        self.artifacts, self.renders = {}, {}
        self.regions, self.mappings, self.unresolved = [], [], []
        self.trace, self.history, self.search = [], [], ''
        self.operations, self.capture = {}, {}
        self.started = time.monotonic()
        policy = self.config['budget']
        self.ledger = BudgetLedger.create(stage / 'budget-state.json',
                                          cap=policy['max_estimated_cost_microunits'],
                                          currency=policy['currency'], policy=policy)
        self.adapter = local_provider(ledger=self.ledger, lang=self.language,
                                      **({'runner': runner} if runner else {}))

    def save(self, name, data):
        path = self.stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        reference = {'path': name, 'sha256': digest(data)}
        self.artifacts[name] = reference
        return reference

    def blob(self, data):
        return self.save('artifacts/' + digest(data), data)

    def scaffold(self, pages):
        self.pages = list(pages)
        self.source_ref = self.save('source.pdf', self.source)
        self.config_ref = self.save('config.json', self.config_raw)
        self.implementation = {
            'consumer_version': __version__, 'unicode_version': unicodedata.unidata_version,
            'modules': {name: digest((Path(__file__).parent / name).read_bytes())
                        for name in ('pipeline.py', 'artifacts.py', 'render.py',
                                     'detect.py', 'crop_ocr.py', 'local_route.py')}}
        geometry = {'kind': 'geometry', 'version': '1', 'frames': [
            {'name': f'page-{p}-pt', 'unit': 'pt', 'origin': 'bottom-left',
             'axes': 'x-right-y-up', 'scale': [1, 1], 'rotation': 0,
             'crop': None, 'source_scope': f'page:{p}'} for p in pages]}
        geometry_ref = self.blob(json_bytes(geometry))
        selector_ref = self.blob(json_bytes({
            'kind': 'selector', 'version': '1', 'selector_kinds': ['pdf-area'],
            'offset_unit': 'unicode-scalar-values', 'endpoints': 'half-open'}))
        self.descriptor = {
            'version': '0.3', 'id': 'digitization-' + digest(self.source)[:16],
            'source': {'format': 'application/pdf', 'sha256': digest(self.source),
                       'locator': 'source.pdf'},
            'views': [{'id': 'physical', 'kind': 'physical', 'root': 'document'},
                      {'id': 'logical', 'kind': 'logical', 'root': 'logical-root'}],
            'regions': [{'id': 'document', 'view_id': 'physical', 'kind': 'document'},
                        {'id': 'logical-root', 'view_id': 'logical', 'kind': 'document'}],
            'contents': [], 'relations': [], 'annotations': [], 'evidence': [],
            'selectors': [], 'interpretations': [], 'coverage': [], 'vocabularies': [],
            'profiles': [dict(id='geometry', kind='geometry', uri=geometry_ref['path'],
                              version='1', sha256=geometry_ref['sha256']),
                         dict(id='selector', kind='selector', uri=selector_ref['path'],
                              version='1', sha256=selector_ref['sha256'])]}

    def begin_page(self, page, png, render):
        render_ref = self.blob(png)
        self.renders[str(page)] = {**render_ref, **render}
        self.trace.append({'operation': 'render', 'page': page, 'artifact': render_ref['sha256']})
        page_id, image_id = f'page-{page}', f'image-{page}'
        self.descriptor['regions'].append({'id': page_id, 'view_id': 'physical', 'kind': 'page'})
        self.descriptor['relations'].extend([
            {'id': f'contains-{page_id}', 'kind': 'contains', 'from': 'document', 'to': page_id},
            {'id': f'has-{image_id}', 'kind': 'has-content', 'from': page_id, 'to': image_id}])
        self.descriptor['contents'].append({'id': image_id, 'kind': 'image', 'value': render_ref['path']})
        self.descriptor['evidence'].append({
            'id': f'evidence-{image_id}', 'origin': 'source',
            'source_ref': f'sha256:{digest(self.source)}#page:{page}',
            'content_ids': [image_id], 'selector_ids': []})

    def proposals(self, page, png, render):
        from digitization.detect import detect_regions
        if self.route == 'regional':
            detections = detect_regions(png, render)
        else:
            size = [int(render['width_pt']), int(render['height_pt'])]
            detections = [{'id': 'baseline', 'kind': 'page-block', 'bbox': [0, 0, *size]}]
        detection_ref = self.blob(json_bytes(detections))
        self.trace.append({'operation': 'detect', 'page': page,
                           'artifact': detection_ref['sha256'], 'mode': 'image-proposals'})
        self.history.append({'operation': 'detect', 'revision': f'page-{page}-regions-0',
                             'parents': [], 'artifact': detection_ref['sha256'],
                             'mode': 'image-proposals'})
        return detections

    def capture_provider(self, request_key, payload):
        raw, receipt = self.adapter(request_key, payload)
        self.capture[request_key] = raw
        return raw, receipt

    def dispatch_region(self, page_state, detection):
        from digitization.crop_ocr import crop_png, crop_transform
        page, png, render = page_state
        rid = f"page-{page}-{detection['id']}"
        regional = self.route == 'regional'
        crop = crop_transform(detection['bbox'], render['dpi'],
                              [render['width_px'], render['height_px']]) if regional else {
            'route': 'baseline', 'dpi': render['dpi'], 'bbox': detection['bbox'],
            'source_px': [render['width_px'], render['height_px']]}
        payload = crop_png(png, crop) if regional else png
        request = {'version': '1',
                   'operation': 'local-crop-ocr' if regional else 'local-page-ocr',
                   'inputs': [digest(self.source), self.renders[str(page)]['sha256']],
                   'region_id': rid, 'region_kind': detection['kind'],
                   'transforms': {'page': page, 'bbox': detection['bbox'], 'crop': crop,
                                  'render': render},
                   'implementation': self.implementation, 'provider': self.provider,
                   'parameters': {'schema': 'local-ocr-v1', 'prompt': '',
                                  'language': self.language, 'preprocessing': {},
                                  'decoding': {}, 'policy': {}}}
        request_key = digest(validator.canonical(request) + b'\n')
        receipt = self.dispatch(self.ledger, request_key=request_key, payload=payload,
                                maximum_charge=0, provider=self.capture_provider)
        self.operations[rid] = {'operation_key': request_key,
                                'selected_attempt': receipt['attempt_id'], 'cache_hit': False}
        return request_key, self.capture[request_key], receipt

    def attribute_region(self, page_state, detection, resolved):
        request_key, raw_bytes, receipt = resolved
        page, _png, render = page_state
        rid = f"page-{page}-{detection['id']}"
        sid, cid = f'sel-{rid}', f'text-{rid}'
        box = detection['bbox']
        geometry_box = {'x': box[0], 'y': int(render['height_pt'] - box[1] - box[3]),
                        'width': box[2], 'height': box[3]}
        self.descriptor['regions'].append({
            'id': rid, 'kind': detection['kind'], 'view_id': 'physical',
            'geometry': {'profile_id': 'geometry', 'space': f'page-{page}-pt', **geometry_box}})
        self.descriptor['selectors'].append({
            'id': sid, 'kind': 'pdf-area', 'profile_id': 'selector',
            'source_sha256': digest(self.source), 'target': rid,
            'locator': f"page:{page} rect:" + ','.join(map(str, box))})
        self.descriptor['contents'].append({'id': cid, 'kind': 'text',
                                            'value': raw_bytes.decode('utf-8', 'replace')})
        self.descriptor['relations'].extend([
            {'id': 'contains-' + rid, 'kind': 'contains', 'from': f'page-{page}', 'to': rid},
            {'id': 'has-' + cid, 'kind': 'has-content', 'from': rid, 'to': cid},
            {'id': 'derived-' + rid, 'kind': 'derived-from', 'from': 'evidence-' + rid,
             'to': f'evidence-image-{page}'}])
        transform_id = 'local-crop-ocr' if self.route == 'regional' else 'local-page-ocr'
        self.descriptor['evidence'].append({
            'id': f'evidence-{rid}', 'origin': 'extracted',
            'source_ref': f'sha256:{digest(self.source)}#page:{page}',
            'content_ids': [cid], 'selector_ids': [sid],
            'transform': {'id': transform_id, 'version': '1', 'config_sha256': request_key,
                          'dependencies': [f"local:{self.provider['id']}@{self.provider['version']}",
                                           render['renderer']],
                          'inputs': [f'image-{page}'], 'outputs': [cid]}})
        return {'rid': rid, 'sid': sid, 'request_key': request_key, 'receipt': receipt,
                'raw_bytes': raw_bytes}

    def record_region(self, page_state, detection, attribution):
        page, _png, render = page_state
        rid, sid = attribution['rid'], attribution['sid']
        raw_bytes = attribution['raw_bytes']
        raw = raw_bytes.decode('utf-8', 'replace')
        search_text = ' '.join(raw.split())
        raw_ref = self.blob(raw_bytes)
        revision = {'operation': 'recognize', 'revision': 'recognized-' + rid,
                    'parents': [f'page-{page}-regions-0'], 'region_id': rid,
                    'artifact': raw_ref['sha256'], 'mode': 'local',
                    'operation_key': attribution['request_key'],
                    'selected_attempt': attribution['receipt']['attempt_id'],
                    'cache_hit': False}
        self.history.append(revision)
        self.trace.append(revision)
        self.regions.append({'region_id': rid, 'local_id': detection['id'], 'page': page,
                             'bbox': detection['bbox'], 'frame': f'page-{page}-pt',
                             'selector_id': sid, 'raw_text': raw, 'layout_text': raw,
                             'search_text': search_text, 'producer': self.provider,
                             'kind': detection['kind'], 'alternatives': [],
                             'revision': revision['revision'],
                             'operation_key': attribution['request_key'],
                             'selected_attempt': attribution['receipt']['attempt_id']})
        self.mappings.append({'region_id': rid, 'page': page, 'selector_id': sid,
                              'start': len(self.search),
                              'end': len(self.search) + len(search_text)})
        self.search += search_text + '\n'

    def page_cycle(self, page, png, render):
        self.begin_page(page, png, render)
        for detection in self.proposals(page, png, render):
            state = (page, png, render)
            attribution = self.attribute_region(state, detection,
                                                self.dispatch_region(state, detection))
            self.record_region(state, detection, attribution)

    def conclude(self):
        from digitization.structure import collect
        structure, structural_unresolved = collect(self.config, self.pages, self.regions,
                                                   self.mappings, digest(self.source))
        self.unresolved.extend(structural_unresolved)
        self.structure_ref = self.save('structure.json', json_bytes(structure))

    def finish(self):
        errors = validator.validate(self.descriptor)
        if errors:
            raise ValueError('export violates DSC: ' + ', '.join(errors))
        descriptor_ref = self.save('descriptor.json', json_bytes(self.descriptor))
        self.save('search.txt', self.search.encode('utf-8'))
        self.save('search-map.json', json_bytes(self.mappings))
        self.save('regions.json', json_bytes(self.regions))
        self.save('unresolved.json', json_bytes({'regions': self.unresolved,
                                                 'coverage': 'unexamined-outside-recorded-regions'}))
        self.save('history.json', json_bytes(self.history))
        self.trace.append({'operation': 'export', 'artifact': descriptor_ref['sha256']})
        self.save('trace.jsonl', b''.join(json_bytes(event) for event in self.trace))
        usage = {'mode': 'local', 'provider_calls': len(self.operations),
                 'estimated_charge_microunits': 0,
                 'attempts': [attempt['id'] for attempt in self.ledger.attempts],
                 'runtime_seconds': time.monotonic() - self.started}
        self.save('ledger.json', json_bytes(usage))
        self.save('operations.json', json_bytes(self.operations))
        stopped = bool(self.unresolved)
        status = 'stopped-with-unresolved-work' if stopped else 'completed'
        reason = 'local-unresolved' if stopped else 'local-inputs-consumed'
        manifest = {'version': '1', 'mode': 'local', 'status': status, 'reason': reason,
                    'source': self.source_ref, 'configuration': self.config_ref,
                    'pages': self.pages, 'descriptor': descriptor_ref,
                    'renders': self.renders, 'artifacts': self.artifacts, 'usage': usage,
                    'operations': self.operations, 'structure': self.structure_ref}
        (self.stage / 'manifest.json').write_bytes(json_bytes(manifest))
        return status, reason, usage

    def fail(self, error):
        return {'status': 'stopped-with-unresolved-work', 'reason': 'provider-failure',
                'detail': str(error), 'provider_calls': len(self.operations),
                'attempts_dispatched': len(self.ledger.attempts)}


def run_local(job, output, runner=None):
    """Run the local route; job = (source_path, pages, config_path)."""
    from digitization.crop_ocr import LocalProviderFailure
    source_path, pages, config_path = job
    source, config_raw, config = _preflight(source_path, pages, config_path, output)
    output = Path(output).absolute()
    with tempfile.TemporaryDirectory(prefix='.digitization-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        export = _LocalRun((source, config_raw, config), stage, runner)
        export.scaffold(pages)
        try:
            for page in pages:
                png, render = render_page(source, page, config['render']['dpi'])
                export.page_cycle(page, png, render)
        except LocalProviderFailure as error:
            preserved = export.fail(error)
            os.rename(stage, output)  # durable ledger + partial artifacts survive
            preserved['run'] = str(output)
            return preserved
        export.conclude()
        status, reason, usage = export.finish()
        os.rename(stage, output)
        return {'manifest': str(output / 'manifest.json'), 'status': status,
                'reason': reason, 'provider_calls': usage['provider_calls']}
