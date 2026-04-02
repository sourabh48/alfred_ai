import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.mobility.models import BikeProfile


class AdvisoryEvidenceFreshnessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="advisory_freshness",
            password="Pass12345!",
            monthly_income=85000,
            rent_or_emi=18000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_travel_advisor_preview_exposes_evidence_freshness(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            make="Royal Enfield",
            model_name="Hunter 350",
            vehicle_type="motorcycle",
            bike_class="retro",
            expected_mileage_kmpl=36,
            fuel_tank_capacity_l=13,
            is_primary=True,
        )
        with patch(
            "apps.mobility.services.travel_advisor.verified_intelligence.geocode_destination",
            return_value=_insight(
                {"display_name": "Darjeeling", "latitude": 27.03, "longitude": 88.26},
                "OpenStreetMap Nominatim",
            ),
        ), patch(
            "apps.mobility.services.travel_advisor.verified_intelligence.weather_snapshot",
            return_value=_insight(
                {"average_max_temp": 24, "average_min_temp": 16, "precipitation_total": 8, "wind_max": 18},
                "Open-Meteo",
            ),
        ), patch(
            "apps.mobility.services.travel_advisor.verified_intelligence.offbeat_suggestions",
            return_value=_insight(
                {"results": [{"name": "Lamahatta", "distance_km": 23}]},
                "OpenStreetMap Nominatim",
            ),
        ):
            response = self.client.post(
                "/api/mobility/travel-advisor/preview/",
                data=json.dumps(
                    {
                        "destination": "Darjeeling",
                        "start_date": date.today().isoformat(),
                        "end_date": date.today().isoformat(),
                        "budget": 12000,
                        "transport_mode": "ride",
                        "vehicle_profile_id": profile.id,
                    }
                ),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["evidence_freshness"]["tracked_records"], 3)
        self.assertEqual(payload["evidence_freshness"]["fresh_records"], 3)

    def test_risk_outlook_exposes_evidence_freshness(self):
        with patch(
            "apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
            return_value={
                "risk_score": 28,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {
                    "unemployment": {"latest_value": 5.1},
                    "inflation": {"latest_value": 4.8},
                    "market": {"one_month_return_pct": 2.1, "india_vix": 14.0},
                },
                "insights": ["Signals are stable."],
                "evidence": [
                    {
                        "source_name": "World Bank",
                        "source_url": "https://example.com/world-bank",
                        "status": "fresh",
                        "stale_after": "2026-04-30T00:00:00+05:30",
                    }
                ],
            },
        ), patch(
            "apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
            return_value={"summary": {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0, "latest_condition_score": 82, "document_compliance_score": 100}},
        ):
            response = self.client.get("/api/risk/outlook/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["evidence_freshness"]["tracked_records"], 1)
        self.assertEqual(
            payload["evidence_freshness"]["fresh_records"],
            payload["evidence_freshness"]["tracked_records"],
        )


def _insight(payload, source_name):
    class DummyInsight:
        def __init__(self):
            self.payload = payload
            self.evidence = {
                "source_name": source_name,
                "source_url": "https://example.com/proof",
                "status": "fresh",
                "stale_after": "2026-04-30T00:00:00+05:30",
            }

    return DummyInsight()
