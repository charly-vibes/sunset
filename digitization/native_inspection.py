# Purpose: Read-only verification of retained native extraction runs.
# Responsibilities: Verify native manifest integrity, artifact digests, mappings
#   and profiles; recompute the outcome from descriptor coverage and report it.
# Rationale: sunset-jbb.4 keeps inspection offline and hash-bound; sunset-1ry
#   recomputes the outcome vocabulary (text-complete/text-with-gaps/no-text-read)
#   from coverage rows instead of trusting the manifest status.
import math
from pathlib import Path
import unicodedata

import pymupdf

from dsc03 import validator

from digitization.native import (NORMALIZATION, OPTIONS, OUTCOME_MANIFEST_VERSION,
                                 _json, _map_box, _sha, classify_outcome)

NATIVE_ARTIFACTS = {'source.pdf', 'raw.txt', 'search.txt', 'word-map.json',
                    'line-map.json', 'page-map.json', 'configuration.json',
                    'descriptor.json', 'carrier/geometry.json', 'carrier/selector.json',
                    'carrier/inventory.json', 'carrier/manifest.json'}


def inspect_native(run_directory):
    root = Path(run_directory).resolve()
    try:
        manifest_path = root / 'manifest.json'
        if manifest_path.is_symlink() or not manifest_path.resolve().is_relative_to(root):
            raise ValueError('manifest path escapes native run')
        manifest = validator.load(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError('invalid native manifest')
        if manifest.get('version') != OUTCOME_MANIFEST_VERSION:
            return {'mode': 'native', 'status': 'unsupported-version', 'reason': 'unsupported-version', 'provider_calls': 0}
        if manifest.get('mode') != 'native':
            raise ValueError('not a native run')
        artifacts = manifest.get('artifacts')
        # carrier/geometry.json is required only when a geometry profile is
        # declared; the profile-binding check below enforces that binding.
        required = NATIVE_ARTIFACTS - {'carrier/geometry.json'}
        if not isinstance(artifacts, dict) or not required <= set(artifacts):
            raise ValueError('incomplete native artifact set')
        if not isinstance(manifest.get('pages'), list) or not isinstance(manifest.get('source'), dict):
            raise ValueError('invalid native manifest mappings')
        root = root.resolve()
        if manifest.get('visual_completeness') != 'not-established':
            raise ValueError('native visual completeness claim is invalid')
        paths = {}
        for name, ref in artifacts.items():
            if not isinstance(ref, dict) or ref.get('path') != name or not isinstance(ref.get('sha256'), str):
                raise ValueError('invalid native artifact reference')
            candidate = root / name
            path = candidate.resolve()
            if not path.is_relative_to(root) or candidate.is_symlink() or _sha(path.read_bytes()) != ref['sha256']:
                raise ValueError('artifact path or digest mismatch')
            paths[name] = path
        semantic = {name: ref['sha256'] for name, ref in sorted(artifacts.items())}
        if (manifest.get('semantic_artifacts') != semantic
                or manifest.get('semantic_sha256') != _sha(_json(semantic))):
            raise ValueError('native semantic digest mismatch')
        for key in ('source', 'configuration', 'descriptor'):
            ref = manifest[key]
            if manifest['artifacts'].get(ref['path']) != ref:
                raise ValueError('unbound native manifest reference')
        descriptor = validator.load(root / manifest['descriptor']['path'])
        errors = validator.validate(descriptor)
        if errors or descriptor['source']['sha256'] != manifest['source']['sha256']:
            raise ValueError('invalid native descriptor')
        from dsc03.profiles import Registry, resolve as resolve_profile
        for profile in descriptor['profiles']:
            if not isinstance(profile, dict) or not isinstance(profile.get('uri'), str):
                raise ValueError('invalid native profile declaration')
            reference = artifacts.get(profile['uri'])
            if (reference is None or reference.get('sha256') != profile.get('sha256')
                    or reference.get('path') != profile['uri']):
                raise ValueError('unbound native profile artifact')
            profile_status, _ = resolve_profile(profile, Registry(root))
            if profile_status != 'resolved':
                raise ValueError('native profile cannot be resolved: ' + profile_status)
        raw = (root / 'raw.txt').read_text(encoding='utf-8')
        search = (root / 'search.txt').read_text(encoding='utf-8')
        words = validator.load(root / 'word-map.json')
        lines = validator.load(root / 'line-map.json')
        frames = validator.load(root / 'page-map.json')
        if not isinstance(words, list) or not isinstance(lines, list) or not isinstance(frames, list):
            raise ValueError('invalid native text mappings')
        source_bytes = paths['source.pdf'].read_bytes()
        source_hash = _sha(source_bytes)
        for item in words + lines:
            if not isinstance(item, dict) or item.get('source_sha256') != source_hash:
                raise ValueError('native mapping source mismatch')
            start, end = item.get('raw_start'), item.get('raw_end')
            if (type(start) is not int or type(end) is not int or start < 0 or end < start
                    or end > len(raw) or raw[start:end] != item.get('text')):
                raise ValueError('native raw span mismatch')
        configuration = validator.load(root / manifest['configuration']['path'])
        if configuration.get('options') != OPTIONS or configuration.get('normalization') != NORMALIZATION:
            raise ValueError('native configuration does not describe the extraction')
        if configuration.get('extractor') != manifest['extractor'] or configuration.get('pages') != manifest['pages']:
            raise ValueError('native configuration does not match the run')
        if not isinstance(words, list) or not isinstance(lines, list):
            raise ValueError('invalid native mappings')
        expected_search = ' '.join(unicodedata.normalize('NFC', word['text']) for word in words)
        if search != expected_search:
            raise ValueError('native search text does not match word mappings')
        frame_by_page = {item['page']: item for item in frames}
        if len(frame_by_page) != len(frames):
            raise ValueError('duplicate native page frame')
        search_cursor = 0
        for item in words:
            normalized = unicodedata.normalize('NFC', item['text'])
            if item['search_start'] != search_cursor or item['search_end'] != search_cursor + len(normalized):
                raise ValueError('native search offset mismatch')
            if search[item['search_start']:item['search_end']] != normalized:
                raise ValueError('native search token mismatch')
            search_cursor = item['search_end'] + 1
            if (type(item.get('search_start')) is not int or type(item.get('search_end')) is not int
                    or item['search_start'] < 0 or item['search_end'] < item['search_start']
                    or item['search_end'] > len(search)):
                raise ValueError('invalid native search span')
            if len(item['box']) != 4 or item['box'][2] <= item['box'][0] or item['box'][3] <= item['box'][1]:
                raise ValueError('invalid native word box')
            frame = frame_by_page.get(item['page'])
            if frame is None or item['frame'] != frame['frame'] or len(item['source_box']) != 4:
                raise ValueError('native word frame mismatch')
            if len(item['source_box']) != 4 or len(item['box']) != 4:
                raise ValueError('invalid native word boxes')
            mapped = _map_box(item['source_box'], pymupdf.Matrix(*frame['source_to_page']))
            if any(not math.isclose(a, b, abs_tol=1e-4) for a, b in zip(mapped, item['box'])):
                raise ValueError('native word transform mismatch')
        for item in lines:
            if item['page'] not in frame_by_page or item['frame'] != frame_by_page[item['page']]['frame']:
                raise ValueError('native line frame mismatch')
        frame_pages = [frame['page'] for frame in frames]
        # Aligner-failed selected pages ship no frame (sunset-1uv): frames are
        # the aligned subset of the selected pages, in selection order.
        if (len(frame_pages) != len(set(frame_pages))
                or not set(frame_pages) <= set(manifest['pages'])
                or frame_pages != [p for p in manifest['pages'] if p in set(frame_pages)]):
            raise ValueError('native page frame mismatch')
        for frame in frames:
            if (frame['frame'] != f"page-{frame['page']}-pt"
                    or frame['source_frame'] != 'unrotated-crop-page-pt'
                    or frame['target_frame'] != 'rotated-visible-page-pt'
                    or len(frame['source_to_page']) != 6
                    or len(frame['source_origin']) != 2
                    or len(frame['source_dimensions']) != 2
                    or len(frame['target_dimensions']) != 2):
                raise ValueError('invalid native page transform')
        coverage_entries = descriptor['coverage']
        excluded_pages = sorted({int(item['scope'][5:]) for item in coverage_entries
                                 if item['scope'].startswith('page:')
                                 and 'excluded by native extraction selection' in item['reason']})
        unexamined_pages = sorted({int(item['scope'][5:]) for item in coverage_entries
                                   if item['scope'].startswith('page:')
                                   and item['feature'] == 'pdf:glyphs'
                                   and item['status'] == 'unexamined'
                                   and (item['reason'].startswith('no native text observed')
                                        or item['reason'].startswith('native word alignment failed'))
                                   and int(item['scope'][5:]) not in excluded_pages})
        textless = set(unexamined_pages)
        expected_status = classify_outcome({page: page not in textless
                                            for page in manifest['pages']})
        expected_reason = 'native-extraction-' + expected_status
        if manifest.get('status') != expected_status or manifest.get('reason') != expected_reason:
            raise ValueError('native status disagrees with descriptor coverage')
        return {'mode': 'native', 'status': manifest['status'], 'reason': manifest['reason'],
                'source': manifest['source'], 'pages': manifest['pages'], 'extractor': manifest['extractor'],
                'words': words, 'lines': lines, 'frames': frames, 'descriptor': manifest['descriptor'],
                'coverage': {'visual_completeness': manifest['visual_completeness'],
                             'excluded_pages': excluded_pages, 'unexamined_pages': unexamined_pages,
                             'features': coverage_entries}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            OverflowError, validator.Duplicate) as error:
        from digitization.inspection import IntegrityError
        raise IntegrityError(str(error)) from error
