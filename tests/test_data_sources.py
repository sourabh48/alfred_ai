from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services.data_sources import data_sources_snapshot
from apps.career.models import CareerProfile, CareerResume
from apps.expenses.models import BankAccount, StatementUpload
from apps.mobility.models import TravelPreferenceProfile
from apps.loans.models import LoanImportDocument
from apps.investments.models import InvestmentImportDocument


class DataSourcesTests(TestCase):
    def test_confirmed_reviews_are_not_pending_even_when_parser_needs_review(self):
        for model, label in ((StatementUpload,'Finance'), (LoanImportDocument,'Loans'),
                             (InvestmentImportDocument,'Investments')):
            model.objects.create(user=self.owner, parser_status='needs_review',
                extracted_payload={'import_review':{'state':'confirmed'}})
            model.objects.create(user=self.owner, parser_status='pending')
            source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label']==label)
            self.assertEqual(source['imports']['awaiting_review'], 1)
            self.assertEqual(source['imports']['confirmed'], 1)
            model.objects.filter(user=self.owner, parser_status='pending').delete()
            source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label']==label)
            self.assertEqual(source['imports']['awaiting_review'], 0)
            self.assertNotEqual(source['state'], 'Review needed')

    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='synthetic-source-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-source-other')

    def test_empty_readiness_does_not_count_other_owners_or_default_preferences(self):
        BankAccount.objects.create(user=self.other, account_number='SYNTHETIC-OTHER')
        TravelPreferenceProfile.objects.create(user=self.owner)
        result = data_sources_snapshot(self.owner)
        self.assertEqual(result['populated'], 0)
        self.assertEqual(result['total'], 6)
        self.assertTrue(all(source['state'] == 'Needs data' for source in result['sources']))

    def test_saved_parsed_review_and_failed_are_distinct_and_owner_scoped(self):
        BankAccount.objects.create(user=self.owner, account_number='SYNTHETIC-OWNED')
        for status in ('parsed', 'needs_review', 'failed'):
            StatementUpload.objects.create(user=self.owner, file_name='synthetic.pdf', parser_status=status)
        StatementUpload.objects.create(user=self.other, file_name='foreign.pdf', parser_status='parsed')
        CareerResume.objects.create(user=self.owner, file_name='synthetic-resume.pdf', parser_status='pending')
        sources = {s['label']: s for s in data_sources_snapshot(self.owner)['sources']}
        finance = sources['Finance']
        self.assertEqual(finance['records'][0]['count'], 1)
        self.assertEqual(finance['imports']['total'], 3)
        self.assertEqual(finance['imports']['parsed'], 1)
        self.assertEqual(finance['imports']['awaiting_review'], 1)
        self.assertEqual(finance['imports']['failed'], 1)
        self.assertIsNotNone(finance['imports']['last_parsed'])
        self.assertEqual(finance['state'], 'Import needs attention')
        self.assertFalse(sources['Career']['has_data'])
        self.assertEqual(sources['Career']['state'], 'Review needed')

    def test_page_is_private_readonly_and_does_not_display_source_contents(self):
        self.assertEqual(self.client.get('/data-sources/').status_code, 302)
        self.client.force_login(self.owner)
        StatementUpload.objects.create(user=self.owner, file_name='SYNTHETIC-PRIVATE-FILENAME.pdf')
        response = self.client.get('/data-sources/')
        self.assertContains(response, 'Data Sources')
        self.assertNotContains(response, 'SYNTHETIC-PRIVATE-FILENAME')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.post('/data-sources/').status_code, 400)

    def test_parsed_financial_preview_is_awaiting_review_without_populating_finance(self):
        StatementUpload.objects.create(user=self.owner, file_name='synthetic-pending.pdf', parser_status='parsed',
            extracted_payload={'import_review': {'state': 'pending'}})
        snapshot = data_sources_snapshot(self.owner)
        finance = snapshot['sources'][0]
        self.assertFalse(finance['has_data'])
        self.assertEqual(finance['state'], 'Review needed')
        self.assertEqual(finance['imports']['awaiting_review'], 1)

    def test_empty_career_profile_is_not_onboarding_readiness(self):
        profile = CareerProfile.objects.create(user=self.owner, role='  ', skills='', experience_years=0)
        result = data_sources_snapshot(self.owner)
        self.assertEqual(result['populated'], 0)
        career = next(source for source in result['sources'] if source['label'] == 'Career')
        self.assertFalse(career['has_data'])
        profile.role = 'Synthetic Developer'; profile.save()
        self.assertTrue(next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label'] == 'Career')['has_data'])

    def test_confirmed_reviews_and_bounded_owned_pending_links_are_distinct(self):
        for model, label, prefix in ((StatementUpload, 'Finance', '/expenses/uploads/'),
                (LoanImportDocument, 'Loans', '/loans/import-uploads/'),
                (InvestmentImportDocument, 'Investments', '/investments/import-uploads/')):
            model.objects.create(user=self.owner, parser_status='parsed', extracted_payload={})
            model.objects.create(user=self.owner, parser_status='parsed',
                extracted_payload={'import_review': {'state': 'confirmed', 'receipt': {'replayed': True}}})
            pending = [model.objects.create(user=self.owner, parser_status='needs_review',
                extracted_payload={'import_review': {'state': 'pending'}}) for _ in range(5)]
            foreign = model.objects.create(user=self.other, parser_status='needs_review',
                extracted_payload={'import_review': {'state': 'pending'}})
            source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label'] == label)
            self.assertEqual(source['imports']['confirmed'], 1)
            self.assertEqual(source['imports']['awaiting_review'], 5)
            self.assertEqual(len(source['reviews']), 3)
            self.assertEqual(source['reviews'][0]['url'], f'{prefix}{pending[-1].pk}/review/')
            self.assertNotIn(f'{prefix}{foreign.pk}/review/', [r['url'] for r in source['reviews']])

    def test_next_setup_prioritizes_review_without_private_content_or_side_effects(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        from unittest.mock import patch
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-source-readiness-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=root/'unopened-memory'))
        pending = LoanImportDocument.objects.create(user=self.owner, file_name='SYNTHETIC-PRIVATE.pdf',
            parser_status='needs_review', extracted_payload={'import_review': {'state': 'pending'}})
        self.client.force_login(self.owner)
        with patch('apps.ml_engine.services.persistent_memory.MemoryStore', side_effect=AssertionError('Memory must stay unopened')):
            snapshot = data_sources_snapshot(self.owner)
            self.assertEqual(snapshot['next_setup']['label'], 'Loans')
            response = self.client.get('/data-sources/')
        self.assertContains(response, f'/loans/import-uploads/{pending.pk}/review/')
        self.assertNotContains(response, 'SYNTHETIC-PRIVATE')
        self.assertFalse((root/'unopened-memory').exists())
        self.assertEqual(LoanImportDocument.objects.filter(user=self.owner).count(), 1)

    def test_database_failure_is_unavailable_with_a_safe_diagnostic_action(self):
        from unittest.mock import patch
        from django.db import DatabaseError
        with patch.object(StatementUpload.objects, 'filter', side_effect=DatabaseError('synthetic unavailable')):
            result = data_sources_snapshot(self.owner)
        finance = result['sources'][0]
        self.assertEqual(finance['state'], 'Unavailable')
        self.assertFalse(finance['has_data'])
        self.assertEqual(finance['reviews'], [])
        self.assertEqual(result['next_setup']['next_action']['url'], '/settings/diagnostics/')

    def test_pending_review_links_explain_expired_and_unverified_deadlines_without_writes(self):
        from datetime import timedelta
        from django.utils import timezone
        for model, label in ((StatementUpload,'Finance'), (LoanImportDocument,'Loans'),
                             (InvestmentImportDocument,'Investments')):
            with self.subTest(label=label):
                for deadline in ((timezone.now()+timedelta(hours=1)).isoformat(), 'invalid',
                                 (timezone.now()-timedelta(hours=1)).isoformat()):
                    model.objects.create(user=self.owner, parser_status='needs_review',
                        file_name='PRIVATE-EXPIRY-SOURCE.pdf', extracted_payload={'import_review':{
                            'state':'pending','expires_at':deadline}})
                model.objects.create(user=self.other, parser_status='needs_review',
                    extracted_payload={'import_review':{'state':'pending','expires_at':'foreign'}})
                before = list(model.objects.values())
                source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label']==label)
                self.assertEqual([r['status'] for r in source['reviews']], ['Expired','Expiry unavailable','Awaiting review'])
                self.assertEqual(source['next_action']['label'], 'Reopen expired review')
                self.assertEqual(source['imports']['awaiting_review'], 3)
                self.assertEqual(list(model.objects.values()), before)
        self.client.force_login(self.owner)
        response = self.client.get('/data-sources/')
        self.assertContains(response, 'Reopen expired review')
        self.assertContains(response, 'Keep edited previews')
        self.assertNotContains(response, 'PRIVATE-EXPIRY-SOURCE')

    def test_deadline_metadata_requires_an_aware_valid_timestamp_and_checks_boundary(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        now = datetime(2026, 11, 11, tzinfo=timezone.utc)
        for value in (None, True, 123, {}, [], '2026-11-12T00:00:00', '2026-99-11T00:00:00Z', 'x'*65):
            with self.subTest(value=value):
                LoanImportDocument.objects.filter(user=self.owner).delete()
                LoanImportDocument.objects.create(user=self.owner, extracted_payload={
                    'import_review':{'state':'pending','expires_at':value}})
                source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label']=='Loans')
                self.assertEqual(source['reviews'][0]['status'], 'Expiry unavailable')
                self.assertIsNone(source['reviews'][0]['expires_at'])
        document = LoanImportDocument.objects.filter(user=self.owner).get()
        for value, expected in (('2026-11-11T00:00:00Z','Expired'),
                                ('2026-11-11T05:30:01+05:30','Awaiting review')):
            document.extracted_payload={'import_review':{'state':'pending','expires_at':value}}
            document.save(update_fields=['extracted_payload'])
            with patch('alfred_ai.services.data_sources.timezone.now', return_value=now):
                source = next(s for s in data_sources_snapshot(self.owner)['sources'] if s['label']=='Loans')
            self.assertEqual(source['reviews'][0]['status'], expected)


class KnowledgeReadinessTests(TestCase):
    def setUp(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        self.root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-knowledge-readiness-')))
        self.directory = self.root / 'vault'
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=self.directory))
        self.owner = get_user_model().objects.create_user(username='synthetic-knowledge-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-knowledge-other')
        self.client.force_login(self.owner)

    def test_explicit_check_does_not_initialize_an_absent_vault(self):
        response = self.client.post('/data-sources/', {'action': 'check_knowledge'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not configured')
        self.assertFalse(self.directory.exists())

    def seed_vault(self):
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.document_corpus import DocumentCorpus
        from tests.test_persistent_memory import SyntheticEmbeddings
        from django.core.files.uploadedfile import SimpleUploadedFile
        store = MemoryStore(self.directory, embedder=SyntheticEmbeddings())
        for owner, count in ((self.owner, 1), (self.other, 2)):
            for i in range(count):
                store.save_verified(owner, {'statement': f'SYNTHETIC-PRIVATE-FACT-{i}'},
                    {'source':'SYNTHETIC-PRIVATE-PROVENANCE'}, verified=True)
                DocumentCorpus(store).upload(owner,
                    SimpleUploadedFile(f'PRIVATE-FILENAME-{i}.txt', b'PRIVATE-DOCUMENT-TEXT hiking supplies'),
                    consent=True, days=7)
        return store

    def test_metadata_is_owned_private_and_uses_existing_encrypted_services_without_inference(self):
        from unittest.mock import patch
        store = self.seed_vault()
        key = store.key_file.read_bytes()
        with patch('apps.ml_engine.services.local_embeddings.OllamaEmbeddings.embed', side_effect=AssertionError('No inference')):
            response = self.client.post('/data-sources/', {'action':'check_knowledge'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['knowledge']['documents'], 1)
        self.assertEqual(response.context['knowledge']['memories'], 1)
        self.assertIsNotNone(response.context['knowledge']['last_memory'])
        self.assertIsNotNone(response.context['knowledge']['last_document'])
        self.assertEqual(response.context['knowledge']['document_retention_days'], 30)
        for secret in ('PRIVATE-FACT', 'PRIVATE-PROVENANCE', 'PRIVATE-FILENAME', 'PRIVATE-DOCUMENT-TEXT', str(self.directory)):
            self.assertNotContains(response, secret)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(store.key_file.read_bytes(), key)
        self.client.force_login(self.other)
        response = self.client.post('/data-sources/', {'action':'check_knowledge'})
        self.assertEqual(response.context['knowledge']['documents'], 2)
        self.assertEqual(response.context['knowledge']['memories'], 2)

    def test_expiry_obeys_existing_policy_without_changing_retention(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        from alfred_ai.services.data_sources import knowledge_sources_snapshot
        store = self.seed_vault()
        store.set_retention(self.owner, 1)
        future = datetime.now(timezone.utc) + timedelta(days=8)
        with patch('apps.ml_engine.services.document_corpus.timezone.now', return_value=future), \
             patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value = future
            clock.fromisoformat.side_effect = datetime.fromisoformat
            snapshot = knowledge_sources_snapshot(self.owner)
        self.assertEqual(snapshot['documents'], 0)
        self.assertEqual(snapshot['memories'], 0)
        self.assertEqual(store.retention_days(self.owner), 1)
        self.assertEqual(len(store.list_memories(self.other)), 2)

    def test_missing_key_never_regenerates_it_and_corrupt_storage_is_preserved(self):
        store = self.seed_vault()
        store.key_file.unlink()
        before = store.database.read_bytes()
        response = self.client.post('/data-sources/', {'action':'check_knowledge'})
        self.assertEqual(response.context['knowledge'], {'state':'Unavailable'})
        self.assertFalse(store.key_file.exists())
        self.assertEqual(store.database.read_bytes(), before)
        store.key_file.write_bytes(b'SYNTHETIC-INVALID-KEY')
        response = self.client.post('/data-sources/', {'action':'check_knowledge'})
        self.assertEqual(response.context['knowledge'], {'state':'Unavailable'})
        self.assertEqual(store.key_file.read_bytes(), b'SYNTHETIC-INVALID-KEY')
        self.assertNotContains(response, str(self.directory))

    def test_authentication_csrf_and_request_scope_are_required(self):
        from django.test import Client
        self.client.logout()
        self.assertEqual(self.client.post('/data-sources/', {'action':'check_knowledge'}).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post('/data-sources/', {'action':'check_knowledge'}).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post('/data-sources/?owner=other', {'action':'check_knowledge'}).status_code, 400)
        self.assertFalse(self.directory.exists())

    def test_normal_get_and_invalid_post_never_open_the_vault(self):
        from unittest.mock import patch
        with patch('apps.ml_engine.services.persistent_memory.MemoryStore', side_effect=AssertionError('Must stay unopened')):
            self.assertContains(self.client.get('/data-sources/'), 'Not checked')
            for data in ({}, {'action':'wrong'}, {'action':'check_knowledge','owner':self.other.pk},
                         {'action':['check_knowledge','check_knowledge']}):
                self.assertEqual(self.client.post('/data-sources/', data).status_code, 400)
        self.assertFalse(self.directory.exists())
