"""Council contracts in disposable Git repositories; no production or model calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
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
        for role in ('architect','developer','reviewer','security'): task=self.council.record(task['id'],role,'PASS',source,actor='synthetic_'+role)
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

    def test_seven_roles_architect_gate_coder_alias_and_guardian_do_not_authorize_release(self):
        task=self.reviewed(); identity=task['id']; source=task['source']
        self.assertEqual(task['contract_version'],3)
        self.assertEqual(set(task['roles']),{'coordinator','architect','developer','reviewer','security','tester','release_guardian'})
        self.assertEqual(task['selection']['code'],'reviewed_master_queue')
        self.council.record(identity,'architect','BLOCKED',source,actor='synthetic_architect')
        with self.assertRaisesRegex(CouncilError,'current_host_reviews_required'): self.council.test(identity)
        self.council.record(identity,'architect','PASS',source,actor='synthetic_architect')
        self.council.record(identity,'coder','PASS',source,actor='synthetic_developer')
        with self.assertRaisesRegex(CouncilError,'explicit_host_review_required'):
            self.council.record(identity,'release_guardian','PASS',source,actor='synthetic_developer')
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0)):
            self.council.test(identity)
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic seven-role change')
        done=self.council.complete(identity,self.git('rev-parse','HEAD'),'synthetic-user-approval')
        self.assertTrue(all(role['status']=='PASS' for role in done['roles'].values()))
        guardian=done['roles']['release_guardian']
        self.assertEqual(guardian['scope'],'development_checkpoint_only')
        self.assertFalse(guardian['production_authorized']); self.assertFalse(guardian['release_ready'])
        self.assertTrue(all(item['status']=='PASS' for item in guardian['gates'].values()))

    def test_guardian_failure_is_retained_redacted_and_bounded_before_checkpoint_acceptance(self):
        task=self.passing(); identity=task['id']
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic pending guardian')
        commit=self.git('rev-parse','HEAD')
        with patch('scripts.development_council.privacy',side_effect=release.GateError('SYNTHETIC_PRIVATE_FINDING')):
            blocked=self.council.complete(identity,commit,'synthetic-user-approval')
        self.assertEqual(blocked['stage'],'BLOCKED'); self.assertNotIn('commit',blocked)
        self.assertNotIn('SYNTHETIC_PRIVATE',json.dumps(blocked))
        self.assertEqual(self.council.next_action(identity)['action'],'host_retry_release_guardian')
        done=Council(self.repo).complete(identity,commit,'synthetic-user-approval')
        self.assertEqual(done['stage'],'COMPLETE')
        self.assertEqual([item['status'] for item in done['guardian_history']],['BLOCKED','PASS'])
        self.council.status(identity)
        self.assertIn('BLOCKED, PASS',(self.council.directory/'status.html').read_text(encoding='utf-8'))

    def test_guardian_repeated_failure_cannot_loop_or_lose_test_and_failure_evidence(self):
        task=self.passing(); identity=task['id']
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic guardian blocked')
        commit=self.git('rev-parse','HEAD')
        with patch('scripts.development_council.privacy',side_effect=release.GateError('synthetic unavailable')):
            for _ in range(2): self.council.complete(identity,commit,'synthetic-user-approval')
            with self.assertRaisesRegex(CouncilError,'guardian_attempt_budget_exhausted'):
                self.council.complete(identity,commit,'synthetic-user-approval')
        retained=self.council._read(identity)
        self.assertEqual(retained['stage'],'BLOCKED'); self.assertEqual(len(retained['guardian_history']),2)
        self.assertEqual(retained['roles']['tester']['status'],'PASS')
        self.assertEqual(self.council.next_action(identity)['action'],'guardian_attempt_budget_exhausted')

    def test_guardian_operational_failures_reserve_and_retain_attempts_without_secret_messages(self):
        task=self.passing(); identity=task['id']
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic guardian transport failure')
        commit=self.git('rev-parse','HEAD')
        for failure in (subprocess.TimeoutExpired('SYNTHETIC_PRIVATE_COMMAND',120),OSError('SYNTHETIC_PRIVATE_PATH')):
            with patch('scripts.development_council.privacy',side_effect=failure):
                result=self.council.complete(identity,commit,'synthetic-user-approval')
            self.assertEqual(result['stage'],'BLOCKED')
            self.assertEqual(result['roles']['release_guardian']['exception_type'],type(failure).__name__)
        self.assertEqual(len(result['guardian_history']),2); self.assertNotIn('SYNTHETIC_PRIVATE',json.dumps(result))
        with self.assertRaisesRegex(CouncilError,'guardian_attempt_budget_exhausted'):
            self.council.complete(identity,commit,'synthetic-user-approval')

    def test_guardian_crash_preserves_lease_budget_and_requires_explicit_stopped_worker_resume(self):
        task=self.passing(); identity=task['id']
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic guardian interrupted')
        commit=self.git('rev-parse','HEAD')
        with patch('scripts.development_council.privacy',side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt): self.council.complete(identity,commit,'synthetic-user-approval')
        retained=Council(self.repo)._read(identity)
        self.assertEqual(retained['roles']['release_guardian']['status'],'RUNNING'); self.assertEqual(len(retained['guardian_history']),1)
        self.assertEqual(self.council.next_action(identity)['status'],'WAIT')
        with self.assertRaisesRegex(CouncilError,'guardian_already_running'):
            self.council.complete(identity,commit,'synthetic-user-approval')
        with self.assertRaisesRegex(CouncilError,'active_worker_lease_preserved'):
            self.council.resume(identity,confirm_worker_stopped=True)
        self.council._change(identity,lambda current:current['roles']['release_guardian'].update(started=time.time()-601))
        self.assertEqual(self.council.next_action(identity)['action'],'confirm_guardian_stopped_before_resume')
        self.council.resume(identity,confirm_worker_stopped=True)
        done=self.council.complete(identity,commit,'synthetic-user-approval')
        self.assertEqual(done['stage'],'COMPLETE')
        self.assertEqual(done['guardian_history'][0]['code'],'interrupted_guardian_preserved')

    def test_v2_task_remains_legacy_without_fabricated_architect_or_guardian_acceptance(self):
        task=self.reviewed(); identity=task['id']
        def legacy(current):
            current['contract_version']=2
            for key in ('architect','release_guardian'): current['roles'].pop(key)
            current['roles']['planner']=dict(status='PASS',provider='deterministic',code='reviewed_master_queue')
            current.pop('selection')
        self.council._change(identity,legacy)
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0)):
            self.council.test(identity)
        self.git('add','apps/sample.py'); self.git('commit','-m','synthetic v2 checkpoint')
        with patch('scripts.development_council.privacy',side_effect=AssertionError('No retroactive guardian')):
            self.assertEqual(self.council.next_action(identity)['status'],'BLOCKED')
            done=self.council.complete(identity,self.git('rev-parse','HEAD'),'synthetic-user-approval')
        self.assertEqual(len(done['roles']),6); self.assertEqual(done['contract_version'],2)
        self.assertNotIn('guardian_history',done)

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
        reused=self.council.advise(task['id'],'reviewer',provider)
        self.assertTrue(reused['advisory_reused']); self.assertEqual(provider.reason.call_count,1)
        provider.reason.side_effect=RuntimeError('SYNTHETIC-SECRET provider quota')
        result=self.council.advise(task['id'],'security',provider)
        self.assertEqual(result['advisory_result']['status'],'BLOCKED')
        with self.assertRaises(CouncilError):
            self.council.advise(task['id'],'planner',provider)
        self.assertNotIn('SYNTHETIC-SECRET',json.dumps(self.council._read(task['id'])))

    def test_failed_advice_is_reused_until_one_explicit_budgeted_retry_and_never_approves(self):
        task=self.plan(); provider=Mock(); provider.reason.side_effect=EmbeddingUnavailable('SYNTHETIC-private outage')
        first=self.council.advise(task['id'],'reviewer',provider)
        cached=self.council.advise(task['id'],'reviewer',provider)
        self.assertTrue(cached['advisory_reused']); self.assertEqual(provider.reason.call_count,1)
        self.assertEqual(cached['reserved_tokens'],first['reserved_tokens'])
        provider.reason.side_effect=None; provider.reason.return_value='{"signals":["tests"]}'
        retried=self.council.advise(task['id'],'reviewer',provider,retry=True)
        self.assertEqual(provider.reason.call_count,2); self.assertEqual(retried['advisory_result']['status'],'ADVISORY_ONLY')
        self.assertEqual(retried['roles']['reviewer']['status'],'NOT_RUN')
        self.assertEqual(retried['advisories'][0]['status'],'BLOCKED'); self.assertGreater(retried['reserved_tokens'],first['reserved_tokens'])
        self.assertTrue(self.council.advise(task['id'],'reviewer',provider,retry=True)['advisory_reused'])
        with self.assertRaisesRegex(CouncilError,'advisory_attempt_budget_exhausted'):
            self.council.advise(task['id'],'planner',provider)
        self.assertNotIn('SYNTHETIC-private',json.dumps(retried))

    def test_duplicate_inflight_advice_and_interrupted_reservations_are_not_refunded(self):
        task=self.plan(); provider=Mock(); seen=[]
        def reply(*args,**kwargs):
            with self.assertRaisesRegex(CouncilError,'advisory_already_running'):
                self.council.advise(task['id'],'planner',provider)
            seen.append(True); return '{"signals":["clear"]}'
        provider.reason.side_effect=reply
        first=self.council.advise(task['id'],'planner',provider)
        self.assertEqual(seen,[True]); self.assertEqual(provider.reason.call_count,1)
        def interrupted(current):
            current['advisories'][-1].update(status='RUNNING',started=time.time()-31,lease_until=time.time()-1)
        self.council._change(task['id'],interrupted)
        with self.assertRaisesRegex(CouncilError,'interrupted_advice_requires_explicit_retry'):
            self.council.advise(task['id'],'planner',provider)
        provider.reason.side_effect=None; provider.reason.return_value='{"signals":["clear"]}'
        retried=self.council.advise(task['id'],'planner',provider,retry=True)
        self.assertEqual(retried['advisories'][0]['code'],'interrupted_advisory_preserved')
        self.assertGreater(retried['reserved_tokens'],first['reserved_tokens'])

    def test_late_worker_cannot_overwrite_interrupt_after_retry_even_if_original_result_is_timely(self):
        task=self.plan(); provider=Mock(); replacement=Mock(); replacement.reason.return_value='{"signals":["tests"]}'
        def late_result(*args,**kwargs):
            self.council._change(task['id'],lambda current:current['advisories'][-1].update(lease_until=time.time()-1))
            retried=self.council.advise(task['id'],'planner',replacement,retry=True)
            self.assertEqual(retried['advisory_result']['status'],'ADVISORY_ONLY')
            return '{"signals":["clear"]}'
        provider.reason.side_effect=late_result
        result=self.council.advise(task['id'],'planner',provider)
        self.assertEqual(result['advisory_result']['status'],'BLOCKED')
        self.assertEqual(result['advisory_result']['code'],'interrupted_advisory_preserved')
        self.assertEqual(result['advisories'][1]['signals'],['tests'])

    def test_expired_advice_is_retained_blocked_when_no_retry_budget_remains(self):
        task=self.plan(); provider=Mock(); provider.reason.return_value='{"signals":["clear"]}'
        first=self.council.advise(task['id'],'planner',provider)
        def crashed_without_budget(current):
            current['advisories'][-1].update(status='RUNNING',lease_until=time.time()-1)
            current['budgets']['reserved_tokens']=current['reserved_tokens']
        self.council._change(task['id'],crashed_without_budget)
        with self.assertRaisesRegex(CouncilError,'advisory_budget_exhausted'):
            self.council.advise(task['id'],'planner',provider,retry=True)
        retained=Council(self.repo)._read(task['id'])
        self.assertEqual(retained['advisories'][0]['code'],'interrupted_advisory_preserved')
        self.assertEqual(retained['advisories'][0]['status'],'BLOCKED')
        self.assertEqual(retained['reserved_tokens'],first['reserved_tokens']); self.assertEqual(provider.reason.call_count,1)

    def test_developer_proposal_contains_only_planned_paths_actions_and_requires_host(self):
        task=self.plan(); provider=Mock()
        provider.reason.return_value=json.dumps(dict(signals=['tests'],steps=[dict(path='apps/sample.py',action='inspect'),dict(path='apps/sample.py',action='implement')]))
        result=self.council.advise(task['id'],'developer',provider)
        self.assertEqual(result['advisory_result']['status'],'ADVISORY_ONLY')
        self.assertEqual(result['roles']['developer']['status'],'NOT_RUN')
        self.assertEqual((self.repo/'apps/sample.py').read_text(encoding='utf-8'),'VALUE = 1\n')
        payload=provider.reason.call_args.args[0]
        self.assertEqual(payload['paths'],task['paths']); self.assertEqual(payload['base'],task['base'])
        self.council.status(task['id']); html=(self.council.directory/'status.html').read_text(encoding='utf-8')
        self.assertIn('Proposal only, host action required: implement apps/sample.py',html)
        self.assertNotIn('VALUE =',html)

    def test_invalid_proposal_paths_actions_extra_commands_and_duplicate_steps_fail_closed(self):
        invalid=[
            [{'path':'../production/private.py','action':'implement'}],
            [{'path':'apps/sample.py','action':'execute'}],
            [{'path':'apps/sample.py','action':'test','command':'SYNTHETIC-private'}],
            [{'path':'apps/sample.py','action':'test'}]*2,
        ]
        for index,steps in enumerate(invalid):
            tracker=self.repo/'docs/PROJECT_STATUS.md'
            tracker.write_text(tracker.read_text(encoding='utf-8').replace('review clarity',f'review clarity {index}'),encoding='utf-8')
            self.git('add','docs/PROJECT_STATUS.md'); self.git('commit','-m','synthetic proposal objective')
            task=self.plan(); provider=Mock(); provider.reason.return_value=json.dumps(dict(signals=['clear'],steps=steps))
            result=self.council.advise(task['id'],'developer',provider)
            self.assertEqual(result['advisory_result']['code'],'advisory_schema_invalid')
            self.assertNotIn('steps',result['advisory_result']); self.assertNotIn('SYNTHETIC-private',json.dumps(result))

    def test_new_tasks_require_distinct_host_reviewer_attribution_even_after_role_change(self):
        task=self.plan(); (self.repo/'apps/sample.py').write_text('VALUE = 2\n',encoding='utf-8'); source=self.council.snapshot(task)[0]
        with self.assertRaisesRegex(CouncilError,'explicit_host_actor_required'):
            self.council.record(task['id'],'developer','PASS',source)
        self.council.record(task['id'],'developer','PASS',source,actor='synthetic_developer')
        with self.assertRaisesRegex(CouncilError,'independent_host_reviewer_required'):
            self.council.record(task['id'],'reviewer','PASS',source,actor='synthetic_developer')
        self.council.record(task['id'],'reviewer','PASS',source,actor='independent_reviewer')
        self.council.record(task['id'],'security','PASS',source,actor='independent_security')
        self.council.record(task['id'],'developer','PASS',source,actor='independent_reviewer')
        with self.assertRaisesRegex(CouncilError,'current_host_reviews_required'): self.council.test(task['id'])

    def test_duplicate_objective_cannot_silently_substitute_scope_or_test_profile(self):
        self.plan()
        with self.assertRaisesRegex(CouncilError,'duplicate_objective_scope_changed'):
            self.council.plan(['apps/sample.py'],['tests.test_council_fixture'],'browser')

    def test_deterministic_routing_completes_host_cycle_without_model_or_git_writes(self):
        task=self.plan(); identity=task['id']
        self.assertEqual(self.council.handoff(identity)['next_action']['action'],'host_implementation')
        (self.repo/'apps/sample.py').write_text('VALUE = 2\n',encoding='utf-8'); source=self.council.snapshot(task)[0]
        for role,action in (('architect','host_architecture_review'),('developer','host_implementation_review'),('reviewer','independent_host_review'),('security','host_security_review')):
            route=self.council.next_action(identity)
            self.assertEqual((route['action'],route['role']),(action,role)); self.assertFalse(route['automatic_execution'])
            self.council.record(identity,role,'PASS',source,actor='synthetic_'+role)
        self.assertEqual(self.council.next_action(identity)['action'],'run_scoped_isolated_tests')
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0)):
            self.council.test(identity)
        self.assertEqual(self.council.next_action(identity)['action'],'authorized_host_commit_then_verify')
        self.assertEqual(self.git('rev-parse','HEAD'),task['base'])
        self.git('add','apps/sample.py'); self.git('commit','-m','authorized synthetic routing cycle')
        self.assertEqual(self.council.next_action(identity)['action'],'verify_authorized_host_commit_and_guardian')
        self.council.complete(identity,self.git('rev-parse','HEAD'),'synthetic-user-approval')
        result=Council(self.repo).status(identity)[0]
        self.assertEqual(result['next_action']['action'],'historical_completed_receipt')
        self.assertEqual(result['next_action']['status'],'COMPLETE')

    def test_routing_does_not_repeat_active_or_interrupted_tests_or_bypass_review(self):
        task=self.reviewed(); identity=task['id']
        def running(current): current['roles']['tester']=dict(status='RUNNING',started=time.time())
        self.council._change(identity,running)
        self.assertEqual(self.council.next_action(identity)['status'],'WAIT')
        def interrupted(current): current['roles']['tester']['started']=time.time()-601
        self.council._change(identity,interrupted)
        self.assertEqual(self.council.next_action(identity)['action'],'confirm_worker_stopped_before_resume')
        self.assertEqual(self.council._read(identity)['roles']['tester']['status'],'RUNNING')
        self.council.resume(identity,confirm_worker_stopped=True)
        self.assertEqual(self.council.next_action(identity)['action'],'host_resolve_test_failure')
        (self.repo/'apps/sample.py').write_text('VALUE = 3\n',encoding='utf-8')
        self.assertEqual(self.council.next_action(identity)['action'],'host_architecture_review')
        (self.repo/'apps/outside.py').write_text('UNPLANNED = 1\n',encoding='utf-8')
        self.assertEqual(self.council.next_action(identity)['status'],'BLOCKED')

    def test_routing_blocks_exhausted_test_budget_and_does_not_create_missing_source(self):
        task=self.plan(); identity=task['id']
        self.council._change(identity,lambda current:current['paths'].append('apps/new.py'))
        self.assertEqual(self.council.next_action(identity)['action'],'host_implementation')
        self.assertFalse((self.repo/'apps/new.py').exists())
        self.council._change(identity,lambda current:current['paths'].remove('apps/new.py'))
        (self.repo/'apps/sample.py').write_text('VALUE = 2\n',encoding='utf-8'); source=self.council.snapshot(self.council._read(identity))[0]
        for role in ('architect','developer','reviewer','security'): self.council.record(identity,role,'PASS',source,actor='synthetic_'+role)
        self.council._change(identity,lambda current:current.update(attempts=2))
        self.assertEqual(self.council.next_action(identity)['action'],'test_attempt_budget_exhausted')

    def test_routing_does_not_hide_incomplete_coverage_or_repeat_existing_pass_after_new_attestation(self):
        task=self.reviewed(); identity=task['id']
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=0,skips=0)):
            self.council.test(identity)
        self.assertEqual(self.council.next_action(identity)['action'],'host_resolve_incomplete_tests')
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0)):
            self.council.test(identity)
        self.council.record(identity,'reviewer','PASS',task['source'],actor='synthetic_reviewer')
        route=self.council.next_action(identity)
        self.assertEqual((route['status'],route['action']),('BLOCKED','test_receipt_state_requires_review'))
        self.assertFalse(route['automatic_execution'])

    def test_each_test_attempt_retains_source_status_counts_and_restarts_without_repeating(self):
        task=self.reviewed()
        with patch('scripts.development_council.run',return_value=dict(status='FAIL',tests=1,skips=0,code='suite_exit')):
            self.council.test(task['id'])
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0,code='suite_exit')):
            result=self.council.test(task['id'])
        self.assertEqual([attempt['status'] for attempt in result['test_history']],['FAIL','PASS'])
        self.assertTrue(all(attempt['source']==task['source'] and attempt['seconds']>=0 for attempt in result['test_history']))
        reopened=Council(self.repo); self.assertEqual(reopened._read(task['id'])['test_history'],result['test_history'])
        reopened.status(task['id']); html=(self.council.directory/'status.html').read_text(encoding='utf-8')
        self.assertIn('attempt 1: FAIL',html); self.assertIn('attempt 2: PASS',html)
        self.assertIn('Counts across attempts are not distinct test coverage',html)
        self.assertIn('not cryptographic identity proof',html)

    def test_legacy_failure_receipt_is_preserved_before_new_version_retry(self):
        task=self.reviewed()
        def legacy_failure(current):
            current.pop('contract_version',None); current['attempts']=1
            current['roles']['tester']=dict(status='FAIL',source=task['source'],tests=7,skips=0,code='legacy_suite_failure')
        self.council._change(task['id'],legacy_failure)
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0,code='suite_exit')):
            result=self.council.test(task['id'])
        self.assertEqual(result['test_history'][0]['code'],'legacy_suite_failure')
        self.assertEqual(result['test_history'][0]['tests'],7); self.assertTrue(result['test_history'][0]['legacy_summary'])
        self.assertNotIn('seconds',result['test_history'][0])
        self.council.status(task['id']); html=(self.council.directory/'status.html').read_text(encoding='utf-8')
        self.assertIn('attempt 1: FAIL, 7 executed, not recorded seconds',html)
        self.assertIn('attempt 2: PASS',html)

    def test_legacy_failure_survives_source_fix_and_fresh_reviews_before_retry(self):
        task=self.reviewed()
        def legacy_failure(current):
            current.pop('contract_version',None); current['attempts']=1
            current['roles']['tester']=dict(status='FAIL',source=task['source'],tests=7,skips=0,code='legacy_suite_failure')
        self.council._change(task['id'],legacy_failure)
        (self.repo/'apps/sample.py').write_text('VALUE = 3\n',encoding='utf-8')
        source=self.council.snapshot(task)[0]
        for role in ('developer','reviewer','security'):
            self.council.record(task['id'],role,'PASS',source,actor='synthetic_'+role)
        with patch('scripts.development_council.run',return_value=dict(status='PASS',tests=1,skips=0,code='suite_exit')):
            result=self.council.test(task['id'])
        first,second=result['test_history']
        self.assertEqual((first['status'],first['tests'],first['source']),('FAIL',7,task['source']))
        self.assertEqual((second['status'],second['tests'],second['source']),('PASS',1,source))
        self.assertNotEqual(first['source'],second['source'])

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

    def test_local_developer_advisor_enforces_scoped_proposal_schema(self):
        advisor=LocalCouncilAdvisor()
        content=json.dumps(dict(signals=['tests'],steps=[dict(path='apps/sample.py',action='inspect')]))
        envelope=dict(model=advisor.model,done=True,message=dict(role='assistant',content=content))
        with patch.object(advisor,'_digest',return_value='1'*64),patch.object(advisor,'_request',return_value=envelope) as request:
            self.assertEqual(advisor.reason(dict(role='developer',paths=['apps/sample.py']),deadline=30),content)
        schema=request.call_args.args[2]['format']
        self.assertEqual(schema['required'],['signals','steps'])
        self.assertEqual(schema['properties']['steps']['items']['properties']['path']['enum'],['apps/sample.py'])
        self.assertFalse(schema['properties']['steps']['items']['additionalProperties'])

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
