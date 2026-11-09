from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services.data_sources import data_sources_snapshot
from apps.career.models import CareerResume
from apps.expenses.models import BankAccount, StatementUpload
from apps.mobility.models import TravelPreferenceProfile


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
