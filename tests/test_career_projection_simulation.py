import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from unittest.mock import patch

from apps.career.models import CareerProfile


class CareerProjectionSimulationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="career_sim_user",
            password="Pass12345!",
            monthly_income=82000,
            variable_income=6000,
            rent_or_emi=18000,
            city="Bengaluru",
        )
        CareerProfile.objects.create(
            user=self.user,
            role="Analyst",
            experience_years=2.0,
            skills="Python, SQL",
            last_salary=82000,
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
            "evidence": [
                {
                    "source_name": "World Bank",
                    "source_url": "https://data.worldbank.org",
                    "verified_at": "2026-04-01T12:00:00+05:30",
                    "summary": "Macro evidence",
                }
            ],
        }

    @patch("apps.career.views.verified_intelligence.macro_context")
    def test_projection_simulation_returns_baseline_scenario_and_explicit_assumptions(self, macro_context):
        macro_context.return_value = self._macro_payload()

        response = self.client.post(
            "/api/career/projection/simulate/",
            data=json.dumps({
                "experience_years": 5.0,
                "skills": ["Python", "SQL", "Django", "AWS", "Docker"],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["baseline"]["projection_mode"], "heuristic")
        self.assertEqual(payload["scenario"]["projection_mode"], "heuristic")
        self.assertGreater(
            payload["scenario"]["projections"][-1]["projected_income"],
            payload["baseline"]["projections"][-1]["projected_income"],
        )
        self.assertGreater(payload["delta"]["year_5_projected_income"], 0)
        self.assertTrue(payload["assumptions"]["macro_context_locked"])
        self.assertEqual(payload["assumptions"]["macro_source"], "Current verified macro snapshot")
        self.assertEqual(payload["assumptions"]["overridden_fields"], ["experience_years", "skills"])

    def test_projection_simulation_requires_at_least_one_override(self):
        response = self.client.post(
            "/api/career/projection/simulate/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("simulate", str(response.json()).lower())

    def test_career_page_exposes_simulation_ui(self):
        response = self.client.get("/career/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What-If Simulation")
        self.assertContains(response, 'id="careerSimulationForm"')
        self.assertContains(response, 'id="careerSimulationPanel"')
