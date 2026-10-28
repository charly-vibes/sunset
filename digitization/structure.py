# Purpose: Retain source-bound OCR, model and manual structural observations.
# Responsibilities: Validate proposals atomically, derive poetic line/token maps,
#   and expose unresolved relationships without changing selected recognition.
# Rationale: sunset-rmx.4 keeps interpretation metadata in manifest-bound sidecars
#   so invalid proposals cannot overwrite valid DSC or select semantic winners.
import copy
import re

RELATIONS = {'caption-of', 'continues-to', 'member-of', 'authored-by', 'precedes'}


def tokens(text, offset=0, lines=(), observation_id=None):
    result, cursor = [], offset
    for match in re.finditer(r'\S+', text):
        line = next((line for line in lines
                     if line['start'] <= match.start() and match.end() <= line['end']), None)
        item = {'start': cursor, 'end': cursor + len(match[0]),
                'raw_start': match.start(), 'raw_end': match.end(),
                'observation_id': observation_id, 'bbox': line['bbox'] if line else None}
        result.append(item)
        cursor = item['end'] + 1
    return result


def _lines(text, supplied, box):
    if not isinstance(supplied, list):
        raise ValueError('lines must be a list')
    if not supplied:
        return []  # Unavailable geometry is explicit; never fabricate line boxes.
    spans, start, stanza, blank = [], 0, 0, False
    for physical in text.splitlines(keepends=True):
        body = physical.rstrip('\r\n')
        if body.strip():
            if blank and spans:
                stanza += 1
            spans.append((start, start + len(body), stanza, len(body) - len(body.lstrip())))
            blank = False
        else:
            blank = True
        start += len(physical)
    if len(supplied) != len(spans):
        raise ValueError('line geometry must cover every nonblank physical line')
    result = []
    for line, (start, end, stanza, indent) in zip(supplied, spans):
        if (not isinstance(line, dict) or set(line) != {'start', 'end', 'bbox'}
                or type(line['start']) is not int or type(line['end']) is not int
                or (line['start'], line['end']) != (start, end)):
            raise ValueError('line offsets must match exact physical text lines')
        bbox = line['bbox']
        if (not isinstance(bbox, list) or len(bbox) != 4
                or any(type(v) is not int for v in bbox)):
            raise ValueError('line boxes must use integer page points')
        x, y, w, h = bbox
        rx, ry, rw, rh = box
        if w <= 0 or h <= 0 or x < rx or y < ry or x + w > rx + rw or y + h > ry + rh:
            raise ValueError('line box outside source region/page frame')
        result.append({**line, 'stanza': stanza, 'indent': indent})
    return result


def _validate(proposal, regions, page, used):
    if not isinstance(proposal, dict) or not set(proposal).issubset(
            {'id', 'kind', 'region_id', 'producer', 'text', 'lines', 'relations'}):
        raise ValueError('invalid structure observation object/fields')
    identifier = proposal['id']
    if not isinstance(identifier, str) or not identifier or identifier in used:
        raise ValueError('missing or duplicate observation identity')
    if proposal['kind'] not in ('ocr', 'model', 'manual'):
        raise ValueError('unknown observation kind')
    region = regions[proposal['region_id']]
    if region['page'] != page:
        raise ValueError('observation must belong to its configured page')
    producer = proposal['producer']
    if (not isinstance(producer, dict) or not isinstance(producer.get('id'), str)
            or not producer['id'] or not isinstance(producer.get('version'), str)
            or not producer['version'] or not isinstance(producer.get('config'), dict)):
        raise ValueError('identified producer and configuration required')
    text = proposal.get('text', region['raw_text'])
    if not isinstance(text, str):
        raise ValueError('observation text must be a string')
    if proposal['kind'] == 'ocr' and text != region['raw_text']:
        raise ValueError('OCR layout must bind the selected raw recognition')
    lines = _lines(text, proposal.get('lines', []), region['bbox'])
    relations = proposal.get('relations', [])
    if not isinstance(relations, list):
        raise ValueError('relations must be a list')
    for relation in relations:
        if (not isinstance(relation, dict) or set(relation) != {'kind', 'target'}
                or relation['kind'] not in RELATIONS or relation['target'] not in regions):
            raise ValueError('invalid relationship kind or missing target')
    return {**copy.deepcopy(proposal), 'text': text, 'lines': lines,
            'relations': copy.deepcopy(relations), 'status': 'unresolved' if relations else 'recorded',
            'source_sha256': region['source_sha256'], 'selector_id': region['selector_id'],
            'frame': region['frame'], 'tokens': tokens(text, lines=lines, observation_id=identifier)}


def collect(config, pages, regions, mappings, source_sha256):
    """Return accepted observations plus diagnostics; never mutate selected OCR."""
    indexed = {r['region_id']: {**r, 'source_sha256': source_sha256} for r in regions}
    observations, diagnostics, unresolved, used = [], [], [], set()
    for region in regions:
        identifier = 'raw-' + region['region_id']
        used.add(identifier)
        observations.append({'id': identifier, 'kind': 'ocr', 'region_id': region['region_id'],
            'producer': region['producer'], 'text': region['raw_text'], 'lines': [], 'relations': [],
            'status': 'recorded', 'source_sha256': source_sha256,
            'selector_id': region['selector_id'], 'frame': region['frame'],
            'operation_key': region['operation_key'], 'selected_attempt': region['selected_attempt']})
    for page in pages:
        supplied = config['pages'][str(page)].get('structure', [])
        if not isinstance(supplied, list):
            supplied = [supplied]  # Record an invalid envelope as a diagnostic too.
            envelope_invalid = True
        else:
            envelope_invalid = False
        for position, proposal in enumerate(supplied):
            try:
                if envelope_invalid:
                    raise ValueError('page structure must be a list')
                observation = _validate(proposal, indexed, page, used)
            except (ValueError, KeyError, TypeError) as error:
                rid = proposal.get('region_id') if isinstance(proposal, dict) else None
                diagnostic = {'page': page, 'position': position, 'region_id': rid,
                              'reason': 'invalid-structure', 'detail': str(error),
                              'proposal': copy.deepcopy(proposal)}
                diagnostics.append(diagnostic)
                unresolved.append({'region_id': rid or f'page-{page}', 'reason': 'invalid-structure'})
                continue
            used.add(observation['id'])
            observations.append(observation)
            region = next(r for r in regions if r['region_id'] == observation['region_id'])
            if observation['relations']:
                region['alternatives'].extend({**relation, 'observation_id': observation['id'],
                                               'producer': observation['producer'], 'status': 'unresolved'}
                                              for relation in observation['relations'])
                unresolved.append({'region_id': region['region_id'], 'reason': 'structural-alternatives'})
    for mapping in mappings:
        region = indexed[mapping['region_id']]
        # Keep every OCR layout reading; pin the first complete geometry for search
        # derivation rather than implicitly letting later model/manual text win.
        layout = next((o for o in observations if o['region_id'] == region['region_id']
                       and o['kind'] == 'ocr' and o['lines']), None)
        mapping['tokens'] = tokens(region['raw_text'], mapping['start'],
                                   layout['lines'] if layout else [],
                                   layout['id'] if layout else 'raw-' + region['region_id'])
    return {'version': '1', 'observations': observations, 'diagnostics': diagnostics}, unresolved
