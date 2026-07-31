import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class ApplicationSmokeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="smoke_user",
            password="Pass12345!",
            monthly_income=95000,
            rent_or_emi=24000,
            city="Bengaluru",
        )
        self.superuser = user_model.objects.create_superuser(
            username="smoke_admin",
            password="Pass12345!",
            email="admin@example.com",
        )
        self.client = Client()

    def test_main_pages_render_for_authenticated_user(self):
        self.client.force_login(self.user)
        page_paths = [
            "/dashboard/",
            "/documents/",
            "/expenses/",
            "/budgets/",
            "/loans/",
            "/investments/",
            "/family/",
            "/career/",
            "/behavioral/",
            "/relationship/",
            "/risk/",
            "/mobility/",
            "/bike-service/",
            "/credit-score/",
            "/recommendations/",
            "/tax-optimizer/",
        ]

        for path in page_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_global_remove_data_button_renders_once_per_authenticated_page(self):
        self.client.force_login(self.user)
        for path in ("/dashboard/", "/career/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="navbarClearDataBtn"', count=1)

    def test_core_create_and_dashboard_endpoints_work_end_to_end(self):
        self.client.force_login(self.user)

        expense_response = self.client.post(
            "/api/expenses/",
            data=json.dumps({
                "amount": 275.5,
                "classification": "expense",
                "category": "food",
                "payment_mode": "UPI",
                "merchant": "Cafe Test",
                "description": "Lunch smoke test",
                "transaction_date": "2026-03-15",
                "direction": "debit",
                "source": "manual",
            }),
            content_type="application/json",
        )
        self.assertEqual(expense_response.status_code, 201)

        budget_response = self.client.post(
            "/api/budgets/",
            data=json.dumps({
                "month": "March 2026",
                "base_budget": 50000,
                "inflation_adjusted": 52000,
                "spent": 275.5,
            }),
            content_type="application/json",
        )
        self.assertEqual(budget_response.status_code, 201)

        behavioral_response = self.client.post(
            "/api/behavioral/",
            data=json.dumps({"stress_score": 4.5, "sleep_hours": 7.0, "work_hours": 8.5}),
            content_type="application/json",
        )
        self.assertEqual(behavioral_response.status_code, 201)

        risk_response = self.client.post(
            "/api/risk/",
            data=json.dumps({"layoff_risk": 3.0, "illness_risk": 2.0, "relocation_risk": 4.0}),
            content_type="application/json",
        )
        self.assertEqual(risk_response.status_code, 201)

        bike_response = self.client.post(
            "/api/mobility/bikes/",
            data=json.dumps({
                "vehicle_type": "motorcycle",
                "display_name": "Smoke Bike",
                "make": "Royal Enfield",
                "model_name": "Hunter 350",
                "bike_class": "roadster",
                "vehicle_number": "KA01AB1234",
                "usage_pattern": "personal",
                "expected_mileage_kmpl": 35,
                "service_interval_km": 5000,
                "service_interval_days": 180,
            }),
            content_type="application/json",
        )
        self.assertEqual(bike_response.status_code, 201)

        travel_response = self.client.post(
            "/api/mobility/travel-plans/",
            data=json.dumps({
                "vehicle_profile": bike_response.json()["id"],
                "title": "Smoke Ride",
                "destination": "Mysuru",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
                "budget": 4500,
                "transport_mode": "ride",
                "status": "planned",
            }),
            content_type="application/json",
        )
        self.assertEqual(travel_response.status_code, 201)

        macro_payload = {
            "payload": {
                "unemployment": {"latest_value": 5.0, "latest_year": 2024},
                "inflation": {"latest_value": 4.8, "latest_year": 2024},
                "market": {"one_month_return_pct": 2.1, "india_vix": 14.0},
            },
            "evidence": [],
        }
        market_payload = {
            "risk_score": 32,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": macro_payload["payload"],
            "insights": ["Smoke market snapshot."],
            "evidence": [],
        }
        openings_payload = {"openings": [], "evidence": []}
        risk_payload = {
            "history": [],
            "latest": None,
            "outlook": {"risk_level": "moderate"},
            "summary": "Smoke outlook",
            "macro_context": macro_payload["payload"],
            "consolidated_risks": [],
            "related_news": [],
            "action_items": [],
            "module_signals": [],
            "evidence": [],
            "insights": ["Smoke risk outlook"],
        }

        api_paths = [
            "/api/expenses/timeline/",
            "/api/expenses/dashboard/",
            "/api/expenses/chart/",
            "/api/expenses/uploads/",
            "/api/budgets/dashboard/",
            "/api/loans/summary/",
            "/api/loans/metrics/",
            "/api/loans/networth/",
            "/api/behavioral/fingerprint/",
            "/api/behavioral/stress/",
            "/api/mobility/dashboard/",
            "/api/mobility/bike-service-dashboard/",
            "/api/mobility/bike-models/catalog/",
            "/api/ai/runtime-status/",
            "/api/integrations/credit-score/",
            "/api/integrations/recommendations/overview/",
            "/api/integrations/tax/overview/",
        ]

        with patch("apps.career.views.verified_intelligence.macro_context", return_value=macro_payload), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value=market_payload,
        ), patch(
            "apps.career.views.job_intelligence.suggest_openings",
            return_value=openings_payload,
        ), patch(
            "apps.risk.views.risk_intelligence.build_outlook",
            return_value=risk_payload,
        ):
            for path in api_paths + ["/api/career/dashboard/", "/api/career/projection/", "/api/risk/outlook/"]:
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)

    def test_superuser_only_pages_and_api_render(self):
        self.client.force_login(self.superuser)
        for path in ("/reports/", "/project-details/", "/api/project-details/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
