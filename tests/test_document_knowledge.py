"""Synthetic selected-text retrieval; no new memory, model, provider or money writes."""
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.investments.models import InvestmentImportDocument
from apps.loans.models import LoanImportDocument
from apps.ml_engine.services.canonical_evidence import document_record_page, SourceSelectionConflict
from apps.ml_engine.services import document_knowledge as knowledge
from tests import test_canonical_evidence as fixtures


class DocumentKnowledgeTests(TestCase):
    def setUp(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.document = InvestmentImportDocument.objects.create(user=self.owner, file_name='Synthetic.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf', b'%PDF synthetic retained original'), parser_status='parsed',
            extracted_text='Synthetic prospectus. Exit load applies for thirty days.\nPast returns are not guaranteed.')
        self.document.linked_investments.add(self.investment)
        self.token = self.page()['catalog_token']
        self.url = f'/api/ai/financial-documents/investment/{self.document.pk}/search/'

    def page(self):
        return document_record_page(self.owner, 'investment', self.document.pk)

    def search(self, query='exit load', token=None):
        return knowledge.search_document(self.owner, 'investment', self.document.pk,
            query=query, catalog_token=self.token if token is None else token)

    def post(self, **changes):
        return self.client.post(self.url, dict(query='exit load', catalog_token=self.token) | changes,
            content_type='application/json')

    def test_exact_excerpt_offsets_source_and_no_money_or_memory_mutation(self):
        before = list(type(self.investment).objects.values())
        with patch('apps.ml_engine.services.persistent_memory.MemoryStore', side_effect=AssertionError('No new memory')):
            result = self.search('EXIT load')
        self.assertEqual(result['status'], 'searched')
        self.assertEqual(len(result['results']), 1)
        hit = result['results'][0]
        self.assertEqual(hit['excerpt'], self.document.extracted_text[hit['start']:hit['end']])
        self.assertIn('unverified', result['limitation'])
        self.assertFalse(result['full_text_qa']); self.assertFalse(result['financial_authority'])
        response = self.client.get(result['source_url'])
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(list(type(self.investment).objects.values()), before)
        self.document.refresh_from_db()
        self.assertEqual(self.document.extracted_payload, {})

    def test_whole_word_and_all_keywords_required_without_claiming_absence(self):
        self.assertEqual(self.search('return')['results'], [])
        self.assertEqual(self.search('load missing')['results'], [])
        self.assertEqual(len(self.search('returns guaranteed')['results']), 1)

    def test_text_bound_result_bound_and_overlap_are_explicit(self):
        self.document.extracted_text = ('x ' * 248 + 'exit load ' + 'x ' * 200 + '\n') * 15
        self.document.save(); token = self.page()['catalog_token']
        result = self.search(token=token)
        self.assertEqual(len(result['results']), knowledge.RESULT_LIMIT)
        self.assertTrue(result['more_matches'])
        self.assertTrue(all(len(hit['excerpt']) <= knowledge.PASSAGE_CHARS for hit in result['results']))
        self.document.extracted_text = 'x' * (knowledge.TEXT_BYTES + 1)
        self.document.save()
        self.assertEqual(self.search(token=self.page()['catalog_token'])['status'], 'extraction_limit')

    def test_unicode_and_passage_boundary_do_not_invent_partial_word_matches(self):
        self.document.extracted_text = 'x' * 499 + 'noload café Straße'
        self.document.save(); token = self.page()['catalog_token']
        self.assertEqual(self.search('load', token)['results'], [])
        self.assertEqual(len(self.search('CAFÉ STRASSE', token)['results']), 1)

    def test_missing_failed_or_removed_extraction_abstains(self):
        for text, state in (('', 'parsed'), ('exit load', 'failed')):
            self.document.extracted_text = text; self.document.parser_status = state; self.document.save()
            self.assertEqual(self.search(token=self.page()['catalog_token'])['status'], 'extraction_unavailable')
        self.document.uploaded_file.delete(save=True)
        self.assertEqual(self.search(token=self.page()['catalog_token'])['status'], 'source_unavailable')

    def test_extraction_source_link_or_name_change_requires_reselection(self):
        for field, value in (('extracted_text', 'Changed private text'), ('file_name', 'Changed.pdf'), ('parser_status', 'failed')):
            setattr(self.document, field, value); self.document.save()
            with self.assertRaises(SourceSelectionConflict): self.search()
            self.token = self.page()['catalog_token']
        self.document.linked_investments.clear()
        with self.assertRaises(SourceSelectionConflict): self.search()

    def test_source_file_change_and_post_search_race_fail_closed(self):
        self.document.uploaded_file.save('changed.pdf', SimpleUploadedFile('changed.pdf', b'changed synthetic bytes'))
        with self.assertRaises(SourceSelectionConflict): self.search()
        self.token = self.page()['catalog_token']
        original = knowledge._passages
        def changed(text):
            yield from original(text)
            InvestmentImportDocument.objects.filter(pk=self.document.pk).update(extracted_text='Changed mid-search')
        with patch.object(knowledge, '_passages', changed), self.assertRaises(SourceSelectionConflict): self.search()

    def test_owner_and_mixed_owner_links_never_return_text(self):
        self.client.force_login(self.other)
        self.assertEqual(self.post().status_code, 404)

    def test_only_selected_document_is_searched_and_tokens_cannot_cross_documents(self):
        other = InvestmentImportDocument.objects.create(user=self.owner, file_name='Another synthetic.pdf',
            uploaded_file=SimpleUploadedFile('other.pdf', b'%PDF other synthetic'), parser_status='parsed',
            extracted_text='Private unrelated redemption penalty clause.')
        self.assertEqual(self.search('redemption penalty')['results'], [])
        token = document_record_page(self.owner, 'investment', other.pk)['catalog_token']
        self.assertEqual(self.post(catalog_token=token).status_code, 404)
        self.assertFalse((self.root/'unused-vault').exists())
        self.client.force_login(self.owner)
        type(self.investment).objects.filter(pk=self.investment.pk).update(user=self.other)
        self.assertEqual(self.post().status_code, 404)

    def test_session_csrf_post_only_payload_and_no_store_contract(self):
        self.assertEqual(Client().post(self.url, {}, content_type='application/json').status_code, 403)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url, {}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        response = self.post(); self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.post(extra='forbidden').status_code, 400)
        self.assertEqual(self.client.post(self.url+'?query=private', {}, content_type='application/json').status_code, 400)
        self.assertEqual(self.post(catalog_token='tampered').status_code, 400)

    def test_invalid_queries_never_search(self):
        for query in ('', 'x', 'x ' * 65, 'exit\nload', 'a b c d e f g h i', 123, ['load'], '.*'):
            with self.subTest(query=query): self.assertEqual(self.post(query=query).status_code, 400)

    def test_expired_source_and_deleted_document_do_not_return_old_excerpts(self):
        import time
        with patch('django.core.signing.time.time', return_value=time.time()+1000):
            self.assertEqual(self.post().status_code, 409)
        self.document.delete()
        self.assertEqual(self.post().status_code, 404)

    def test_unlinked_loan_extraction_can_be_found_without_asserting_financial_truth(self):
        document = LoanImportDocument.objects.create(user=self.owner, file_name='Synthetic loan.pdf',
            uploaded_file=SimpleUploadedFile('loan.pdf', b'%PDF synthetic loan'), parser_status='needs_review',
            extracted_text='Floating rate reset. Confirm current terms with the lender.')
        page = document_record_page(self.owner, 'loan', document.pk)
        result = knowledge.search_document(self.owner, 'loan', document.pk, query='rate reset', catalog_token=page['catalog_token'])
        self.assertEqual(len(result['results']), 1)
        self.assertFalse(result['financial_authority'])
