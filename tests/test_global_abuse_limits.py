from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from diskcache import Cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.budgets.models import Budget


class GlobalAbuseLimitTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix='alfred-global-limits-'))
        self.directory = directory
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=directory,
            ALFRED_LOGIN_ACCOUNT_LIMIT=1, ALFRED_LOGIN_IP_LIMIT=10, ALFRED_LOGIN_GLOBAL_LIMIT=30,
            ALFRED_API_ACCOUNT_LIMIT=2, ALFRED_API_GLOBAL_LIMIT=30,
            ALFRED_EXPENSIVE_ACCOUNT_LIMIT=1, ALFRED_EXPENSIVE_GLOBAL_LIMIT=10))
        self.user = get_user_model().objects.create_user(username='synthetic-guard-user', password='SyntheticStrongPass42!')

    def test_login_paths_share_limit_before_authentication(self):
        self.assertEqual(self.client.post('/', {'username': self.user.username, 'password': 'synthetic-wrong'}).status_code, 200)
        for path in ('/login/', '/', '/admin/login/'):
            with self.subTest(path=path):
                client = Client()
                response = client.post(path, {'username': self.user.username, 'password': 'SyntheticStrongPass42!'})
                self.assertEqual(response.status_code, 429)
                self.assertGreater(int(response['Retry-After']), 0)
                self.assertNotIn('_auth_user_id', client.session)

    def test_ip_and_global_login_limits_ignore_forwarded_header_spoofing(self):
        with override_settings(ALFRED_LOGIN_IP_LIMIT=1):
            self.client.post('/login/', {'username': 'synthetic-a', 'password': 'wrong'}, HTTP_X_FORWARDED_FOR='198.51.100.1')
            response = self.client.post('/login/', {'username': 'synthetic-b', 'password': 'wrong'}, HTTP_X_FORWARDED_FOR='198.51.100.2')
        self.assertEqual(response.status_code, 429)
        with override_settings(ALFRED_LOGIN_GLOBAL_LIMIT=1):
            response = self.client.post('/login/', {'username': 'synthetic-c', 'password': 'wrong'}, REMOTE_ADDR='198.51.100.3')
        self.assertEqual(response.status_code, 429)

    def test_success_and_csrf_are_preserved(self):
        csrf = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf.post('/login/', {'username': self.user.username, 'password': 'SyntheticStrongPass42!'}).status_code, 403)
        self.assertEqual(self.client.post('/login/', {'username': self.user.username, 'password': 'SyntheticStrongPass42!'}).status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_api_rejection_is_per_account_and_causes_no_mutation(self):
        self.client.force_login(self.user)
        data = {'month': 'Oct 2026', 'base_budget': 100, 'inflation_adjusted': 100}
        self.assertEqual(self.client.post('/api/budgets/', data).status_code, 201)
        self.assertEqual(self.client.post('/api/budgets/', data).status_code, 201)
        self.assertEqual(self.client.post('/api/budgets/', data).status_code, 429)
        self.assertEqual(Budget.objects.count(), 2)
        other = get_user_model().objects.create_user(username='synthetic-other-guard')
        client = Client()
        client.force_login(other)
        self.assertEqual(client.get('/api/budgets/').status_code, 200)
        self.assertEqual(len(client.get('/api/budgets/').json()), 0)

    def test_global_api_limit_applies_across_accounts(self):
        self.client.force_login(self.user)
        with override_settings(ALFRED_API_GLOBAL_LIMIT=1):
            self.assertEqual(self.client.get('/api/budgets/').status_code, 200)
            other = get_user_model().objects.create_user(username='synthetic-global-other')
            client = Client()
            client.force_login(other)
            self.assertEqual(client.get('/api/budgets/').status_code, 429)

    def test_expensive_upload_and_retry_share_budget_before_processing(self):
        self.client.force_login(self.user)
        self.client.post('/api/loans/import-pdf/', {})
        with patch('alfred_ai.views.retry_review_item') as retry:
            response = self.client.post('/api/documents/review-queue/retry/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 429)
        retry.assert_not_called()

    def test_document_search_uses_existing_expensive_budget_before_parser_or_query(self):
        self.client.force_login(self.user)
        for kind in ('expense', 'loan', 'investment'):
            with self.subTest(kind=kind), override_settings(ALFRED_API_ACCOUNT_LIMIT=100):
                self.client.post('/api/loans/import-pdf/', {})
                with patch('apps.ml_engine.services.document_knowledge.search_document') as search:
                    response = self.client.post(f'/api/ai/financial-documents/{kind}/1/search/', '{}', content_type='application/json')
                self.assertEqual(response.status_code, 429)
                self.assertIn('Retry-After', response)
                search.assert_not_called()

    def test_document_discovery_does_not_consume_expensive_search_budget(self):
        self.client.force_login(self.user)
        with override_settings(ALFRED_API_ACCOUNT_LIMIT=100):
            self.client.get('/api/ai/financial-documents/investment/')
            with patch('apps.ml_engine.services.document_knowledge.search_document', return_value={'status': 'searched'}) as search:
                response = self.client.post('/api/ai/financial-documents/investment/1/search/', '{}', content_type='application/json')
            self.assertEqual(response.status_code, 200)
            search.assert_called_once()

    def test_private_corpus_requests_share_expensive_budget_before_vault_or_source_reads(self):
        self.client.force_login(self.user)
        with override_settings(ALFRED_API_ACCOUNT_LIMIT=100):
            self.client.post('/api/loans/import-pdf/', {})
            with patch('apps.ml_engine.api.document_corpus.memory_store') as store:
                for method, path in (('get',''), ('post',''), ('post','search/'), ('post','question/'), ('post','upload/'),
                        ('get','a'*32+'/original/'), ('delete','a'*32+'/')):
                    with self.subTest(method=method, path=path):
                        response = getattr(self.client, method)('/api/ai/document-corpus/'+path,
                            data={}, content_type='application/json')
                        self.assertEqual(response.status_code, 429)
                        self.assertIn('Retry-After', response)
                store.assert_not_called()

    def test_anonymous_and_missing_csrf_never_mutate(self):
        self.assertEqual(self.client.post('/api/budgets/', {}).status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post('/api/budgets/', {}).status_code, 403)
        self.assertEqual(Budget.objects.count(), 0)

    def test_protection_failure_is_safe_and_fail_closed(self):
        marker = r'F:\synthetic-private\secret-token'
        self.client.force_login(self.user)
        with patch('alfred_ai.services.throttling.Cache', side_effect=OSError(marker)), self.assertLogs('alfred_ai.services.abuse_protection', level='ERROR') as logs:
            response = self.client.post('/api/budgets/', {})
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()['error_id'])
        self.assertNotIn(marker, response.content.decode() + '\n'.join(logs.output))
        self.assertFalse(Budget.objects.exists())

    def test_reservations_are_atomic_across_all_buckets_and_restart(self):
        from alfred_ai.services.throttling import reserve_attempts
        barrier = Barrier(12, timeout=30)
        buckets = [('shared', 3, 600), ('per-account', 5, 600)]
        def attempt(_):
            barrier.wait()
            return reserve_attempts(self.directory, buckets)
        with ThreadPoolExecutor(max_workers=12) as pool:
            outcomes = list(pool.map(attempt, range(12)))
        self.assertEqual(outcomes.count(0), 3)
        with Cache(self.directory) as store:
            self.assertEqual(len(store.get('per-account')), 3)
        self.assertGreater(reserve_attempts(self.directory, buckets), 0)
        now = timezone.now()
        with patch('django.utils.timezone.now', return_value=now + timedelta(seconds=601)):
            self.assertEqual(reserve_attempts(self.directory, buckets), 0)

    def test_invalid_configuration_fails_closed(self):
        self.client.force_login(self.user)
        for config in ({'ALFRED_ABUSE_THROTTLE_DIR': ''}, {'ALFRED_ABUSE_THROTTLE_DIR': 'relative'}, {'ALFRED_API_ACCOUNT_LIMIT': 0}):
            with override_settings(**config):
                self.assertEqual(self.client.get('/api/budgets/').status_code, 503)

    def test_rate_store_never_contains_username_or_password(self):
        self.client.post('/login/', {'username': 'synthetic-private-user', 'password': 'synthetic-private-password'})
        with Cache(self.directory) as store:
            text = str(list(store.iterkeys()))
        self.assertNotIn('synthetic-private-user', text)
        self.assertNotIn('synthetic-private-password', text)

    def test_signup_is_bounded_before_user_creation(self):
        with override_settings(ALFRED_SIGNUP_IP_LIMIT=1):
            self.client.post('/signup/', {})
            self.assertEqual(self.client.post('/signup/', {}).status_code, 429)
        self.assertEqual(get_user_model().objects.count(), 1)
