"""Whole retained extraction is supplied completely or refused, never silently trimmed."""
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.ml_engine.services.canonical_evidence import SourceSelectionConflict
from apps.ml_engine.services.document_questions import answer_question
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from tests import test_document_corpus as fixtures


class DocumentFullContextTests(TestCase):
    make_document = fixtures.DocumentCorpusTests.make_document

    def setUp(self):
        fixtures.DocumentCorpusTests.setUp(self)
        self.local = Mock(select=Mock(return_value='{"state":"evidence","evidence":[0]}'))

    def save_text(self, text, *, user=None, name='Synthetic retained text.txt'):
        return self.corpus.upload(user or self.owner,
            SimpleUploadedFile(name, text.encode(), content_type='text/plain'),
            consent=True, days=1)['document']['id']

    def ask(self, ids, question='What does the selected document state?', **changes):
        return answer_question(self.corpus, self.owner, ids, question,
            local=self.local, context_mode='full_extraction', **changes)

    def test_complete_text_including_late_qualification_and_exact_ranges(self):
        text = 'Exit load applies for thirty days. ' + 'Administrative context only. ' * 24 + '\nException: the period is ninety days.'
        identity = self.save_text(text)
        keyword_hits = self.corpus.search(self.owner, [identity], 'exit load')['results']
        self.assertNotIn('ninety days', ' '.join(hit['excerpt'] for hit in keyword_hits))
        self.local.select.return_value = '{"state":"conflict","evidence":[0,1]}'
        result = self.ask([identity])
        self.assertEqual(result['status'], 'conflicting_evidence')
        self.assertTrue(result['context_complete'])
        self.assertEqual(result['context_mode'], 'full_extraction')
        self.assertFalse(result['financial_authority'])
        self.assertFalse(result['full_text_qa'])  # Arbitrary original PDF/OCR comprehension is not established.
        covered = set()
        for hit in result['results']:
            self.assertEqual(hit['id'], identity)
            self.assertEqual(hit['excerpt'], text[hit['start']:hit['end']])
            covered.update(range(hit['start'], hit['end']))
        self.assertEqual(covered, set(range(len(text))))
        payload = self.local.select.call_args.args[0]
        self.assertIn('ninety days', json.dumps(payload))
        self.assertEqual(set(payload), {'question', 'passages'})
        self.assertNotIn(identity, json.dumps(payload))
        self.assertNotIn('source_url', json.dumps(payload))
        self.embedder.embed.assert_not_called()
        with self.store._transaction() as db:
            for table in ('memories', 'events', 'conversations', 'memory_sync'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)

    def test_every_selected_document_is_supplied_and_partial_selection_is_rejected(self):
        ids = [self.save_text('Deposit date: 2026-09-01.'), self.save_text('Account status: open.')]
        self.local.select.return_value = '{"state":"evidence","evidence":[0,1]}'
        result = self.ask(ids)
        self.assertEqual({hit['id'] for hit in result['results']}, set(ids))
        self.assertEqual([hit['document'] for hit in self.local.select.call_args.args[0]['passages']], [0, 1])
        self.local.select.return_value = '{"state":"evidence","evidence":[0]}'
        result = self.ask(ids)
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['results'], [])
        self.assertTrue(result['context_complete'])

    def test_pdf_whole_context_retains_text_layer_provenance_and_original(self):
        from hashlib import sha256
        from tests.test_document_knowledge import text_pdf
        raw = text_pdf()
        source = self.corpus.upload(self.owner, SimpleUploadedFile('Synthetic full context.pdf', raw),
            consent=True, days=1)['document']
        result = self.ask([source['id']], 'What does the policy say about maintenance?')
        self.assertTrue(result['context_complete'])
        hit = result['results'][0]
        self.assertEqual(hit['text_origin'], 'uploaded_pdf_text_layer')
        self.assertIn('Annual maintenance waiver applies.', hit['excerpt'])
        self.assertEqual(hit['source_fingerprint'], sha256(raw).hexdigest())
        self.assertEqual(self.corpus.original(self.owner, source['id'])[1], raw)

    def test_passage_and_utf8_request_limits_refuse_before_any_inference(self):
        for text in ('Retained context. ' * 300, 'गग ' * 700):
            with self.subTest(kind='unicode' if 'ग' in text else 'passages'):
                identity = self.save_text(text)
                result = self.ask([identity])
                self.assertEqual(result['status'], 'context_limit')
                self.assertFalse(result['context_complete'])
                self.assertEqual(result['results'], [])
                self.assertIn('No partial context', result['answer'])
        self.local.select.assert_not_called()

    def test_mode_and_keyword_ambiguity_are_rejected_before_private_reads(self):
        with patch.object(self.corpus, 'search') as search:
            for mode in (None, [], {}, True, 'all', 'full'):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    answer_question(self.corpus, self.owner, [], 'Synthetic question', context_mode=mode)
            with self.assertRaises(ValueError):
                self.ask([], keywords='ignored search terms')
            search.assert_not_called()
        self.local.select.assert_not_called()

    def test_foreign_missing_mixed_and_expired_selections_never_reach_model(self):
        own = self.save_text('Owned synthetic text.')
        foreign = self.save_text('FOREIGN-PRIVATE-TEXT', user=self.other)
        for ids in ([foreign], [own, foreign], ['a' * 32]):
            with self.subTest(ids=ids), self.assertRaises(SourceSelectionConflict):
                self.ask(ids)
        with patch('apps.ml_engine.services.document_corpus.timezone.now',
                return_value=timezone.now() + timedelta(days=2)):
            with self.assertRaises(SourceSelectionConflict):
                self.ask([own])
        self.local.select.assert_not_called()

    def test_changes_outside_selected_quote_still_invalidate_complete_context(self):
        self.document.extracted_text = 'Exit load: thirty days. ' + 'Context. ' * 90
        self.document.save()
        identity = fixtures.DocumentCorpusTests.ingest(self)['document']['id']
        def change(*args, **kwargs):
            self.document.extracted_text += ' Later correction: ninety days.'
            self.document.save()
            return '{"state":"evidence","evidence":[0]}'
        self.local.select.side_effect = change
        with self.assertRaises(SourceSelectionConflict):
            self.ask([identity])

    def test_delete_or_reset_during_inference_rejects_source(self):
        for action in ('delete', 'reset'):
            with self.subTest(action=action):
                identity = self.save_text('Synthetic context.')
                def revoke(*args, **kwargs):
                    if action == 'delete':
                        self.corpus.delete(self.owner, identity)
                    else:
                        self.store.reset_owner(self.owner)
                    return '{"state":"evidence","evidence":[0]}'
                self.local.select.side_effect = revoke
                with self.assertRaises(SourceSelectionConflict):
                    self.ask([identity])

    def test_invalid_or_abstaining_model_output_does_not_become_an_answer(self):
        identity = self.save_text('No penalty amount is specified.')
        for raw in ('{"state":"insufficient","evidence":[]}',
                '{"state":"evidence","evidence":[6]}',
                '{"state":"evidence","evidence":[true]}',
                '{"state":"evidence","evidence":[0],"answer":"invented"}', 'not JSON'):
            with self.subTest(raw=raw):
                self.local.select.return_value = raw
                result = self.ask([identity], 'Calculate the prepayment penalty.')
                self.assertEqual(result['status'], 'insufficient_evidence')
                self.assertEqual(result['results'], [])
                self.assertFalse(result['financial_authority'])
                self.assertNotIn('invented', result['answer'])

    def test_unavailable_or_late_model_never_falls_back(self):
        identity = self.save_text('Owned synthetic text.')
        self.local.select.side_effect = EmbeddingUnavailable('Synthetic local outage')
        with self.assertRaises(EmbeddingUnavailable):
            self.ask([identity])
        self.local.select.side_effect = None
        with patch('apps.ml_engine.services.document_questions.time.monotonic', side_effect=[10, 40]):
            with self.assertRaises(EmbeddingUnavailable):
                self.ask([identity])

    def test_owner_api_requires_session_csrf_and_explicit_mode_with_no_url_data(self):
        identity = self.save_text('Deposit date: 2026-09-01.')
        url = '/api/ai/document-corpus/question/'
        body = dict(ids=[identity], question='What is the deposit date?', context_mode='full_extraction')
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(url, body, content_type='application/json').status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post(url, body, content_type='application/json').status_code, 403)
        client.get('/documents/'); csrf = client.cookies['csrftoken'].value
        with patch('apps.ml_engine.services.document_questions.DocumentQuestionReasoner', return_value=self.local):
            response = client.post(url, body, content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['context_complete'])
            self.assertEqual(response['Cache-Control'], 'no-store, private')
            for wrong in (dict(body, context_mode=[]), dict(body, owner=self.other.pk), dict(body, keywords='deposit')):
                self.assertEqual(client.post(url, wrong, content_type='application/json', HTTP_X_CSRFTOKEN=csrf).status_code, 400)
            self.assertEqual(client.post(url + '?question=private', body, content_type='application/json', HTTP_X_CSRFTOKEN=csrf).status_code, 400)
            self.assertEqual(client.get(url).status_code, 405)
