"""Career 2.0: owner-set application stages, follow-up timing and stale matches after resume changes."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume
from apps.career.services import application_tracker as tracker


def _fit(skills, role="backend engineer", years=4.0, record_id=1, kind="resume_upload"):
    return {"fit": {"sources": [{"kind": kind, "record_id": record_id, "skills": skills, "role": role, "experience_years": years}]}}


class FollowUpTimingTests(SimpleTestCase):
    today = date(2026, 11, 7)

    def at(self, *changes):
        record = None
        for change in changes:
            record = tracker.apply_change(record, change, today=self.today)
        return record

    def test_applied_is_due_after_seven_days_then_weekly_then_cold_after_two(self):
        record = self.at({"stage": "applied", "on": "2026-10-30"})
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["due_on"], "2026-11-06")
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["status"], "due")
        record = tracker.apply_change(record, {"follow_up_sent": True, "on": "2026-11-06"}, today=self.today)
        status = tracker.follow_up_status(record, today=self.today)
        self.assertEqual((status["status"], status["due_on"]), ("upcoming", "2026-11-13"))
        record = tracker.apply_change(record, {"follow_up_sent": True}, today=self.today)
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["status"], "cold")

    def test_interview_is_due_next_day_then_every_three_days(self):
        record = self.at({"stage": "applied", "on": "2026-11-01"}, {"stage": "interview", "on": "2026-11-05"})
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["due_on"], "2026-11-06")
        record = tracker.apply_change(record, {"follow_up_sent": True, "on": "2026-11-06"}, today=self.today)
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["due_on"], "2026-11-09")

    def test_closed_or_unset_stages_track_nothing_and_bad_changes_are_refused(self):
        self.assertEqual(tracker.follow_up_status(None, today=self.today)["status"], "no_stage")
        record = self.at({"stage": "rejected"})
        self.assertEqual(tracker.follow_up_status(record, today=self.today)["status"], "not_tracked")
        refusals = [
            ({"stage": "ghosted"}, "Choose a stage"),
            ({"stage": "applied", "on": "2026-11-08"}, "future"),
            ({"stage": "applied", "follow_up_sent": True}, "not both"),
            ({"follow_up_sent": True}, "only while"),
            ({"stage": "rejected"}, "already"),
            ({"stage": "applied", "on": "2026-11-01"}, "before the last"),
        ]
        record = self.at({"stage": "rejected", "on": "2026-11-05"})
        for change, message in refusals:
            with self.subTest(change=change), self.assertRaisesMessage(ValueError, message):
                tracker.apply_change(record, change, today=self.today)

    def test_match_freshness_reports_the_exact_resume_change(self):
        current = tracker.resume_evidence({"skills": ["Python", "Django", "AWS"], "role": "Backend Engineer", "experience_years": 5},
                                          kind="resume_upload", record_id=2)
        fresh = tracker.match_freshness(_fit(["Python", "Django", "Sql"], years=4.0, record_id=1), current)
        self.assertEqual(fresh["status"], "stale")
        self.assertEqual((fresh["added_skills"], fresh["removed_skills"]), (["Aws"], ["Sql"]))
        self.assertEqual(len(fresh["reasons"]), 3)  # different resume, skills, experience; role unchanged
        same = tracker.match_freshness(_fit(["Python", "Django", "Aws"], years=5.0, record_id=2), current)
        self.assertEqual(same["status"], "current")
        self.assertEqual(tracker.match_freshness({}, current)["status"], "unknown")

    def test_missing_stage_date_never_becomes_a_follow_up_from_today(self):
        status = tracker.follow_up_status({'stage': 'applied'}, today=self.today)
        self.assertEqual(status['status'], 'unavailable')
        self.assertIsNone(status['due_on'])
        self.assertIsNone(status['sent_in_stage'])

    def test_malformed_or_conflicting_history_is_unavailable_and_cannot_be_overwritten(self):
        from copy import deepcopy
        valid = {'stage': 'applied', 'history': [{'stage': 'applied', 'on': '2026-11-01'}]}
        invalid = [dict(valid, history=1), dict(valid, history=[True]),
            dict(valid, history=[{'stage': 'applied', 'on': 'bad'}]),
            dict(valid, history=[{'stage': [], 'on': '2026-11-01'}]),
            dict(valid, history=[{'stage': 'applied', 'on': '2026-12-01'}]),
            dict(valid, history=[{'stage': 'interview', 'on': '2026-11-01'}]),
            dict(valid, follow_ups=[{'stage': 'applied', 'on': {}}]),
            dict(valid, follow_ups=[{'stage': 'applied', 'on': '2026-12-01'}]),
            dict(valid, history=[{'stage':'applied','on':'2026-11-02'}, {'stage':'applied','on':'2026-11-01'}]),
            dict(valid, stage=''), dict(valid, stage=[]),
            dict(valid, history=valid['history']*61)]
        for record in invalid:
            with self.subTest(record=record):
                before = deepcopy(record)
                self.assertEqual(tracker.follow_up_status(record, today=self.today)['status'], 'unavailable')
                with self.assertRaisesMessage(ValueError, 'review'):
                    tracker.apply_change(record, {'stage': 'interview'}, today=self.today)
                self.assertEqual(record, before)

    def test_valid_change_preserves_source_metadata_without_mutating_input(self):
        from copy import deepcopy
        record = self.at({'stage':'applied','on':'2026-11-01'})
        record['provenance'] = {'source':'SYNTHETIC-RETAINED'}
        record['history'][0]['source_note'] = 'Keep this evidence'
        before = deepcopy(record)
        changed = tracker.apply_change(record, {'stage':'interview'}, today=self.today)
        self.assertEqual(changed['provenance'], record['provenance'])
        self.assertEqual(changed['history'][0], record['history'][0])
        self.assertEqual(record, before)


class CareerApplicationApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-career-applications")
        self.other = get_user_model().objects.create_user(username="synthetic-career-other")
        self.client.force_login(self.owner)
        self.analysis = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/1", job_title="Backend Engineer",
                                                         company="Example", extracted_payload=_fit(["Python"], record_id=None, kind="manual_profile"))

    def post(self, analysis, body):
        return self.client.post(f"/api/career/job-analyses/{analysis.pk}/application/", body, content_type="application/json")

    def test_stage_and_follow_up_are_saved_listed_and_never_sent(self):
        applied_on = (timezone.localdate() - timedelta(days=8)).isoformat()
        saved = self.post(self.analysis, {"stage": "applied", "on": applied_on})
        self.assertEqual(saved.status_code, 200, saved.content)
        application = saved.json()["opportunity"]["application"]
        self.assertEqual((application["stage"], application["follow_up"]["status"]), ("applied", "due"))
        due = self.client.get("/api/career/follow-ups/").json()["due"]
        self.assertEqual([row["id"] for row in due], [self.analysis.pk])
        sent = self.post(self.analysis, {"follow_up_sent": True}).json()["opportunity"]["application"]
        self.assertEqual((len(sent["follow_ups"]), sent["follow_up"]["status"]), (1, "upcoming"))
        self.assertEqual(self.client.get("/api/career/follow-ups/").json()["due"], [])
        listed = self.client.get("/api/career/job-analyses/").json()["results"][0]
        self.assertEqual(listed["application"]["stage"], "applied")

    def test_owner_isolation_validation_and_stale_revision(self):
        foreign = CareerJobAnalysis.objects.create(user=self.other, job_url="https://jobs.example.test/2")
        self.assertEqual(self.post(foreign, {"stage": "applied"}).status_code, 404)
        self.assertEqual(self.post(self.analysis, {"stage": "nope"}).status_code, 400)
        self.assertEqual(self.post(self.analysis, {"stage": "applied", "revision": "2000-01-01T00:00:00Z"}).status_code, 409)
        self.analysis.refresh_from_db()
        self.assertNotIn("application", self.analysis.extracted_payload)
        self.assertEqual(self.client.get("/api/career/follow-ups/").json()["due"], [])

    def test_corrupt_history_keeps_other_follow_ups_available_and_preserves_raw_record(self):
        from copy import deepcopy
        bad = {'stage': 'applied', 'history': [{'stage': 'applied', 'on': 'PRIVATE-MALFORMED-DATE'}]}
        self.analysis.extracted_payload = {'application': bad, 'private_source': 'RETAIN-SYNTHETIC-EVIDENCE'}
        self.analysis.save()
        before = deepcopy(self.analysis.extracted_payload)
        valid = CareerJobAnalysis.objects.create(user=self.owner, job_title='Valid Synthetic Opportunity',
            extracted_payload={'application': tracker.apply_change({}, {'stage':'applied','on':
                (timezone.localdate()-timedelta(days=10)).isoformat()}, today=timezone.localdate())})
        response = self.client.get('/api/career/follow-ups/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.json()['due']], [valid.pk])
        self.assertEqual([row['id'] for row in response.json()['unavailable']], [self.analysis.pk])
        self.assertNotIn('PRIVATE-', str(response.json()))
        listed = self.client.get('/api/career/job-analyses/')
        self.assertEqual(listed.status_code, 200)
        row = next(row for row in listed.json()['results'] if row['id'] == self.analysis.pk)
        self.assertEqual(row['application']['follow_up']['status'], 'unavailable')
        self.assertEqual(self.post(self.analysis, {'stage':'interview'}).status_code, 400)
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.extracted_payload, before)

    def test_wrong_history_shapes_are_safe_to_list_and_refused_without_data_loss(self):
        for application in ({'stage':'applied','history':123}, {'stage':[]},
                {'stage':'applied','history':[{'stage':{},'on':'2026-11-01'}]}, ['PRIVATE-LEGACY']):
            with self.subTest(application=application):
                CareerJobAnalysis.objects.filter(pk=self.analysis.pk).update(extracted_payload={'application':application})
                with self.assertNoLogs('django.request', level='ERROR'):
                    listed = self.client.get('/api/career/job-analyses/')
                    follow = self.client.get('/api/career/follow-ups/')
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(follow.status_code, 200)
                self.assertEqual(listed.json()['results'][0]['application']['follow_up']['status'], 'unavailable')
                self.assertIn('no-store', follow['Cache-Control'])
                denied = self.post(self.analysis, {'stage':'interview'})
                self.assertEqual(denied.status_code, 400)
                self.assertNotIn('PRIVATE-', str(denied.json()))
                self.analysis.refresh_from_db()
                self.assertEqual(self.analysis.extracted_payload['application'], application)

    def test_a_new_resume_marks_older_matches_stale_and_versions_compare(self):
        CareerProfile.objects.create(user=self.owner, role="Backend Engineer", experience_years=4, skills="Python")
        first = CareerResume.objects.create(user=self.owner, file_name="v1.pdf", parser_status="parsed",
                                            extracted_payload={"skills": ["Python", "SQL"], "role": "Backend Engineer", "experience_years": 4})
        self.analysis.extracted_payload = _fit(["Python", "Sql"], record_id=first.pk)
        self.analysis.save()
        listed = lambda: self.client.get("/api/career/job-analyses/").json()["results"][0]["match_freshness"]
        self.assertEqual(listed()["status"], "current")
        second = CareerResume.objects.create(user=self.owner, file_name="v2.pdf", parser_status="parsed",
                                             extracted_payload={"skills": ["Python", "Kafka"], "role": "Backend Engineer", "experience_years": 5})
        fresh = listed()
        self.assertEqual((fresh["status"], fresh["added_skills"], fresh["removed_skills"]), ("stale", ["Kafka"], ["Sql"]))
        diff = self.client.get(f"/api/career/resumes/compare/?from={first.pk}&to={second.pk}").json()
        self.assertEqual((diff["added_skills"], diff["removed_skills"], diff["kept_skills"]), (["Kafka"], ["Sql"], ["Python"]))
        self.assertTrue(diff["experience_years"]["changed"])
        foreign = CareerResume.objects.create(user=self.other, file_name="x.pdf")
        self.assertEqual(self.client.get(f"/api/career/resumes/compare/?from={first.pk}&to={foreign.pk}").status_code, 404)
        self.assertEqual(self.client.get("/api/career/resumes/compare/?from=x&to=1").status_code, 400)
