# Purpose: Expose local digitization run and inspection commands.
# Responsibilities: Parse documented operations, emit stable JSON outcomes and
#   keep recovery/replay offline and bound to original run artifacts.
# Rationale: sunset-rmx.3 adds cache/fresh/selection controls; .7 enables safe
#   inspection-based recovery, .8 owns recorded replay, and sunset-jbb.3 adds
#   explicit partial native results and stable expected-failure exits.
import argparse
import json
from pathlib import Path

from digitization.artifacts import CacheIntegrityError
from digitization.inspection import IntegrityError, format_report, inspect_run
from digitization.pipeline import InputError, resume as resume_run, run
from digitization.replay import replay as replay_run
from digitization.evaluation import evaluate as evaluate_run
from digitization.native import NativeInputError, extract as extract_native


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
    replay.add_argument('--compare')
    evaluate = commands.add_parser('evaluate')
    evaluate.add_argument('--baseline', required=True)
    evaluate.add_argument('--candidate', required=True)
    evaluate.add_argument('--reference', required=True)
    evaluate.add_argument('--policy', required=True)
    evaluate.add_argument('--output', required=True)
    native = commands.add_parser('native')
    native.add_argument('--source', required=True)
    native.add_argument('--output', required=True)
    native.add_argument('--pages')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'replay':
            result = replay_run(args.run, args.output, compare=args.compare)
            code = {'replayed': 0, 'incomplete-artifacts': 2,
                    'unsupported-version': 4}.get(result['status'], 5)
        elif args.operation == 'evaluate':
            result = evaluate_run(args.baseline, args.candidate, args.reference,
                                  args.policy, args.output)
            code = 0 if result['status'] == 'measured' else 2
        elif args.operation == 'resume':
            result = resume_run(args.run)
            code = {'stopped-with-unresolved-work': 2, 'partial': 2,
                    'unsupported-version': 4}.get(result['status'], 0)
        elif args.operation == 'inspect':
            result = inspect_run(args.run)
            if result.get('status') == 'unsupported-version':
                code = 4
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                return code
            if not args.json:
                print(format_report(result))
                return 0
            code = 0
        elif args.operation == 'native':
            try:
                pages = None if args.pages is None else [int(p) for p in args.pages.split(',')]
            except ValueError as error:
                raise InputError('pages must be comma-separated integer PDF indices') from error
            result = extract_native(args.source, args.output, pages)
            code = 2 if result['status'] == 'partial' else 0
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
    except NativeInputError as error:
        result = {'status': 'invalid-input', 'reason': error.reason, 'detail': str(error), 'provider_calls': 0}
        code = 3
    except (InputError, OSError, ValueError) as error:
        result = {'status': 'invalid-input', 'reason': 'invalid-input', 'detail': str(error), 'provider_calls': 0}
        code = 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
