from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services import job_intelligence
from apps.ml_engine.models import DocumentParserLearningMemory


class CareerRecruiterAndEvidenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="career_intake_user",
            password="Pass12345!",
            monthly_income=95000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.html", b"<html></html>", content_type="text/html"),
            file_name="resume.html",
            parser_status="parsed",
            parse_confidence=0.84,
            extracted_payload={
                "role": "Data Analyst",
                "experience_years": 4,
                "skills": ["Python", "SQL", "Power BI"],
            },
            summary="Parsed resume",
        )

    def test_recruiter_match_endpoint_persists_analysis_and_parser_learning(self):
        with patch(
            "apps.career.views.verified_intelligence.macro_context",
            return_value={
                "payload": {
                    "unemployment": {"latest_value": 5.2, "latest_year": 2025},
                    "inflation": {"latest_value": 4.9, "latest_year": 2025},
                    "market": {"one_month_return_pct": 1.7, "india_vix": 14.0},
                },
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value={
                "risk_score": 31,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {},
                "insights": ["Hiring conditions are usable."],
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value={
                "openings": [
                    {
                        "title": "Senior Data Analyst",
                        "company": "Example Analytics",
                        "location": "Bengaluru",
                        "url": "https://example.com/jobs/1",
                        "salary": "18-22 LPA",
                        "tags": ["SQL", "Python", "Power BI"],
                    }
                ],
                "evidence": {"source_name": "Remotive Jobs API", "status": "fresh"},
            },
        ):
            response = self.client.post(
                "/api/career/recruiter-match/",
                data={
                    "message_text": "\n".join(
                        [
                            "Role: Senior Data Analyst",
                            "Company: Example Analytics",
                            "Location: Bengaluru",
                            "Compensation: 18-22 LPA",
                            "Need Python, SQL, Power BI",
                            "Apply here: https://example.com/jobs/1",
                        ]
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["compensation_benchmark"]["available"])
        analysis = CareerJobAnalysis.objects.latest("id")
        self.assertEqual(analysis.extracted_payload["job_snapshot"]["source_kind"], "recruiter_message")
        self.assertEqual(analysis.company, "Example Analytics")
        self.assertEqual(analysis.parser_status, "parsed")
        self.assertGreaterEqual(analysis.parse_confidence, 0.62)
        self.assertTrue(
            DocumentParserLearningMemory.objects.filter(
                user=self.user,
                scope="recruiter_document",
            ).exists()
        )

    def test_career_dashboard_and_tax_overview_expose_materialized_and_evidence_metadata(self):
        with patch(
            "apps.career.views.verified_intelligence.macro_context",
            return_value={
                "payload": {
                    "unemployment": {"latest_value": 5.1, "latest_year": 2025},
                    "inflation": {"latest_value": 4.8, "latest_year": 2025},
                    "market": {"one_month_return_pct": 1.9, "india_vix": 15.0},
                },
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value={
                "risk_score": 29,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {},
                "insights": ["Stable demand."],
                "evidence": [],
            },
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value={"openings": [], "evidence": {"source_name": "Remotive Jobs API", "status": "fresh"}},
        ):
            first = self.client.get("/api/career/dashboard/")
            second = self.client.get("/api/career/dashboard/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["_materialized"]["cached"])
        self.assertTrue(second.json()["_materialized"]["cached"])

        tax_response = self.client.get("/api/integrations/tax/overview/")
        self.assertEqual(tax_response.status_code, 200)
        tax_payload = tax_response.json()
        self.assertEqual(tax_payload["tax_evidence"]["freshness"]["tracked_records"], 3)
        self.assertEqual(len(tax_payload["tax_evidence"]["evidence"]), 3)

    def test_parse_job_page_supports_workday_pages(self):
        response = Mock()
        response.text = """
            <html>
              <head>
                <meta name="application-name" content="Example Analytics" />
                <meta name="description" content="Location Bengaluru, Karnataka, India. Compensation 18-22 LPA." />
              </head>
              <body>
                <div data-automation-id="jobPostingHeader"><h1>Senior Data Analyst</h1></div>
                <div data-automation-id="locations">Bengaluru, Karnataka, India</div>
                <div data-automation-id="jobPostingDescription">Need Python, SQL, Power BI.</div>
              </body>
            </html>
        """
        response.raise_for_status = Mock()

        with patch("apps.career.services.job_intelligence.requests.get", return_value=response):
            snapshot = job_intelligence.parse_job_page(
                "https://example.wd5.myworkdayjobs.com/en-US/careers/job/Bengaluru/Senior-Data-Analyst_JR-1"
            )

        self.assertEqual(snapshot.source_name, "Workday")
        self.assertEqual(snapshot.company, "Example Analytics")
        self.assertEqual(snapshot.title, "Senior Data Analyst")
        self.assertIn("Bengaluru", snapshot.location)
        self.assertEqual(snapshot.salary_min, 1800000)
        self.assertEqual(snapshot.salary_max, 2200000)

    def test_parse_job_page_supports_ashby_pages(self):
        response = Mock()
        response.text = """
            <html>
              <head>
                <meta property="og:site_name" content="Northwind Labs" />
              </head>
              <body>
                <main>
                  <h1>Staff Data Engineer</h1>
                  <section><strong>Location</strong> Bengaluru, Karnataka, India</section>
                  <section data-testid="job-posting-description">
                    Build pipelines with Python, SQL, Airflow, and Spark. Compensation 40-48 LPA.
                  </section>
                </main>
              </body>
            </html>
        """
        response.raise_for_status = Mock()

        with patch("apps.career.services.job_intelligence.requests.get", return_value=response):
            snapshot = job_intelligence.parse_job_page("https://jobs.ashbyhq.com/northwind/abcd-1234")

        self.assertEqual(snapshot.source_name, "Ashby")
        self.assertEqual(snapshot.company, "Northwind Labs")
        self.assertEqual(snapshot.title, "Staff Data Engineer")
        self.assertIn("Bengaluru", snapshot.location)
        self.assertEqual(snapshot.salary_min, 4000000)
        self.assertEqual(snapshot.salary_max, 4800000)

    def test_salary_parser_supports_rupee_en_dash_lpa_ranges(self):
        salary = job_intelligence._parse_salary_text("Compensation: \u20b918\u201322 LPA")

        self.assertEqual(salary["currency"], "INR")
        self.assertEqual(salary["salary_min"], 1800000)
        self.assertEqual(salary["salary_max"], 2200000)
