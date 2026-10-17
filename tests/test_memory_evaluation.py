"""Synthetic multi-case retrieval quality, citation, privacy and revocation tests."""
import json
from math import nan
from unittest.mock import patch

from django.contrib.sessions.models import Session
from django.test import Client, TestCase

from apps.ml_engine.services.persistent_memory import MemoryConflict, MemoryStore
from tests import test_memory_learning as fixtures


def synthetic_embedding(text):
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
        self.assertFalse(result['generated_hypotheses_are_facts'])
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
