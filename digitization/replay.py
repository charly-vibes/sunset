# Purpose: Reconstruct a verified recorded run without inference or network I/O.
# Responsibilities: Validate source artifacts and selected responses, copy the
#   immutable semantic record, and retain original execution data separately.
# Rationale: sunset-rmx.8 keeps replay distinct from fresh extraction and never
#   fills missing outputs or refreshes source-run timing and billing values.
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from dsc03 import validator
from digitization.budget import BudgetLedger
from digitization.inspection import IntegrityError, inspect_run
from digitization.pipeline import InputError, digest, json_bytes
from digitization.artifacts import validate_response


SEMANTIC_EXCLUSIONS = {'ledger.json'}


def _verify_recorded_selections(run):
    """Validate every selected recorded attempt against its bound artifact."""
    for operation in run['report']['operations'].values():
        outcome = _verify_recorded_operation(operation, run)
        if outcome is not None:
            return outcome
    return None


def _verify_recorded_operation(operation, run):
    """One recorded operation: versioned request, available selection, outputs."""
    if (not isinstance(operation, dict) or not isinstance(operation.get('request'), dict)
            or operation['request'].get('version') != '1'):
        return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                'provider_calls': 0}
    attempts = operation.get('attempts')
    selected = operation.get('selected_attempt')
    if (not isinstance(attempts, list) or any(not isinstance(a, dict) for a in attempts)
            or not any(a.get('id') == selected for a in attempts)):
        raise IntegrityError('selected response attempt is unavailable')
    for attempt in attempts:
        outcome = _verify_recorded_attempt(attempt, run)
        if outcome is not None:
            return outcome
    return None


def _verify_recorded_attempt(attempt, run):
    """One recorded attempt: pinned output must hold a valid response."""
    if attempt.get('version') != '1':
        return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                'provider_calls': 0}
    try:
        output = attempt['output']
        ref = run['manifest']['artifacts'][output['path']]
        if ref['sha256'] != output['sha256']:
            raise ValueError('response artifact reference mismatch')
        validate_response(validator.load(run['root'] / output['path']))
    except (OSError, ValueError, KeyError, TypeError, validator.Duplicate) as error:
        raise IntegrityError('invalid recorded response artifact') from error
    return None


def _verify_local_selections(run):
    """Cross-bind local selections: manifest summary, region, history, blob.

    A completed local run records operation_key and selected_attempt on the
    manifest summary and on the matching region record; freshly dispatched
    operations additionally carry one recognize revision in history whose raw
    output blob is digest-bound in the manifest artifacts. Cache-served
    operations leave no fresh blob — their selection rests on the region
    record and the hash-bound usage ledger. Replaying never re-dispatches.
    """
    artifacts = run['manifest']['artifacts']
    for name in ('history.json', 'regions.json'):
        reference = artifacts.get(name)
        if not isinstance(reference, dict) or reference.get('path') != name:
            raise IntegrityError('unbound replay artifact: ' + name)
    fresh = _local_fresh_selections(run['root'], artifacts)
    _verify_local_operations(run['report'], fresh)
    return None


def _local_history_record(entry):
    """Validated (key, attempt, revision, blob) of a local recognize entry."""
    if (not isinstance(entry, dict) or entry.get('operation') != 'recognize'
            or entry.get('mode') != 'local'):
        return None
    fields = (entry.get('operation_key'), entry.get('selected_attempt'),
              entry.get('revision'), entry.get('artifact'))
    if any(not isinstance(value, str) or not value for value in fields):
        raise IntegrityError('invalid local history record')
    return fields


def _local_fresh_selections(root, artifacts):
    """Map operation_key to (attempt, revision) for freshly dispatched ops."""
    try:
        history = json.loads((root / 'history.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise IntegrityError('invalid local history') from error
    if not isinstance(history, list):
        raise IntegrityError('invalid local history')
    fresh = {}
    for entry in history:
        record = _local_history_record(entry)
        if record is None:
            continue
        key, attempt, revision, blob = record
        if not any(reference['sha256'] == blob for reference in artifacts.values()):
            raise IntegrityError('unbound local response artifact')
        fresh[key] = (attempt, revision)
    return fresh


def _local_selection_record(operation):
    """A local manifest selection: bool cache_hit plus nonempty key strings."""
    if not isinstance(operation, dict):
        raise IntegrityError('invalid local operation selection record')
    if not isinstance(operation.get('cache_hit'), bool):
        raise IntegrityError('invalid local operation selection record')
    fields = (operation.get('operation_key'), operation.get('selected_attempt'))
    if any(not isinstance(value, str) or not value for value in fields):
        raise IntegrityError('invalid local operation selection record')


def _region_agrees(region, operation):
    """True when the region record carries the manifest's selection."""
    return (region is not None and region.get('operation_key') == operation['operation_key']
            and region.get('selected_attempt') == operation['selected_attempt']
            and isinstance(region.get('revision'), str))


def _verify_local_operations(report, fresh):
    """Every local operation selection must agree with region and history."""
    regions = {region['region_id']: region for region in report['regions']}
    for operation_id, operation in report['operations'].items():
        _local_selection_record(operation)
        region = regions.get(operation_id)
        if not _region_agrees(region, operation):
            raise IntegrityError('local selection disagrees with region records')
        if operation['cache_hit']:
            continue
        if fresh.get(operation['operation_key']) != (operation['selected_attempt'],
                                                     region['revision']):
            raise IntegrityError('local selection history is unverifiable')


def _load_run(directory):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise InputError('run directory does not exist')
    manifest_path = root / 'manifest.json'
    if not manifest_path.resolve().is_relative_to(root.resolve()):
        raise IntegrityError('manifest path escapes run directory')
    try:
        manifest = validator.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError, validator.Duplicate) as error:
        raise IntegrityError('invalid replay manifest') from error
    if not isinstance(manifest, dict):
        raise IntegrityError('invalid replay manifest')
    if manifest.get('mode') == 'native':
        from digitization.native import inspect_native
        report = inspect_native(root)
        if report.get('status') == 'unsupported-version':
            return {'status': 'unsupported-version', 'reason': 'unsupported-version', 'provider_calls': 0}
        return {'root': root, 'manifest': manifest, 'report': report, 'native': True,
                'paths': {name: root / name for name in manifest['artifacts']}}
    if manifest.get('version') != '1':
        return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                'provider_calls': 0}
    mode = manifest.get('mode')
    if mode not in ('recorded', 'local') or not isinstance(manifest.get('artifacts'), dict):
        return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                'provider_calls': 0}
    artifacts = manifest['artifacts']
    root_resolved = root.resolve()
    paths = {}
    for name, reference in artifacts.items():
        if (not isinstance(reference, dict) or not isinstance(reference.get('path'), str)
                or not isinstance(reference.get('sha256'), str)):
            raise IntegrityError('invalid artifact reference')
        path = (root / reference['path']).resolve()
        if not path.is_relative_to(root_resolved):
            raise IntegrityError('artifact path escapes run directory')
        if not path.is_file():
            return {'status': 'incomplete-artifacts', 'reason': 'incomplete-artifacts',
                    'provider_calls': 0, 'missing': reference['path']}
        try:
            artifact_bytes = path.read_bytes()
        except FileNotFoundError:
            return {'status': 'incomplete-artifacts', 'reason': 'incomplete-artifacts',
                    'provider_calls': 0, 'missing': reference['path']}
        except OSError as error:
            raise IntegrityError('unreadable artifact: ' + reference['path']) from error
        if digest(artifact_bytes) != reference['sha256']:
            raise IntegrityError('artifact digest mismatch: ' + reference['path'])
        paths[name] = path

    try:
        config = validator.load(root / manifest['configuration']['path'])
        descriptor = validator.load(root / manifest['descriptor']['path'])
    except (OSError, ValueError, KeyError, TypeError, validator.Duplicate) as error:
        raise IntegrityError('invalid pinned replay schema') from error
    if config.get('version') != '1' or descriptor.get('version') != '0.3':
        return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                'provider_calls': 0}
    for field, expected in (('structure', '1'), ('refinement', '1')):
        reference = manifest.get(field)
        if reference is not None:
            try:
                value = validator.load(root / reference['path'])
            except (OSError, ValueError, KeyError, TypeError, validator.Duplicate) as error:
                raise IntegrityError('invalid ' + field + ' replay schema') from error
            if value.get('version') != expected:
                return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                        'provider_calls': 0}

    report = inspect_run(root)
    operations = report['operations']
    if not isinstance(operations, dict):
        raise IntegrityError('invalid operation selections')
    recorded = {'root': root, 'manifest': manifest, 'paths': paths,
                'report': report, 'config': config}
    if mode == 'local':
        _verify_local_selections(recorded)
    else:
        outcome = _verify_recorded_selections(recorded)
        if outcome is not None:
            return outcome

    ledger_path = root / 'budget-state.json'
    if config.get('budget') is not None and not ledger_path.is_file():
        return {'status': 'incomplete-artifacts', 'reason': 'incomplete-artifacts',
                'provider_calls': 0, 'missing': 'budget-state.json'}
    if ledger_path.is_file():
        if not ledger_path.resolve().is_relative_to(root_resolved):
            raise IntegrityError('budget state escapes run directory')
        try:
            budget = BudgetLedger.open(ledger_path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise IntegrityError('invalid durable budget state') from error
        if budget.state['policy'] != config.get('budget'):
            raise IntegrityError('durable budget policy mismatch')
    return recorded


def _comparison(recorded, fresh):
    before = {region['region_id']: region['raw_text'] for region in recorded['report']['regions']}
    after = {region['region_id']: region['raw_text'] for region in fresh['report']['regions']}
    differences = []
    for region_id in sorted(set(before) | set(after)):
        old, new = before.get(region_id), after.get(region_id)
        if old != new:
            differences.append({'region_id': region_id, 'recorded': old, 'fresh': new,
                                'status': 'different'})
    return {'fresh_run_manifest': str(fresh['root'] / 'manifest.json'),
            'differences': differences}


def replay(run_directory, output, *, compare=None):
    recorded = _load_run(run_directory)
    if 'root' not in recorded:
        return recorded
    if recorded.get('native'):
        root = recorded['root']
        destination = Path(output).absolute()
        if destination.exists() or destination.is_symlink():
            raise InputError('replay output directory already exists')
        if destination.resolve().is_relative_to(root) or root.is_relative_to(destination.resolve()):
            raise InputError('replay output must be separate from source run')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.replay-', dir=destination.parent) as temporary:
            stage = Path(temporary) / 'run'
            stage.mkdir()
            for name, reference in recorded['manifest']['artifacts'].items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(recorded['paths'][name], target)
            shutil.copyfile(root / 'manifest.json', stage / 'manifest.json')
            (stage / 'replay-report.json').write_bytes(json_bytes({
                'version': '1', 'status': 'replayed', 'provider_calls': 0,
                'semantic_artifacts': recorded['manifest']['semantic_artifacts'],
                'semantic_sha256': recorded['manifest']['semantic_sha256'],
                'execution_envelope': {'origin': 'original-run', 'fresh_measurement': False}}))
            os.rename(stage, destination)
        return {'manifest': str(destination / 'manifest.json'), 'status': 'replayed',
                'reason': 'replay-verified', 'provider_calls': 0,
                'semantic_sha256': recorded['manifest']['semantic_sha256']}
    fresh = _load_run(compare) if compare is not None else None
    if fresh is not None and 'root' not in fresh:
        return fresh
    root = recorded['root']
    destination = Path(output).absolute()
    resolved_destination = destination.resolve()
    if destination.exists() or destination.is_symlink():
        raise InputError('replay output directory already exists')
    if resolved_destination.is_relative_to(root) or root.is_relative_to(resolved_destination):
        raise InputError('replay output must be separate from source run')

    semantic_hashes = {name: reference['sha256']
                       for name, reference in recorded['manifest']['artifacts'].items()
                       if name not in SEMANTIC_EXCLUSIONS}
    semantic_digest = hashlib.sha256(json_bytes(semantic_hashes)).hexdigest()
    comparison = _comparison(recorded, fresh) if fresh is not None else None
    replay_report = {'version': '1', 'status': 'replayed', 'provider_calls': 0,
                     'semantic_artifacts': semantic_hashes,
                     'semantic_sha256': semantic_digest,
                     'execution_envelope': {'origin': 'original-run',
                                            'usage': recorded['report']['usage'],
                                            'fresh_measurement': False},
                     'fresh_comparison': comparison}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.replay-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        for name, reference in recorded['manifest']['artifacts'].items():
            relative = Path(reference['path'])
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(recorded['paths'][name], target)
        shutil.copyfile(root / 'manifest.json', stage / 'manifest.json')
        if (root / 'budget-state.json').is_file():
            shutil.copyfile(root / 'budget-state.json', stage / 'budget-state.json')
        (stage / 'replay-report.json').write_bytes(json_bytes(replay_report))
        os.rename(stage, destination)
    return {'manifest': str(destination / 'manifest.json'), 'status': 'replayed',
            'reason': 'replay-verified', 'provider_calls': 0,
            'semantic_sha256': semantic_digest,
            'fresh_comparison': comparison}
