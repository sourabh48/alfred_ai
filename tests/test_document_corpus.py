"""Synthetic encrypted document lifecycle; no provider, financial mutation or production data."""
from datetime import timedelta
import json
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client, TestCase
from django.utils import timezone

from apps.investments.models import InvestmentImportDocument
from apps.ml_engine.services.canonical_evidence import document_record_page, SourceSelectionConflict
from apps.ml_engine.services import document_corpus as corpus
from apps.ml_engine.services.persistent_memory import MemoryStore, MemoryConflict, _owner
from tests import test_canonical_evidence as fixtures
from tests.test_persistent_memory import SyntheticEmbeddings


class DocumentCorpusTests(TestCase):
    def setUp(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.embedder = Mock(embed=Mock(side_effect=AssertionError('No inference for document indexing')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=self.embedder))
        self.store = MemoryStore(settings.ALFRED_MEMORY_DIR, embedder=SyntheticEmbeddings())
        self.corpus = corpus.DocumentCorpus(self.store)
        self.document = self.make_document()
        self.client.force_login(self.owner)
        self.url = '/api/ai/document-corpus/'

    def make_document(self, user=None, text='LOCAL-CORPUS-SECRET. Exit load applies for thirty days. Past returns are not guaranteed.'):
        document = InvestmentImportDocument.objects.create(user=user or self.owner, file_name='Synthetic prospectus.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf', b'%PDF synthetic original'),
            parser_status='parsed', extracted_text=text)
        if user is None or user == self.owner:
            document.linked_investments.add(self.investment)
        return document

    def ingest(self, document=None, user=None, **changes):
        document = document or self.document; user = user or self.owner
        args = dict(catalog_token=document_record_page(user, 'investment', document.pk)['catalog_token'], consent=True, days=30)
        return self.corpus.ingest(user, 'investment', document.pk, **(args | changes))

    def search(self, identities, query='exit load', user=None):
        return self.corpus.search(user or self.owner, identities, query)

    def count(self):
        with self.store._transaction() as db:
            return db.execute('SELECT COUNT(*) FROM document_corpus').fetchone()[0]

    def test_consent_and_retention_are_explicit_and_no_record_is_written_on_rejection(self):
        for args in ({'consent':False}, {'consent':'true'}, {'days':True}, {'days':0}, {'days':31}):
            with self.subTest(args=args), self.assertRaises(ValueError): self.ingest(**args)
        with self.assertRaises(ValueError): self.ingest(catalog_token='wrong-token')
        with self.assertRaises(Http404): self.ingest(self.make_document(self.other))
        self.assertEqual(self.count(), 0)

    def test_encrypted_index_survives_reopen_with_exact_citations_and_no_fact_or_history(self):
        before = list(type(self.investment).objects.values())
        result = self.ingest(); identity = result['document']['id']
        fresh = corpus.DocumentCorpus(MemoryStore(settings.ALFRED_MEMORY_DIR, embedder=SyntheticEmbeddings()))
        found = fresh.search(self.owner, [identity], 'EXIT load')
        self.assertEqual(len(found['results']), 1)
        hit = found['results'][0]
        self.assertEqual(hit['excerpt'], self.document.extracted_text[hit['start']:hit['end']])
        self.assertEqual(hit['document_id'], self.document.pk)
        self.assertEqual(hit['source_fingerprint'], result['document']['source_fingerprint'])
        response = self.client.get(hit['source_url']); self.assertEqual(response.status_code, 200); response.close()
        self.assertFalse(found['financial_authority']); self.assertFalse(found['full_text_qa'])
        self.assertNotIn(b'LOCAL-CORPUS-SECRET', self.store.database.read_bytes())
        self.assertNotIn(b'Synthetic prospectus', self.store.database.read_bytes())
        with self.store._transaction() as db:
            for table in ('memories', 'events', 'conversations', 'memory_sync'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0], 0)
        self.embedder.embed.assert_not_called()
        self.assertEqual(list(type(self.investment).objects.values()), before)
        self.assertTrue(fresh.list(self.owner)['rollback_requires_clear'])

    def test_multi_document_selection_is_owner_scoped_and_never_combines_partial_matches(self):
        first = self.ingest()['document']['id']
        second = self.ingest(self.make_document(text='Exit fees are discussed. Load estimates may be wrong.'))['document']['id']
        third = self.ingest(self.make_document(text='A different private topic.'))['document']['id']
        self.assertEqual({hit['id'] for hit in self.search([second, first])['results']}, {first, second})
        self.assertEqual(self.search([third])['results'], [])
        foreign = self.ingest(self.make_document(self.other), self.other)['document']['id']
        for identities in ([foreign], [first,foreign], [first,first], [], [first,second,third,foreign], [True]):
            with self.subTest(ids=identities), self.assertRaises((ValueError, SourceSelectionConflict)):
                self.search(identities)
        self.assertEqual(self.corpus.list(self.other)['documents'][0]['id'], foreign)
        self.assertEqual(len(self.corpus.list(self.owner)['documents']), 3)

    def test_query_terms_do_not_match_across_documents_or_inside_words(self):
        first = self.ingest(self.make_document(text='Exit options only.'))['document']['id']
        second = self.ingest(self.make_document(text='Load options only.'))['document']['id']
        self.assertEqual(self.search([first,second])['results'], [])
        self.assertEqual(self.search([first], 'exiting')['results'], [])

    def test_document_and_financial_corrections_invalidate_and_remove_index(self):
        identity = self.ingest()['document']['id']
        self.investment.refresh_from_db()
        self.investment.current_value += 1; self.investment.save()
        with self.assertRaises(SourceSelectionConflict): self.search([identity])
        self.assertEqual(self.count(), 0)
        identity = self.ingest()['document']['id']
        self.document.extracted_text += ' Revised extraction.'; self.document.save()
        with self.assertRaises(SourceSelectionConflict): self.search([identity])
        self.assertEqual(self.count(), 0)

    def test_file_and_ownership_changes_invalidate_without_leaking_old_text(self):
        identity = self.ingest()['document']['id']
        with self.document.uploaded_file.open('wb') as stream: stream.write(b'%PDF changed source')
        self.assertEqual(self.corpus.list(self.owner)['documents'], [])
        with self.assertRaises(SourceSelectionConflict): self.search([identity])
        identity = self.ingest()['document']['id']
        InvestmentImportDocument.objects.filter(pk=self.document.pk).update(user=self.other)
        with self.assertRaises(SourceSelectionConflict): self.search([identity])
        self.assertEqual(self.count(), 0)

    def test_source_deleted_revokes_copy_immediately(self):
        self.ingest()
        self.document.delete()
        self.assertEqual(self.count(), 0)

    def test_search_rechecks_sources_after_matching_and_commits_invalidation(self):
        identity = self.ingest()['document']['id']; original = corpus.matching_passages
        def change(*args):
            InvestmentImportDocument.objects.filter(pk=self.document.pk).update(extracted_text='Changed during retrieval')
            return original(*args)
        with patch.object(corpus, 'matching_passages', side_effect=change), self.assertRaises(SourceSelectionConflict):
            self.search([identity])
        self.assertEqual(self.count(), 0)

    def test_reset_during_ingestion_cannot_recreate_a_copy(self):
        original = corpus.document_text
        def reset(*args, **kwargs):
            self.store.reset_owner(self.owner)
            return original(*args, **kwargs)
        with patch.object(corpus, 'document_text', side_effect=reset), self.assertRaises(MemoryConflict): self.ingest()
        self.assertEqual(self.count(), 0)

    def test_retention_can_shorten_but_never_extend_existing_expiry(self):
        identity = self.ingest()['document']['id']; now = timezone.now()
        self.store.set_retention(self.owner, 1)
        expiry = self.corpus.list(self.owner)['documents'][0]['expires_at']
        self.store.set_retention(self.owner, 30)
        self.assertEqual(self.corpus.list(self.owner)['documents'][0]['expires_at'], expiry)
        with patch.object(corpus.timezone, 'now', return_value=now + timedelta(days=2)):
            self.store.expire_all()
            with self.assertRaises(SourceSelectionConflict): self.search([identity])
        self.assertEqual(self.count(), 0)

    def test_owner_reset_and_restore_do_not_resurrect_document_knowledge(self):
        identity = self.ingest()['document']['id']
        foreign = self.ingest(self.make_document(self.other), self.other)['document']['id']
        self.store.reset_owner(self.owner); self.store.restore_owner(self.owner)
        self.assertEqual(self.corpus.list(self.owner)['documents'], [])
        with self.assertRaises(SourceSelectionConflict): self.search([identity])
        self.assertEqual(self.corpus.list(self.other)['documents'][0]['id'], foreign)

    def test_missing_key_is_not_regenerated_and_corruption_is_preserved(self):
        identity = self.ingest()['document']['id']; original = self.store.key_file.read_bytes()
        preserved = self.store.key_file.with_suffix('.preserved')
        self.store.key_file.rename(preserved)
        try:
            with self.assertRaises(RuntimeError): self.corpus.list(self.owner)
            self.assertFalse(self.store.key_file.exists()); self.assertEqual(self.count(), 1)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 503); self.assertNotIn('LOCAL-CORPUS-SECRET', response.content.decode())
        finally:
            preserved.rename(self.store.key_file)
        self.assertEqual(self.store.key_file.read_bytes(), original)
        with self.store._transaction() as db: db.execute('UPDATE document_corpus SET record=? WHERE id=?', (b'corrupt', identity))
        with self.assertRaises(RuntimeError): self.search([identity])
        self.assertEqual(self.count(), 1)
        with self.store._transaction() as db: self.assertEqual(db.execute('SELECT record FROM document_corpus').fetchone()[0], b'corrupt')

    def test_ciphertext_cannot_be_transplanted_between_owners(self):
        identity = self.ingest()['document']['id']
        with self.store._transaction() as db:
            db.execute('UPDATE document_corpus SET owner=? WHERE id=?', (_owner(self.other), identity))
        with self.assertRaises(RuntimeError): self.corpus.list(self.other)
        self.assertEqual(self.count(), 1)

    def test_quota_rejection_preserves_previous_copy_and_enforces_token_and_global_limits(self):
        identity = self.ingest()['document']['id']
        with patch.object(corpus, 'MAX_OWNER_BYTES', 0), self.assertRaises(ValueError): self.ingest()
        self.assertEqual(self.search([identity])['results'][0]['id'], identity)
        with patch.object(corpus, 'MAX_TOKENS', 1), self.assertRaises(ValueError): self.ingest()
        with patch.object(corpus, 'MAX_GLOBAL_DOCUMENTS', 1), self.assertRaises(ValueError):
            self.ingest(self.make_document(self.other), self.other)
        self.assertEqual(self.count(), 1)

    def test_api_auth_csrf_validation_no_store_and_owner_delete(self):
        unauthenticated = Client()
        self.assertEqual(unauthenticated.get(self.url).status_code, 403)
        client = Client(enforce_csrf_checks=True); client.force_login(self.owner)
        data = dict(kind='investment', document_id=self.document.pk,
            catalog_token=document_record_page(self.owner,'investment',self.document.pk)['catalog_token'], consent=True, days=7)
        self.assertEqual(client.post(self.url, data, content_type='application/json').status_code, 403)
        client.get('/documents/'); token = client.cookies['csrftoken'].value
        response = client.post(self.url, data, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('no-store', response['Cache-Control'])
        identity = response.json()['document']['id']
        found = client.post(self.url+'search/', dict(ids=[identity],query='exit load'), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(found.status_code, 200); self.assertTrue(found.json()['results'])
        self.assertEqual(client.post(self.url+'?query=secret', data, content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.delete(self.url+identity+'/').status_code, 404)
        self.assertEqual(client.delete(self.url+identity+'/').status_code, 403)
        self.assertEqual(client.delete(self.url+identity+'/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(self.count(), 0)

    def test_bank_text_layer_is_indexed_but_scans_and_foreign_parent_accounts_are_refused(self):
        from apps.expenses.models import BankAccount, StatementUpload
        from tests.test_document_knowledge import text_pdf, image_pdf
        document = StatementUpload.objects.create(user=self.owner, bank_account=self.account,
            source='bank_statement', file_name='Synthetic bank.pdf', parser_status='parsed',
            original_file=SimpleUploadedFile('bank.pdf', text_pdf()))
        def ingest():
            token = document_record_page(self.owner, 'expense', document.pk)['catalog_token']
            return self.corpus.ingest(self.owner, 'expense', document.pk, catalog_token=token, consent=True, days=1)
        identity = ingest()['document']['id']
        with patch.object(corpus, 'document_text', side_effect=AssertionError('Search must use the retained index')):
            found = self.search([identity], 'maintenance waiver')['results'][0]
        self.assertEqual(found['text_origin'], 'original_text_layer')
        self.assertIn('Annual maintenance waiver applies.', found['excerpt'])
        foreign = BankAccount.objects.create(user=self.other, account_number='SYNTHETIC-FOREIGN')
        StatementUpload.objects.filter(pk=document.pk).update(bank_account=foreign)
        with self.assertRaises(SourceSelectionConflict): self.search([identity], 'maintenance waiver')
        self.assertEqual(self.count(), 0)
        with self.assertRaises(Http404): ingest()
        document.bank_account = self.account; document.save()
        document.original_file.save('scan.pdf', SimpleUploadedFile('scan.pdf', image_pdf()))
        self.assertFalse(ingest()['stored']); self.assertEqual(self.count(), 0)

    def test_count_linked_record_text_and_global_byte_limits_do_not_discard_existing_copy(self):
        identity = self.ingest()['document']['id']
        with patch.object(corpus, 'MAX_DOCUMENTS', 1), self.assertRaises(ValueError):
            self.ingest(self.make_document())
        with patch.object(corpus, 'MAX_LINKED_RECORDS', 0), self.assertRaises(ValueError): self.ingest()
        with patch.object(corpus, 'MAX_GLOBAL_BYTES', 0), self.assertRaises(ValueError): self.ingest()
        oversized = self.make_document(text='x' * (corpus.TEXT_BYTES + 1))
        self.assertFalse(self.ingest(oversized)['stored'])
        self.assertEqual(self.search([identity])['results'][0]['id'], identity)
        self.assertEqual(self.count(), 1)

    def test_authenticated_but_invalid_index_and_corrupt_wrapped_key_are_preserved(self):
        identity = self.ingest()['document']['id']
        with self.store._transaction() as db:
            wrapped, ciphertext = db.execute('SELECT wrapped,record FROM document_corpus WHERE id=?', (identity,)).fetchone()
            cipher = Fernet(self.store._cipher(db).decrypt(wrapped))
            record = json.loads(cipher.decrypt(ciphertext))
            record['index']['exit'][0][1] += 1
            db.execute('UPDATE document_corpus SET record=? WHERE id=?', (cipher.encrypt(json.dumps(record).encode()), identity))
        with self.assertRaises(RuntimeError): self.search([identity])
        self.assertEqual(self.count(), 1)
        with self.store._transaction() as db:
            db.execute('UPDATE document_corpus SET record=?,wrapped=? WHERE id=?', (ciphertext, b'corrupt-key', identity))
        with self.assertRaises(RuntimeError): self.corpus.list(self.owner)
        self.assertEqual(self.count(), 1)

    def test_source_change_during_ingestion_cannot_store_old_text(self):
        original = corpus.document_text
        def change(*args, **kwargs):
            result = original(*args, **kwargs)
            InvestmentImportDocument.objects.filter(pk=self.document.pk).update(extracted_text='Changed after extraction')
            return result
        with patch.object(corpus, 'document_text', side_effect=change), self.assertRaises(SourceSelectionConflict): self.ingest()
        self.assertEqual(self.count(), 0)

    def test_account_clear_and_deletion_revoke_only_that_owners_copies(self):
        self.ingest()
        foreign = self.ingest(self.make_document(self.other), self.other)['document']['id']
        response = self.client.post('/api/users/profile/clear-data/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.corpus.list(self.owner)['documents'], [])
        self.assertEqual(self.corpus.list(self.other)['documents'][0]['id'], foreign)
        self.other.delete()
        self.assertEqual(self.count(), 0)
