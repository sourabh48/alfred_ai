from ipaddress import ip_address
from unittest.mock import Mock, patch

import urllib3
from django.test import SimpleTestCase

from alfred_ai.services.public_http import PublicHTTPError
from apps.career.services import job_intelligence


class CareerJobHTTPTests(SimpleTestCase):
    def setUp(self):
        dns = patch('alfred_ai.services.public_http._resolve_host_ips',
                    return_value=[ip_address('93.184.215.14')])
        self.dns = dns.start()
        self.addCleanup(dns.stop)
        pool = patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool')
        self.pool_class = pool.start()
        self.addCleanup(pool.stop)
        self.pool = self.pool_class.return_value
        self.response = Mock(status=200, headers={'Content-Type': 'text/html; charset=utf-8'})
        self.response.read.side_effect = [b'<html><h1>Python Developer</h1></html>', b'']
        self.pool.urlopen.return_value = self.response

    def test_html_fetch_pins_dns_once_and_preserves_tls_identity(self):
        snapshot = job_intelligence.parse_job_page('https://example.org/jobs/1')
        self.assertEqual(snapshot.job_url, 'https://example.org/jobs/1')
        self.assertEqual(self.dns.call_count, 1)
        self.assertEqual(self.pool_class.call_args.args[0], '93.184.215.14')
        self.assertEqual(self.pool_class.call_args.kwargs['assert_hostname'], 'example.org')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'example.org')
        self.assertFalse(self.pool.urlopen.call_args.kwargs['redirect'])
        self.assertFalse(self.pool.urlopen.call_args.kwargs['preload_content'])
        self.response.close.assert_called_once()
        self.pool.close.assert_called_once()

    def test_private_dns_and_unsafe_urls_never_connect(self):
        for url in ['http://example.org', 'https://127.0.0.1/',
                    'https://user:secret@example.org/', 'https://example.org:8000/']:
            with self.subTest(url=url), self.assertRaises(PublicHTTPError):
                job_intelligence.parse_job_page(url)
        self.dns.return_value = [ip_address('93.184.215.14'), ip_address('10.0.0.1')]
        with self.assertRaisesRegex(PublicHTTPError, 'unsafe_url'):
            job_intelligence.parse_job_page('https://example.org/')
        self.pool_class.assert_not_called()

    def test_redirect_to_private_host_is_not_followed(self):
        self.response.status = 302
        self.response.headers['Location'] = 'http://169.254.169.254/latest/meta-data'
        with self.assertRaisesRegex(PublicHTTPError, 'redirect_blocked'):
            job_intelligence.parse_job_page('https://example.org/')
        self.assertEqual(self.pool.urlopen.call_count, 1)
        self.response.read.assert_not_called()
        self.response.close.assert_called_once()

    def test_html_size_mime_and_compression_are_bounded(self):
        for headers, code in [({'Content-Type': 'application/pdf'}, 'unexpected_content_type'),
                              ({'Content-Type': 'text/html', 'Content-Encoding': 'gzip'}, 'unexpected_content_encoding'),
                              ({'Content-Type': 'text/html', 'Content-Length': '2000001'}, 'response_too_large')]:
            self.response.headers = headers
            with self.subTest(code=code), self.assertRaisesRegex(PublicHTTPError, code):
                job_intelligence.parse_job_page('https://example.org/')
        self.response.headers = {'Content-Type': 'text/html'}
        self.response.read.side_effect = [b'x' * 65536] * 31
        with self.assertRaisesRegex(PublicHTTPError, 'response_too_large'):
            job_intelligence.parse_job_page('https://example.org/')

    def test_timeout_is_sanitized_and_closes_pool(self):
        self.pool.urlopen.side_effect = urllib3.exceptions.ReadTimeoutError(None, '/?token=secret', 'secret')
        with self.assertRaisesRegex(PublicHTTPError, '^timeout$'):
            job_intelligence.parse_job_page('https://example.org/')
        self.pool.close.assert_called_once()
