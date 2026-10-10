import ipaddress
from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services.verified_intelligence import VerifiedIntelligenceService
from apps.investments.services.portfolio_intelligence import PortfolioIntelligenceService


class RemainingPublicHTTPTests(TestCase):
    def setUp(self):
        cache.clear()
        self.verified = VerifiedIntelligenceService()
        self.portfolio = PortfolioIntelligenceService()
        legacy = patch('requests.get', side_effect=RuntimeError('Legacy direct HTTP is forbidden in this regression'))
        legacy.start()
        self.addCleanup(legacy.stop)

    def test_every_remaining_fetch_adapter_uses_shared_transport(self):
        calls = [
            lambda: self.verified._fetch_world_bank('https://example.org/indicator', 'Indicator'),
            lambda: self.verified._fetch_yahoo_chart('TEST', '1mo', '1d'),
            lambda: self.verified._fetch_geocode('Synthetic place'),
            lambda: self.verified._fetch_offbeat('Synthetic place'),
            lambda: self.verified._fetch_weather(12, 77, date(2026, 10, 11), date(2026, 10, 12)),
            lambda: self.verified._fetch_google_news('https://example.org/feed', 'Synthetic query'),
            lambda: self.verified._fetch_remotive_jobs('Synthetic role'),
            lambda: self.verified._fetch_arbeitnow_jobs('Synthetic role'),
            lambda: self.verified._fetch_remoteok_jobs('Synthetic role'),
            self.portfolio._get_amfi_latest_nav_report,
            lambda: self.portfolio._get_amfi_history_report(days=60),
            self.portfolio._scrape_trending_sectors,
        ]
        with patch('alfred_ai.services.public_http.request', return_value=PublicResponse(b'{}', 'application/json')) as fetch:
            for call in calls:
                with self.subTest(adapter=call):
                    fetch.reset_mock()
                    try:
                        call()
                    except (ValueError, TypeError, KeyError, RuntimeError):
                        pass  # Empty synthetic responses need not contain provider business fields.
                    self.assertTrue(fetch.called)
                    self.assertEqual(fetch.call_args.args[0], 'GET')

    def test_dynamic_feed_private_destination_never_opens_connection(self):
        with patch('alfred_ai.services.public_http._resolve_host_ips', return_value=[ipaddress.ip_address('127.0.0.1')]), patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool') as pool:
            with self.assertRaisesRegex(PublicHTTPError, '^unsafe_url$'):
                self.verified._fetch_google_news('https://attacker.example/feed', 'Synthetic')
            pool.assert_not_called()

    def test_amfi_redirect_is_blocked_and_failure_is_safe(self):
        response = Mock(status=302, headers={'Location': 'http://169.254.169.254/secret'})
        pool = Mock()
        pool.urlopen.return_value = response
        with patch('alfred_ai.services.public_http._resolve_host_ips', return_value=[ipaddress.ip_address('93.184.215.14')]), patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool', return_value=pool):
            result = self.portfolio._get_amfi_latest_nav_report()
        self.assertEqual(result['items'], [])
        self.assertNotIn('169.254', str(result))
        response.read.assert_not_called()
        self.assertEqual(pool.urlopen.call_count, 1)
        self.assertFalse(pool.urlopen.call_args.kwargs['redirect'])

    def test_amfi_stream_cap_applies_without_content_length(self):
        response = Mock(status=200, headers={'Content-Type': 'text/plain'})
        response.read.side_effect = [b'x' * 65536] * 123
        pool = Mock()
        pool.urlopen.return_value = response
        with patch('alfred_ai.services.public_http._resolve_host_ips', return_value=[ipaddress.ip_address('93.184.215.14')]), patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool', return_value=pool):
            result = self.portfolio._get_amfi_latest_nav_report()
        self.assertEqual(result['items'], [])
        self.assertLessEqual(response.read.call_count, 123)
        response.close.assert_called_once()

    def test_provider_exception_is_not_persisted_or_returned(self):
        marker = r'F:\private\source secret-token synthetic-account-123'
        with patch('alfred_ai.services.public_http.request', side_effect=RuntimeError(marker)), self.assertLogs('apps.integrations.services.verified_intelligence', level='ERROR') as logs:
            result = self.verified.world_bank_indicator('SYNTHETIC', 'Synthetic indicator', force=True)
        record = VerifiedExternalInsight.objects.get(cache_key='world-bank:SYNTHETIC')
        self.assertNotIn(marker, str(result))
        self.assertNotIn(marker, str(record.payload) + record.notes + record.last_refresh_error)
        self.assertNotIn(marker, '\n'.join(logs.output))
        self.assertTrue(record.payload['error_id'])

    def test_amfi_text_and_html_success_remain_usable(self):
        with patch('alfred_ai.services.public_http.request', return_value=PublicResponse(b'<h2>Bank market news</h2>', 'text/html')):
            self.assertEqual(len(self.portfolio._scrape_trending_sectors()), 1)
