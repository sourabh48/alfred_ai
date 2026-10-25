"""Synthetic assistant availability, safe failures and existing GET compatibility."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_learning import MemoryLearning
from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider
from tests.test_persistent_memory import SyntheticEmbeddings


class IntelligenceUITests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-ui-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'), ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        self.user = get_user_model().objects.create_user(username='synthetic-ui-owner')
        self.client.force_login(self.user)
        self.store = MemoryStore(root/'vault')
        self.root = root

    def test_status_is_bounded_local_only_and_does_not_build_financial_insights(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model, patch('apps.ml_engine.api.views.build_financial_intelligence') as finance, \
                patch('apps.ml_engine.api.views.monotonic', return_value=100.0):
            response = self.client.get('/api/ai/personal-insights/?assistant_status=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['local_model_status'], 'available')
        model.return_value._digest.assert_called_once_with(deadline=101.0)
        finance.assert_not_called()
        self.assertIn('no-store', response['Cache-Control'])

    def test_unavailable_status_does_not_expose_internal_diagnostics(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model:
            model.return_value._digest.side_effect = EmbeddingUnavailable('C:/private/loan-123.txt secret-token')
            response = self.client.get('/api/ai/personal-insights/?assistant_status=1')
        self.assertEqual(response.json()['local_model_status'], 'unavailable')
        self.assertNotIn('secret-token', str(response.json()))

    def test_generation_failure_preserves_safe_code_reference_and_status(self):
        with patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner') as model:
            model.return_value.reason.side_effect = EmbeddingUnavailable('C:/private/OCR-sensitive')
            response = self.client.post('/api/ai/personal-insights/', {'query':'synthetic question'}, content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'local_model_unavailable')
        self.assertTrue(response.json()['error_id'])
        self.assertNotIn('OCR-sensitive', str(response.json()))

    def test_existing_insights_get_does_not_probe_or_replace_its_contract(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model, patch('apps.ml_engine.api.views.build_financial_intelligence', return_value={'metrics':{'known':42}}):
            response = self.client.get('/api/ai/personal-insights/')
        model.assert_not_called()
        self.assertEqual(response.json()['metrics'], {'known':42})

    def test_selected_reset_is_atomic_owner_scoped_and_preserves_other_records(self):
        save = lambda user,text:self.store.save_verified(user,{'statement':text},{'source':'synthetic user'},verified=True)
        first = save(self.user,'synthetic first'); second = save(self.user,'synthetic second')
        other = get_user_model().objects.create_user(username='synthetic-ui-other')
        foreign = save(other,'synthetic foreign')
        response = self.client.post('/api/ai/memories/reset/', {'confirm':True,'ids':[first,foreign]},content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(self.store.list_memories(self.user)),2)
        response = self.client.post('/api/ai/memories/reset/', {'confirm':True,'ids':[first]},content_type='application/json')
        self.assertEqual(response.json()['deleted'],1)
        self.store.restore_owner(self.user)
        self.assertEqual([r['id'] for r in self.store.list_memories(self.user)],[second])
        self.assertEqual([r['id'] for r in self.store.list_memories(other)],[foreign])

    def test_invalid_or_empty_selection_does_not_reset_all_memories(self):
        self.store.save_verified(self.user,{'statement':'synthetic retained'},{'source':'synthetic'},verified=True)
        for selection in (None,[],['0'*32]*2,['0'*32]*21):
            response = self.client.post('/api/ai/memories/reset/',{'confirm':True,'ids':selection},content_type='application/json')
            self.assertEqual(response.status_code,400)
        self.assertEqual(len(self.store.list_memories(self.user)),1)

    def test_rejected_candidate_cannot_be_verified_or_recovered(self):
        learning = MemoryLearning(self.store)
        identity = learning.extract(self.user,'synthetic hypothesis',{'source':'synthetic AI proposal'})[0]
        response = self.client.delete(f'/api/ai/memories/{identity}/')
        self.assertEqual(response.status_code,204)
        self.assertEqual(learning.candidates(self.user),[])
        self.assertEqual(self.store.restore_owner(self.user),0)
        with self.assertRaises(ValueError): learning.verify(self.user,identity,verified=True)

    def test_status_records_actual_mock_sync_success_and_keeps_real_provider_disabled(self):
        sync = MemorySynchronizer(self.store,MockCloudProvider(self.root/'mock'))
        sync.configure(self.user,enabled=True,consent=True)
        before = time.time(); sync.run(self.user)
        stamp = sync.status(self.user)['last_success_at']
        self.assertGreaterEqual(stamp,before)
        self.assertEqual(sync.status(self.user)['retry_at'],0)
        response = self.client.get('/api/ai/memories/reason/')
        self.assertFalse(response.json()['real_provider_enabled'])
        self.assertEqual(response.json()['usage']['basis'],'conservative_reservation')
        self.assertNotIn('key', str(response.json()['usage']))

    def test_usage_is_owner_scoped_and_expired_reservations_are_not_today_usage(self):
        from datetime import datetime,timezone,timedelta
        with self.store._transaction() as db:
            state = self.store._sync_state(db,_owner(self.user))
            state['reasoning']={'day':(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat(),'reserved':100,'reserved_microusd':99}
            state['openai_key']='SYNTHETIC-DO-NOT-DISCLOSE'
            self.store._write_sync_state(db,_owner(self.user),state)
        response = self.client.get('/api/ai/memories/reason/')
        self.assertEqual(response.json()['usage']['reserved_tokens'],0)
        self.assertNotIn('SYNTHETIC-DO-NOT-DISCLOSE',str(response.json()))
