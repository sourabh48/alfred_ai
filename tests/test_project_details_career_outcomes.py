from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.career.models import CareerJobAnalysis


class ProjectDetailsCareerOutcomeEntryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="career-entry-user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(
            username="career-entry-admin",
            password="Pass12345!",
            email="career-entry@example.com",
        )
        self.analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/entry",
            company="Entry Co",
            job_title="Senior Data Analyst",
            location="Bengaluru, Karnataka, India",
        )
        self.client = Client()

    def test_project_details_career_outcome_entry_is_superuser_only(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/project-details/career-outcomes/",
            data={
                "analysis": self.analysis.id,
                "outcome": "accepted",
                "salary_text": "INR 24-30 LPA",
                "source_url": "https://example.com/jobs/entry",
                "location": "Bengaluru, Karnataka, India",
                "notes": "Accepted real offer.",
                "salary_currency": "INR",
                "salary_period": "year",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.analysis.refresh_from_db()
        self.assertNotIn("opportunity_outcome", self.analysis.extracted_payload)

    def test_superuser_entry_form_records_valid_outcome_and_project_details_counts_it(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            "/project-details/career-outcomes/",
            data={
                "analysis": self.analysis.id,
                "outcome": "accepted",
                "salary_text": "INR 24-30 LPA",
                "source_url": "https://example.com/jobs/entry",
                "location": "Bengaluru, Karnataka, India",
                "notes": "Accepted real offer.",
                "salary_currency": "INR",
                "salary_period": "year",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/project-details/#careerOutcomeEntry")
        self.analysis.refresh_from_db()
        outcome = self.analysis.extracted_payload["opportunity_outcome"]
        self.assertEqual(outcome["outcome"], "accepted")
        self.assertEqual(outcome["salary_min_annual"], 2400000)
        self.assertEqual(outcome["source_url"], "https://example.com/jobs/entry")
        self.assertEqual(outcome["location"], "Bengaluru, Karnataka, India")

        payload = self.client.get("/api/project-details/").json()
        entry = payload["career_outcome_entry"]
        self.assertEqual(entry["summary"]["validated_outcome_count"], 1)
        self.assertEqual(entry["summary"]["accepted_count"], 1)
        self.assertEqual(entry["summary"]["remaining_salary_bearing_outcomes"], 7)
        self.assertEqual(entry["summary"]["remaining_accepted_outcomes"], 2)
        self.assertEqual(entry["remaining_total"], 7)
        self.assertEqual(entry["remaining_accepted"], 2)
        self.assertEqual(entry["remaining_rejected"], 3)
        self.assertTrue(entry["recent_outcomes"][0]["counts_toward_maturity"])

    def test_entry_form_rejects_missing_salary_source_location_or_required_reason(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            "/project-details/career-outcomes/",
            data={
                "analysis": self.analysis.id,
                "outcome": "rejected",
                "salary_text": "",
                "source_url": "",
                "location": "",
                "notes": "",
                "rejection_reason": "",
                "salary_currency": "INR",
                "salary_period": "year",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter either salary text or both salary minimum and salary maximum.", status_code=400)
        self.assertContains(response, "This field is required.", status_code=400)
        self.assertContains(response, "Rejected outcomes require a rejection reason.", status_code=400)
        self.analysis.refresh_from_db()
        self.assertNotIn("opportunity_outcome", self.analysis.extracted_payload)

    def test_project_details_page_renders_outcome_entry_and_deployment_contract(self):
        self.client.force_login(self.superuser)

        response = self.client.get("/project-details/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="careerOutcomeEntry"')
        self.assertContains(response, 'id="careerOutcomeEntryForm"')
        self.assertContains(response, "Career Outcome Maturity Gate")
        self.assertContains(response, "Deployment Readiness Contract")
        self.assertContains(response, "Scope Completion")
