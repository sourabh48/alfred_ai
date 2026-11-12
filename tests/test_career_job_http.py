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
        # robots.txt (404 here, so no file) and then the job page: one pinned lookup each.
        statuses = iter([404, 200])

        def answer(*args, **kwargs):
            self.response.status = next(statuses)
            return self.response
        self.pool.urlopen.side_effect = answer
        self.response.read.side_effect = [b'', b'<html><h1>Python Developer</h1></html>', b'']
        snapshot = job_intelligence.parse_job_page('https://example.org/jobs/1')
        self.assertEqual(snapshot.job_url, 'https://example.org/jobs/1')
        self.assertEqual(self.dns.call_count, 2)
        self.assertEqual(self.pool.urlopen.call_args_list[0].args[1], '/robots.txt')
        self.assertEqual(self.pool_class.call_args.args[0], '93.184.215.14')
        self.assertEqual(self.pool_class.call_args.kwargs['assert_hostname'], 'example.org')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'example.org')
        self.assertFalse(self.pool.urlopen.call_args.kwargs['redirect'])
        self.assertFalse(self.pool.urlopen.call_args.kwargs['preload_content'])
        self.assertEqual(self.response.close.call_count, 2)
        self.assertEqual(self.pool.close.call_count, 2)

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


class CareerFreeJobBoardAPITests(SimpleTestCase):
    """Greenhouse and Lever postings come from their free public JSON APIs, never their HTML pages."""

    def setUp(self):
        dns = patch('alfred_ai.services.public_http._resolve_host_ips', return_value=[ip_address('93.184.215.14')])
        dns.start()
        self.addCleanup(dns.stop)
        pool = patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool')
        self.pool_class = pool.start()
        self.addCleanup(pool.stop)
        self.pool = self.pool_class.return_value
        self.response = Mock(status=200, headers={'Content-Type': 'application/json'})
        self.pool.urlopen.return_value = self.response

    def reply(self, payload):
        import json
        self.response.read.side_effect = [json.dumps(payload).encode(), b'']

    def test_greenhouse_posting_uses_job_board_api(self):
        self.reply({'title': 'Data Engineer', 'company_name': 'Synthetic Co', 'location': {'name': 'Pune, India'},
                    'absolute_url': 'https://job-boards.greenhouse.io/synthetic/jobs/4821',
                    'content': '&lt;p&gt;Build Python and SQL pipelines. 3+ years experience.&lt;/p&gt;'
                               '&lt;script&gt;alert(1)&lt;/script&gt;'})
        job = job_intelligence.parse_job_page('https://boards.greenhouse.io/synthetic/jobs/4821?gh_src=x')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'boards-api.greenhouse.io')
        self.assertEqual(self.pool.urlopen.call_args.args[1], '/v1/boards/synthetic/jobs/4821')
        self.assertEqual(self.pool.urlopen.call_count, 1)
        self.assertEqual((job.source_name, job.company, job.title, job.location),
                         ('Greenhouse', 'Synthetic Co', 'Data Engineer', 'Pune, India'))
        self.assertIn('Python', job.required_skills)
        self.assertNotIn('<', job.description)
        self.assertEqual(job.apply_url, 'https://job-boards.greenhouse.io/synthetic/jobs/4821')

    def test_lever_posting_uses_postings_api_with_stated_pay(self):
        posting = '0f0e0d0c-0b0a-4908-8706-050403020100'
        self.reply({'text': 'Backend Engineer', 'categories': {'location': 'Remote', 'commitment': 'Full-time'},
                    'descriptionPlain': 'Django services.', 'additionalPlain': '',
                    'lists': [{'text': 'Requirements', 'content': '<li>Docker</li><li>SQL</li>'}],
                    'applyUrl': f'https://jobs.lever.co/synthetic-labs/{posting}/apply',
                    'salaryRange': {'currency': 'USD', 'interval': 'per-year-salary', 'min': 90000, 'max': 120000}})
        job = job_intelligence.parse_job_page(f'https://jobs.lever.co/synthetic-labs/{posting}')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'api.lever.co')
        self.assertEqual(self.pool.urlopen.call_args.args[1], f'/v0/postings/synthetic-labs/{posting}')
        self.assertEqual((job.company, job.title, job.location, job.employment_type),
                         ('Synthetic Labs', 'Backend Engineer', 'Remote', 'Full-time'))
        self.assertEqual((job.salary_min, job.salary_max, job.salary_currency, job.salary_period),
                         (90000.0, 120000.0, 'USD', 'year'))
        self.assertIn('Docker', job.required_skills)

    def test_unknown_pay_interval_is_not_guessed(self):
        posting = '0f0e0d0c-0b0a-4908-8706-050403020100'
        self.reply({'text': 'Analyst', 'salaryRange': {'currency': 'EUR', 'interval': 'one-time', 'min': 5, 'max': 9}})
        job = job_intelligence.parse_job_page(f'https://jobs.eu.lever.co/synthetic/{posting}')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'api.eu.lever.co')
        self.assertEqual(job.salary_period, '')

    def test_api_failure_does_not_fall_back_to_reading_the_page(self):
        for payload in (['not', 'an', 'object'], None):
            with self.subTest(payload=payload):
                self.pool.urlopen.reset_mock()
                if payload is None:
                    self.response.read.side_effect = [b'{broken', b'']
                else:
                    self.reply(payload)
                with self.assertRaisesRegex(PublicHTTPError, 'api_error'):
                    job_intelligence.parse_job_page('https://boards.greenhouse.io/synthetic/jobs/1')
                self.assertEqual(self.pool.urlopen.call_count, 1)

    def test_other_board_paths_still_read_the_page(self):
        self.response.headers = {'Content-Type': 'text/html'}
        statuses = iter([404, 200])  # no robots.txt, then the page

        def answer(*args, **kwargs):
            self.response.status = next(statuses)
            return self.response
        self.pool.urlopen.side_effect = answer
        self.response.read.side_effect = [b'', b'<html><h1>Careers</h1></html>', b'']
        job_intelligence.parse_job_page('https://boards.greenhouse.io/synthetic')
        self.assertEqual(self.pool.urlopen.call_args.args[1], '/synthetic')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'boards.greenhouse.io')


class CareerAshbyAndRobotsTests(SimpleTestCase):
    POSTING = '0f0e0d0c-0b0a-4908-8706-050403020100'

    def setUp(self):
        dns = patch('alfred_ai.services.public_http._resolve_host_ips', return_value=[ip_address('93.184.215.14')])
        dns.start()
        self.addCleanup(dns.stop)
        pool = patch('alfred_ai.services.public_http.urllib3.HTTPSConnectionPool')
        self.pool_class = pool.start()
        self.addCleanup(pool.stop)
        self.pool = self.pool_class.return_value
        self.responses = []
        self.pool.urlopen.side_effect = lambda *a, **k: self.responses.pop(0)

    def add(self, status, mime, body):
        response = Mock(status=status, headers={'Content-Type': mime})
        response.read.side_effect = [body, b''] if body else [b'']
        self.responses.append(response)

    def test_ashby_posting_is_picked_from_the_public_board_api(self):
        import json
        board = {'jobs': [{'id': 'other', 'title': 'Wrong job'},
                          {'id': self.POSTING.upper(), 'title': 'Platform Engineer', 'location': 'Berlin',
                           'employmentType': 'FullTime', 'descriptionPlain': 'Kubernetes and Python.',
                           'applyUrl': f'https://jobs.ashbyhq.com/synthetic/{self.POSTING}/application',
                           'compensation': {'summaryComponents': [
                               {'compensationType': 'EquityPercentage', 'interval': '1 YEAR', 'minValue': 1, 'maxValue': 2},
                               {'compensationType': 'Salary', 'interval': '1 YEAR', 'currencyCode': 'EUR',
                                'minValue': 70000, 'maxValue': 85000}]}}]}
        self.add(200, 'application/json', json.dumps(board).encode())
        job = job_intelligence.parse_job_page(f'https://jobs.ashbyhq.com/synthetic/{self.POSTING}')
        self.assertEqual(self.pool_class.call_args.kwargs['server_hostname'], 'api.ashbyhq.com')
        self.assertEqual(self.pool.urlopen.call_args.args[1],
                         '/posting-api/job-board/synthetic?includeCompensation=true')
        self.assertEqual((job.source_name, job.title, job.location, job.employment_type),
                         ('Ashby', 'Platform Engineer', 'Berlin', 'FullTime'))
        self.assertEqual((job.salary_min, job.salary_max, job.salary_currency, job.salary_period),
                         (70000.0, 85000.0, 'EUR', 'year'))

    def test_ashby_missing_posting_is_reported(self):
        self.add(200, 'application/json', b'{"jobs": []}')
        with self.assertRaisesRegex(PublicHTTPError, 'posting_not_found'):
            job_intelligence.parse_job_page(f'https://jobs.ashbyhq.com/synthetic/{self.POSTING}')
        self.assertEqual(self.pool.urlopen.call_count, 1)

    def test_robots_disallow_stops_before_the_page_is_read(self):
        self.add(200, 'text/plain', b'User-agent: *\nDisallow: /jobs/')
        with self.assertRaisesRegex(PublicHTTPError, 'robots_disallowed'):
            job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')
        self.assertEqual(self.pool.urlopen.call_count, 1)
        self.assertEqual(self.pool.urlopen.call_args.args[1], '/robots.txt')

    def test_missing_robots_or_other_agent_rules_allow_the_page(self):
        for status, body in ((404, b''), (200, b'User-agent: SomeOtherBot\nDisallow: /')):
            with self.subTest(status=status):
                self.pool.urlopen.reset_mock()
                self.add(status, 'text/plain', body)
                self.add(200, 'text/html', b'<html><title>Analyst</title></html>')
                job = job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')
                self.assertEqual(self.pool.urlopen.call_count, 2)
                self.assertEqual(job.title, 'Analyst')

    def test_uncertain_robots_answers_refuse_before_the_page_is_read(self):
        cases = [(200, 'text/html', b'<html>Sign in to this Wi-Fi</html>', 'robots_unreadable'),  # captive portal
                 (200, 'text/plain', b'<!doctype html><p>Not found</p>', 'robots_unreadable'),  # substituted page
                 (200, 'text/plain', b'\xff\xfeUser-agent', 'robots_unreadable'),  # not UTF-8
                 (401, 'text/plain', b'', 'authorization_failed'), (403, 'text/html', b'', 'authorization_failed'),
                 (429, 'text/plain', b'', 'quota_exhausted'), (503, 'text/plain', b'', 'api_error'),
                 (301, 'text/html', b'', 'redirect_blocked'), (200, 'application/json', b'{}', 'unexpected_content_type')]
        for status, mime, body, code in cases:
            with self.subTest(status=status, body=body):
                self.pool.urlopen.reset_mock()
                self.add(status, mime, body)
                with self.assertRaisesRegex(PublicHTTPError, code):
                    job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')
                self.assertEqual(self.pool.urlopen.call_count, 1)
        self.pool.urlopen.side_effect = urllib3.exceptions.ReadTimeoutError(None, '/robots.txt', 'slow')
        with self.assertRaisesRegex(PublicHTTPError, 'timeout'):
            job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')

    def test_robots_rules_ruleless_text_bom_and_404_page(self):
        for status, mime, body in ((410, 'text/html', b'<html>Gone</html>'), (200, 'text/plain', b'# no rules\nnonsense line'),
                                   (200, 'text/plain', b'\xef\xbb\xbfUser-agent: OtherBot\nDisallow: /')):
            with self.subTest(status=status, body=body):
                self.add(status, mime, body)
                self.add(200, 'text/html', b'<html><title>Analyst</title></html>')
                self.assertEqual(job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7').title, 'Analyst')
        self.add(200, 'text/plain', b'\xef\xbb\xbfUser-agent: *\nDisallow: /jobs/')  # a BOM must not hide the rules
        with self.assertRaisesRegex(PublicHTTPError, 'robots_disallowed'):
            job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')

    def test_agent_specific_disallow_is_honoured(self):
        self.add(200, 'text/plain', b'User-agent: AlfredAI\nDisallow: /')
        with self.assertRaisesRegex(PublicHTTPError, 'robots_disallowed'):
            job_intelligence.parse_job_page('https://careers.synthetic.example/jobs/7')
