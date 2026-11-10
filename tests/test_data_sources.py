from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services.data_sources import data_sources_snapshot
from apps.career.models import CareerProfile, CareerResume
from apps.expenses.models import BankAccount, StatementUpload
from apps.mobility.models import TravelPreferenceProfile
from apps.loans.models import LoanImportDocument
from apps.investments.models import InvestmentImportDocument


class DataSourcesTests(TestCase):
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
        self.assertEqual(self.client.post('/data-sources/').status_code, 405)

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
