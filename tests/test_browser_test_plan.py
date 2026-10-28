from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

from scripts.browser_test_plan import aggregate, plan_tests, main


class BrowserPlanTests(TestCase):
    def test_deterministic_measured_balance_and_complete_membership(self):
        durations=dict(zip('abcdef', [9,8,7,2,1,1]))
        first=plan_tests(list(durations),durations,3)
        self.assertEqual(first,plan_tests(list(reversed(durations)),dict(reversed(list(durations.items()))),3))
        self.assertEqual(sorted(sum(first['shards'],[])),list('abcdef'))
        self.assertEqual(sorted(first['measured_weight_seconds']),[9,9,10])

    def test_unknown_duplicate_or_invalid_duration_fails_closed(self):
        for value in (None,-1,float('nan'),float('inf'),True,'1'):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):
                plan_tests(['a'],{'a':value},1)
        for ids,count in (([],1),(['a','a'],1),(['a'],3),(['a'],0)):
            with self.assertRaises(ValueError):plan_tests(ids,{'a':1},count)

    def proof(self):
        folder=Path(self.enterContext(TemporaryDirectory(prefix='alfred-shard-contract-')))
        manifest={'durations':{'tests.a':3,'tests.b':2,'tests.c':1}}
        plan=plan_tests(list(manifest['durations']),manifest['durations'],3)
        paths=[]
        for index,selected in enumerate(plan['shards']):
            path=folder/f'shard-{index}'/f'test-results.ci-chrome-shard-{index}.json'
            path.parent.mkdir()
            report=dict(plan=plan,inventory=plan['inventory'],selected=selected,execution_ids=selected,
                shard_index=index,shard_count=3,checkout_sha='a'*40,source_sha='b'*40,
                github_sha='a'*40,github_run_id='synthetic-run',platform='Windows',complete=True,runtime=f'synthetic/shard-{index}',
                test_database=f'synthetic/shard-{index}/db.sqlite',media=f'synthetic/shard-{index}/media',
                cache_backend='django.core.cache.backends.locmem.LocMemCache',seconds=4,
                tests=[dict(id=name,status='passed',seconds=1) for name in selected])
            self.write(path,report)
            paths.append(path)
        return paths,manifest

    def write(self,path,report):
        path.write_text(json.dumps(report),encoding='utf-8')
        summary=dict(driver_backed_success=True,runner_return_code=0,return_code=0,status='passed',skipped_count=0,
            browser='Chrome',require_browser=True,run_context='ci',run_browser_tests_env='true',
            proof_label=f"ci-chrome-shard-{report['shard_index']}",tests_found_count=len(report['inventory']),
            started_at_utc='2026-10-29T00:00:00+00:00',finished_at_utc='2026-10-29T00:00:04+00:00',
            tests_run_count=len(report['tests']),accounting=dict(complete=True,sha256=sha256(path.read_bytes()).hexdigest(),
                assigned_count=len(report['tests']),executed_count=len(report['tests'])),
            github_actions=dict(enabled=True,sha='a'*40,source_sha='b'*40,run_id=report['github_run_id']))
        path.with_name(path.name.replace('test-results.','browser_regression_summary.')).write_text(json.dumps(summary))

    def test_complete_hosted_proof_is_exact_sha_bound(self):
        paths,manifest=self.proof()
        result=aggregate(paths,manifest,'a'*40,'b'*40,3,True)
        self.assertEqual((result['intended'],result['executed'],result['passed']),(3,3,3))
        self.assertEqual(result['failed'],0)
        self.assertEqual(result['proof_label'],'ci-chrome')
        self.assertEqual(result['tests_run_count'],3)
        self.assertEqual(result['artifact_contract']['labeled_summary_filename'],'browser_regression_summary.ci-chrome.json')
        with self.assertRaises(ValueError):aggregate(paths,manifest,'c'*40,'b'*40,3,True)
        with self.assertRaises(ValueError):aggregate(paths,manifest,'a'*40,'c'*40,3,True)

    def test_missing_or_duplicate_shard_is_rejected(self):
        paths,manifest=self.proof()
        for supplied in (paths[:-1],[paths[0],paths[0],paths[2]]):
            with self.assertRaises(ValueError):aggregate(supplied,manifest,'a'*40,'b'*40,3,True)

    def test_duplicate_execution_cannot_be_hidden_by_unique_result_records(self):
        paths,manifest=self.proof()
        report=json.loads(paths[0].read_text());report['execution_ids']*=2;self.write(paths[0],report)
        with self.assertRaisesRegex(ValueError,'duplicated test execution'):
            aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_missing_duplicate_failed_skipped_and_extra_cases_are_rejected(self):
        paths,manifest=self.proof()
        original=json.loads(paths[0].read_text())
        for change in ('missing','duplicate','failed','skipped','extra'):
            report=deepcopy(original)
            if change=='missing':report['tests']=[]
            elif change=='duplicate':report['tests']*=2
            elif change=='extra':report['tests'].append(dict(id='tests.unknown',status='passed',seconds=1))
            else:report['tests'][0]['status']=change
            self.write(paths[0],report)
            with self.subTest(change=change),self.assertRaises(ValueError):
                aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_shared_runtime_or_forged_summary_is_rejected(self):
        paths,manifest=self.proof()
        original=json.loads(paths[1].read_text())
        report=deepcopy(original);report['runtime']='synthetic/shard-0'
        self.write(paths[1],report)
        with self.assertRaisesRegex(ValueError,'shared mutable'):aggregate(paths,manifest,'a'*40,'b'*40,3,True)
        self.write(paths[1],original)
        summary=paths[1].with_name(paths[1].name.replace('test-results.','browser_regression_summary.'))
        value=json.loads(summary.read_text());value['driver_backed_success']=False;summary.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'summary/accounting'):aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_shared_database_media_or_external_cache_is_rejected(self):
        paths,manifest=self.proof();original=json.loads(paths[1].read_text())
        for key,value in (('test_database','synthetic/shard-0/db.sqlite'),('media','synthetic/shard-0/media'),
                          ('cache_backend','redis')):
            report=deepcopy(original);report[key]=value;self.write(paths[1],report)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'isolation proof'):
                aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_reports_from_different_runs_cannot_be_combined(self):
        paths,manifest=self.proof()
        report=json.loads(paths[1].read_text());report['github_run_id']='older-run'
        self.write(paths[1],report)
        with self.assertRaises(ValueError):aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_linux_proof_cannot_substitute_for_windows_private_storage_acceptance(self):
        paths,manifest=self.proof()
        report=json.loads(paths[0].read_text());report['platform']='Linux';self.write(paths[0],report)
        with self.assertRaisesRegex(ValueError,'Hosted CI source binding'):
            aggregate(paths,manifest,'a'*40,'b'*40,3,True)

    def test_workflow_yaml_preserves_checks_cache_isolation_and_event_contexts(self):
        import yaml
        root=Path(__file__).resolve().parents[1]
        workflow=yaml.load((root/'.github/workflows/browser-regression.yml').read_text(encoding='utf-8'),Loader=yaml.BaseLoader)
        jobs=workflow['jobs']
        self.assertEqual(set(jobs),{'native-windows','linux-secure-failure','selenium-shards','selenium'})
        self.assertEqual(jobs['selenium-shards']['runs-on'],'windows-latest')
        self.assertEqual(jobs['selenium-shards']['strategy']['matrix']['shard'],['0','1','2'])
        self.assertEqual(jobs['selenium-shards']['strategy']['fail-fast'],'false')
        self.assertEqual(jobs['selenium']['needs'],'selenium-shards')
        self.assertEqual(jobs['selenium']['if'],'${{ always() }}')
        self.assertEqual(workflow['on']['push']['branches'],['master'])
        self.assertIn('workflow_dispatch',workflow['on']);self.assertNotIn('workflow_call',workflow['on'])
        self.assertEqual(workflow['concurrency']['cancel-in-progress'],'false')
        for key in ('github.event_name','github.ref','github.sha'):
            self.assertIn(key,workflow['concurrency']['group'])
        for name in ('native-windows','linux-secure-failure','selenium-shards'):
            step=next(step for step in jobs[name]['steps'] if step.get('uses','').startswith('actions/setup-python@'))
            self.assertEqual(step['with']['cache'],'pip')
            self.assertEqual(step['with']['cache-dependency-path'].split(),['requirements.txt','constraints/*.txt'])
        text=json.dumps(jobs)
        self.assertIn('test_memory_platform',text);self.assertIn('--extended',text)
        self.assertIn('release_gate.py preflight',text);self.assertIn('--profile backend',text)

    def test_failed_job_cannot_publish_a_passing_canonical_proof(self):
        paths,manifest=self.proof();root=paths[0].parents[1]
        source=root/'durations.json';source.write_text(json.dumps(manifest))
        target=root/'aggregate.json'
        args=['aggregate','--artifacts',str(root),'--manifest',str(source),'--checkout-sha','a'*40,
              '--source-sha','b'*40,'--output',str(target),'--job-result','failure','--require-ci']
        with patch('sys.argv',args),redirect_stdout(StringIO()),self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code,1)
        canonical=json.loads((root/'browser_regression_summary.ci-chrome.json').read_text())
        self.assertEqual(canonical['status'],'failed');self.assertFalse(canonical.get('driver_backed_success',False))
        self.assertEqual(canonical['unvalidated_reported_counts']['executed'],3)
