"""Council contracts in disposable Git repositories; no production or model calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import time
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from scripts import release_gate as release
from scripts.development_council import BRANCH, Council, CouncilError, feature_queue


class DevelopmentCouncilTests(SimpleTestCase):
    def setUp(self):
        self.repo=Path(self.enterContext(TemporaryDirectory(prefix='alfred-council-synthetic-')))
        self.git('init','-b',BRANCH)
        self.git('config','user.name','Synthetic Council'); self.git('config','user.email','synthetic@example.invalid')
        for path,content in {
            '.gitignore':'/artifacts/\n', 'apps/sample.py':'VALUE = 1\n',
            'tests/test_council_fixture.py':'# Synthetic test identifier fixture\n',
            'docs/PROJECT_STATUS.md':'# Synthetic status\n### AI-16 — Quality\n**PARTIALLY_IMPLEMENTED**\n- Next: [COUNCIL_SAFE_LOCAL] Improve <script> review clarity.\n',
        }.items():
            target=self.repo/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding='utf-8')
        self.git('add','.'); self.git('commit','-m','synthetic base')
        self.council=Council(self.repo)

    def git(self,*args): return release.git(self.repo,*args)

    def plan(self,profile='backend'):
        return self.council.plan(['apps/sample.py'],['tests.test_council_fixture'],profile)

    def reviewed(self,profile='backend'):
        task=self.plan(profile); (self.repo/'apps/sample.py').write_text('VALUE = 2\n',encoding='utf-8')
        source=self.council.snapshot(task)[0]
        for role in ('developer','reviewer','security'): task=self.council.record(task['id'],role,'PASS',source)
        return task

    def passing(self,profile='backend'):
        task=self.reviewed(profile)
        with patch('scripts.development_council.run',return_value=dict(status='PASS',code='suite_exit',tests=1,skips=0)):
            return self.council.test(task['id'])

    def test_host_cycle_resume_exact_commit_and_safe_html(self):
        task=self.passing(); council=Council(self.repo)
        self.assertEqual(council._read(task['id'])['stage'],'READY_FOR_AUTHORIZED_COMMIT')
        with self.assertRaises(CouncilError): council.complete(task['id'],self.git('rev-parse','HEAD'),'')
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic approved host change')
        commit=self.git('rev-parse','HEAD')
        result=council.complete(task['id'],commit,'synthetic-user-approval')
        self.assertEqual(result['stage'],'COMPLETE'); self.assertEqual(result['commit'],commit)
        self.assertEqual(council.complete(task['id'],commit,'synthetic-user-approval')['stage'],'COMPLETE')
        council.status(); html=(council.directory/'status.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',html); self.assertNotIn('<script>',html)

    def test_duplicate_tasks_and_blocked_queue_do_not_spawn_coders(self):
        task=self.plan(); self.assertEqual(self.plan()['id'],task['id'])
        handoff=self.council.handoff(task['id'])
        self.assertEqual(handoff['developer'],'codex_host_or_human_required')
        self.assertFalse(feature_queue('### FIN-01 — Unknown currency\n**BLOCKED_APPROVAL**\n- Next: [COUNCIL_SAFE_LOCAL] Migrate.\n'))
        with self.assertRaises(CouncilError): self.council.plan(['../outside.py'],['tests.test_council_fixture'])
        with self.assertRaises(CouncilError): self.council.plan(['apps/loans/migrations/next.py'],['tests.test_council_fixture'])
        with self.assertRaises(CouncilError): self.council.test(task['id'])

    def test_tracker_and_source_edits_invalidate_all_evidence(self):
        task=self.reviewed(); tracker=self.repo/'docs/PROJECT_STATUS.md'
        tracker.write_text(tracker.read_text(encoding='utf-8')+'Changed tracker.\n',encoding='utf-8')
        with self.assertRaises(CouncilError): self.council.test(task['id'])
        self.assertNotEqual(self.council.snapshot(task)[0],task['source'])
        with self.assertRaises(CouncilError): self.council.record(task['id'],'reviewer','PASS',task['source'],provider='ollama')
        (self.repo/'apps/extra.py').write_text('UNAPPROVED = True\n',encoding='utf-8')
        with self.assertRaises(CouncilError): self.council.snapshot(task)

    def test_source_changes_during_testing_and_missing_coverage_block_completion(self):
        task=self.reviewed()
        def changed(*args,**kwargs):
            (self.repo/'apps/sample.py').write_text('VALUE = 3\n',encoding='utf-8')
            return dict(status='PASS',tests=1,skips=0)
        with patch('scripts.development_council.run',side_effect=changed): result=self.council.test(task['id'])
        self.assertEqual(result['roles']['tester']['status'],'FAIL')
        (self.repo/'apps/sample.py').write_text('VALUE = 2\n',encoding='utf-8')
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=0,skips=0)):
            result=self.council.test(task['id'])
        self.assertEqual(result['roles']['tester']['status'],'NOT_RUN')
        with self.assertRaises(CouncilError): self.council.test(task['id'])

    def test_advice_is_bounded_redacted_and_never_review_approval(self):
        task=self.plan(); provider=Mock()
        provider.reason.return_value='{"signals":["clear"]}'
        result=self.council.advise(task['id'],'reviewer',provider)
        self.assertEqual(result['roles']['reviewer']['status'],'NOT_RUN')
        self.assertEqual(result['advisories'][0]['status'],'ADVISORY_ONLY')
        provider.reason.side_effect=RuntimeError('SYNTHETIC-SECRET provider quota')
        with self.assertRaises(CouncilError):
            for _ in range(10): result=self.council.advise(task['id'],'reviewer',provider)
        self.assertNotIn('SYNTHETIC-SECRET',json.dumps(self.council._read(task['id'])))

    def test_interrupted_worker_is_not_restarted_without_confirmation_and_expired_lease(self):
        task=self.reviewed()
        def pending(current): current['roles']['tester']=dict(status='RUNNING',started=int(time.time())-1000)
        self.council._change(task['id'],pending)
        with self.assertRaises(CouncilError): self.council.resume(task['id'])
        result=self.council.resume(task['id'],confirm_worker_stopped=True)
        self.assertEqual(result['roles']['tester']['status'],'BLOCKED')

    def test_native_requires_fresh_evidence_and_checks_source_afterward(self):
        task=self.reviewed('native')
        with patch('scripts.development_council.run',side_effect=lambda *a,**k: dict(status='PASS',tests=1,skips=0)):
            result=self.council.test(task['id'])
        self.assertEqual(result['roles']['tester']['status'],'FAIL')
        clock=[0]; timeouts=[]
        def native(*args,**kwargs):
            timeouts.append(args[-1])
            if len(timeouts)==1: clock[0]=595
            else:
                report=self.repo/'artifacts/ops/native_huey_verification.json'; report.parent.mkdir(parents=True,exist_ok=True)
                report.write_text(json.dumps({'passed':True,'checks':{'synthetic':True}},indent=2),encoding='utf-8')
            return dict(status='PASS',tests=1,skips=0)
        with patch('scripts.development_council.time.monotonic',side_effect=lambda:clock[0]),patch('scripts.development_council.run',side_effect=native):
            result=self.council.test(task['id'])
        self.assertEqual(result['roles']['tester']['status'],'PASS'); self.assertLessEqual(timeouts[1],5)
        retained=self.council.directory/(task['id']+'-2')/'native-report.json'
        self.assertEqual(release.sha256(retained),result['roles']['tester']['native_report_sha256'])

    def test_native_source_mutation_after_fresh_report_blocks_completion(self):
        task=self.reviewed('native'); calls=[]
        def native(*args,**kwargs):
            calls.append(args)
            if len(calls)==2:
                report=self.repo/'artifacts/ops/native_huey_verification.json'; report.parent.mkdir(parents=True,exist_ok=True)
                report.write_text(json.dumps({'passed':True,'checks':{'synthetic':True}}),encoding='utf-8')
                (self.repo/'apps/sample.py').write_text('VALUE = 3\n',encoding='utf-8')
            return dict(status='PASS',tests=1,skips=0)
        with patch('scripts.development_council.run',side_effect=native): result=self.council.test(task['id'])
        self.assertEqual(result['roles']['tester']['status'],'FAIL')
        self.assertEqual(result['roles']['tester']['code'],'source_changed_during_tests')

    def test_production_branch_and_linked_status_outputs_are_rejected(self):
        self.git('switch','-c','master')
        with self.assertRaises(CouncilError): Council(self.repo)
        self.git('switch',BRANCH)
        outside=self.repo/'outside.txt'; outside.write_text('preserved',encoding='utf-8')
        os.link(outside,self.council.directory/'status.html')
        with self.assertRaises(CouncilError): self.council.status()
        self.assertEqual(outside.read_text(encoding='utf-8'),'preserved')
