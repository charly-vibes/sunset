# Purpose: Extract embedded PDF text with source-bound word and line locations.
# Responsibilities: Validate native inputs, retain pinned local artifacts, build
#   a valid DSC 0.3 descriptor, normalize searchable tokens and inspect mappings.
# Rationale: sunset-jbb.4 declares deterministic semantic artifacts and uses the
#   same integrity boundary for read-only inspection, resume and offline replay;
#   sunset-1ry classifies per-page text retention into the outcome vocabulary
#   (text-complete/text-with-gaps/no-text-read) carried by manifest version 2.
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unicodedata

import pymupdf

from dsc03 import validator
from dsc03.adapters import describe_pdf


EXTRACTOR = {'id': 'pymupdf', 'version': pymupdf.VersionBind,
             'mupdf_version': pymupdf.VersionFitz}
OPTIONS = {'sort': True, 'text_flags': 0}
NORMALIZATION = 'nfc-token-whitespace-v1'
# Manifest version carrying the outcome vocabulary (distinguish-native-
# extraction-outcomes, design Decision 3). Version 1 manifests carry only the
# legacy partial status and are refused as unsupported-version, never guessed.
OUTCOME_MANIFEST_VERSION = '2'


def classify_outcome(retained_by_page):
    """Return the native extraction outcome for a page selection.

    retained_by_page maps each selected page number to whether that page
    contributed retained native text. The outcome is a pure function of
    these retention results: approximated non-text features are not part
    of the input and cannot downgrade an outcome, while pages whose glyphs
    are unexamined or whose extraction failed map to False and do.
    """
    retained = [bool(value) for value in retained_by_page.values()]
    if not retained:
        raise ValueError('outcome classification requires a nonempty page selection')
    if all(retained):
        return 'text-complete'
    if any(retained):
        return 'text-with-gaps'
    return 'no-text-read'


class NativeInputError(ValueError):
    """Expected request refusal with a stable machine-readable reason."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode()


def _matrix(matrix):
    return [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f]


def _map_box(box, matrix):
    x0, y0, x1, y1 = box
    points = [pymupdf.Point(x, y) * matrix for x, y in
              ((x0, y0), (x0, y1), (x1, y0), (x1, y1))]
    return [min(p.x for p in points), min(p.y for p in points),
            max(p.x for p in points), max(p.y for p in points)]


def _align_raw_words(raw, tokens, page_num):
    """Map extractor words to contiguous raw spans, allowing adjacent tokens."""
    spans, cursor = [], 0
    for token in tokens:
        while cursor < len(raw) and raw[cursor].isspace():
            cursor += 1
        target = unicodedata.normalize('NFC', token)
        end = cursor
        while end < len(raw) and not raw[end].isspace():
            end += 1
        matched = None
        maximum_end = min(end, cursor + max(len(token) * 4 + 8, len(token) + 1))
        for candidate_end in range(cursor + 1, maximum_end + 1):
            candidate = unicodedata.normalize('NFC', raw[cursor:candidate_end])
            if candidate == target:
                matched = candidate_end
                break
        if matched is None:
            raise ValueError(f'native extractor word does not align with raw text on page {page_num}: {token!r}')
        spans.append((cursor, matched))
        cursor = matched
    if raw[cursor:].strip():
        raise ValueError(f'native raw text contains unmapped word on page {page_num}')
    return spans


def _put(root, relative, data, artifacts):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    artifacts[relative] = {'path': relative, 'sha256': _sha(data)}


def _descriptor(source_hash, pages, raw_pages, page_maps, root, config_sha):
    selector_profile = {'kind': 'selector', 'version': '1',
                        'offset_unit': 'unicode-scalar-values', 'endpoints': 'half-open'}
    selector_bytes = _json(selector_profile)
    (root / 'selector.json').write_bytes(selector_bytes)
    geometry_profile = {'kind': 'geometry', 'version': '1',
                        'frames': [{'name': f'page-{item["page"]}-pt',
                                    'source_frame': item['source_frame'],
                                    'target_frame': item['target_frame'],
                                    'source_to_target': item['source_to_page']}
                                   for item in page_maps]}
    if page_maps:  # all pages aligner-failed: no frames, no native selectors
        geometry_bytes = _json(geometry_profile)
        (root / 'geometry.json').write_bytes(geometry_bytes)
    desc = describe_pdf(root.parent / 'source.pdf', root)
    desc['source']['locator'] = 'source.pdf'
    next(r for r in desc['regions'] if r['id'] == 'r-log')['kind'] = 'document'
    for profile in desc['profiles']:
        profile['uri'] = 'carrier/' + profile['uri']
    desc['profiles'].append({'id': 'selector', 'kind': 'selector', 'uri': 'carrier/selector.json',
                             'version': '1', 'sha256': _sha(selector_bytes)})
    if page_maps:
        desc['profiles'].append({'id': 'geometry', 'kind': 'geometry', 'uri': 'carrier/geometry.json',
                                 'version': '1', 'sha256': _sha(geometry_bytes)})
    # Keep the full independent inventory, but remove source text observations
    # outside the requested extraction scope. Page structure and coverage remain.
    excluded = {e['id'] for e in desc['evidence']
                if e['source_ref'].rsplit('#page:', 1)[-1].isdigit()
                and int(e['source_ref'].rsplit('#page:', 1)[-1]) not in pages}
    excluded_contents = {cid for evidence in desc['evidence'] if evidence['id'] in excluded
                         for cid in evidence['content_ids']}
    desc['evidence'] = [e for e in desc['evidence'] if e['id'] not in excluded]
    desc['contents'] = [c for c in desc['contents'] if c['id'] not in excluded_contents]
    desc['relations'] = [r for r in desc['relations']
                         if not (r['kind'] == 'has-content' and r['to'] in excluded_contents)]
    for annotation in desc['annotations']:
        if annotation['target'] in excluded_contents:
            page = next((int(r['id'][2:]) for r in desc['regions']
                         if r['id'].startswith('pg') and r['id'][2:].isdigit()
                         and annotation['id'].startswith(f'an{r["id"][2:]}-')), None)
            if page is not None:
                annotation['target'] = f'pg{page}'
            annotation['status'] = 'asserted_without_evidence'
            annotation['evidence'] = []
    for item in desc['coverage']:
        if item['scope'].startswith('page:'):
            page = int(item['scope'][5:])
            if page not in pages:
                item['status'] = 'unexamined'
                item['reason'] = 'page excluded by native extraction selection'
            elif item['feature'] == 'pdf:glyphs' and page not in raw_pages:
                item['status'] = 'unexamined'
                item['reason'] = 'native word alignment failed; glyphs unexamined'
            elif item['feature'] == 'pdf:glyphs' and not raw_pages[page].strip():
                item['status'] = 'unexamined'
                item['reason'] = 'no native text observed; page not established blank'
    for page in pages:
        if page not in raw_pages:
            continue
        pid = f'pg{page}'
        base = next((e for e in desc['evidence'] if f'#page:{page}' in e['source_ref']), None)
        source_text = next((cid for cid in base['content_ids']), None) if base else None
        if source_text is None:
            continue
        cid, eid, sid = f'native-text-{page}', f'native-evidence-{page}', f'native-page-{page}'
        desc['contents'].append({'id': cid, 'kind': 'text', 'value': raw_pages[page]})
        desc['relations'].append({'id': f'native-has-{page}', 'kind': 'has-content', 'from': pid, 'to': cid})
        desc['selectors'].append({'id': sid, 'kind': 'pdf-area', 'profile_id': 'selector',
                                  'source_sha256': source_hash, 'target': pid,
                                  'locator': f'page:{page}'})
        desc['evidence'].append({'id': eid, 'origin': 'extracted',
                                 'source_ref': f'sha256:{source_hash}#page:{page}',
                                 'content_ids': [cid], 'selector_ids': [sid],
                                 'transform': {'id': 'native-text-extraction', 'version': '1',
                                               'config_sha256': config_sha,
                                               'dependencies': [f"{EXTRACTOR['id']}@{EXTRACTOR['version']}",
                                                                f"MuPDF@{EXTRACTOR['mupdf_version']}"],
                                               'inputs': [source_text], 'outputs': [cid]}})
        desc['relations'].append({'id': f'native-derived-{page}', 'kind': 'derived-from',
                                  'from': eid, 'to': base['id']})
    return desc


def extract(source, output, pages=None):
    source, output = Path(source).resolve(), Path(output)
    if output.exists() or output.is_symlink():
        raise NativeInputError('output-already-exists', 'output path already exists')
    output = output.resolve()
    try:
        data = source.read_bytes()
    except OSError as error:
        raise NativeInputError('source-unreadable', 'source PDF is missing or unreadable') from error
    source_hash = _sha(data)
    try:
        pdf_context = pymupdf.open(stream=data, filetype='pdf')
    except Exception as error:
        raise NativeInputError('malformed-pdf', 'malformed or unreadable PDF') from error
    with pdf_context as pdf:
        if pdf.needs_pass:
            raise NativeInputError('encrypted-pdf-unsupported', 'encrypted PDF is unsupported')
        selected = list(range(1, pdf.page_count + 1)) if pages is None else list(pages)
        if (not selected or any(type(p) is not int for p in selected)
                or len(set(selected)) != len(selected)
                or any(p < 1 or p > pdf.page_count for p in selected)):
            raise NativeInputError('invalid-pages', 'pages must be unique one-based indices within the PDF')
        raw_pages, word_maps, line_maps, page_maps = {}, [], [], []
        raw_base = 0
        search_base = 0
        for page_num in selected:
            page = pdf[page_num - 1]
            raw = page.get_text('text', sort=OPTIONS['sort'], flags=OPTIONS['text_flags'])
            if not raw.endswith('\n'):
                raw += '\n'
            grouped = {}
            extracted_words = page.get_text('words', sort=OPTIONS['sort'], flags=OPTIONS['text_flags'])
            try:
                spans = _align_raw_words(raw, [item[4] for item in extracted_words], page_num)
            except ValueError:
                # Aligner failure is a tool limitation, not user error (sunset-1uv):
                # the page stays selected but contributes nothing — raw_pages and
                # page_maps omit it so no extracted text is claimed and the raw
                # offsets of later pages never advance past unaligned text.
                continue
            raw_pages[page_num] = raw
            matrix = page.rotation_matrix
            page_maps.append({'page': page_num, 'rotation': page.rotation,
                              'cropbox': list(page.cropbox), 'frame': f'page-{page_num}-pt',
                              'source_origin': [page.cropbox.x0, page.cropbox.y0],
                              'source_dimensions': [page.cropbox.width, page.cropbox.height],
                              'target_dimensions': [page.rect.width, page.rect.height],
                              'source_frame': 'unrotated-crop-page-pt',
                              'target_frame': 'rotated-visible-page-pt',
                              'source_to_page': _matrix(matrix)})
            for item, (position, end) in zip(extracted_words, spans):
                x0, y0, x1, y1, token, bno, lno, _ = item
                mapped_box = _map_box([x0, y0, x1, y1], matrix)
                word_maps.append({'source_sha256': source_hash, 'page': page_num,
                                  'frame': f'page-{page_num}-pt', 'raw_start': raw_base + position,
                                  'raw_end': raw_base + end, 'text': raw[position:end],
                                  'source_box': [x0, y0, x1, y1], 'box': mapped_box,
                                  'search_start': search_base, 'search_end': search_base + len(unicodedata.normalize('NFC', token))})
                grouped.setdefault((bno, lno), []).append((raw[position:end], mapped_box, position, end))
                search_base += len(unicodedata.normalize('NFC', token)) + 1
            for group in grouped.values():
                start, end = group[0][2], group[-1][3]
                boxes = [word[1] for word in group]
                line_maps.append({'source_sha256': source_hash, 'page': page_num, 'frame': f'page-{page_num}-pt',
                                  'raw_start': raw_base + start, 'raw_end': raw_base + end,
                                  'text': raw[start:end],
                                  'box': [min(w[0] for w in boxes), min(w[1] for w in boxes),
                                          max(w[2] for w in boxes), max(w[3] for w in boxes)]})
            raw_base += len(raw)
        # Selected source pages are retained in the same order supplied by caller.
    words = word_maps
    stage = Path(tempfile.mkdtemp(prefix='.native-', dir=output.parent))
    try:
        artifacts = {}
        source_ref = {'path': 'source.pdf', 'sha256': source_hash}
        _put(stage, 'source.pdf', data, artifacts)
        raw_text = ''.join(raw_pages[p] for p in selected if p in raw_pages)
        _put(stage, 'raw.txt', raw_text.encode(), artifacts)
        search_text = ' '.join(unicodedata.normalize('NFC', word['text']) for word in words)
        _put(stage, 'search.txt', search_text.encode(), artifacts)
        _put(stage, 'word-map.json', _json(words), artifacts)
        _put(stage, 'line-map.json', _json(line_maps), artifacts)
        _put(stage, 'page-map.json', _json(page_maps), artifacts)
        configuration = {'extractor': EXTRACTOR, 'options': OPTIONS, 'pages': selected,
                         'offset_unit': 'unicode-scalar-values', 'normalization': NORMALIZATION, 'version': '1'}
        config_bytes = _json(configuration)
        _put(stage, 'configuration.json', config_bytes, artifacts)
        carrier_dir = stage / 'carrier'
        carrier_dir.mkdir()
        desc = _descriptor(source_ref['sha256'], selected, raw_pages, page_maps, carrier_dir, _sha(config_bytes))
        for path in sorted(carrier_dir.rglob('*')):
            if path.is_file():
                rel = path.relative_to(stage).as_posix()
                artifacts[rel] = {'path': rel, 'sha256': _sha(path.read_bytes())}
        desc_bytes = _json(desc)
        _put(stage, 'descriptor.json', desc_bytes, artifacts)
        errors = validator.validate(desc)
        if errors:
            raise ValueError('native export violates DSC: ' + ', '.join(errors))
        status = classify_outcome({page: bool(raw_pages.get(page, '').strip()) for page in selected})
        reason = 'native-extraction-' + status
        semantic_artifacts = {name: artifacts[name]['sha256'] for name in sorted(artifacts)}
        semantic_digest = _sha(_json(semantic_artifacts))
        manifest = {'version': OUTCOME_MANIFEST_VERSION, 'mode': 'native', 'status': status, 'reason': reason,
                    'visual_completeness': 'not-established',
                    'source': source_ref, 'configuration': {'path': 'configuration.json', 'sha256': _sha(config_bytes)},
                    'descriptor': artifacts['descriptor.json'], 'pages': selected,
                    'extractor': EXTRACTOR, 'provider_calls': 0, 'artifacts': artifacts,
                    'semantic_artifacts': semantic_artifacts, 'semantic_sha256': semantic_digest}
        (stage / 'manifest.json').write_bytes(_json(manifest))
        os.rename(stage, output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {'manifest': str(output / 'manifest.json'), 'status': status,
            'reason': reason, 'provider_calls': 0}
