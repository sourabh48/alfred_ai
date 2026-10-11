from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings

from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_learning import MemoryLearning
from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider
from tests.test_persistent_memory import SyntheticEmbeddings


class MemoryLearningTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-learning-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root/'vault'),ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'limits')))
        self.embedder=SyntheticEmbeddings()
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=self.embedder))
        self.store=MemoryStore(self.root/'vault'); self.learning=MemoryLearning(self.store)
        self.alice=get_user_model().objects.create_user(username='synthetic-learning-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-learning-bob')

    def extract(self,user=None):
        return self.learning.extract(user or self.alice,'SYNTHETIC-PRIVATE hiking preference',{'source':'synthetic-confirmation','reference':'SYNTHETIC-ACCOUNT-9001'})[0]

    def test_candidates_are_encrypted_unverified_and_excluded_from_retrieval(self):
        identity=self.extract(); candidates=self.learning.candidates(self.alice)
        self.assertEqual(candidates[0]['classification'],'unverified_candidate'); self.assertEqual(candidates[0]['confidence'],0.5)
        self.assertEqual(self.store.retrieve(self.alice,'hiking'),[])
        for path in self.root.rglob('*'):
            if path.is_file(): self.assertNotIn(b'SYNTHETIC-PRIVATE',path.read_bytes())
        self.assertEqual(self.learning.candidates(self.bob),[])
        with self.assertRaises(ValueError): self.learning.verify(self.bob,identity,verified=True)

    def test_duplicate_candidates_reuse_id_and_require_explicit_verification(self):
        identity=self.extract(); self.assertEqual(self.extract(),identity)
        with self.assertRaises(PermissionError): self.learning.verify(self.alice,identity)
        verified=self.learning.verify(self.alice,identity,verified=True,content={'preference':'corrected mountain hiking'})
        self.assertEqual(self.learning.candidates(self.alice),[])
        self.assertEqual(self.learning.verify(self.alice,identity,verified=True),verified)
        result=self.store.retrieve(self.alice,'hiking')[0]
        self.assertEqual(result['content']['preference'],'corrected mountain hiking')
        self.assertEqual(result['provenance']['verification'],'user_verified')

    def test_deleted_verified_candidate_cannot_be_verified_again(self):
        candidate=self.extract(); identity=self.learning.verify(self.alice,candidate,verified=True)
        self.store.delete_memory(self.alice,identity)
        with self.assertRaises(ValueError): self.learning.verify(self.alice,candidate,verified=True)
        self.assertEqual(self.store.restore_owner(self.alice),0)

    def test_embedding_failure_preserves_candidate_for_retry(self):
        identity=self.extract()
        with patch.object(self.embedder,'embed',side_effect=OSError('synthetic private failure')),self.assertRaises(OSError):
            self.learning.verify(self.alice,identity,verified=True)
        self.assertEqual(self.learning.candidates(self.alice)[0]['id'],identity)
        self.assertEqual(self.store.list_memories(self.alice),[])

    def test_reset_during_verification_cannot_restore_candidate(self):
        identity=self.extract(); embed=self.embedder.embed
        def resetting(text):
            self.store.reset_owner(self.alice)
            return embed(text)
        with patch.object(self.embedder,'embed',side_effect=resetting),self.assertRaises(ValueError):
            self.learning.verify(self.alice,identity,verified=True)
        self.assertEqual(self.learning.candidates(self.alice),[])
        self.assertEqual(self.store.list_memories(self.alice),[])

    def test_candidate_expiration_delete_and_reset_remove_keys(self):
        with patch('apps.ml_engine.services.memory_learning.datetime') as clock:
            clock.now.return_value=datetime.now(timezone.utc)-timedelta(days=31)
            self.extract()
        self.assertEqual(self.learning.candidates(self.alice),[])
        identity=self.extract(); self.assertEqual(self.store.delete_memory(self.alice,identity),1)
        self.extract(); bob=self.extract(self.bob); self.store.reset_owner(self.alice)
        self.assertEqual(self.learning.candidates(self.alice),[]); self.assertEqual(self.learning.candidates(self.bob)[0]['id'],bob)

    def test_correction_consolidation_and_incremental_reembedding_revoke_old_ids(self):
        first=self.learning.verify(self.alice,self.extract(),verified=True)
        second=self.learning.revise(self.alice,[first],{'statement':'corrected preference'},verified=True)
        third=self.store.save_verified(self.alice,{'other':'synthetic'}, {'source':'synthetic'},sensitivity='public',verified=True)
        merged=self.learning.revise(self.alice,[second,third],{'preference':'merged and confirmed'},verified=True)
        self.assertEqual([r['id'] for r in self.store.list_memories(self.alice)],[merged])
        self.assertEqual(self.store.list_memories(self.alice)[0]['sensitivity'],'sensitive')
        refreshed=self.learning.revise(self.alice,[merged],None,verified=True,reembed=True)
        self.assertEqual(self.store.restore_owner(self.alice),1)
        self.assertEqual(self.store.retrieve(self.alice,'preference')[0]['id'],refreshed)

    def test_foreign_and_malformed_correction_or_evaluation_is_rejected(self):
        identity=self.learning.verify(self.alice,self.extract(),verified=True)
        for identities in ([identity],[[]]):
            with self.assertRaises((ValueError,PermissionError)):
                self.learning.revise(self.bob,identities,{'statement':'synthetic'},verified=True)
        with self.assertRaises(ValueError): self.learning.evaluate(self.bob,[{'query':'synthetic','expected_id':identity}])
        result=self.learning.evaluate(self.alice,[{'query':'preference','expected_id':identity}])
        self.assertEqual(result['recall_at_3'],1); self.assertFalse(result['generated_hypotheses_are_facts'])

    def test_learning_does_not_change_canonical_financial_records(self):
        from apps.expenses.models import BankAccount
        account=BankAccount.objects.create(user=self.alice,account_number='SYNTHETIC-ACCOUNT',current_balance=123)
        identity=self.learning.extract(self.alice,'Loan balance hypothesis: 90000',{'source':'synthetic extraction'})[0]
        self.learning.verify(self.alice,identity,verified=True)
        account.refresh_from_db(); self.assertEqual(account.current_balance,123)

    def test_unverified_candidates_never_synchronize_and_correction_propagates(self):
        provider=MockCloudProvider(self.root/'cloud'); sync=MemorySynchronizer(self.store,provider)
        sync.configure(self.alice,enabled=True,consent=True); candidate=self.extract(); sync.run(self.alice)
        with self.store._transaction() as db:
            self.assertEqual(sync._snapshot(db,_owner(self.alice))['records'],{})
        identity=self.learning.verify(self.alice,candidate,verified=True); sync.run(self.alice)
        replacement=self.learning.revise(self.alice,[identity],{'statement':'corrected synthetic'},verified=True); sync.run(self.alice)
        self.assertEqual(self.store.restore_owner(self.alice),1); self.assertEqual(self.store.list_memories(self.alice)[0]['id'],replacement)

    def test_learning_api_rejects_client_owner_and_enforces_csrf(self):
        url='/api/ai/memories/learning/'
        client=Client(enforce_csrf_checks=True); data={'action':'extract','text':'synthetic','provenance':{'source':'synthetic'}}
        self.assertEqual(client.post(url,data,content_type='application/json').status_code,403)
        client.force_login(self.alice); self.assertEqual(client.post(url,data,content_type='application/json').status_code,403)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.post(url,data|{'owner':self.bob.pk},content_type='application/json').status_code,400)
        response=self.client.post(url,data,content_type='application/json')
        self.assertEqual(response.status_code,201); self.assertIn('no-store',response['Cache-Control'])
        identity=response.json()['candidate_ids'][0]
        self.assertEqual(self.client.post(url,{'action':'verify','id':identity},content_type='application/json').status_code,400)
        self.assertEqual(self.client.post(url,{'action':'verify','id':identity,'verified':True},content_type='application/json').status_code,200)

    def test_discarded_candidates_leave_no_cloud_tombstone_or_journal_growth(self):
        identity=self.extract(); self.assertEqual(self.store.delete_memory(self.alice,identity),1)
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_keys').fetchone()[0],0)
        self.assertEqual(self.learning.candidates(self.alice),[])
