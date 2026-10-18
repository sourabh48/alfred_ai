"""Council contracts in disposable Git repositories; no production or model calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import time
from unittest.mock import Mock, patch
from contextlib import redirect_stdout
from io import StringIO

from django.test import SimpleTestCase

from scripts import release_gate as release
from scripts.development_council import BRANCH, Council, CouncilError, LocalCouncilAdvisor, feature_queue, main
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable


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

    def test_late_or_oversized_advice_is_blocked_and_visible_without_raw_output(self):
        for offset,reply in ((31,'{"signals":["clear"]}'),(1,'SYNTHETIC-PRIVATE-'+('x'*4096))):
            with self.subTest(offset=offset):
                # Each subcase uses an independent reviewed objective and budget.
                tracker=self.repo/'docs/PROJECT_STATUS.md'
                tracker.write_text(tracker.read_text(encoding='utf-8').replace('review clarity',f'review clarity {offset}'),encoding='utf-8')
                self.git('add','docs/PROJECT_STATUS.md'); self.git('commit','-m','new synthetic reviewed objective')
                task=self.plan(); provider=Mock(); provider.reason.return_value=reply
                with patch('scripts.development_council.time.monotonic',side_effect=[0,offset]):
                    result=self.council.advise(task['id'],'reviewer',provider)
                self.assertEqual(result['advisories'][-1]['status'],'BLOCKED')
                self.assertEqual(result['advisories'][-1]['code'],'advisory_deadline_exceeded' if offset==31 else 'advisory_output_budget_exceeded')
                self.assertEqual(result['roles']['reviewer']['status'],'NOT_RUN')
                self.council.status(task['id']); html=(self.council.directory/'status.html').read_text(encoding='utf-8')
                self.assertIn('reviewer: BLOCKED',html); self.assertIn('conservative reservation',html)
                self.assertIn('Required-role blockers:',html); self.assertNotIn('SYNTHETIC-PRIVATE',html)

    def test_failed_optional_advice_has_nonzero_cli_exit_without_false_role_approval(self):
        task=self.plan(); output=StringIO()
        with patch('scripts.development_council.Council',return_value=self.council),patch(
                'scripts.development_council.LocalCouncilAdvisor') as provider,redirect_stdout(output):
            provider.return_value.reason.side_effect=RuntimeError('SYNTHETIC-PRIVATE provider failure')
            code=main(['advise','--repo',str(self.repo),'--task',task['id'],'--role','planner'])
        self.assertEqual(code,2)
        evidence=json.loads(output.getvalue())
        self.assertEqual(evidence['advisories'][-1]['status'],'BLOCKED')
        self.assertEqual(evidence['roles']['developer']['status'],'NOT_RUN')
        self.assertNotIn('SYNTHETIC-PRIVATE',output.getvalue())

    def test_advisory_failure_categories_never_retain_messages_or_approve_roles(self):
        examples=[
            (RuntimeError('SYNTHETIC-PRIVATE provider error'),'provider_failed'),
            (EmbeddingUnavailable('SYNTHETIC-PRIVATE socket error'),'local_provider_unavailable'),
            ('SYNTHETIC-PRIVATE not json','advisory_json_invalid'),
            ('{"signals":[]}','advisory_schema_invalid'),
            ('{"signals":["clear","clear"]}','advisory_schema_invalid'),
            ('{"signals":[["clear"]]}','advisory_schema_invalid'),
            ('{"signals":["clear"],"command":"SYNTHETIC-PRIVATE"}','advisory_schema_invalid'),
        ]
        for index,(reply,code) in enumerate(examples):
            with self.subTest(code=code,index=index):
                tracker=self.repo/'docs/PROJECT_STATUS.md'
                tracker.write_text(tracker.read_text(encoding='utf-8').replace('review clarity',f'review clarity {index}'),encoding='utf-8')
                self.git('add','docs/PROJECT_STATUS.md'); self.git('commit','-m','independent synthetic advisory objective')
                task=self.plan(); provider=Mock()
                if isinstance(reply,Exception): provider.reason.side_effect=reply
                else: provider.reason.return_value=reply
                result=self.council.advise(task['id'],'reviewer',provider)
                advice=result['advisories'][-1]
                self.assertEqual((advice['status'],advice['code']),('BLOCKED',code))
                self.assertEqual(result['roles']['reviewer']['status'],'NOT_RUN')
                self.assertNotIn('SYNTHETIC-PRIVATE',json.dumps(result))

    def test_local_advisor_reuses_digest_transport_with_bounded_structured_signals(self):
        advisor=LocalCouncilAdvisor()
        envelope={'model':advisor.model,'done':True,'message':{'role':'assistant','content':'{"signals":["tests"]}'}}
        with patch.object(advisor,'_digest',return_value='1'*64) as digest,patch.object(advisor,'_request',return_value=envelope) as request:
            self.assertEqual(advisor.reason({'objective':'Review fictional fixture.'},max_output_tokens=256,deadline=30),envelope['message']['content'])
        self.assertEqual(digest.call_count,2)
        method,path,body=request.call_args.args
        self.assertEqual((method,path),('POST','/api/chat'))
        self.assertEqual(body['model'],'qwen3.5:4b'); self.assertFalse(body['stream']); self.assertFalse(body['think'])
        self.assertEqual(body['options']['num_predict'],256); self.assertEqual(body['options']['temperature'],0)
        self.assertFalse(body['format']['additionalProperties'])
        self.assertEqual(body['format']['required'],['signals'])
        self.assertIn('Never output code, commands',body['messages'][0]['content'])
        self.assertNotIn('sources',body['messages'][1]['content'])
        self.assertEqual(request.call_args.kwargs,{'deadline':30})

    def test_local_advisor_rejects_model_swap_tool_calls_and_unbounded_tokens(self):
        advisor=LocalCouncilAdvisor()
        envelope={'model':advisor.model,'done':True,'message':{'role':'assistant','content':'{"signals":["clear"]}'}}
        for changed in ({'model':'other-model'},{'done':False},{'message':{'role':'assistant','content':'{}','tool_calls':[{'name':'unsafe'}]}}):
            with self.subTest(changed=changed),patch.object(advisor,'_digest',return_value='1'*64),patch.object(advisor,'_request',return_value=envelope|changed):
                with self.assertRaisesRegex(CouncilError,'local_response_invalid'): advisor.reason({},deadline=30)
        with patch.object(advisor,'_digest',side_effect=['1'*64,'2'*64]),patch.object(advisor,'_request',return_value=envelope):
            with self.assertRaisesRegex(CouncilError,'local_model_changed'): advisor.reason({},deadline=30)
        with patch.object(advisor,'_digest') as digest:
            for tokens in (True,0,257):
                with self.assertRaises(CouncilError): advisor.reason({},max_output_tokens=tokens,deadline=30)
            with self.assertRaisesRegex(CouncilError,'advisory_context_budget_exceeded'):
                advisor.reason({'objective':'x'*3900},deadline=30)
            digest.assert_not_called()

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
