"""Measured deterministic browser shards and fail-closed aggregate proof (stdlib only)."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def plan_tests(inventory, durations, count):
    ids = sorted(inventory)
    if not ids or len(set(ids)) != len(ids) or not 1 <= count <= 3 or len(ids) < count:
        raise ValueError('Nonempty unique inventory and one to three nonempty shards required')
    weights = {}
    for name in ids:
        value = durations.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Missing or invalid measured duration: ' + name)
        weights[name] = value
    shards = [[] for _ in range(count)]
    loads = [0.0] * count
    for name in sorted(ids, key=lambda key: (-weights[key], key)):
        index = min(range(count), key=lambda index: (loads[index], index))
        shards[index].append(name)
        loads[index] += weights[name]
    return dict(inventory=ids, inventory_sha256=digest(ids),
                shards=[sorted(shard) for shard in shards], measured_weight_seconds=loads)


def aggregate(paths, manifest, checkout_sha, source_sha, count, require_ci=False):
    if not checkout_sha or not source_sha or len(paths) != count:
        raise ValueError('Exact SHAs and every shard report required')
    expected = plan_tests(sorted(manifest['durations']), manifest['durations'], count)
    reports = [json.loads(Path(path).read_text(encoding='utf-8')) for path in paths]
    indexes = [row.get('shard_index') for row in reports]
    if any(type(index) is not int for index in indexes) or sorted(indexes) != list(range(count)) or len(set(indexes)) != count:
        raise ValueError('Missing or duplicate shard indexes')
    executed, runtimes, databases, media_roots, timings, run_ids, summaries = [], [], [], [], [], set(), []
    for path, report in zip(paths, reports):
        index = report['shard_index']
        if (report.get('plan') != expected or report.get('shard_count') != count
                or report.get('inventory') != expected['inventory']
                or report.get('selected') != expected['shards'][index]
                or report.get('checkout_sha') != checkout_sha or report.get('source_sha') != source_sha
                or report.get('complete') is not True):
            raise ValueError('Shard inventory, source, assignment or completion mismatch')
        rows = report.get('tests', [])
        ids = [row['id'] for row in rows]
        execution = report.get('execution_ids', [])
        if sorted(execution) != report['selected'] or len(set(execution)) != len(execution):
            raise ValueError('Missing or duplicated test execution')
        if sorted(ids) != report['selected'] or len(set(ids)) != len(ids) or any(
                row.get('status') != 'passed' or not math.isfinite(row.get('seconds', -1)) or row['seconds'] < 0
                for row in rows):
            raise ValueError('Failed, skipped, missing, duplicate or invalid test result')
        summary_path = Path(path).with_name(Path(path).name.replace('test-results.', 'browser_regression_summary.'))
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        accounting = summary.get('accounting', {})
        github = summary.get('github_actions', {})
        if (summary.get('driver_backed_success') is not True or summary.get('runner_return_code') != 0
                or summary.get('return_code') != 0 or summary.get('status') != 'passed'
                or summary.get('skipped_count') != 0 or summary.get('tests_run_count') != len(ids)
                or summary.get('tests_found_count') != len(expected['inventory'])
                or summary.get('browser') != 'Chrome' or summary.get('require_browser') is not True
                or summary.get('run_browser_tests_env') != 'true'
                or summary.get('proof_label') != f'ci-chrome-shard-{index}'
                or accounting.get('sha256') != sha256(Path(path).read_bytes()).hexdigest()
                or accounting.get('assigned_count') != len(ids) or accounting.get('executed_count') != len(ids)
                or accounting.get('complete') is not True):
            raise ValueError('Driver-backed summary/accounting proof mismatch')
        if require_ci and (github.get('enabled') is not True or github.get('sha') != checkout_sha
                           or report.get('platform') != 'Windows'
                           or summary.get('run_context') != 'ci'
                           or github.get('source_sha') != source_sha
                           or report.get('github_sha') != checkout_sha
                           or not github.get('run_id') or github['run_id'] != report.get('github_run_id')):
            raise ValueError('Hosted CI source binding missing')
        run_ids.add(report.get('github_run_id'))
        runtime = report.get('runtime')
        if not runtime or runtime in runtimes:
            raise ValueError('Missing or shared mutable shard runtime')
        database, media = report.get('test_database'), report.get('media')
        if (not database or database in databases or not media or media in media_roots
                or report.get('cache_backend') != 'django.core.cache.backends.locmem.LocMemCache'):
            raise ValueError('Database, media or cache isolation proof missing')
        runtimes.append(runtime)
        databases.append(database); media_roots.append(media)
        executed.extend(ids)
        timings.append(dict(shard=index, tests=len(ids), seconds=report['seconds']))
        summaries.append(summary)
    if len(run_ids) != 1 or sorted(executed) != expected['inventory'] or len(set(executed)) != len(executed):
        raise ValueError('Complete suite is not accounted exactly once')
    result = dict(summaries[0])
    contract = dict(result.get('artifact_contract', {}))
    contract.update(summary_filename='browser_regression_summary.json',
                    labeled_summary_filename='browser_regression_summary.ci-chrome.json', upload_path='artifacts/browser',
                    shard_artifacts=[f'browser-regression-artifacts-shard-{index}' for index in range(count)])
    started = min(datetime.fromisoformat(row['started_at_utc']) for row in summaries)
    finished = max(datetime.fromisoformat(row['finished_at_utc']) for row in summaries)
    result.update(status='passed', checkout_sha=checkout_sha, source_sha=source_sha,
                inventory_sha256=expected['inventory_sha256'], intended=len(executed),
                executed=len(executed), passed=len(executed), failed=0, skipped=0, shards=timings,
                summary_version=2, proof_label='ci-chrome', tests_found_count=len(executed),
                tests_run_count=len(executed), test_labels=['complete measured browser inventory'],
                command=['python','scripts/browser_test_plan.py','--require-ci'] if require_ci else ['python','scripts/browser_test_plan.py'],
                started_at_utc=started.isoformat(), finished_at_utc=finished.isoformat(),
                duration_seconds=(finished-started).total_seconds(),
                artifact_dir='artifacts/browser', artifact_contract=contract,
                accounting=dict(complete=True, shards=count, inventory_count=len(executed), executed_count=len(executed),
                    reports=[dict(shard=report['shard_index'], file=Path(path).name,
                        sha256=sha256(Path(path).read_bytes()).hexdigest()) for path, report in zip(paths, reports)]),
                execution_model='aggregate of independently validated Selenium shards')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--manifest', default='tests/browser_durations.json')
    parser.add_argument('--checkout-sha', required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--shards', type=int, default=3)
    parser.add_argument('--require-ci', action='store_true')
    parser.add_argument('--job-result', choices=('success','failure','cancelled','skipped'), default='success')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    paths = sorted(Path(args.artifacts).rglob('test-results.ci-chrome-shard-*.json'))
    try:
        if args.job_result != 'success':
            raise ValueError('Windows shard jobs did not succeed: ' + args.job_result)
        result = aggregate(paths, json.loads(Path(args.manifest).read_text(encoding='utf-8')),
                           args.checkout_sha, args.source_sha, args.shards, args.require_ci)
    except (ValueError, KeyError, TypeError, OSError) as error:
        result = dict(status='failed', validation_error=str(error), reports_found=len(paths),
                      expected_shards=args.shards, checkout_sha=args.checkout_sha, source_sha=args.source_sha)
        reported = []
        for path in paths:
            try:
                reported.extend(json.loads(path.read_text(encoding='utf-8')).get('tests', []))
            except (ValueError, TypeError, OSError):
                continue
        result['unvalidated_reported_counts'] = dict(executed=len(reported),
            passed=sum(row.get('status')=='passed' for row in reported),
            failed=sum(row.get('status') in ('failed','error','unexpected_success') for row in reported),
            skipped=sum(row.get('status') in ('skipped','expected_failure') for row in reported))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    # Preserve readiness consumers' canonical proof names without inventing a single-process run.
    for name in ('browser_regression_summary.ci-chrome.json','browser_regression_summary.json'):
        target.with_name(name).write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(result))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
