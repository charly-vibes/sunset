# Purpose: Define allocation-independent semantic state for refinement.
# Responsibilities: Canonicalize the active attributed graph while preserving multiplicity.
# Rationale: Cycle detection compares meaning across revisions without changing DSC identity.
import hashlib
import itertools
import json


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _producer(region):
    return region.get('producer')


def semantic_projection(config, pages, report):
    """Return versioned canonical bytes for the selected semantic graph state."""
    regions = report['regions']
    groups = {}
    for region in regions:
        attributes = {
            'page': region['page'], 'frame': region['frame'], 'bbox': region['bbox'],
            'kind': region['kind'], 'producer': _producer(region),
            'raw_text': region['raw_text'], 'layout_text': region['layout_text'],
            'search_text': region['search_text'],
        }
        groups.setdefault(_canonical(attributes), []).append(region)

    keys = sorted(groups)
    base = {
        'version': '1', 'source_sha256': config['source_sha256'],
        'provider': config['provider'], 'pages': sorted(pages),
        'render': config.get('render'), 'recognition': config.get('recognition'),
        'coverage': report['coverage'],
    }
    best = None
    # Permute only equal-attribute region nodes. This is the exact lexicographic
    # graph canonicalization required by the contract; multiplicity is retained.
    for partition in itertools.product(*(itertools.permutations(groups[key]) for key in keys)):
        ordered = [region for group in partition for region in group]
        labels = {region['region_id']: index for index, region in enumerate(ordered)}
        nodes = []
        for region in ordered:
            nodes.append({
                'page': region['page'], 'frame': region['frame'], 'bbox': region['bbox'],
                'kind': region['kind'], 'producer': _producer(region),
                'raw_text': region['raw_text'], 'layout_text': region['layout_text'],
                'search_text': region['search_text'],
                'alternatives': sorted(({
                    'kind': item.get('kind'),
                    'target': labels.get(item.get('target'), 'external'),
                    'producer': item.get('producer'), 'status': item.get('status'),
                } for item in region.get('alternatives', [])), key=_canonical),
            })
        observations = []
        for observation in report['structure']['observations']:
            observations.append({
                'region': labels[observation['region_id']],
                'kind': observation['kind'], 'producer': observation['producer'],
                'text': observation['text'], 'lines': observation['lines'],
                'status': observation['status'],
                'relations': sorted(({
                    'kind': relation['kind'],
                    'target': labels.get(relation['target'], 'external'),
                } for relation in observation['relations']), key=_canonical),
            })
        observations.sort(key=_canonical)
        unresolved = sorted(({
            'region': labels.get(item.get('region_id'), 'run'),
            'reason': item['reason'],
        } for item in report['unresolved']), key=_canonical)
        candidate = _canonical({**base, 'regions': nodes,
                                'observations': observations, 'unresolved': unresolved})
        if best is None or candidate < best:
            best = candidate
    return best or _canonical({**base, 'regions': [], 'observations': [], 'unresolved': []})


def projection_digest(projection):
    return hashlib.sha256(projection).hexdigest()
