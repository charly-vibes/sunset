# Purpose: Expose local digitization run and inspection commands.
# Responsibilities: Parse documented operations, emit stable JSON outcomes and
#   refuse unavailable resume/replay instead of starting replacement runs.
# Rationale: sunset-rmx.3 adds explicit cache/fresh/selection controls; .7/.8 own recovery.
import argparse
import json

from digitization.artifacts import CacheIntegrityError
from digitization.inspection import IntegrityError, format_report, inspect_run
from digitization.pipeline import InputError, run


def main(argv=None):
    parser = argparse.ArgumentParser(description='Recorded, source-linked DSC digitization')
    commands = parser.add_subparsers(dest='operation', required=True)
    start = commands.add_parser('run')
    for flag in ('source', 'pages', 'config', 'output'):
        start.add_argument('--' + flag, required=True)
    start.add_argument('--cache')
    start.add_argument('--fresh', action='append', default=[], metavar='REGION_ID')
    start.add_argument('--select', action='append', default=[], metavar='REGION_ID=ATTEMPT_ID')
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--run', required=True)
    inspect.add_argument('--json', action='store_true')
    resume = commands.add_parser('resume')
    resume.add_argument('--run', required=True)
    replay = commands.add_parser('replay')
    replay.add_argument('--run', required=True)
    replay.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation in ('resume', 'replay'):
            result = {'status': 'unsupported', 'reason': 'unsupported-operation',
                      'operation': args.operation, 'provider_calls': 0}
            code = 4
        elif args.operation == 'inspect':
            result = inspect_run(args.run)
            if not args.json:
                print(format_report(result))
                return 0
            code = 0
        else:
            try:
                pages = [int(p) for p in args.pages.split(',')]
            except ValueError as error:
                raise InputError('pages must be comma-separated integer PDF indices') from error
            selections = {}
            for selection in args.select:
                if '=' not in selection:
                    raise InputError('selection must be REGION_ID=ATTEMPT_ID')
                region, attempt = selection.split('=', 1)
                if not region or not attempt or region in selections:
                    raise InputError('invalid or duplicate explicit selection')
                selections[region] = attempt
            result = run(args.source, pages, args.config, args.output, cache_dir=args.cache,
                         fresh=args.fresh, selections=selections)
            code = 2 if result['status'] == 'stopped-with-unresolved-work' else 0
    except CacheIntegrityError as error:
        result = {'status': 'cache-failed', 'reason': 'cache-integrity-failure', 'detail': str(error), 'provider_calls': 0}
        code = 5
    except IntegrityError as error:
        result = {'status': 'inspection-failed', 'reason': 'integrity-failure', 'detail': str(error), 'provider_calls': 0}
        code = 5
    except (InputError, OSError) as error:
        result = {'status': 'invalid-input', 'reason': 'invalid-input', 'detail': str(error), 'provider_calls': 0}
        code = 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
