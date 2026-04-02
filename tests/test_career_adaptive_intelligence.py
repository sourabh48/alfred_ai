from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory
from apps.expenses.models import StatementUpload
from apps.integrations.models import CreditScore
from apps.mobility.models import BikeDocument, BikeProfile


class CareerAdaptiveIntelligenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="career_owner",
            password="Pass12345!",
            monthly_income=90000,
        )
        self.other_user = user_model.objects.create_user(
            username="other_owner",
            password="Pass12345!",
            monthly_income=60000,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_resume_learning_memory_is_user_scoped_and_dashboard_returns_study_plan(self):
        resume = SimpleUploadedFile(
            "resume.html",
            b"""
            <html><body>
            <h1>Soura Analyst</h1>
            <p>Data Analyst with 3 years experience in Python, Excel and Tableau.</p>
            <p>Email: soura@example.com</p>
            <p>Phone: 9876543210</p>
            </body></html>
            """,
            content_type="text/html",
        )
        other_resume = SimpleUploadedFile(
            "other-resume.html",
            b"<html><body><h1>Other User</h1><p>Backend developer with Django and AWS.</p></body></html>",
            content_type="text/html",
        )

        response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})
        self.assertEqual(response.status_code, 201)

        other_client = Client()
        other_client.force_login(self.other_user)
        other_response = other_client.post("/api/career/resumes/upload/", data={"resume": other_resume})
        self.assertEqual(other_response.status_code, 201)

        self.assertEqual(CareerResumeLearningMemory.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CareerResumeLearningMemory.objects.filter(user=self.other_user).count(), 1)

        latest_resume = CareerResume.objects.filter(user=self.user).first()
        CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/analyst",
            apply_url="https://example.com/jobs/analyst/apply",
            company="Example Co",
            job_title="Data Analyst",
            location="Bengaluru",
            fit_score=63,
            market_risk_score=34,
            strengths="Matched skills: Python.",
            gaps="Likely missing or weak skills: SQL, Power BI.",
            summary="Test analysis",
            extracted_payload={
                "fit": {
                    "matched_skills": ["Python"],
                    "missing_skills": ["SQL", "Power BI"],
                }
            },
            evidence=[],
        )

        with patch(
            "apps.career.views.verified_intelligence.macro_context",
            return_value={
                "payload": {
                    "unemployment": {"latest_value": 5.1, "latest_year": 2024},
                    "inflation": {"latest_value": 4.8, "latest_year": 2024},
                    "market": {"one_month_return_pct": 2.4, "india_vix": 15.0},
                },
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value={
                "risk_score": 34,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {
                    "unemployment": {"latest_value": 5.1, "latest_year": 2024},
                    "inflation": {"latest_value": 4.8, "latest_year": 2024},
                    "market": {"one_month_return_pct": 2.4, "india_vix": 15.0},
                },
                "insights": ["Market pressure is moderate."],
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value={
                "openings": [
                    {"title": "Data Analyst", "tags": ["SQL", "Power BI", "Excel"], "company_name": "Example Co"},
                    {"title": "BI Analyst", "tags": ["SQL", "Tableau"], "company_name": "Another Co"},
                ],
                "evidence": {},
            },
        ):
            dashboard = self.client.get("/api/career/dashboard/")

        self.assertEqual(dashboard.status_code, 200)
        payload = dashboard.json()
        self.assertEqual(payload["latest_resume"]["id"], latest_resume.id)
        self.assertNotEqual(payload["latest_resume"]["file_name"], "other-resume.html")
        self.assertTrue(payload["study_recommendations"]["tracks"])
        suggested_skills = {item["skill"] for item in payload["study_recommendations"]["tracks"]}
        self.assertTrue({"Sql", "Power Bi"} & suggested_skills)

    @patch(
        "apps.career.views.verified_intelligence.macro_context",
        return_value={
            "payload": {
                "unemployment": {"latest_value": 5.1, "latest_year": 2024},
                "inflation": {"latest_value": 4.8, "latest_year": 2024},
                "market": {"one_month_return_pct": 2.4, "india_vix": 15.0},
            },
            "evidence": [],
        },
    )
    @patch(
        "apps.career.views.job_intelligence.market_outlook",
        return_value={
            "risk_score": 34,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": {
                "unemployment": {"latest_value": 5.1, "latest_year": 2024},
                "inflation": {"latest_value": 4.8, "latest_year": 2024},
                "market": {"one_month_return_pct": 2.4, "india_vix": 15.0},
            },
            "insights": ["Market pressure is moderate."],
            "evidence": [],
        },
    )
    @patch("apps.career.services.job_intelligence.verified_intelligence.remotive_jobs")
    def test_career_dashboard_filters_verified_openings_by_country_and_state(self, remotive_jobs, _market_outlook, _macro_context):
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=3.0,
            skills="Python, SQL, Tableau",
            last_salary=90000,
        )
        remotive_jobs.return_value = SimpleNamespace(
            payload={
                "jobs": [
                    {
                        "title": "Senior Data Analyst",
                        "company": "Example Co",
                        "location": "Bengaluru, Karnataka, India",
                        "category": "Data",
                        "url": "https://boards.greenhouse.io/example/jobs/1",
                        "publication_date": "2026-04-01T10:00:00Z",
                        "salary": "INR 18 LPA",
                        "tags": ["Python", "SQL", "Tableau"],
                    },
                    {
                        "title": "Data Analyst",
                        "company": "Other Co",
                        "location": "Mumbai, Maharashtra, India",
                        "category": "Data",
                        "url": "https://example.com/jobs/2",
                        "publication_date": "2026-04-01T10:00:00Z",
                        "salary": "",
                        "tags": ["Python", "Excel"],
                    },
                    {
                        "title": "Analytics Engineer",
                        "company": "US Co",
                        "location": "San Francisco, California, United States",
                        "category": "Engineering",
                        "url": "https://example.com/jobs/3",
                        "publication_date": "2026-04-01T10:00:00Z",
                        "salary": "$120k",
                        "tags": ["Python", "SQL"],
                    },
                ]
            },
            evidence={
                "source_name": "Remotive Jobs API",
                "source_url": "https://remotive.com/api/remote-jobs",
                "status": "fresh",
                "verified_at": "2026-04-01T10:00:00Z",
            },
        )

        response = self.client.get("/api/career/dashboard/?country=India&state=Karnataka")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["active_opening_filters"]["country"], "India")
        self.assertEqual(payload["active_opening_filters"]["state"], "Karnataka")
        self.assertEqual(payload["opening_counts"]["filtered_candidates"], 1)
        self.assertEqual(payload["openings"][0]["country"], "India")
        self.assertEqual(payload["openings"][0]["state"], "Karnataka")
        self.assertTrue(payload["openings"][0]["verified_source"])
        self.assertEqual(payload["openings"][0]["portal_name"], "Remotive Jobs API")
        self.assertEqual(payload["openings"][0]["portal_family"], "Greenhouse")
        self.assertEqual(payload["openings"][0]["portal_host"], "boards.greenhouse.io")
        self.assertIn("India", payload["opening_filters"]["countries"])
        self.assertIn("Karnataka", payload["opening_filters"]["states_by_country"]["India"])


class UserDataIsolationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="alpha", password="Pass12345!")
        self.other_user = user_model.objects.create_user(username="beta", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_user_document_and_vehicle_data_stay_isolated(self):
        profile = BikeProfile.objects.create(user=self.user, model_name="Hunter 350", display_name="My Bike", vehicle_type="motorcycle")
        other_profile = BikeProfile.objects.create(user=self.other_user, model_name="Nexon", display_name="Other Car", vehicle_type="car")

        StatementUpload.objects.create(user=self.user, file_name="alpha.pdf", source="bank_statement")
        StatementUpload.objects.create(user=self.other_user, file_name="beta.pdf", source="bank_statement")
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("alpha-resume.html", b"<html></html>", content_type="text/html"),
            file_name="alpha-resume.html",
            parser_status="parsed",
            parse_confidence=0.8,
        )
        CareerResume.objects.create(
            user=self.other_user,
            uploaded_file=SimpleUploadedFile("beta-resume.html", b"<html></html>", content_type="text/html"),
            file_name="beta-resume.html",
            parser_status="parsed",
            parse_confidence=0.8,
        )
        BikeDocument.objects.create(user=self.user, bike_profile=profile, bike_name="My Bike", document_type="insurance")
        BikeDocument.objects.create(user=self.other_user, bike_profile=other_profile, bike_name="Other Car", document_type="insurance")

        statements = self.client.get("/api/expenses/uploads/")
        resumes = self.client.get("/api/career/resumes/")
        documents = self.client.get("/api/mobility/bike-documents/")

        self.assertEqual(statements.status_code, 200)
        self.assertEqual(resumes.status_code, 200)
        self.assertEqual(documents.status_code, 200)

        self.assertEqual(len(statements.json()), 1)
        self.assertEqual(statements.json()[0]["file_name"], "alpha.pdf")
        self.assertEqual(len(resumes.json()), 1)
        self.assertEqual(resumes.json()[0]["file_name"], "alpha-resume.html")
        self.assertEqual(len(documents.json()), 1)
        self.assertEqual(documents.json()[0]["bike_name"], "My Bike")


class CreditEstimateIntegrityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="credit_user", password="Pass12345!", monthly_income=85000)
        self.client = Client()
        self.client.force_login(self.user)

    def test_credit_score_endpoint_returns_estimate_without_persisting_fake_bureau_pull(self):
        response = self.client.get("/api/integrations/credit-score/?bureau=CIBIL")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["score_kind"], "estimated")
        self.assertIn("not an official bureau score", payload["detail"].lower())
        self.assertEqual(CreditScore.objects.count(), 0)

        trend = self.client.get("/api/integrations/credit-score/trend/?months=12")
        self.assertEqual(trend.status_code, 200)
        self.assertEqual(trend.json()["trend"], [])
