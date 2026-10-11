from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings

from apps.ml_engine.services.persistent_memory import MemoryStore, MemoryConflict, _owner
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

    def test_changed_verification_retry_returns_conflict_without_disclosing_content(self):
        candidate=self.extract()
        identity=self.learning.verify(self.alice,candidate,verified=True,content={'statement':'first synthetic choice'})
        self.client.force_login(self.alice)
        with self.assertLogs('apps.ml_engine.api.memory',level='ERROR') as logs:
            response=self.client.post('/api/ai/memories/learning/',{'action':'verify','id':candidate,'verified':True,
                'content':{'statement':'SYNTHETIC-PRIVATE changed choice'}},content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertIn('no-store',response['Cache-Control'])
        self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
        self.assertNotIn('SYNTHETIC-PRIVATE',' '.join(logs.output))
        self.assertIn(response.json()['error_id'],' '.join(logs.output))
        self.assertEqual(logs.records[0].exception_type,'MemoryConflict')
        self.assertEqual(self.store.list_memories(self.alice)[0]['id'],identity)
        self.assertEqual(self.store.list_memories(self.alice)[0]['content'],{'statement':'first synthetic choice'})

    def test_identical_verification_retry_preserves_id_and_journal(self):
        candidate=self.extract(); content={'statement':'synthetic confirmed choice'}
        identity=self.learning.verify(self.alice,candidate,verified=True,content=content)
        with patch.object(self.embedder,'embed',side_effect=AssertionError('retry must not infer')):
            self.assertEqual(self.learning.verify(self.alice,candidate,verified=True,content=content),identity)
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)

    def test_competing_corrections_preserve_winner_and_reject_late_writer(self):
        original=self.learning.verify(self.alice,self.extract(),verified=True)
        embed=self.embedder.embed; winners=[]
        def competing(text):
            with patch.object(self.embedder,'embed',side_effect=embed):
                winners.append(self.learning.revise(self.alice,[original],{'statement':'synthetic winner'},verified=True))
            return embed(text)
        with patch.object(self.embedder,'embed',side_effect=competing),self.assertRaises(MemoryConflict):
            self.learning.revise(self.alice,[original],{'statement':'synthetic late writer'},verified=True)
        self.assertEqual(self.store.list_memories(self.alice)[0]['id'],winners[0])
        self.assertEqual(self.store.restore_owner(self.alice),1)
        self.client.force_login(self.alice)
        response=self.client.post('/api/ai/memories/learning/',{'action':'correct','id':original,
            'content':{'statement':'synthetic stale edit'},'verified':True},content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.store.list_memories(self.alice)[0]['content'],{'statement':'synthetic winner'})

    def test_competing_candidate_reviews_never_overwrite_verified_winner(self):
        candidate=self.extract(); embed=self.embedder.embed; winners=[]
        def competing(text):
            with patch.object(self.embedder,'embed',side_effect=embed):
                winners.append(self.learning.verify(self.alice,candidate,verified=True,content={'statement':'synthetic winner'}))
            return embed(text)
        with patch.object(self.embedder,'embed',side_effect=competing),self.assertRaises(MemoryConflict):
            self.learning.verify(self.alice,candidate,verified=True,content={'statement':'synthetic late writer'})
        self.assertEqual(self.store.list_memories(self.alice)[0]['id'],winners[0])
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)

    def test_failed_correction_keeps_original_retrievable_and_recoverable(self):
        original=self.learning.verify(self.alice,self.extract(),verified=True)
        with patch.object(self.embedder,'embed',side_effect=OSError('SYNTHETIC-PRIVATE embedding failure')),self.assertRaises(OSError):
            self.learning.revise(self.alice,[original],{'statement':'synthetic changed'},verified=True)
        self.assertEqual(self.store.retrieve(self.alice,'hiking')[0]['id'],original)
        self.assertEqual(self.store.restore_owner(self.alice),1)

    def test_evaluation_measures_ranking_misses_and_no_match_without_retaining_queries(self):
        def embedding(text):
            return ([1.0,0.0] if 'mountain' in text else [0.0,1.0]),'synthetic-quality-model'
        with patch.object(self.embedder,'embed',side_effect=embedding):
            mountain=self.store.save_verified(self.alice,{'statement':'mountain'}, {'source':'synthetic'},verified=True)
            coast=self.store.save_verified(self.alice,{'statement':'coast'}, {'source':'synthetic'},verified=True)
            result=self.learning.evaluate(self.alice,[{'query':'SYNTHETIC-QUALITY-QUERY mountain','expected_id':mountain},
                {'query':'SYNTHETIC-QUALITY-QUERY coast','expected_id':mountain},
                {'query':'SYNTHETIC-QUALITY-QUERY unrelated','expected_id':None}])
        self.assertEqual(result['positive_cases'],2); self.assertEqual(result['negative_cases'],1)
        self.assertEqual(result['recall_at_3'],1); self.assertEqual(result['mean_reciprocal_rank'],0.75)
        self.assertEqual(result['top_1_accuracy'],0.5); self.assertEqual(result['false_positive_rate'],1)
        self.assertEqual(result['abstention_rate'],0)
        with patch.object(self.store,'retrieve',return_value=[{'id':coast}]):
            missed=self.learning.evaluate(self.alice,[{'query':'mountain','expected_id':mountain}])
        self.assertEqual(missed['recall_at_3'],0); self.assertEqual(missed['mean_reciprocal_rank'],0)
        self.assertIsNone(missed['false_positive_rate'])
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],2)
        self.assertNotIn('SYNTHETIC-QUALITY-QUERY',str(result))
        for path in self.root.rglob('*'):
            if path.is_file(): self.assertNotIn(b'SYNTHETIC-QUALITY-QUERY',path.read_bytes())

    def test_negative_only_evaluation_of_empty_vault_measures_abstention(self):
        result=self.learning.evaluate(self.alice,[{'query':'synthetic absent memory','expected_id':None}])
        self.assertEqual(result['positive_cases'],0); self.assertEqual(result['abstention_rate'],1)
        self.assertEqual(result['false_positive_rate'],0)
        for key in ('recall_at_3','mean_reciprocal_rank','top_1_accuracy'): self.assertIsNone(result[key])

    def test_evaluation_compares_opt_in_cutoff_with_unfiltered_false_positive(self):
        identity=self.store.save_verified(self.alice,{'statement':'mountain hiking'},{'source':'synthetic'},verified=True)
        cases=[{'query':'mountain','expected_id':identity},{'query':'coast','expected_id':None}]
        self.assertEqual(self.learning.evaluate(self.alice,cases)['false_positive_rate'],1)
        result=self.learning.evaluate(self.alice,cases,min_score=0.45)
        self.assertEqual(result['recall_at_3'],1); self.assertEqual(result['abstention_rate'],1)

    def test_evaluation_rejects_malformed_ground_truth_before_inference(self):
        for case in ({'query':'synthetic','expected_id':False},{'query':'synthetic','expected_id':[]},
                {'query':'','expected_id':None},{'query':'x'*8193,'expected_id':None},
                {'query':'synthetic','expected_id':None,'owner':self.bob.pk}):
            with patch.object(self.embedder,'embed',side_effect=AssertionError('invalid case must not infer')),self.assertRaises(ValueError):
                self.learning.evaluate(self.alice,[case])

    def test_evaluation_during_correction_reports_conflict_without_private_results(self):
        original=self.learning.verify(self.alice,self.extract(),verified=True)
        retrieve=self.store.retrieve
        def correcting(user,query,**kwargs):
            self.learning.revise(user,[original],{'statement':'synthetic corrected'},verified=True)
            return retrieve(user,query,**kwargs)
        self.client.force_login(self.alice)
        with patch.object(MemoryStore,'retrieve',side_effect=correcting):
            response=self.client.post('/api/ai/memories/learning/',{'action':'evaluate',
                'cases':[{'query':'SYNTHETIC-PRIVATE-QUALITY QUERY','expected_id':original}]},content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
        self.assertNotIn('recall_at_3',response.json())
        self.assertEqual(self.store.list_memories(self.alice)[0]['content'],{'statement':'synthetic corrected'})

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
