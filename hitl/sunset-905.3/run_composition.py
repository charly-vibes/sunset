# Purpose: Execute the owner-scoped real-PDF composition comparison for sunset-905.3.
# Responsibilities: Pin raw inputs, persist adapter outputs, check assembly laws,
#   and retain human region losses and unrecorded judgments without choosing a reader.
# Rationale: Partial page/text adapters cannot claim human segmentation conformance;
#   executable law witnesses and explicit unknown/loss accounting are separate results.
"""Run from the repository root: python3 hitl/sunset-905.3/run_composition.py."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dsc03 import adapters, canonical, validator
from dsc03.substrate import assembly, reader_b

CARRIERS = ('diario-de-poesia-excerpt', 'agentic-patterns-excerpt',
            'bank-statement-ca-excerpt')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def partition(desc):
    """Split existing page output into three compatible parts, never re-extract.

    Shared roots/profiles and document coverage stay identical. Each page and
    its dependent contents/evidence/annotations belong to exactly one part.
    One-page carriers have two root-only parts: the associativity witness is
    valid but exercises no three-page continuation semantics.
    """
    pages = [r['id'] for r in desc['regions'] if r['kind'] == 'page']
    roots = {v['root'] for v in desc['views']}
    parts = []
    for chunk in range(3):
        selected = set(pages[len(pages) * chunk // 3:len(pages) * (chunk + 1) // 3])
        regions = roots | selected
        content_ids = {r['to'] for r in desc['relations']
                       if r['kind'] == 'has-content' and r['from'] in regions}
        part = copy.deepcopy(desc)
        part['regions'] = [r for r in desc['regions'] if r['id'] in regions]
        part['contents'] = [c for c in desc['contents'] if c['id'] in content_ids]
        part['relations'] = [r for r in desc['relations']
                             if r['from'] in regions and r['to'] in regions | content_ids]
        part['evidence'] = [e for e in desc['evidence']
                            if set(e['content_ids']) <= content_ids]
        part['annotations'] = [a for a in desc['annotations']
                               if a['target'] in regions | content_ids]
        # Existing adapters declare pages with pgN / rbpN, in source-page order.
        scopes = {f'page:{i}' for i, rid in enumerate(pages, 1) if rid in selected}
        part['coverage'] = [c for c in desc['coverage']
                            if c['scope'] == 'document' or c['scope'] in scopes]
        parts.append(part)
    return parts


def record_set(items):
    return {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in items}


def check_laws(desc):
    a, b, c = partition(desc)
    left = assembly.compose(assembly.compose(a, b), c)
    right = assembly.compose(a, assembly.compose(b, c))
    identity = [assembly.compose(desc, assembly.empty_part()),
                assembly.compose(assembly.empty_part(), desc)]
    assembled = left.get('descriptor')
    laws = {
        'identity': all(r['status'] == 'assembled' and
                        assembly.canonically_equal(r['descriptor'], desc) for r in identity),
        'associativity': left['status'] == right['status'] == 'assembled' and
                         assembly.canonically_equal(left['descriptor'], right['descriptor']),
        'records_preserved': assembled is not None and all(
            record_set(assembled[k]) == record_set(desc[k])
            for k in desc if isinstance(desc[k], list)),
        'no_invented_relations': assembled is not None and
                                 record_set(assembled['relations']) == record_set(desc['relations']),
    }
    return laws, left, parts_from(a, b, c)


def parts_from(*parts):
    return list(parts)


def compare_human(sheet, source_sha, outputs):
    pages = [[r for r in d['regions'] if r['kind'] == 'page'] for d in outputs]
    # These adapters expose no source-anchored sub-page regions or geometry.
    # Refuse to reuse this projection if that contract changes: add an explicit
    # geometry-profile/anchor mapping instead of pairing by local IDs or labels.
    for desc in outputs:
        if desc['selectors'] or any(r.get('geometry') for r in desc['regions']):
            raise ValueError('geometry projection requires a declared source-frame mapping')
        if any(r['kind'] not in {'document', 'article', 'page'} for r in desc['regions']):
            raise ValueError('new subregion output requires a declared source-anchor mapping')
    inventory = [p['index'] for p in sheet['page_inventory']]
    page_counts = [len(p) for p in pages]
    inventory_class = ('AGREE' if inventory and
                       all(inventory == list(range(1, n + 1)) for n in page_counts)
                       else 'UNKNOWN' if not inventory else 'DISAGREE')
    rows = []
    for i, region in enumerate(sheet['structure']):
        rows.append({
            'source_index': i, 'page': region['page'], 'bbox': region['bbox'],
            'source_ref': f'sha256:{source_sha}#page:{region["page"]}',
            'class': 'LOSS',
            'reason': 'Neither current adapter emits source-anchored sub-page region geometry',
        })
    return {
        'reader': sheet['reader'],
        'page_inventory': {'class': inventory_class, 'human': inventory,
                           'machine_page_counts': page_counts},
        'region_geometry': rows,
        'reading_order': {'class': 'UNKNOWN',
                          'reason': 'Human ranks absent or derived_from_arrangement; no independent order oracle'},
        'types': {'class': 'UNKNOWN',
                  'reason': 'Regions-first scope; default/blank types are not a classification oracle'},
        'sections': {k: 'UNKNOWN' if not sheet[k] else 'LOSS'
                     for k in ('relations', 'space', 'context', 'annotations', 'losses', 'uncertainties')},
    }


def run(repo, out):
    repo, out = Path(repo), Path(out)
    hitl = repo / 'hitl/sunset-905.3'
    result = {
        'run_kind': 'agent-executed composition and extraction comparison against human sheets',
        'epub': 'owner-waived', 'real_carrier_conformance': False,
        'runner_sha256': sha(Path(__file__).read_bytes()),
        'implementation_sha256': {str(p.relative_to(repo)): sha(p.read_bytes()) for p in (
            repo / 'dsc03/adapters.py', repo / 'dsc03/substrate/reader_b.py',
            repo / 'dsc03/substrate/assembly.py', repo / 'dsc03/canonical.py')},
        'pymupdf_version': __import__('pymupdf').VersionBind,
        'pdftotext_version': subprocess.run(['pdftotext', '-v'], capture_output=True,
                                           text=True, check=True).stderr.splitlines()[0],
        'carriers': [],
    }
    for name in CARRIERS:
        source = repo / 'fixtures/carriers' / (name + '.pdf')
        source_sha = sha(source.read_bytes())
        if source.read_bytes() != (hitl / 'bundle/carriers' / source.name).read_bytes():
            raise ValueError(f'Carrier differs from human bundle: {name}')
        row = {'carrier': name, 'source_path': str(source.relative_to(repo)),
               'source_sha256': source_sha, 'outputs': [], 'human_comparisons': []}
        descriptors = []
        for label, describe in [('pymupdf', adapters.describe_pdf),
                                ('pdftotext', reader_b.describe_pdf_b)]:
            target = out / name / label
            desc = describe(source, target)
            desc['source']['locator'] = str(source.relative_to(repo))
            laws, assembled, parts = check_laws(desc)
            write_json(target / 'descriptor.json', desc)
            write_json(target / 'assembled.json', assembled)
            for i, part in enumerate(parts):
                write_json(target / f'part-{i + 1}.json', part)
            descriptors.append(desc)
            conflicting = copy.deepcopy(desc)
            conflicting['regions'][0]['kind'] = 'section'
            refusal = assembly.compose(desc, conflicting)
            row['outputs'].append({
                'injected_conflict': refusal,
                'adapter': label, 'descriptor_path': str((target / 'descriptor.json').relative_to(out)),
                'descriptor_sha256': sha((target / 'descriptor.json').read_bytes()),
                'schema_errors': validator.validate(desc),
                'canonical_readers_agree': canonical.agree(desc), 'laws': laws,
                'page_count': sum(r['kind'] == 'page' for r in desc['regions']),
                'text_content_count': sum(c['kind'] == 'text' for c in desc['contents']),
                'region_geometry_count': sum(bool(r.get('geometry')) for r in desc['regions']),
            })
        row['machine_agreement'] = reader_b.agreement(*descriptors)
        for reader in ('reader-a', 'reader-b'):
            path = hitl / 'runs' / reader / (name + '.observations.json')
            raw = path.read_bytes()
            comparison = compare_human(json.loads(raw), source_sha, descriptors)
            comparison.update(sheet_path=str(path.relative_to(repo)), sheet_sha256=sha(raw))
            row['human_comparisons'].append(comparison)
        result['carriers'].append(row)
    write_json(out / 'comparison.json', result)
    return result


if __name__ == '__main__':
    run(REPO, REPO / 'hitl/sunset-905.3/runs/composition')
