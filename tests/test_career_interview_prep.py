"""CAREER-07: interview prompts come only from the owner's saved job match."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.career.models import CareerJobAnalysis


class CareerInterviewPrepTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='synthetic-prep-owner')
        self.client.force_login(self.owner)

    def create(self, user=None, fit=None, **extra):
        return CareerJobAnalysis.objects.create(user=user or self.owner, job_title='Synthetic analyst', company='Synthetic Co',
            job_url='https://example.org/synthetic-job', extracted_payload={'fit': fit} if fit is not None else {}, **extra)

    def prep(self, row):
        rows = self.client.get('/api/career/job-analyses/').json()['results']
        return next(item['interview_prep'] for item in rows if item['id'] == row.pk)

    def test_prompts_follow_saved_matched_and_missing_skills(self):
        row = self.create(fit={'matched_skills': ['SQL', 'Python', 7, ''], 'missing_skills': ['Airflow']})
        prep = self.prep(row)
        self.assertTrue(prep['available'])
        self.assertEqual([item['skill'] for item in prep['prove']], ['SQL', 'Python'])
        self.assertEqual([item['skill'] for item in prep['gaps']], ['Airflow'])
        self.assertIn('Synthetic analyst at Synthetic Co?', prep['general'][0])
        self.assertIn('not likely questions or a hiring prediction', prep['basis'])

    def test_without_a_job_match_it_abstains(self):
        for fit in (None, {}, {'matched_skills': 'SQL'}, 'broken'):
            with self.subTest(fit=fit):
                CareerJobAnalysis.objects.all().delete()
                self.assertFalse(self.prep(self.create(fit=fit))['available'])

    def test_foreign_opportunities_are_not_listed(self):
        other = get_user_model().objects.create_user(username='synthetic-prep-other')
        self.create(user=other, fit={'matched_skills': ['FOREIGN-SKILL']})
        self.assertNotIn('FOREIGN-SKILL', self.client.get('/api/career/job-analyses/').content.decode())
