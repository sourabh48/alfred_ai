"""Synthetic multi-case retrieval quality, citation, privacy and revocation tests."""
import json
import time
from datetime import timedelta
from hashlib import sha256
from math import nan
from unittest.mock import patch

from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.ml_engine.services.persistent_memory import MemoryConflict, MemoryStore
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from tests import test_memory_learning as fixtures


def synthetic_embedding(text, *, deadline=None):
    text=text.lower()
    index=0 if 'mountain' in text or 'hiking' in text else 1 if 'coast' in text else 3 if 'bike' in text else 2
    return [int(i==index) for i in range(4)],'synthetic-evaluation-v1'


class MemoryEvaluationTests(TestCase):
    def setUp(self):
        fixtures.MemoryLearningTests.setUp(self)
        self.enterContext(patch.object(self.embedder,'embed',side_effect=synthetic_embedding))
        self.client.force_login(self.alice)

    def save(self,text,user=None):
        return self.store.save_verified(user or self.alice,{'statement':text},
            {'source':'Synthetic owner review'},verified=True)

    def post(self,cases,**changes):
        return self.client.post('/api/ai/memories/learning/',dict(action='evaluate',cases=cases,min_score=0.45)|changes,
            content_type='application/json')

    def test_corrections_conflicting_relevance_irrelevance_deletion_and_owner_isolation(self):
        original=self.save('SYNTHETIC-PRIVATE mountain old statement')
        current=self.learning.revise(self.alice,[original],{'statement':'SYNTHETIC-PRIVATE mountain corrected'},verified=True)
        coast=self.save('SYNTHETIC-PRIVATE I prefer the coast')
        contrary=self.save('SYNTHETIC-PRIVATE I dislike the coast')
        deleted=self.save('SYNTHETIC-PRIVATE bike record'); self.store.delete_memory(self.alice,deleted)
        foreign=self.save('SYNTHETIC-FOREIGN astronomy',self.bob)
        candidate=self.learning.extract(self.alice,'SYNTHETIC-HYPOTHESIS astronomy',{'source':'Synthetic AI hypothesis'})[0]
        cases=[dict(query='SYNTHETIC-QUERY mountain',expected_id=current),
            dict(query='SYNTHETIC-QUERY coast',expected_ids=[coast,contrary]),
            dict(query='SYNTHETIC-QUERY irrelevant astronomy',expected_ids=[]),
            dict(query='SYNTHETIC-QUERY deleted bike',expected_ids=[]),
            dict(query='SYNTHETIC-QUERY foreign astronomy',expected_ids=[])]
        before=self.store.list_memories(self.alice)
        with self.store._transaction() as db:
            events=db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        result=self.learning.evaluate(self.alice,cases,min_score=0.45)
        for key in ('precision','recall','recall_at_3','mean_reciprocal_rank','top_1_accuracy',
                'exact_match_rate','abstention_rate','citation_correctness'):
            self.assertEqual(result[key],1.0,key)
        self.assertEqual(result['false_positive_rate'],0)
        self.assertEqual(result['checked_citations'],3); self.assertEqual(result['positive_cases'],2)
        self.assertEqual(result['negative_cases'],3)
        self.assertEqual(result['precision_at_k'],{'1':1.0,'2':.75,'3':.5})
        self.assertEqual(result['recall_at_k'],{'1':.75,'2':1.0,'3':1.0})
        self.assertEqual(result['retrieval_errors'],dict(unexpected_references=0,missed_references=0,false_abstentions=0,false_matches=0))
        self.assertFalse(result['generated_hypotheses_are_facts'])
        context=result['retrieval_context']
        self.assertEqual(context['protocol'],'owner-cosine-top3-v1')
        self.assertEqual(context['indexed_memories'],3); self.assertEqual(context['dimensions'],4)
        self.assertEqual(context['embedding_identity'],sha256(b'synthetic-evaluation-v1').hexdigest())
        self.assertEqual(context['cohort_persistence'],'none')
        ids={cite['id'] for case in result['per_case'] for cite in case['citations']}
        self.assertEqual(ids,{current,coast,contrary})
        for identity in (original,deleted,foreign,candidate): self.assertNotIn(identity,json.dumps(result))
        for case in result['per_case']:
            for citation in case['citations']:
                self.assertEqual(citation['url'],f"/settings/#memory-{citation['id']}")
        self.assertEqual(self.store.list_memories(self.alice),before)
        with self.store._transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],events)
        for private in ('SYNTHETIC-PRIVATE','SYNTHETIC-QUERY','SYNTHETIC-FOREIGN','SYNTHETIC-HYPOTHESIS'):
            self.assertNotIn(private,json.dumps(result))
        for path in self.root.rglob('*'):
            if path.is_file(): self.assertNotIn(b'SYNTHETIC-QUERY',path.read_bytes())

    def test_precision_recall_ranking_and_false_positive_metrics_are_not_always_perfect(self):
        identities=[self.save(text) for text in ('mountain','coast','bike','astronomy')]
        cases=[dict(query='SYNTHETIC-QUERY positive',expected_ids=[identities[0],identities[2],identities[3]]),
            dict(query='SYNTHETIC-QUERY negative',expected_ids=[])]
        with patch.object(self.store,'retrieve',side_effect=[
                [dict(id=identity,score=1-i*.1) for i,identity in enumerate(identities[:3])],
                [dict(id=identities[1],score=.8)]]):
            result=self.learning.evaluate(self.alice,cases,min_score=.45)
        self.assertEqual(result['precision'],.5); self.assertAlmostEqual(result['recall'],2/3)
        self.assertAlmostEqual(result['recall_at_3'],2/3)
        self.assertEqual(result['false_positive_rate'],1); self.assertEqual(result['abstention_rate'],0)
        self.assertEqual(result['exact_match_rate'],0); self.assertEqual(result['mean_reciprocal_rank'],1)
        self.assertEqual(result['per_case'][0]['missed'],1); self.assertEqual(result['per_case'][0]['irrelevant'],1)
        self.assertEqual(result['per_case'][1]['precision'],0); self.assertIsNone(result['per_case'][1]['recall'])

    def test_empty_vault_has_no_vacuous_precision_or_citation_accuracy(self):
        result=self.learning.evaluate(self.alice,[dict(query='Synthetic absent',expected_ids=[])])
        for key in ('precision','recall','recall_at_3','citation_correctness','top_1_accuracy'):
            self.assertIsNone(result[key],key)
        self.assertEqual(result['abstention_rate'],1); self.assertEqual(result['checked_citations'],0)
        self.assertEqual(result['exact_match_rate'],1)
        self.assertIsNone(result['retrieval_context']['embedding_identity'])
        self.assertIsNone(result['retrieval_context']['dimensions'])
        self.assertEqual(result['retrieval_context']['indexed_memories'],0)
        self.assertTrue(all(band['returned']==0 and band['observed_precision'] is None
            for band in result['score_diagnostics']['bands']))

    def test_score_bands_measure_reviewed_relevance_without_claiming_probabilities(self):
        identities=[self.save('mountain source '+str(i)) for i in range(6)]
        rows=[dict(id=identity,score=score) for identity,score in zip(identities,(-.5,.49,.5,.75,.9,1))]
        cases=[dict(query='SYNTHETIC-QUERY first',expected_ids=[identities[0],identities[2]]),
            dict(query='SYNTHETIC-QUERY second',expected_ids=[identities[4]])]
        before=self.store.list_memories(self.alice)
        with patch.object(self.store,'retrieve',side_effect=[list(reversed(rows[:3])),list(reversed(rows[3:]))]):
            result=self.learning.evaluate(self.alice,cases,min_score=-1)
        diagnostics=result['score_diagnostics']
        self.assertFalse(diagnostics['score_is_probability'])
        self.assertFalse(diagnostics['automatic_threshold_change'])
        self.assertEqual(diagnostics['scope'],'reviewed_cases_in_this_run_only')
        self.assertEqual([(b['returned'],b['relevant'],b['observed_precision']) for b in diagnostics['bands']],
            [(2,1,.5),(1,1,1),(1,0,0),(2,1,.5)])
        self.assertEqual(sum(b['returned'] for b in diagnostics['bands']),result['checked_citations'])
        self.assertEqual(self.store.list_memories(self.alice),before)
        self.assertNotIn('SYNTHETIC-QUERY',json.dumps(diagnostics))

    def test_indexed_profile_excludes_foreign_models_and_does_not_expose_model_strings_or_vectors(self):
        owned=self.save('mountain')
        private_label='SYNTHETIC-PRIVATE-model-identity'
        with patch.object(self.embedder,'embed',return_value=([1,2,3],private_label)):
            self.save('astronomy',self.bob)
        result=self.learning.evaluate(self.alice,[dict(query='mountain',expected_ids=[owned])])
        context=result['retrieval_context']
        self.assertEqual(context['indexed_memories'],1); self.assertEqual(context['dimensions'],4)
        self.assertNotIn(private_label,json.dumps(result)); self.assertNotIn('embedding_model',json.dumps(result))
        self.assertNotIn('embedding',context)
        foreign=self.store.retrieval_profile(self.bob)
        self.assertEqual(foreign['embedding_identity'],sha256(private_label.encode()).hexdigest())
        self.assertEqual(foreign['dimensions'],3)

    def test_changed_index_model_profile_discards_the_entire_report(self):
        owned=self.save('mountain'); before=self.store.retrieval_profile(self.alice)
        with patch.object(self.store,'retrieval_profile',side_effect=[before,before|{'dimensions':3}]),self.assertRaises(MemoryConflict):
            self.learning.evaluate(self.alice,[dict(query='mountain',expected_ids=[owned])])

    def test_mixed_indexed_models_fail_before_query_embedding_without_disclosing_identifiers(self):
        owned=self.save('mountain')
        with patch.object(self.embedder,'embed',return_value=([1,2,3],'SYNTHETIC-PRIVATE-different-model')):
            self.save('coast')
        with patch.object(MemoryStore,'retrieve',side_effect=AssertionError('Mixed index must not infer')) as retrieve:
            response=self.post([dict(query='mountain',expected_ids=[owned])])
        self.assertEqual(response.status_code,503); retrieve.assert_not_called()
        self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
        self.assertNotIn('retrieval_context',response.json())

    def test_legacy_single_expected_id_and_new_labels_have_identical_metrics(self):
        identity=self.save('mountain')
        old=self.learning.evaluate(self.alice,[dict(query='mountain',expected_id=identity)])
        new=self.learning.evaluate(self.alice,[dict(query='mountain',expected_ids=[identity])])
        self.assertEqual(old,new)

    def test_malformed_foreign_deleted_and_over_budget_cases_fail_before_embedding(self):
        owned=self.save('mountain'); foreign=self.save('coast',self.bob)
        deleted=self.save('bike'); self.store.delete_memory(self.alice,deleted)
        invalid=[[],[dict(query='mountain',expected_ids=[owned])]*21,
            [dict(query='x'*8193,expected_ids=[])],
            [dict(query='x'*4096,expected_ids=[]),dict(query='x'*4097,expected_ids=[])],
            [dict(query='mountain',expected_ids=[owned,owned])],
            [dict(query='mountain',expected_ids=[foreign])],[dict(query='bike',expected_ids=[deleted])],
            [dict(query='mountain',expected_ids=True)],[dict(query='mountain',expected_ids=[None])],
            [dict(query='mountain',expected_ids=[],expected_id=None)],
            [dict(query='mountain',expected_ids=[],owner=self.alice.pk)]]
        with patch.object(self.store,'retrieve',side_effect=AssertionError('Invalid cases must not retrieve')):
            for cases in invalid:
                with self.subTest(index=invalid.index(cases)),self.assertRaises(ValueError): self.learning.evaluate(self.alice,cases)
            for score in (True,nan,float('inf'),-2,2,'0.5'):
                with self.subTest(score_type=type(score).__name__),self.assertRaises(ValueError):
                    self.learning.evaluate(self.alice,[dict(query='mountain',expected_ids=[owned])],min_score=score)

    def test_foreign_duplicate_nonfinite_and_stale_retrievals_are_rejected_without_leaking_results(self):
        owned=self.save('mountain'); foreign=self.save('SYNTHETIC-FOREIGN coast',self.bob)
        for rows in ([dict(id=foreign,score=1)], [dict(id=owned,score=1)]*2,
                [dict(id=owned,score=nan)], [dict(id=owned,score=True)],
                [dict(id=owned,score=.9,content={'statement':'SYNTHETIC-STALE'})]):
            with self.subTest(index=len(rows)),patch.object(MemoryStore,'retrieve',return_value=rows):
                response=self.post([dict(query='SYNTHETIC-QUERY mountain',expected_ids=[owned])])
                self.assertEqual(response.status_code,409)
                for private in (foreign,owned,'SYNTHETIC-QUERY','SYNTHETIC-FOREIGN','SYNTHETIC-STALE','per_case'):
                    self.assertNotIn(private,response.content.decode())

    def test_deleted_or_corrected_source_during_any_case_invalidates_the_whole_report(self):
        owned=self.save('mountain'); retrieve=self.store.retrieve
        def deleting(user,query,**kwargs):
            rows=retrieve(user,query,**kwargs); self.store.delete_memory(user,owned); return rows
        with patch.object(MemoryStore,'retrieve',side_effect=deleting):
            response=self.post([dict(query='mountain',expected_ids=[owned]),dict(query='coast',expected_ids=[])])
        self.assertEqual(response.status_code,409); self.assertNotIn('per_case',response.json())
        self.assertEqual(self.store.restore_owner(self.alice),0)

    def test_same_id_payload_change_cannot_pass_snapshot_revalidation(self):
        owned=self.save('mountain'); initial=self.store.list_memories(self.alice)
        changed=[initial[0]|{'provenance':{'source':'Synthetic changed source'}}]
        with patch.object(self.store,'list_memories',side_effect=[initial,changed]),self.assertRaises(MemoryConflict):
            self.learning.evaluate(self.alice,[dict(query='mountain',expected_ids=[owned])])

    def test_one_shared_budget_stops_late_results_and_all_later_queries(self):
        clock=[100.0]; deadlines=[]
        def slow(user,query,**kwargs):
            deadlines.append(kwargs['deadline']); clock[0]+=61; return []
        with patch('apps.ml_engine.services.memory_learning.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.store,'retrieve',side_effect=slow) as retrieve:
            with self.assertRaises(EmbeddingUnavailable):
                self.learning.evaluate(self.alice,[dict(query='synthetic first',expected_ids=[]),dict(query='synthetic second',expected_ids=[])])
        self.assertEqual(deadlines,[160.0]); self.assertEqual(retrieve.call_count,1)

    def test_every_query_receives_the_same_deadline(self):
        with patch.object(self.store,'retrieve',return_value=[]) as retrieve:
            result=self.learning.evaluate(self.alice,[dict(query='synthetic first',expected_ids=[]),dict(query='synthetic second',expected_ids=[])])
        self.assertEqual(retrieve.call_count,2)
        self.assertEqual(retrieve.call_args_list[0].kwargs['deadline'],retrieve.call_args_list[1].kwargs['deadline'])
        self.assertEqual(result['processing_budget_seconds'],60)

    def test_retrieval_rejects_invalid_deadline_and_discards_an_overdue_embedding(self):
        self.save('mountain')
        for deadline in (True,nan,float('inf'),'later'):
            with self.assertRaises(ValueError): self.store.retrieve(self.alice,'mountain',deadline=deadline)
        with patch.object(self.embedder,'embed') as embed,self.assertRaises(EmbeddingUnavailable):
            self.store.retrieve(self.alice,'mountain',deadline=time.monotonic()-1)
        embed.assert_not_called()
        clock=[100.0]
        def slow(text,**kwargs): clock[0]=161.0; return synthetic_embedding(text)
        with patch('apps.ml_engine.services.persistent_memory.time.monotonic',side_effect=lambda:clock[0]),patch.object(self.embedder,'embed',side_effect=slow):
            with self.assertRaises(EmbeddingUnavailable): self.store.retrieve(self.alice,'mountain',deadline=160.0)

    def test_evaluation_is_owner_session_csrf_no_store_and_does_not_invoke_cloud_or_training(self):
        owned=self.save('mountain'); cases=[dict(query='mountain',expected_ids=[owned])]
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.alice)
        self.assertEqual(csrf.post('/api/ai/memories/learning/',dict(action='evaluate',cases=cases),content_type='application/json').status_code,403)
        self.client.force_login(self.bob); self.assertEqual(self.post(cases).status_code,400)
        self.client.logout(); self.assertIn(self.post(cases).status_code,(401,403))
        self.client.force_login(self.alice)
        with patch('apps.ml_engine.services.memory_reasoning.reasoning_provider',side_effect=AssertionError('No cloud')):
            response=self.post(cases)
        self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response.json()['privacy'],'owner_only_local')

    def test_logout_during_evaluation_discards_results_and_cannot_revive_session(self):
        owned=self.save('mountain'); session=self.client.session.session_key; retrieve=MemoryStore.retrieve
        def logging_out(store,user,query,**kwargs):
            result=retrieve(store,user,query,**kwargs); Session.objects.filter(session_key=session).delete(); return result
        with patch.object(MemoryStore,'retrieve',autospec=True,side_effect=logging_out):
            response=self.post([dict(query='SYNTHETIC-QUERY mountain',expected_ids=[owned])])
        self.assertEqual(response.status_code,403)
        self.assertNotIn(owned,response.content.decode()); self.assertNotIn('per_case',response.json())
        self.assertFalse(Session.objects.filter(session_key=session).exists())

    @override_settings(SESSION_SAVE_EVERY_REQUEST=True)
    def test_failed_evaluation_cannot_refresh_a_session_that_expired_during_retrieval(self):
        owned=self.save('mountain'); session=self.client.session.session_key
        def expire_and_conflict(*args,**kwargs):
            Session.objects.filter(session_key=session).update(expire_date=timezone.now()-timedelta(seconds=1))
            raise MemoryConflict('Synthetic concurrent correction')
        with patch.object(MemoryStore,'retrieve',side_effect=expire_and_conflict):
            response=self.post([dict(query='SYNTHETIC-QUERY mountain',expected_ids=[owned])])
        self.assertEqual(response.status_code,403)
        self.assertNotIn(owned,response.content.decode()); self.assertNotIn('per_case',response.json())
        self.assertFalse(Session.objects.filter(session_key=session).exists())

    def test_evaluation_preserves_canonical_financial_rows_fingerprints_and_decimal_baseline(self):
        from django.contrib.auth import get_user_model
        from apps.expenses.models import Expense, BankAccount
        from apps.budgets.models import Budget
        from apps.loans.models import Loan, LoanPaymentHistory
        from apps.investments.models import Investment
        from apps.family.models import FamilyAccountLink
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        from tests.user_acceptance_scenario import seed_acceptance_user
        self.client.logout(); owner=seed_acceptance_user(self.client)['user']
        identity=self.save('synthetic mountain preference',owner)
        models=(get_user_model(),BankAccount,Expense,Budget,Loan,LoanPaymentHistory,Investment,FamilyAccountLink)
        snapshot=lambda:[list(model.objects.order_by('pk').values()) for model in models]
        before=snapshot(); baseline=resolve_canonical_financial_baseline(owner,fresh=True)['decimal_amounts']
        self.learning.evaluate(owner,[dict(query='mountain',expected_ids=[identity]),dict(query='astronomy',expected_ids=[])],min_score=.45)
        self.assertEqual(snapshot(),before)
        self.assertEqual(resolve_canonical_financial_baseline(owner,fresh=True)['decimal_amounts'],baseline)
