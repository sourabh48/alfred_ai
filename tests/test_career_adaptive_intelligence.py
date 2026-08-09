import json
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory
from apps.career.services.job_intelligence import job_intelligence
from apps.expenses.models import StatementUpload
from apps.integrations.models import CreditScore
from apps.mobility.models import BikeDocument, BikeProfile


class CareerAdaptiveIntelligenceTests(TestCase):
    def setUp(self):
        cache.clear()
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
    @patch("apps.career.services.job_intelligence.verified_intelligence.remoteok_jobs")
    @patch("apps.career.services.job_intelligence.verified_intelligence.arbeitnow_jobs")
    @patch("apps.career.services.job_intelligence.verified_intelligence.remotive_jobs")
    def test_career_dashboard_filters_verified_openings_by_country_and_state(self, remotive_jobs, arbeitnow_jobs, remoteok_jobs, _market_outlook, _macro_context):
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=3.0,
            skills="Python, SQL, Tableau",
            last_salary=90000,
        )
        remotive_jobs.return_value = _job_feed_result(
            "Remotive Jobs API",
            "https://remotive.com/api/remote-jobs",
            [
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
            ],
        )
        arbeitnow_jobs.return_value = _job_feed_result(
            "Arbeitnow Job Board API",
            "https://www.arbeitnow.com/api/job-board-api",
            [
                {
                    "title": "Analytics Engineer",
                    "company": "EU Co",
                    "location": "Berlin, Germany",
                    "category": "Engineering",
                    "url": "https://arbeitnow.com/jobs/analytics-engineer-1",
                    "publication_date": "2026-04-01T10:00:00Z",
                    "salary": "USD 90000 per year",
                    "tags": ["Python", "SQL"],
                }
            ],
        )
        remoteok_jobs.return_value = _job_feed_result(
            "Remote OK API",
            "https://remoteok.com/api",
            [
                {
                    "title": "Remote Data Analyst",
                    "company": "US Co",
                    "location": "Remote",
                    "category": "Data",
                    "url": "https://remoteok.com/remote-jobs/1",
                    "publication_date": "2026-04-01T10:00:00Z",
                    "salary": "USD 120000 per year",
                    "tags": ["Python", "SQL"],
                }
            ],
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
        self.assertTrue(payload["openings"][0]["salary_signal"]["available"])
        self.assertEqual(
            payload["openings_source_coverage"]["configured_feeds"],
            ["Remotive Jobs API", "Arbeitnow Job Board API", "Remote OK API"],
        )
        self.assertEqual(payload["openings_source_coverage"]["configured_feed_count"], 3)
        self.assertEqual(payload["openings_source_coverage"]["live_feed_count"], 3)
        self.assertTrue(payload["openings_source_coverage"]["coverage_complete"])
        self.assertGreaterEqual(payload["openings_source_coverage"]["salary_bearing_candidates"], 2)
        self.assertIn("Remote OK API", payload["openings_source_coverage"]["source_salary_counts"])
        gap_policy = payload["openings_source_coverage"]["specialty_source_gap_policy"]
        self.assertFalse(gap_policy["gap_exposed"])
        self.assertFalse(gap_policy["recommended_sources"])
        self.assertEqual(gap_policy["policy"], "core_feeds_sufficient_for_current_role_geography")
        self.assertIn("India", payload["opening_filters"]["countries"])
        self.assertIn("Karnataka", payload["opening_filters"]["states_by_country"]["India"])
        self.assertTrue(payload["compensation_benchmark"]["available"])
        self.assertEqual(payload["compensation_benchmark"]["geography_scope"]["requested_state"], "Karnataka")
        self.assertEqual(payload["compensation_benchmark"]["geography_scope"]["requested_country"], "India")
        self.assertEqual(payload["compensation_benchmark"]["evidence_contract"]["selected_salary_count"], 1)
        self.assertEqual(payload["compensation_benchmark"]["evidence_contract"]["geo_match_level"], "state")
        self.assertTrue(payload["compensation_benchmark"]["evidence_contract"]["proof_complete"])

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
            "macro_context": {},
            "insights": ["Market pressure is moderate."],
            "evidence": [],
        },
    )
    @patch("apps.career.services.job_intelligence.verified_intelligence.remoteok_jobs")
    @patch("apps.career.services.job_intelligence.verified_intelligence.arbeitnow_jobs")
    @patch("apps.career.services.job_intelligence.verified_intelligence.remotive_jobs")
    def test_career_dashboard_recommends_specialty_sources_only_for_exposed_geo_salary_gap(self, remotive_jobs, arbeitnow_jobs, remoteok_jobs, _market_outlook, _macro_context):
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=3.0,
            skills="Python, SQL, Tableau",
            last_salary=90000,
        )
        remotive_jobs.return_value = _job_feed_result(
            "Remotive Jobs API",
            "https://remotive.com/api/remote-jobs",
            [
                {
                    "title": "Data Analyst",
                    "company": "Local Co",
                    "location": "Bengaluru, Karnataka, India",
                    "category": "Data",
                    "url": "https://example.com/jobs/local-data-analyst",
                    "publication_date": "2026-04-01T10:00:00Z",
                    "salary": "",
                    "tags": ["Python", "SQL"],
                }
            ],
        )
        arbeitnow_jobs.return_value = _job_feed_result(
            "Arbeitnow Job Board API",
            "https://www.arbeitnow.com/api/job-board-api",
            [
                {
                    "title": "Analytics Engineer",
                    "company": "EU Co",
                    "location": "Berlin, Germany",
                    "category": "Engineering",
                    "url": "https://arbeitnow.com/jobs/analytics-engineer-2",
                    "publication_date": "2026-04-01T10:00:00Z",
                    "salary": "USD 90000 per year",
                    "tags": ["Python", "SQL"],
                }
            ],
        )
        remoteok_jobs.return_value = _job_feed_result(
            "Remote OK API",
            "https://remoteok.com/api",
            [
                {
                    "title": "Remote Data Analyst",
                    "company": "US Co",
                    "location": "Remote",
                    "category": "Data",
                    "url": "https://remoteok.com/remote-jobs/2",
                    "publication_date": "2026-04-01T10:00:00Z",
                    "salary": "USD 120000 per year",
                    "tags": ["Python", "SQL"],
                }
            ],
        )

        response = self.client.get("/api/career/dashboard/?country=India&state=Karnataka")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["opening_counts"]["filtered_candidates"], 1)
        self.assertFalse(payload["openings"][0]["salary_signal"]["available"])
        gap_policy = payload["openings_source_coverage"]["specialty_source_gap_policy"]
        self.assertTrue(gap_policy["gap_exposed"])
        self.assertEqual(gap_policy["role_family"], "data")
        self.assertEqual(gap_policy["requested_country"], "India")
        self.assertEqual(gap_policy["filtered_salary_bearing_candidates"], 0)
        recommended_names = {item["name"] for item in gap_policy["recommended_sources"]}
        self.assertTrue({"Naukri", "Instahyre"} <= recommended_names)
        self.assertEqual(gap_policy["policy"], "candidate_only_until_connector_or_adapter_is_added")

    def test_career_job_outcome_endpoint_records_salary_bearing_decisions_and_dashboard_summary(self):
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=4.0,
            skills="Python, SQL, Power BI",
            last_salary=90000,
        )
        accepted_analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/accepted",
            apply_url="https://example.com/jobs/accepted/apply",
            company="Accepted Co",
            job_title="Senior Data Analyst",
            location="Bengaluru, Karnataka, India",
            fit_score=82,
            market_risk_score=24,
            summary="Accepted role",
            extracted_payload={"job_snapshot": {"title": "Senior Data Analyst", "company": "Accepted Co", "location": "Bengaluru, Karnataka, India", "source_kind": "recruiter_message"}},
            evidence=[],
        )
        rejected_analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/rejected",
            apply_url="https://example.com/jobs/rejected/apply",
            company="Rejected Co",
            job_title="BI Analyst",
            location="Bengaluru, Karnataka, India",
            fit_score=72,
            market_risk_score=31,
            summary="Rejected role",
            extracted_payload={"job_snapshot": {"title": "BI Analyst", "company": "Rejected Co", "location": "Bengaluru, Karnataka, India", "source_kind": "job_page"}},
            evidence=[],
        )

        accepted_response = self.client.post(
            f"/api/career/job-analyses/{accepted_analysis.id}/outcome/",
            data=json.dumps({"outcome": "accepted", "salary_text": "INR 24-30 LPA", "notes": "Offer accepted."}),
            content_type="application/json",
        )
        rejected_response = self.client.post(
            f"/api/career/job-analyses/{rejected_analysis.id}/outcome/",
            data=json.dumps({"outcome": "rejected", "salary_text": "INR 18-22 LPA", "rejection_reason": "Below target."}),
            content_type="application/json",
        )

        self.assertEqual(accepted_response.status_code, 200)
        self.assertEqual(rejected_response.status_code, 200)
        accepted_analysis.refresh_from_db()
        self.assertEqual(accepted_analysis.extracted_payload["opportunity_outcome"]["outcome"], "accepted")
        self.assertTrue(accepted_analysis.extracted_payload["opportunity_outcome"]["salary_bearing"])
        self.assertEqual(accepted_analysis.extracted_payload["opportunity_outcome"]["salary_min_annual"], 2400000)
        self.assertEqual(
            accepted_analysis.extracted_payload["opportunity_outcome"]["source_url"],
            "https://example.com/jobs/accepted",
        )
        self.assertEqual(
            accepted_analysis.extracted_payload["opportunity_outcome"]["location"],
            "Bengaluru, Karnataka, India",
        )
        summary = rejected_response.json()["opportunity_outcome_learning"]
        self.assertEqual(summary["salary_bearing_outcome_count"], 2)
        self.assertEqual(summary["accepted_count"], 1)
        self.assertEqual(summary["rejected_count"], 1)
        self.assertEqual(summary["maturity_status"], "collecting")

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
                "macro_context": {},
                "insights": ["Market pressure is moderate."],
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value={"openings": [], "evidence": {}, "source_coverage": {}},
        ):
            dashboard = self.client.get("/api/career/dashboard/")

        self.assertEqual(dashboard.status_code, 200)
        dashboard_summary = dashboard.json()["opportunity_outcome_learning"]
        self.assertEqual(dashboard_summary["salary_bearing_outcome_count"], 2)
        self.assertEqual(dashboard_summary["accepted_count"], 1)
        self.assertEqual(dashboard_summary["rejected_count"], 1)

    def test_career_job_outcome_endpoint_rejects_incomplete_salary_source_location_contract(self):
        missing_source = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="",
            company="Missing Source Co",
            job_title="Data Analyst",
            location="Bengaluru, Karnataka, India",
            extracted_payload={"job_snapshot": {"location": "Bengaluru, Karnataka, India"}},
        )
        missing_location = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/missing-location",
            company="Missing Location Co",
            job_title="Data Analyst",
            location="",
            extracted_payload={"job_snapshot": {"location": ""}},
        )
        missing_salary = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/missing-salary",
            company="Missing Salary Co",
            job_title="Data Analyst",
            location="Bengaluru, Karnataka, India",
        )

        missing_source_response = self.client.post(
            f"/api/career/job-analyses/{missing_source.id}/outcome/",
            data=json.dumps({"outcome": "accepted", "salary_text": "INR 20-24 LPA"}),
            content_type="application/json",
        )
        missing_location_response = self.client.post(
            f"/api/career/job-analyses/{missing_location.id}/outcome/",
            data=json.dumps({"outcome": "rejected", "salary_text": "INR 18-22 LPA"}),
            content_type="application/json",
        )
        missing_salary_response = self.client.post(
            f"/api/career/job-analyses/{missing_salary.id}/outcome/",
            data=json.dumps({"outcome": "accepted"}),
            content_type="application/json",
        )

        self.assertEqual(missing_source_response.status_code, 400)
        self.assertIn("source URL", missing_source_response.json()["detail"])
        self.assertEqual(missing_location_response.status_code, 400)
        self.assertIn("location", missing_location_response.json()["detail"])
        self.assertEqual(missing_salary_response.status_code, 400)
        self.assertIn("salary evidence", missing_salary_response.json()["detail"])
        for analysis in [missing_source, missing_location, missing_salary]:
            analysis.refresh_from_db()
            self.assertNotIn("opportunity_outcome", analysis.extracted_payload)

        summary = job_intelligence.opportunity_outcome_learning_summary(
            CareerJobAnalysis.objects.filter(id__in=[missing_source.id, missing_location.id, missing_salary.id])
        )
        self.assertEqual(summary["outcome_count"], 0)
        self.assertEqual(summary["validated_outcome_count"], 0)

    def test_career_job_outcome_endpoint_accepts_structured_location_contract(self):
        analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/structured-location",
            company="Structured Location Co",
            job_title="Data Analyst",
            location="",
        )

        response = self.client.post(
            f"/api/career/job-analyses/{analysis.id}/outcome/",
            data=json.dumps(
                {
                    "outcome": "accepted",
                    "salary_text": "INR 21-25 LPA",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "country": "India",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        analysis.refresh_from_db()
        outcome = analysis.extracted_payload["opportunity_outcome"]
        self.assertEqual(outcome["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(outcome["city"], "Bengaluru")
        self.assertEqual(outcome["state"], "Karnataka")
        self.assertEqual(outcome["country"], "India")

    def test_opportunity_outcome_summary_counts_only_validated_salary_source_location_decisions(self):
        valid = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/valid",
            company="Valid Co",
            job_title="Data Analyst",
            location="Bengaluru, Karnataka, India",
            extracted_payload={
                "opportunity_outcome": {
                    "outcome": "accepted",
                    "salary_bearing": True,
                    "salary_min_annual": 1800000,
                    "salary_max_annual": 2200000,
                    "salary_mid_annual": 2000000,
                    "source_url": "https://example.com/jobs/valid",
                    "location": "Bengaluru, Karnataka, India",
                    "country": "India",
                    "state": "Karnataka",
                    "city": "Bengaluru",
                }
            },
        )
        missing_source = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/missing-source",
            company="Missing Source Co",
            job_title="Data Analyst",
            location="Bengaluru, Karnataka, India",
            extracted_payload={
                "opportunity_outcome": {
                    "outcome": "rejected",
                    "salary_bearing": True,
                    "salary_min_annual": 1600000,
                    "salary_max_annual": 1800000,
                    "salary_mid_annual": 1700000,
                    "source_url": "",
                    "location": "Bengaluru, Karnataka, India",
                }
            },
        )
        missing_location = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="manual-test",
            job_url="https://example.com/jobs/missing-location",
            company="Missing Location Co",
            job_title="Data Analyst",
            location="",
            extracted_payload={
                "opportunity_outcome": {
                    "outcome": "accepted",
                    "salary_bearing": True,
                    "salary_min_annual": 2000000,
                    "salary_max_annual": 2400000,
                    "salary_mid_annual": 2200000,
                    "source_url": "https://example.com/jobs/missing-location",
                    "location": "",
                }
            },
        )

        summary = job_intelligence.opportunity_outcome_learning_summary(
            CareerJobAnalysis.objects.filter(id__in=[valid.id, missing_source.id, missing_location.id])
        )

        self.assertEqual(summary["outcome_count"], 3)
        self.assertEqual(summary["salary_bearing_outcome_count"], 1)
        self.assertEqual(summary["validated_outcome_count"], 1)
        self.assertEqual(summary["unvalidated_outcome_count"], 2)
        self.assertEqual(summary["accepted_count"], 1)
        self.assertEqual(summary["rejected_count"], 0)
        self.assertEqual(
            summary["validation_contract"],
            ["accepted_or_rejected_decision", "salary_range", "source_url", "location_match"],
        )


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


def _job_feed_result(source_name, source_url, jobs):
    now = timezone.now()
    return SimpleNamespace(
        payload={"jobs": jobs},
        evidence={
            "source_name": source_name,
            "source_url": source_url,
            "summary": f"{source_name} fixture",
            "status": "fresh",
            "fetched_at": now.isoformat(),
            "verified_at": now.isoformat(),
            "stale_after": (now + timedelta(days=2)).isoformat(),
            "query": "Data Analyst",
        },
    )
