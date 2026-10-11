"""Synthetic session, budget and supervisor boundaries for encrypted synchronization."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
from io import StringIO
import json
from uuid import uuid4
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from apps.ml_engine.services.memory_reasoning import MockReasoner, ReasoningBudgetExceeded, reason_with_memory
from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider, SyncUnavailable, SyncConflict
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings


class MemorySyncRuntimeTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-sync-runtime-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root/'vault'),
            ALFRED_MEMORY_SYNC_MOCK_DIR=str(self.root/'mock'),ALFRED_MEMORY_MOCK_REASONING=True,
            ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'limits')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.alice=get_user_model().objects.create_user(username='synthetic-sync-runtime-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-sync-runtime-bob')
        self.store=MemoryStore(self.root/'vault')
        self.provider=MockCloudProvider(self.root/'mock')
        self.sync=MemorySynchronizer(self.store,self.provider)
        self.client.force_login(self.alice)

    def save(self,user=None,*,sensitivity='public'):
        return self.store.save_verified(user or self.alice,{'preference':'synthetic mountain trip'},
            {'source':'synthetic owner verification','reference':uuid4().hex},sensitivity=sensitivity,verified=True)

    def post(self,path,payload):
        return self.client.post('/api/ai/memories/'+path+'/',payload,content_type='application/json')

    def test_api_explicit_sync_consent_owner_scope_and_no_store(self):
        self.save()
        self.assertEqual(self.post('sync',{'action':'configure','enabled':True}).status_code,400)
        response=self.post('sync',{'action':'configure','enabled':True,'consent':True})
        self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.post('sync',{'action':'sync'}).json()['result'],'uploaded')
        self.assertEqual(self.post('sync',{'action':'recover'}).status_code,400)
        for payload in ({'action':[]},{'action':'sync','owner':self.bob.pk},{'action':'sync','enabled':True}):
            self.assertEqual(self.post('sync',payload).status_code,400)
        self.client.force_login(self.bob)
        self.assertFalse(self.client.get('/api/ai/memories/sync/').json()['status']['enabled'])
        self.assertEqual(self.post('sync',{'action':'sync'}).json()['result'],'disabled')

    def test_sync_and_reasoning_require_session_csrf(self):
        client=Client(enforce_csrf_checks=True)
        for path,payload in (('sync',{'action':'configure','enabled':True,'consent':True}),
                             ('reason',{'query':'synthetic','consent':True,'query_sensitivity':'public'})):
            url='/api/ai/memories/'+path+'/'
            self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_AUTHORIZATION='Token synthetic').status_code,403)
            client.force_login(self.alice)
            self.assertEqual(client.post(url,payload,content_type='application/json').status_code,403)
        self.assertFalse(self.sync.status(self.alice)['enabled'])
        client.get('/settings/'); csrf=client.cookies['csrftoken'].value
        self.assertEqual(client.post('/api/ai/memories/sync/',{'action':'configure','enabled':True,'consent':True},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,200)

    def test_shared_expensive_limit_rejects_sync_before_provider(self):
        self.sync.configure(self.alice,enabled=True,consent=True)
        with override_settings(ALFRED_EXPENSIVE_ACCOUNT_LIMIT=1):
            self.assertEqual(self.post('sync',{'action':'sync'}).status_code,200)
            with patch('apps.ml_engine.api.memory.memory_sync',side_effect=AssertionError('Rejected before provider')):
                response=self.post('sync',{'action':'sync'})
            self.assertEqual(response.status_code,429); self.assertIn('Retry-After',response)
        self.assertEqual(self.sync.status(self.bob)['revision'],0)

    def test_provider_failure_and_conflict_use_safe_references(self):
        for failure,status in ((OSError('F:/private/SYNTHETIC-TOKEN-9001'),503),(SyncConflict('SYNTHETIC-TOKEN-9001'),409)):
            with patch('apps.ml_engine.api.memory.memory_sync',side_effect=failure),self.assertLogs('apps.ml_engine.api.memory',level='ERROR') as logs:
                response=self.post('sync',{'action':'sync'})
            self.assertEqual(response.status_code,status)
            self.assertIn(response.json()['error_id'],''.join(logs.output))
            self.assertNotIn('SYNTHETIC-TOKEN-9001',str(response.content)+''.join(logs.output))

    def test_unconfigured_provider_is_unavailable_without_network_or_opt_in(self):
        with override_settings(ALFRED_MEMORY_SYNC_MOCK_DIR='',ALFRED_MEMORY_MOCK_REASONING=False):
            self.assertEqual(self.post('sync',{'action':'configure','enabled':True,'consent':True}).status_code,503)
            self.assertEqual(self.post('reason',{'query':'synthetic','consent':True,'query_sensitivity':'public'}).status_code,503)
        self.assertFalse(self.sync.status(self.alice)['enabled'])

    def test_reasoning_requires_consent_public_query_and_public_memories(self):
        provider=Mock()
        for kwargs in ({},{'consent':True},{'consent':True,'query_sensitivity':'personal'}):
            with self.assertRaises(PermissionError): reason_with_memory(self.store,self.alice,'synthetic',provider=provider,**kwargs)
        self.save(sensitivity='sensitive')
        with self.assertRaises(PermissionError): reason_with_memory(self.store,self.alice,'synthetic',consent=True,query_sensitivity='public',provider=provider)
        provider.reason.assert_not_called()

    def test_public_reasoning_strips_provenance_and_reserves_owner_budget(self):
        self.save(); self.save(self.bob,sensitivity='sensitive')
        provider=MockReasoner()
        with patch.object(provider,'reason',wraps=provider.reason) as reason:
            result=reason_with_memory(self.store,self.alice,'synthetic',consent=True,query_sensitivity='public',provider=provider)
        payload=reason.call_args.args[0]
        self.assertEqual(set(payload),{'query','memories'}); self.assertNotIn('source',json.dumps(payload))
        with self.store._transaction() as db:
            state=self.store._sync_state(db,_owner(self.alice)); bob=self.store._sync_state(db,_owner(self.bob))
        self.assertEqual(state['reasoning']['reserved'],result['reserved_tokens']); self.assertNotIn('reasoning',bob)

    def test_budget_persists_across_failure_restart_and_reset(self):
        self.save(); provider=Mock(); provider.reason.side_effect=OSError('SYNTHETIC-SECRET')
        with self.assertRaises(SyncUnavailable): reason_with_memory(self.store,self.alice,'synthetic',consent=True,query_sensitivity='public',provider=provider,daily_tokens=1200)
        self.store.reset_owner(self.alice)
        restarted=MemoryStore(self.root/'vault')
        with self.assertRaises(ReasoningBudgetExceeded): reason_with_memory(restarted,self.alice,'synthetic',consent=True,query_sensitivity='public',provider=provider,daily_tokens=1200)
        self.assertEqual(provider.reason.call_count,1)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,_owner(self.alice)); state['reasoning']['day']=(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat()
            self.store._write_sync_state(db,_owner(self.alice),state)
        self.assertIn('answer',reason_with_memory(restarted,self.alice,'synthetic',consent=True,query_sensitivity='public',provider=MockReasoner(),daily_tokens=1200))

    def test_reasoning_api_budget_429_and_payload_rejection(self):
        payload={'query':'synthetic','consent':True,'query_sensitivity':'public'}
        for bad in (payload|{'owner':self.bob.pk},payload|{'daily_tokens':99999},payload|{'consent':False}):
            self.assertEqual(self.post('reason',bad).status_code,400)
        with override_settings(ALFRED_MEMORY_REASONING_DAILY_TOKENS=1200):
            self.assertEqual(self.post('reason',payload).status_code,200)
            response=self.post('reason',payload)
            self.assertEqual(response.status_code,429); self.assertIn('Retry-After',response)

    def test_command_incremental_retry_and_owner_opt_in(self):
        self.save(); self.save(self.bob); self.sync.configure(self.alice,enabled=True,consent=True)
        output=StringIO(); call_command('sync_private_memory',stdout=output)
        self.assertIn('processed=1',output.getvalue()); self.assertEqual(self.sync.status(self.alice)['revision'],1)
        self.assertIsNone(self.provider.head(_owner(self.bob),deadline=time.monotonic()+5))
        self.save(); call_command('sync_private_memory',stdout=StringIO())
        self.assertEqual(self.sync.status(self.alice)['revision'],2)

    def test_command_safe_failure_retains_pending_queue(self):
        self.save(); self.sync.configure(self.alice,enabled=True,consent=True)
        with patch.object(MockCloudProvider,'publish',side_effect=OSError('SYNTHETIC-SECRET')),self.assertLogs('apps.ml_engine.management.commands.sync_private_memory',level='ERROR') as logs:
            call_command('sync_private_memory',stdout=StringIO())
        self.assertTrue(self.sync.status(self.alice)['pending']); self.assertNotIn('SYNTHETIC-SECRET',''.join(logs.output))

    def test_unconfigured_command_does_not_create_mock_storage(self):
        with override_settings(ALFRED_MEMORY_SYNC_MOCK_DIR=''),patch('apps.ml_engine.services.memory_cloud.MockCloudProvider',side_effect=AssertionError('No provider')):
            call_command('sync_private_memory',stdout=StringIO())

    def test_native_startup_download_and_shutdown_upload_after_writer_drain(self):
        import alfred_native
        self.save(); self.sync.configure(self.alice,enabled=True,consent=True)
        data=self.root/'native'; data.mkdir(); child=Mock(); child.pid=1234; child.poll.return_value=None
        child.wait.side_effect=lambda:self.save()
        server=Mock(); tray=Mock(); order=[]
        def command(name,**kwargs):
            order.append(name)
            if name=='sync_private_memory':
                self.assertLessEqual(kwargs['seconds'],5)
                call_command(name,stdout=StringIO(),**kwargs)
        def start_tray(data,state,*args,**kwargs):
            (alfred_native.runtime_directory(data)/('stop-'+state['instance'])).touch()
            return tray
        with patch.object(alfred_native,'configure'),patch.object(alfred_native,'spawn',return_value=child),\
             patch('django.core.management.call_command',side_effect=command),patch('django.core.wsgi.get_wsgi_application'),\
             patch('alfred_ai.services.native_web.create_native_server',return_value=server),\
             patch('alfred_ai.tasks.production_probe_task') as probe,patch('alfred_tray.start_tray',side_effect=start_tray):
            probe.delay.side_effect=lambda instance:Mock(get=Mock(return_value={'probe_id':instance}))
            self.assertEqual(alfred_native.serve(data,49123),0)
        self.assertEqual(self.sync.status(self.alice)['revision'],2)
        child.wait.assert_called_once(); server.close.assert_called_once()
        self.assertEqual(order.count('sync_private_memory'),2)

    def test_native_tick_uses_bounded_command(self):
        from alfred_ai.native_tasks import native_private_memory_sync
        with patch('django.core.management.call_command') as command:
            native_private_memory_sync.call_local()
        command.assert_called_once_with('sync_private_memory',seconds=2,verbosity=0)
