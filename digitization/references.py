# Purpose: Convert staged SPA review verdicts into the reference.json regions
#   scope consumed by the shared evaluate operation (sunset-rmx.23; parser of
#   record: digitization/evaluation.py, reference.get('regions') ->
#   match_regions). Schema v1 is documented in digitization/references-schema.md.
# Responsibilities: Validate review-verdicts.json (SPA output shape plus the
#   schema-v1 correction_px extension) and the reference-regions-scope record;
#   map agree -> witness, differ (+ human correction rect) -> counterexample,
#   missed-ink -> human-only region, unknown/unreviewed/unmappable -> recorded
#   unknown excluded from denominators; freeze per-page scopes with source
#   digests (descriptor sha, verdicts sha, page render frames); keep pages with
#   no human-established truth (and descriptor pages absent from the verdict
#   file) as MISSING scopes (regions: null), never a fabricated empty truth.
# Rationale: Ownership lives in the digitization package, next to the evaluate
#   parser that normatively defines the regions scope — not in
#   dsc03/visual/verdicts_to_reference.py: the SPA-side module must stay a pure
#   bundle builder so the offline file:// review contract is untouched, and
#   reference-building is evaluation-side semantics. No silent resolution
#   anywhere: unknown stays unknown, disputed claims without a correction rect
#   never become truth, and every exclusion is recorded with a typed reason.
"""Review verdicts -> reference regions scopes (schema v1)."""
import hashlib
import json
import math
from pathlib import Path

VERDICTS = ('agree', 'differ', 'unknown')
ORIGINS = ('witness', 'counterexample', 'missed-ink')
PAGE_STATUSES = ('partial', 'missing')
UNKNOWN_REASONS = ('unreviewed', 'reviewer-unknown', 'unmapped-rect',
                   'page-unavailable', 'page-number-not-derivable')
REFERENCE_KIND = 'reference-regions-scope'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _rect_shape_ok(rect):
    return isinstance(rect, list) and len(rect) == 4


def _rect_numbers_ok(rect):
    return all(_is_number(v) for v in rect)


def _rect_extent_ok(rect):
    return _rect_numbers_ok(rect) and rect[2] > 0 and rect[3] > 0


def _valid_rect(rect):
    return _rect_shape_ok(rect) and _rect_extent_ok(rect)


def _page_number_ok(page):
    return page is None or type(page) is int


def _unavailable_ok(value):
    return value is None or isinstance(value, str)


def _rect_field_ok(rect):
    return rect is None or _valid_rect(rect)


def _verdict_ok(verdict):
    return verdict is None or verdict in VERDICTS


def _correction_ok(region):
    return 'correction_px' not in region or _valid_rect(region['correction_px'])


def _validate_carriers(carriers):
    _require(isinstance(carriers, list) and carriers != [], 'carriers-missing')


def _validate_region(region):
    _require(isinstance(region, dict), 'region-not-a-mapping')
    _require(isinstance(region.get('id'), str), 'region-id-not-string')
    _require(_rect_field_ok(region.get('rect_px')), 'region-rect-invalid')
    _require(_verdict_ok(region.get('verdict')), 'verdict-outside-vocabulary')
    _require(isinstance(region.get('note', ''), str), 'region-note-not-string')
    _require(_correction_ok(region), 'correction-rect-invalid')


def _validate_missed_ink(missed_ink):
    _require(isinstance(missed_ink, list), 'missed-ink-missing')
    for box in missed_ink:
        _require(_valid_rect(box.get('rect_px')), 'missed-ink-rect-invalid')


def _validate_regions(regions):
    _require(isinstance(regions, list), 'regions-missing')
    for region in regions:
        _validate_region(region)


def _validate_page(page):
    _require(isinstance(page, dict), 'page-not-a-mapping')
    _require(_page_number_ok(page.get('page')), 'page-number-invalid')
    _require(_unavailable_ok(page.get('unavailable')), 'unavailable-invalid')
    _validate_regions(page.get('regions'))
    _validate_missed_ink(page.get('missed_ink'))


def _validate_carrier(carrier):
    _require(isinstance(carrier, dict), 'carrier-not-a-mapping')
    _require(isinstance(carrier.get('carrier'), str), 'carrier-id-not-string')
    for page in carrier.get('pages', []):
        _validate_page(page)


def validate_verdicts(record):
    """Validate a review-verdicts.json record (schema v1); raise ValueError."""
    _require(isinstance(record, dict), 'verdicts-not-a-mapping')
    _validate_carriers(record.get('carriers'))
    for carrier in record['carriers']:
        _validate_carrier(carrier)


def _validate_reference_region(region):
    _require(isinstance(region, dict), 'reference-region-not-a-mapping')
    _require(isinstance(region.get('id'), str), 'reference-region-id-not-string')
    _require(type(region.get('page')) is int, 'reference-region-page-invalid')
    _require(_valid_rect(region.get('bbox')), 'reference-region-bbox-invalid')
    _require(region.get('origin') in ORIGINS, 'reference-origin-invalid')


def _missing_scope_ok(page):
    return page.get('status') != 'missing' or page.get('regions') is None


def _validate_reference_page(page):
    _require(isinstance(page, dict), 'reference-page-not-a-mapping')
    _require(page.get('status') in PAGE_STATUSES, 'reference-status-invalid')
    _require(_page_number_ok(page.get('page')), 'reference-page-number-invalid')
    _require(_missing_scope_ok(page), 'missing-scope-must-not-fabricate')


def validate_reference(record):
    """Validate a reference-regions-scope record (schema v1); raise ValueError."""
    _require(isinstance(record, dict), 'reference-not-a-mapping')
    _require(record.get('version') == '1', 'reference-version-unsupported')
    _require(record.get('kind') == REFERENCE_KIND, 'reference-kind-invalid')
    _require(isinstance(record.get('regions'), list), 'reference-regions-missing')
    _require(isinstance(record.get('pages'), list), 'reference-pages-missing')
    for region in record['regions']:
        _validate_reference_region(region)
    for page in record['pages']:
        _validate_reference_page(page)


def _unknown_reason(page_record, region):
    conditions = (
        (page_record.get('page') is None, 'page-number-not-derivable'),
        (page_record.get('unavailable') is not None, 'page-unavailable'),
        (region.get('rect_px') is None, 'unmapped-rect'))
    return next((reason for flag, reason in conditions if flag), None)


def _truth_bucket(region, page):
    if region.get('verdict') == 'agree':
        entry = {'id': region['id'], 'page': page, 'bbox': region['rect_px'],
                 'origin': 'witness'}
        return 'regions', entry
    return _differ_bucket(region, page)


def _differ_bucket(region, page):
    if _valid_rect(region.get('correction_px')):
        entry = {'id': region['id'], 'page': page, 'bbox': region['correction_px'],
                 'origin': 'counterexample', 'claim_bbox': region['rect_px']}
        return 'regions', entry
    differed = {'id': region['id'], 'claim_bbox': region['rect_px'],
                'correction_bbox': None}
    return 'differed', differed


def _classify(page_record, region):
    reason = _unknown_reason(page_record, region)
    if reason is not None:
        return 'unknown', {'id': region.get('id'), 'reason': reason}
    verdict_reason = {None: 'unreviewed', 'unknown': 'reviewer-unknown'}.get(
        region.get('verdict'))
    if verdict_reason is not None:
        return 'unknown', {'id': region.get('id'), 'reason': verdict_reason}
    return _truth_bucket(region, page_record.get('page'))


def _missed_ink_reason(page_record):
    if page_record.get('page') is None:
        return 'page-number-not-derivable'
    if page_record.get('unavailable') is not None:
        return 'page-unavailable'
    return None


def _missed_ink_pass(scope, page_record):
    reason = _missed_ink_reason(page_record)
    page = page_record.get('page')
    for index, box in enumerate(page_record.get('missed_ink', []), start=1):
        if reason is not None:
            scope['unknown'].append({'bbox': box.get('rect_px'), 'reason': reason})
            continue
        entry = {'id': f'missed-ink-{page}-{index}', 'page': page,
                 'bbox': box['rect_px'], 'origin': 'missed-ink'}
        scope['regions'].append(entry)
        scope['missed_ink'].append(entry)


def _witness_ids(regions):
    return [region['id'] for region in regions if region['origin'] == 'witness']


def _finalize(scope):
    if not scope['regions']:
        scope['regions'] = None
        return scope
    scope['status'] = 'partial'
    scope['witnesses'] = _witness_ids(scope['regions'])
    return scope


def _page_scope(page_record):
    scope = {'page': page_record.get('page'), 'status': 'missing', 'regions': [],
             'witnesses': [], 'differed': [], 'missed_ink': [], 'unknown': []}
    for region in page_record.get('regions', []):
        bucket, payload = _classify(page_record, region)
        scope[bucket].append(payload)
    _missed_ink_pass(scope, page_record)
    return _finalize(scope)


def _scope_regions(page):
    return page['regions'] or []


def _scope_regions_all(pages):
    entries = []
    for page in pages:
        entries.extend(_scope_regions(page))
    return entries


def _missing_pages(pages):
    return [page['page'] for page in pages if page['status'] == 'missing']


def _run_pages(run_directory):
    regions = json.loads((Path(run_directory) / 'regions.json').read_bytes())
    return {region.get('page') for region in regions}


def _unreviewed_pages(pages, run_directory):
    covered = {page['page'] for page in pages if page['page'] is not None}
    template = {'status': 'missing', 'regions': None, 'witnesses': [],
                'differed': [], 'missed_ink': [], 'unknown': []}
    return [{'page': page, **template} for page in sorted(_run_pages(run_directory) - covered)]


def _frames(path):
    frames = {}
    for region in json.loads(Path(path).read_bytes()):
        known = frames.setdefault(str(region.get('page')), [])
        if region.get('frame') not in known:
            known.append(region.get('frame'))
    return frames


def _single_carrier(record, descriptor):
    carriers = record.get('carriers', [])
    if len(carriers) != 1:
        raise ValueError('verdicts-carrier-count')
    carrier = carriers[0]
    if carrier.get('carrier') != descriptor.get('id'):
        raise ValueError('carrier-descriptor-mismatch')
    return carrier


def verdicts_to_reference(verdicts_path, run_directory):
    """Convert one SPA review-verdicts.json into a reference-regions-scope.

    ``run_directory`` is the digitization run under review (descriptor.json +
    regions.json); the returned record carries source digests (descriptor and
    verdicts sha256, page render frames) and per-page frozen scopes. Pages with
    no human-established truth — and descriptor pages absent from the verdict
    file — freeze as MISSING scopes (regions: null).
    """
    raw = Path(verdicts_path).read_bytes()
    record = json.loads(raw)
    validate_verdicts(record)
    run = Path(run_directory)
    descriptor = json.loads((run / 'descriptor.json').read_bytes())
    carrier = _single_carrier(record, descriptor)
    pages = [_page_scope(page) for page in carrier.get('pages', [])]
    pages += _unreviewed_pages(pages, run)
    source = {'carrier': descriptor.get('id'), 'reviewer': record.get('reviewer'),
              'rules': record.get('rules'),
              'descriptor_sha256': _sha256_file(run / 'descriptor.json'),
              'verdicts_sha256': hashlib.sha256(raw).hexdigest(),
              'frames': _frames(run / 'regions.json')}
    return {'version': '1', 'kind': REFERENCE_KIND, 'source': source,
            'regions': _scope_regions_all(pages), 'pages': pages,
            'missing_pages': _missing_pages(pages)}
