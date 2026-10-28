# Purpose: Inspect retained digitization evidence without inference or mutation.
# Responsibilities: Verify local artifact bytes, reuse DSC validation/index and
#   locator resolution, and present source links, text, uncertainty and history.
# Rationale: sunset-rmx.20 reports usage only when the manifest agrees exactly
#   with its hash-bound ledger; revision and interpretation evidence stays visible.
import json
from pathlib import Path

from dsc03 import validator
from dsc03.inspect import build_index
from dsc03.locators import resolve
from digitization.pipeline import digest


class IntegrityError(ValueError):
    """Evidence is missing, malformed or inconsistent with retained hashes."""


def inspect_run(run_directory):
    root = Path(run_directory).resolve()
    try:
        manifest = validator.loads((root / 'manifest.json').read_text())
        if manifest['version'] != '1':
            raise ValueError('unsupported manifest version')
        for reference in manifest['artifacts'].values():
            path = (root / reference['path']).resolve()
            if not path.is_relative_to(root) or digest(path.read_bytes()) != reference['sha256']:
                raise ValueError('artifact path or digest mismatch')
        for key in ('source', 'configuration', 'descriptor'):
            ref = manifest[key]
            if manifest['artifacts'].get(ref['path']) != ref:
                raise ValueError('unbound manifest reference')
        ledger_ref = manifest['artifacts'].get('ledger.json')
        if ledger_ref is None or ledger_ref.get('path') != 'ledger.json':
            raise ValueError('unbound usage ledger')
        ledger = validator.load(root / 'ledger.json')
        if validator.canonical(ledger) != validator.canonical(manifest['usage']):
            raise ValueError('manifest usage disagrees with retained ledger')
        descriptor = validator.load(root / manifest['descriptor']['path'])
        errors = validator.validate(descriptor)
        if errors:
            raise ValueError('invalid DSC: ' + ', '.join(errors))
        if descriptor['source']['sha256'] != manifest['source']['sha256']:
            raise ValueError('descriptor source mismatch')
        operations = {}
        if 'operations' in manifest:
            operations = json.loads((root / 'operations.json').read_text())
            if manifest['artifacts'].get('operations.json') is None or operations != manifest['operations']:
                raise ValueError('unbound or inconsistent operation selections')
        structure = {'version': '1', 'observations': [], 'diagnostics': []}
        if 'structure' in manifest:
            ref = manifest['structure']
            if manifest['artifacts'].get(ref['path']) != ref:
                raise ValueError('unbound structure reference')
            structure = validator.load(root / ref['path'])
            if structure['version'] != '1':
                raise ValueError('unsupported structure version')
        refinement = None
        if 'refinement' in manifest:
            ref = manifest['refinement']
            if manifest['artifacts'].get(ref['path']) != ref:
                raise ValueError('unbound refinement reference')
            refinement = validator.load(root / ref['path'])
            if refinement['version'] != '1':
                raise ValueError('unsupported refinement version')
        index = build_index(descriptor)
        regions = json.loads((root / 'regions.json').read_text())
        for region in regions:
            selection = resolve(index, region['region_id'])
            if selection.status != 'resolved':
                raise ValueError('unresolved descriptor selector')
            region['selector'] = index.selectors[region['selector_id']]
            region['source_resolution'] = selection.status
        return {'status': manifest['status'], 'reason': manifest['reason'],
                'source': manifest['source'], 'configuration': manifest['configuration'],
                'regions': regions, 'usage': manifest['usage'],
                'unresolved': json.loads((root / 'unresolved.json').read_text())['regions'],
                'coverage': 'unexamined-outside-recorded-regions',
                'history': json.loads((root / 'history.json').read_text()),
                'trace': [json.loads(line) for line in (root / 'trace.jsonl').read_text().splitlines()],
                'descriptor': manifest['descriptor'], 'operations': operations, 'structure': structure, 'refinement': refinement}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, validator.Duplicate) as error:
        raise IntegrityError(str(error)) from error


def format_report(report):
    lines = [f"{report['status']}: {report['reason']}",
             f"Source SHA256: {report['source']['sha256']}",
             f"Coverage: {report['coverage']}"]
    for region in report['regions']:
        lines.extend([f"{region['region_id']} ({region['kind']}, {region['producer']})",
                      f"  {region['selector']['locator']} in {region['frame']}",
                      f"  Raw/layout: {region['raw_text']!r}",
                      f"  Search: {region['search_text']!r}",
                      f"  Revision: {region['revision']}; alternatives: {region['alternatives']}"])
    lines.extend(f"Unresolved {item['region_id']}: {item['reason']}" for item in report['unresolved'])
    if report['refinement'] is not None:
        lines.append('Refinement revisions/invalidations: ' + json.dumps(report['refinement'], ensure_ascii=False))
    lines.append('Structure observations/diagnostics: ' + json.dumps(report['structure'], ensure_ascii=False))
    lines.append('Operations/selections: ' + json.dumps(report['operations'], ensure_ascii=False, sort_keys=True))
    lines.append('Usage: ' + json.dumps(report['usage'], sort_keys=True))
    lines.append('History: ' + json.dumps(report['history'], ensure_ascii=False))
    return '\n'.join(lines)
