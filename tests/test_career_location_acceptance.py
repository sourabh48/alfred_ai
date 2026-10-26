from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.career.models import CareerProfile
from apps.career.services import job_intelligence
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches


def location_feed_results(_term):
    now = timezone.now()
    locations = ['', 'Remote', 'Remote (US only)',
                 'Remote - Bengaluru, Karnataka, India', 'Worldwide',
                 'Non-remote, Mumbai, India', 'India / United States',
                 'Anywhere except United States']
    return [{'source_name': 'Remotive Jobs API', 'evidence': {
        'source_name': 'Remotive Jobs API', 'source_url': 'https://remotive.com/api/remote-jobs',
        'status': 'fresh', 'verified_at': now.isoformat(),
        'stale_after': (now + timedelta(hours=1)).isoformat(),
    }, 'payload': {'jobs': [dict(title=f'Python Developer {i}', company=f'Company {i}',
        location=location, url=f'https://example.org/jobs/{i}', tags=['Python'],
        publication_date='', salary='') for i, location in enumerate(locations)]}}]


class CareerLocationRulesTests(SimpleTestCase):
    def opening(self, location):
        return job_intelligence._normalize_opening(
            {'title': 'Developer', 'location': location}, role='Developer', skills=[], evidence={})

    def test_missing_location_does_not_invent_remote_eligibility(self):
        opening = self.opening('')
        self.assertEqual(opening['location'], '')
        self.assertFalse(opening['is_remote'])
        self.assertFalse(job_intelligence._opening_matches_location(opening, country='Remote'))

    def test_remote_country_restriction_survives_work_model(self):
        for location in ['Remote (US only)', 'United States, Remote', 'Remote - USA']:
            with self.subTest(location=location):
                opening = self.opening(location)
                self.assertEqual(opening['country'], 'United States')
                self.assertTrue(opening['is_remote'])
                self.assertFalse(job_intelligence._opening_matches_location(opening, country='India'))
                self.assertTrue(job_intelligence._opening_matches_location(opening, country='USA'))

    def test_remote_city_and_state_restrictions_remain_filterable(self):
        opening = self.opening('Remote - Bengaluru, Karnataka, India')
        self.assertEqual((opening['country'], opening['state']), ('India', 'Karnataka'))
        self.assertTrue(job_intelligence._opening_matches_location(opening, country='India', state='Karnataka'))
        self.assertFalse(job_intelligence._opening_matches_location(opening, country='India', state='Maharashtra'))

    def test_unqualified_remote_is_not_worldwide(self):
        for location in ['Remote', 'Remote - Europe', 'Anywhere except United States']:
            with self.subTest(location=location):
                self.assertFalse(job_intelligence._opening_matches_location(self.opening(location), country='India'))

    def test_explicit_worldwide_has_no_invented_state(self):
        for location in ['Worldwide', 'Remote, Worldwide', 'Anywhere', 'Global']:
            with self.subTest(location=location):
                opening = self.opening(location)
                self.assertTrue(job_intelligence._opening_matches_location(opening, country='India'))
                self.assertFalse(job_intelligence._opening_matches_location(opening, country='India', state='Karnataka'))

    def test_negated_remote_and_ambiguous_countries_do_not_create_matches(self):
        self.assertFalse(self.opening('Non-remote, Mumbai, India')['is_remote'])
        opening = self.opening('India / United States')
        self.assertEqual(opening['country'], '')
        self.assertFalse(job_intelligence._opening_matches_location(opening, country='India'))

    def test_conflicting_states_and_substring_city_names_do_not_guess(self):
        self.assertEqual(self.opening('Remote, Bengaluru, Maharashtra, India')['country'], '')
        self.assertEqual(self.opening('Austinville')['country'], '')

    def test_country_and_remote_filters_keep_restricted_roles_distinct(self):
        with patch.object(job_intelligence, '_live_job_feed_results', side_effect=location_feed_results):
            india = job_intelligence.suggest_openings('Developer', ['Python'], country='India')
            remote = job_intelligence.suggest_openings('Developer', ['Python'], country='Remote')
        self.assertEqual({i['location'] for i in india['openings']}, {
            'Remote - Bengaluru, Karnataka, India', 'Worldwide', 'Non-remote, Mumbai, India'})
        self.assertNotIn('Non-remote, Mumbai, India', {i['location'] for i in remote['openings']})
        self.assertIn('Remote', india['filters']['countries'])


class CareerLocationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.enterContext(_offline_fixture_patches())
        self.enterContext(patch.object(job_intelligence, '_live_job_feed_results', side_effect=location_feed_results))
        self.enterContext(patch.object(job_intelligence, 'suggest_openings',
            side_effect=lambda *a, **kw: type(job_intelligence).suggest_openings(job_intelligence, *a, **kw)))
        self.owner = get_user_model().objects.create_user(username='location-owner', password='synthetic-only')
        self.other = get_user_model().objects.create_user(username='location-other', password='synthetic-only')
        for user in (self.owner, self.other):
            CareerProfile.objects.create(user=user, role='Developer', skills='Python', experience_years=3)

    def test_filtered_owner_cache_preserves_restrictions_and_records(self):
        before = list(CareerProfile.objects.order_by('pk').values())
        self.client.force_login(self.owner)
        for query, expected in [('country=India', 3), ('country=India&state=Karnataka', 1),
                                ('country=USA', 2), ('country=India', 3)]:
            response = self.client.get('/api/career/dashboard/?' + query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['opening_counts']['filtered_candidates'], expected)
        self.assertEqual(before, list(CareerProfile.objects.order_by('pk').values()))
        self.client.force_login(self.other)
        response = self.client.get(f'/api/career/dashboard/?country=Remote&user_id={self.owner.pk}')
        self.assertEqual(response.json()['profile']['user'], self.other.pk)

    def test_anonymous_request_cannot_read_owned_career(self):
        self.assertIn(self.client.get('/api/career/dashboard/').status_code, (401, 403))
