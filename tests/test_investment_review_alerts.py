from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.investments.models import Investment
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings


class InvestmentReviewAlertTests(TestCase):
    URL='/api/investments/review-alerts/'

    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-review-alert-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root/'vault')))
        self.embedder=self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.owner=get_user_model().objects.create_user(username='synthetic-review-owner')
        self.other=get_user_model().objects.create_user(username='synthetic-review-other')
        self.client.force_login(self.owner)
        self.row=Investment.objects.create(user=self.owner,asset_name='SYNTHETIC-REVIEW-PRIVATE',asset_type='equity',current_value='123.45')
        self.old=timezone.now()-timedelta(days=40)
        Investment.objects.filter(pk=self.row.pk).update(updated_at=self.old)

    def get(self):
        response=self.client.get(self.URL)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        return response.json()

    def post(self,action,**kwargs):
        payload=dict(action=action,revision=self.get()['revision'],**kwargs)
        return self.client.post(self.URL,payload,content_type='application/json')

    def enable(self):
        response=self.post('configure',enabled=True,days=30,consent=True)
        self.assertEqual(response.status_code,200)

    def test_default_consent_and_no_monetary_or_provider_behavior(self):
        self.assertFalse(self.get()['enabled'])
        self.assertEqual(self.get()['items'],[])
        self.assertEqual(self.post('evaluate').status_code,400)
        self.assertEqual(self.post('configure',enabled=True,days=30).status_code,400)
        for data in ({'enabled':True,'days':True,'consent':True},{'enabled':True,'days':30,'consent':True,'currency':'USD'}):
            self.assertEqual(self.post('configure',**data).status_code,400)
        self.assertFalse(self.get()['enabled'])
        self.row.refresh_from_db(); self.assertEqual(str(self.row.current_value),'123.45')

    def test_encrypted_reopen_dedup_read_dismiss_and_disable(self):
        self.enable()
        first=self.post('evaluate').json(); self.assertEqual(len(first['items']),1)
        self.assertEqual(first['items'][0]['status'],'unread')
        self.assertEqual(self.post('evaluate').json()['items'],first['items'])
        self.assertEqual(self.post('read',id=self.row.pk).json()['items'][0]['status'],'read')
        self.assertEqual(self.post('dismiss',id=self.row.pk).json()['items'][0]['status'],'dismissed')
        self.assertEqual(self.post('evaluate').json()['items'][0]['status'],'dismissed')
        store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings())
        with store._transaction() as db:
            state=store._sync_state(db,_owner(self.owner))
            self.assertTrue(state['investment_record_review']['enabled'])
        self.assertNotIn(b'SYNTHETIC-REVIEW-PRIVATE',store.database.read_bytes())
        self.assertNotIn(b'investment_record_review',store.database.read_bytes())
        self.assertEqual(self.post('configure',enabled=False,days=30).json()['items'],[])

    def test_owner_csrf_and_revision_isolation(self):
        self.enable(); self.post('evaluate')
        old=self.get()['revision']; self.post('read',id=self.row.pk)
        self.assertEqual(self.client.post(self.URL,dict(action='dismiss',revision=old,id=self.row.pk),content_type='application/json').status_code,409)
        other=Client(); other.force_login(self.other)
        self.assertFalse(other.get(self.URL).json()['enabled'])
        self.assertEqual(other.post(self.URL,dict(action='read',revision=0,id=self.row.pk),content_type='application/json').status_code,409)
        strict=Client(enforce_csrf_checks=True); strict.force_login(self.owner)
        self.assertEqual(strict.post(self.URL,dict(action='evaluate',revision=0),content_type='application/json').status_code,403)
        self.assertEqual(Client().get(self.URL).status_code,403)

    def test_record_correction_threshold_change_deletion_and_expiry_invalidate(self):
        self.enable(); self.post('evaluate')
        self.assertEqual(self.post('configure',enabled=True,days=90,consent=True).json()['items'][0]['status'],'resolved')
        self.post('configure',enabled=True,days=30,consent=True); self.post('evaluate')
        Investment.objects.filter(pk=self.row.pk).update(updated_at=timezone.now())
        self.assertEqual(self.get()['items'][0]['status'],'resolved')
        Investment.objects.filter(pk=self.row.pk).update(updated_at=self.old)
        self.post('evaluate'); self.row.delete()
        self.assertEqual(self.get()['items'],[])
        future=timezone.now()+timedelta(days=91)
        with patch('apps.investments.services.review_alerts.timezone') as clock:
            clock.now.return_value=future
            self.assertEqual(self.get()['items'],[])

    def test_existing_expiry_job_removes_expired_notifications(self):
        self.enable(); self.post('evaluate')
        store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings())
        with store._transaction() as db:
            state=store._sync_state(db,_owner(self.owner))
            state['investment_record_review']['items'][str(self.row.pk)]['created_at']=(timezone.now()-timedelta(days=91)).isoformat()
            store._write_sync_state(db,_owner(self.owner),state)
        store.expire_all()
        with store._transaction() as db:
            self.assertEqual(store._sync_state(db,_owner(self.owner))['investment_record_review']['items'],{})

    def test_maximum_batch_preserves_other_policy_and_is_not_exported(self):
        from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider
        Investment.objects.bulk_create([Investment(user=self.owner,asset_type='equity',asset_name=f'Synthetic bound {i}') for i in range(19)])
        Investment.objects.filter(user=self.owner).update(updated_at=self.old)
        store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings())
        with store._transaction() as db:
            state=store._sync_state(db,_owner(self.owner)); state['synthetic_other_policy']={'enabled':False}
            store._write_sync_state(db,_owner(self.owner),state)
        self.enable(); response=self.post('evaluate')
        self.assertEqual(response.status_code,200); self.assertEqual(len(response.json()['items']),20)
        with store._transaction() as db:
            self.assertEqual(store._sync_state(db,_owner(self.owner))['synthetic_other_policy'],{'enabled':False})
            snapshot=MemorySynchronizer(store,MockCloudProvider(self.root/'unused-synthetic-provider'))._snapshot(db,_owner(self.owner))
        self.assertNotIn('investment_record_review',str(snapshot))

    def test_quota_future_dates_and_account_reset(self):
        self.enable()
        Investment.objects.filter(pk=self.row.pk).update(updated_at=timezone.now()+timedelta(days=1))
        result=self.post('evaluate').json()
        self.assertEqual(result['items'],[]); self.assertEqual(result['unassessed_records'],1)
        Investment.objects.bulk_create([Investment(user=self.owner,asset_type='equity',asset_name=f'Synthetic {i}') for i in range(20)])
        before=self.get()['revision']; self.assertEqual(self.post('evaluate').status_code,400)
        self.assertEqual(self.get()['revision'],before)
        MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings()).reset_owner(self.owner)
        self.assertFalse(self.get()['enabled'])

    def test_key_loss_and_corruption_fail_closed_without_overwrite(self):
        self.enable(); self.post('evaluate')
        key=self.root/'vault'/'journal.key'; original=key.read_bytes(); key.write_bytes(b'synthetic-corrupt-key')
        before=(self.root/'vault'/'verified.sqlite3').read_bytes()
        self.assertEqual(self.client.get(self.URL).status_code,503)
        self.assertEqual((self.root/'vault'/'verified.sqlite3').read_bytes(),before)
        key.write_bytes(original); key.unlink()
        self.assertEqual(self.client.get(self.URL).status_code,503)

    def test_unavailable_storage_preserves_shared_private_cache_contract(self):
        from apps.ml_engine.services.memory_key import MemoryStorageUnavailable
        with patch('apps.investments.alert_views.memory_store',side_effect=MemoryStorageUnavailable('synthetic-private-vault')):
            for method, data in (('get',None),('post',{'action':'evaluate','revision':0})):
                with self.subTest(method=method):
                    response=getattr(self.client,method)(self.URL,data=data,content_type='application/json')
                    self.assertEqual(response.status_code,503)
                    self.assertEqual(response['Cache-Control'],'no-store, private')
                    self.assertNotIn('synthetic-private-vault',response.content.decode())
