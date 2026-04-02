import json
from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.mobility.models import BikeConditionSnapshot, BikeProfile, BikeServiceRecord, FuelRefillLog
from apps.mobility.services.bike_catalog import build_profile_payload


class MobilityVehicleDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="mobility_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_vehicle_profile_patch_keeps_manual_spec_overrides(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            make="Royal Enfield",
            model_name="Hunter 350",
            vehicle_type="motorcycle",
            bike_class="roadster",
            expected_mileage_kmpl=36,
            service_interval_km=5000,
            service_interval_days=180,
        )

        response = self.client.patch(
            f"/api/mobility/bikes/{profile.id}/",
            data=json.dumps(
                {
                    "display_name": "Hunter 350 City Ride",
                    "vehicle_number": "WB12AB1234",
                    "expected_mileage_kmpl": 41.5,
                    "fuel_tank_capacity_l": 13.5,
                    "service_interval_km": 6200,
                    "service_interval_days": 210,
                    "optimal_cruising_speed_kmph": 78,
                    "is_primary": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.display_name, "Hunter 350 City Ride")
        self.assertEqual(profile.vehicle_number, "WB12AB1234")
        self.assertAlmostEqual(profile.expected_mileage_kmpl, 41.5)
        self.assertAlmostEqual(profile.fuel_tank_capacity_l, 13.5)
        self.assertEqual(profile.service_interval_km, 6200)
        self.assertEqual(profile.service_interval_days, 210)
        self.assertEqual(profile.optimal_cruising_speed_kmph, 78)

    def test_refill_log_create_returns_actual_mileage(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Pulsar N160",
            model_name="Pulsar N160",
            vehicle_type="motorcycle",
            bike_class="roadster",
        )

        response = self.client.post(
            "/api/mobility/bike-refills/",
            data=json.dumps(
                {
                    "bike_profile": profile.id,
                    "refill_date": "2026-03-10",
                    "trip_meter_km": 245,
                    "fuel_liters": 5,
                    "total_cost": 540,
                    "is_full_tank": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["bike_profile"], profile.id)
        self.assertAlmostEqual(payload["actual_mileage_kmpl"], 49.0, places=2)

    def test_bike_service_dashboard_returns_actual_vs_optimal_mileage_trend(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Activa 125",
            model_name="Activa 125",
            vehicle_type="scooter",
            bike_class="scooter",
            expected_mileage_kmpl=50,
            official_source_name="Honda",
            official_source_url="https://www.honda2wheelersindia.com/activa125",
            is_primary=True,
        )
        BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date=date(2026, 1, 10),
            odometer_km=1200,
            service_type="routine",
            cost=900,
        )
        BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date=date(2026, 2, 20),
            odometer_km=1850,
            service_type="routine",
            cost=1100,
        )
        BikeConditionSnapshot.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            captured_at=timezone.make_aware(datetime(2026, 3, 5, 9, 30)),
            odometer_km=1960,
            overall_status="good",
            engine_status="good",
            brake_status="watch",
            tyre_status="good",
            battery_status="good",
            body_status="good",
        )
        FuelRefillLog.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            refill_date=date(2026, 2, 10),
            trip_meter_km=210,
            fuel_liters=4.5,
            total_cost=480,
            is_full_tank=True,
        )
        FuelRefillLog.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            refill_date=date(2026, 3, 1),
            trip_meter_km=232,
            fuel_liters=4.0,
            total_cost=430,
            is_full_tank=True,
        )

        response = self.client.get("/api/mobility/bike-service-dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        mileage_trend = payload["charts"]["mileage_trend"]
        self.assertEqual(mileage_trend["actual_values"], [46.67, 58.0])
        self.assertEqual(mileage_trend["optimal_values"], [50, 50])
        self.assertEqual(mileage_trend["source_name"], "Honda")
        self.assertEqual(payload["summary"]["refill_count"], 2)
        self.assertAlmostEqual(payload["summary"]["average_actual_mileage_kmpl"], 52.34, places=2)

    def test_catalog_endpoint_filters_models_by_vehicle_type(self):
        response = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=car")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["results"])
        self.assertTrue(all(item["vehicle_type"] == "car" for item in payload["results"]))
        self.assertFalse(any(item["vehicle_type"] == "motorcycle" for item in payload["results"]))

    def test_catalog_and_profile_payload_cover_new_manufacturers_and_model_guidance(self):
        motorcycles = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=motorcycle").json()["results"]
        cars = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=car").json()["results"]

        self.assertTrue(any(item["display_name"] == "KTM Duke 200" for item in motorcycles))
        self.assertTrue(any(item["display_name"] == "Toyota Urban Cruiser Hyryder" for item in cars))
        self.assertTrue(any(item["display_name"] == "MG Comet EV" for item in cars))

        payload = build_profile_payload("Hunter 350", make="Royal Enfield")
        guidance_labels = [item["label"] for item in payload["maintenance_guidance"]]
        self.assertIn("Rear-Shock And Tyre Wear Review", guidance_labels)
