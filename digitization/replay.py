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
    if manifest.get('mode') != 'recorded' or not isinstance(manifest.get('artifacts'), dict):
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
    for operation in operations.values():
        if not isinstance(operation, dict):
            raise IntegrityError('invalid operation selection record')
        if (not isinstance(operation.get('request'), dict)
                or operation['request'].get('version') != '1'):
            return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                    'provider_calls': 0}
        attempts = operation.get('attempts')
        selected = operation.get('selected_attempt')
        if (not isinstance(attempts, list) or any(not isinstance(a, dict) for a in attempts)
                or not any(a.get('id') == selected for a in attempts)):
            raise IntegrityError('selected response attempt is unavailable')
        for attempt in attempts:
            if attempt.get('version') != '1':
                return {'status': 'unsupported-version', 'reason': 'unsupported-version',
                        'provider_calls': 0}
            try:
                output = attempt['output']
                ref = artifacts[output['path']]
                if ref['sha256'] != output['sha256']:
                    raise ValueError('response artifact reference mismatch')
                validate_response(validator.load(root / output['path']))
            except (OSError, ValueError, KeyError, TypeError, validator.Duplicate) as error:
                raise IntegrityError('invalid recorded response artifact') from error

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
    return {'root': root, 'manifest': manifest, 'paths': paths,
            'report': report, 'config': config}


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
