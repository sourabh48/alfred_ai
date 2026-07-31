from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.career.models import CareerProfile, CareerResume
from apps.expenses.models import Expense


class CareerIncomeSignalsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="career_income_user",
            password="Pass12345!",
            monthly_income=1800000,
            variable_income=60000,
            city="Bengaluru",
        )
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=4,
            skills="Python, SQL, Power BI",
            last_salary=0,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _macro_payload(self):
        return {
            "payload": {
                "unemployment": {"latest_value": 5.0, "latest_year": 2025},
                "inflation": {"latest_value": 4.5, "latest_year": 2025},
                "market": {"one_month_return_pct": 1.5, "india_vix": 13.0},
            },
            "evidence": [],
        }

    def _market_payload(self):
        return {
            "risk_score": 28,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": self._macro_payload()["payload"],
            "insights": ["Market is stable."],
            "evidence": [],
        }

    def test_resume_upload_extracts_current_company_when_explicitly_listed(self):
        resume = SimpleUploadedFile(
            "resume.html",
            b"""
            <html><body>
            <h1>Soura Analyst</h1>
            <p>Current Company: Example Analytics Pvt Ltd</p>
            <p>Data Analyst with 4 years experience in Python, SQL and Power BI.</p>
            <p>Email: soura@example.com</p>
            <p>Phone: 9876543210</p>
            </body></html>
            """,
            content_type="text/html",
        )

        response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})

        self.assertEqual(response.status_code, 201)
        payload = response.json()["resume"]
        self.assertEqual(payload["extracted_payload"]["current_company"], "Example Analytics Pvt Ltd")

    @patch("apps.career.views.job_intelligence.suggest_openings", return_value={"openings": [], "evidence": {}})
    @patch("apps.career.views.job_intelligence.market_outlook")
    @patch("apps.career.views.verified_intelligence.macro_context")
    def test_career_dashboard_prefers_salary_credits_for_monthly_income_and_reported_ctc_for_annual_benchmark(
        self,
        macro_context,
        market_outlook,
        _suggest_openings,
    ):
        macro_context.return_value = self._macro_payload()
        market_outlook.return_value = self._market_payload()
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.html", b"<html></html>", content_type="text/html"),
            file_name="resume.html",
            parser_status="parsed",
            parse_confidence=0.88,
            extracted_payload={
                "role": "Data Analyst",
                "skills": ["Python", "SQL"],
                "current_company": "Example Analytics",
            },
        )
        for index, amount in enumerate((150000.0, 150500.0, 149800.0), start=1):
            Expense.objects.create(
                user=self.user,
                amount=amount,
                classification="other",
                category="income",
                payment_mode="BANK",
                merchant="Example Analytics Payroll",
                description="Monthly salary credit",
                raw_description="SALARY CREDIT EXAMPLE ANALYTICS",
                transaction_date=date(2026, index, 28),
                direction="credit",
                source="bank_statement",
                company_name="Example Analytics",
                counterparty="Example Analytics",
            )

        response = self.client.get("/api/career/dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        signals = payload["employment_signals"]
        self.assertEqual(signals["current_employer"], "Example Analytics")
        self.assertEqual(signals["current_employer_source"], "resume")
        self.assertEqual(signals["reported_income"]["mode"], "annual_ctc")
        self.assertAlmostEqual(signals["monthly_cash_income"], 150000.0, places=0)
        self.assertEqual(signals["annualized_compensation"], 1800000.0)
        self.assertEqual(payload["projection"]["projection_basis"]["current_employer"], "Example Analytics")
        self.assertEqual(payload["projection"]["projection_basis"]["annualized_compensation"], 1800000.0)

    @patch("apps.career.views.job_intelligence.market_outlook")
    @patch("apps.career.views.verified_intelligence.macro_context")
    def test_career_projection_uses_salary_credit_monthly_cash_income_when_reported_field_is_annual_ctc(
        self,
        macro_context,
        market_outlook,
    ):
        macro_context.return_value = self._macro_payload()
        market_outlook.return_value = self._market_payload()
        Expense.objects.create(
            user=self.user,
            amount=152000.0,
            classification="other",
            category="income",
            payment_mode="BANK",
            merchant="Example Analytics Payroll",
            description="Salary credit",
            raw_description="SALARY CREDIT EXAMPLE ANALYTICS",
            transaction_date=date(2026, 1, 28),
            direction="credit",
            source="bank_statement",
            company_name="Example Analytics",
            counterparty="Example Analytics",
        )
        Expense.objects.create(
            user=self.user,
            amount=151500.0,
            classification="other",
            category="income",
            payment_mode="BANK",
            merchant="Example Analytics Payroll",
            description="Salary credit",
            raw_description="SALARY CREDIT EXAMPLE ANALYTICS",
            transaction_date=date(2026, 2, 28),
            direction="credit",
            source="bank_statement",
            company_name="Example Analytics",
            counterparty="Example Analytics",
        )

        response = self.client.get("/api/career/projection/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["employment_signals"]["reported_income"]["mode"], "annual_ctc")
        self.assertAlmostEqual(payload["current_income"], 151750.0, places=0)
        self.assertAlmostEqual(payload["projection_basis"]["reported_current_income"], 151750.0, places=0)
        self.assertEqual(payload["income_signals"]["annualized_compensation"], 1821000.0)
