"""Baseline for the AWIE Career parser pilot (owner approval 2026-11-11).

The same synthetic job is published in three layouts of one employer site. The pilot adds a
Scrapling parser beside BeautifulSoup and adopts it only if it recovers more of EXPECTED on
these layouts than the baseline asserted here.
"""
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.career.services import job_intelligence

URL = 'https://careers.synthetic-employer.example/jobs/4821'
EXPECTED = {
    'title': 'Senior Python Developer',
    'company': 'Synthetic Employer',
    'location': 'Pune',
    'skills': {'python', 'django', 'sql'},
    'experience_years': 5.0,
}
BODY = ('We build Django services in Python. You need 5+ years of experience with Python, '
        'Django and SQL. Location: Pune, Maharashtra, India. Full-time.')

LAYOUTS = {
    # v1: structured schema.org JobPosting.
    'json_ld': f'''<html><head><title>Careers</title><script type="application/ld+json">
{{"@type": "JobPosting", "title": "{EXPECTED['title']}",
 "hiringOrganization": {{"@type": "Organization", "name": "{EXPECTED['company']}"}},
 "jobLocation": {{"address": {{"addressLocality": "Pune", "addressRegion": "Maharashtra", "addressCountry": "IN"}}}},
 "description": "<p>{BODY}</p>"}}</script></head><body><main><p>{BODY}</p></main></body></html>''',
    # v2: schema removed; Open Graph metadata and a main element remain.
    'meta_only': f'''<html><head><title>{EXPECTED['title']} - {EXPECTED['company']}</title>
<meta property="og:title" content="{EXPECTED['title']}">
<meta property="og:site_name" content="{EXPECTED['company']}">
<meta name="description" content="{BODY}"></head>
<body><main class="job-detail"><h1>{EXPECTED['title']}</h1><p>{BODY}</p></main></body></html>''',
    # v3: redesign; metadata dropped, classes renamed, content moved into nested divs.
    'redesign': f'''<html><head><title>Open role</title></head><body>
<div class="x9a"><div class="x9a__hd"><span class="t-xl">{EXPECTED['title']}</span>
<span class="t-sm">{EXPECTED['company']}</span></div>
<div class="x9a__bd"><div><div>{BODY}</div></div></div></div></body></html>''',
}


def recovered(snapshot) -> set[str]:
    """Fields of EXPECTED this snapshot got right; the pilot's comparison metric."""
    found = set()
    if snapshot.title == EXPECTED['title']:
        found.add('title')
    if snapshot.company == EXPECTED['company']:
        found.add('company')
    if EXPECTED['location'] in snapshot.location:
        found.add('location')
    if EXPECTED['skills'] <= {s.lower() for s in snapshot.required_skills}:
        found.add('skills')
    if snapshot.experience_years == EXPECTED['experience_years']:
        found.add('experience_years')
    return found


def parse(html: str):
    with patch('alfred_ai.services.public_http.request', return_value=Mock(content=html.encode())):
        return job_intelligence.parse_job_page(URL)


class CareerLayoutBaselineTests(SimpleTestCase):
    # Current BeautifulSoup parser, measured 2026-11-12. A change that lowers any row is a regression.
    BASELINE = {
        'json_ld': {'title', 'company', 'location', 'skills', 'experience_years'},
        'meta_only': {'title', 'company', 'location', 'skills', 'experience_years'},
        # Redesign keeps company (from the host) and location; the description, so skills and experience, is lost.
        'redesign': {'company', 'location'},
    }

    def test_current_parser_baseline_per_layout(self):
        for name, html in LAYOUTS.items():
            with self.subTest(layout=name):
                self.assertEqual(recovered(parse(html)), self.BASELINE[name])

    def test_redesign_never_invents_title_or_company(self):
        snapshot = parse(LAYOUTS['redesign'])
        self.assertNotEqual(snapshot.title, EXPECTED['title'])
        self.assertIn(snapshot.title, {'', 'Open role'})
        self.assertNotIn(snapshot.company, {'Senior Python Developer'})

    def test_employer_name_skips_job_site_host_labels(self):
        from apps.career.services.job_intelligence import _domain_company
        self.assertEqual(_domain_company('careers.synthetic-employer.example'), 'Synthetic Employer')
        self.assertEqual(_domain_company('jobs.acme.co.uk'), 'Acme')
        self.assertEqual(_domain_company('acme.wd5.myworkdayjobs.com'), 'Acme')
        self.assertEqual(_domain_company('example.org'), 'Example')
        self.assertEqual(_domain_company('jobs.com'), 'Jobs')
