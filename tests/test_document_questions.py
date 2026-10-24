"""Synthetic selected-corpus questions; models may select evidence, never author claims."""
import json
from unittest.mock import Mock, patch

from django.test import Client, TestCase

from apps.ml_engine.services.canonical_evidence import SourceSelectionConflict, document_record_page
from apps.ml_engine.services.document_questions import answer_question, DocumentQuestionReasoner, SCHEMA
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from tests import test_document_corpus as fixtures


class DocumentQuestionTests(TestCase):
    make_document = fixtures.DocumentCorpusTests.make_document

    def setUp(self):
        fixtures.DocumentCorpusTests.setUp(self)
        self.identity = self.corpus.ingest(self.owner, 'investment', self.document.pk,
            catalog_token=document_record_page(self.owner,'investment',self.document.pk)['catalog_token'],consent=True,days=7)['document']['id']
        self.local = Mock(select=Mock(return_value='{"state":"evidence","evidence":[0]}'))

    def ask(self, identities=None, question='What is the exit load period?', keywords='exit load'):
        return answer_question(self.corpus,self.owner,identities or [self.identity],question,keywords,local=self.local)

    def test_answer_is_exact_selected_source_text_not_model_prose_or_financial_authority(self):
        before = list(type(self.investment).objects.values())
        result = self.ask()
        self.assertEqual(result['status'],'excerpt_evidence'); self.assertFalse(result['financial_authority'])
        self.assertEqual(result['results'][0]['excerpt'],self.document.extracted_text)
        self.assertEqual(result['results'][0]['id'],self.identity)
        self.assertNotIn('LOCAL-CORPUS-SECRET',result['answer'])
        payload = self.local.select.call_args.args[0]
        self.assertEqual(set(payload),{'question','passages'})
        self.assertNotIn('source_url',json.dumps(payload)); self.assertNotIn(self.identity,json.dumps(payload))
        self.assertEqual(list(type(self.investment).objects.values()),before)
        with self.store._transaction() as db:
            for table in ('memories','events','conversations','memory_sync'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.embedder.embed.assert_not_called()

    def test_missing_or_broad_evidence_abstains_before_model(self):
        self.assertEqual(self.ask(keywords='missing keywords')['status'],'insufficient_evidence')
        with patch.object(self.corpus,'search',return_value={'results':[], 'more_matches':True,
                'checked_at':'synthetic','result_limit':6}):
            self.assertEqual(self.ask()['status'],'insufficient_evidence')
        self.local.select.assert_not_called()

    def test_invalid_output_cannot_introduce_claims_citations_or_partial_source_answers(self):
        for raw in ('{"state":"evidence","evidence":[99]}','{"state":"evidence","evidence":[true]}',
                '{"state":"evidence","evidence":[0,0]}','{"state":"evidence","evidence":[]}',
                '{"state":"insufficient","evidence":[0]}','{"state":"conflict","evidence":[0]}',
                '{"state":"evidence","state":"conflict","evidence":[0]}',
                '{"state":"evidence","evidence":[0],"answer":"Fabricated balance 99999"}',
                '```json\n{"state":"evidence","evidence":[0]}\n```', 'null', '[]', 'not JSON'):
            with self.subTest(raw=raw):
                self.local.select.return_value=raw
                result=self.ask()
                self.assertEqual(result['status'],'insufficient_evidence'); self.assertEqual(result['results'],[])
                self.assertNotIn('99999',str(result))

    def test_explicit_abstention_and_conflict_never_claim_reconciliation(self):
        self.local.select.return_value='{"state":"insufficient","evidence":[]}'
        self.assertEqual(self.ask()['results'],[])
        other = fixtures.DocumentCorpusTests.make_document(self,text='Exit load applies for ninety days; not thirty.')
        second = fixtures.DocumentCorpusTests.ingest(self,other)['document']['id']
        self.local.select.return_value='{"state":"conflict","evidence":[0,1]}'
        result = self.ask([self.identity,second])
        self.assertEqual(result['status'],'conflicting_evidence')
        self.assertEqual({hit['id'] for hit in result['results']},{self.identity,second})
        self.assertIn('No financial conclusion',result['answer'])
        self.local.select.return_value='{"state":"evidence","evidence":[0]}'
        self.assertEqual(self.ask([self.identity,second])['status'],'insufficient_evidence')

    def test_foreign_missing_and_mixed_selection_never_reaches_model(self):
        foreign = fixtures.DocumentCorpusTests.make_document(self,self.other)
        identity = fixtures.DocumentCorpusTests.ingest(self,foreign,self.other)['document']['id']
        for identities in ([identity],[self.identity,identity],['a'*32]):
            with self.subTest(ids=identities), self.assertRaises(SourceSelectionConflict): self.ask(identities)
        self.local.select.assert_not_called()

    def test_correction_deletion_and_reset_during_inference_reject_the_answer(self):
        def change(*args,**kwargs):
            self.document.extracted_text='Corrected extraction'; self.document.save()
            return '{"state":"evidence","evidence":[0]}'
        self.local.select.side_effect=change
        with self.assertRaises(SourceSelectionConflict): self.ask()
        self.document.extracted_text='Exit load applies.'; self.document.save()
        self.identity = fixtures.DocumentCorpusTests.ingest(self)['document']['id']
        def reset(*args,**kwargs):
            self.store.reset_owner(self.owner)
            return '{"state":"evidence","evidence":[0]}'
        self.local.select.side_effect=reset
        with self.assertRaises(SourceSelectionConflict): self.ask()

    def test_expired_model_deadline_and_unavailable_model_do_not_fallback(self):
        self.local.select.side_effect=EmbeddingUnavailable('synthetic local failure')
        with self.assertRaises(EmbeddingUnavailable): self.ask()
        self.local.select.side_effect=None
        with patch('apps.ml_engine.services.document_questions.time.monotonic',side_effect=[10,40]):
            with self.assertRaises(EmbeddingUnavailable): self.ask()

    def test_question_bounds_and_post_only_session_csrf_contract(self):
        for question in ('', 'x'*513, 'x\nprivate', 3):
            with self.assertRaises(ValueError): self.ask(question=question)
        url='/api/ai/document-corpus/question/'
        body=dict(ids=[self.identity],question='What is the exit load period?',keywords='exit load')
        self.assertEqual(Client().post(url,body,content_type='application/json').status_code,403)
        client=Client(enforce_csrf_checks=True); client.force_login(self.owner)
        self.assertEqual(client.post(url,body,content_type='application/json').status_code,403)
        client.get('/documents/'); token=client.cookies['csrftoken'].value
        with patch('apps.ml_engine.services.document_questions.DocumentQuestionReasoner',return_value=self.local):
            response=client.post(url,body,content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        self.assertEqual(client.post(url+'?question=private',body,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,400)
        self.assertEqual(client.get(url).status_code,405)

    def test_local_adapter_uses_fixed_runtime_structured_output_and_strict_completion(self):
        reasoner=DocumentQuestionReasoner()
        valid=dict(model=reasoner.model,done=True,done_reason='stop',message=dict(role='assistant',content='{"state":"insufficient","evidence":[]}'))
        with patch.object(reasoner,'_digest',return_value='a'*64), patch.object(reasoner,'_request',return_value=valid) as request:
            self.assertTrue(reasoner.select({'question':'synthetic','passages':[]},deadline=123))
        body=request.call_args.args[2]
        self.assertIn(json.dumps(SCHEMA,separators=(',',':')),body['messages'][0]['content'])
        self.assertEqual(body['format'],SCHEMA); self.assertEqual(body['keep_alive'],'0'); self.assertFalse(body['think'])
        self.assertEqual(body['model'],reasoner.model); self.assertEqual(request.call_args.kwargs['deadline'],123)
        for change in ({'done_reason':'length'},{'done':False},{'model':'different'},
                {'message':dict(role='assistant',content='{}',tool_calls=[{}])}):
            with patch.object(reasoner,'_digest',return_value='a'*64), patch.object(reasoner,'_request',return_value=valid|change):
                with self.assertRaises(EmbeddingUnavailable): reasoner.select({'question':'synthetic','passages':[]},deadline=123)
        with patch.object(reasoner,'_digest',side_effect=['a'*64,'b'*64]), patch.object(reasoner,'_request',return_value=valid):
            with self.assertRaises(EmbeddingUnavailable): reasoner.select({'question':'synthetic','passages':[]},deadline=123)
