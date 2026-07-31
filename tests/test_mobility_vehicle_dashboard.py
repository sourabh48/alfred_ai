import json
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.mobility.models import BikeConditionSnapshot, BikeProfile, BikeServiceRecord, FuelRefillLog, TravelPlan, TripLog
from apps.mobility.services.bike_catalog import build_profile_payload, catalog_coverage_summary


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

    def test_vehicle_profile_create_accepts_single_make_field_and_catalog_match(self):
        response = self.client.post(
            "/api/mobility/bikes/",
            data=json.dumps(
                {
                    "vehicle_type": "motorcycle",
                    "display_name": "Hunter 350",
                    "make": "Royal Enfield",
                    "model_name": "Hunter 350",
                    "bike_class": "retro",
                    "usage_pattern": "personal",
                    "vehicle_number": "KA01AB1234",
                    "is_primary": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["make"], "Royal Enfield")
        self.assertEqual(payload["model_name"], "Hunter 350")
        self.assertEqual(payload["catalog_key"], "royal-enfield-hunter-350")
        self.assertEqual(payload["verification_status"], "official")
        self.assertTrue(payload["official_source_url"])

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

    def test_bike_service_dashboard_exposes_route_aware_wear_and_cost_pressure(self):
        today = timezone.localdate()
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            model_name="Hunter 350",
            vehicle_type="motorcycle",
            bike_class="retro",
            expected_mileage_kmpl=36,
            service_interval_km=5000,
            is_primary=True,
        )
        BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date=today - timedelta(days=30),
            odometer_km=4000,
            service_type="routine",
            cost=2200,
        )
        plan = TravelPlan.objects.create(
            user=self.user,
            vehicle_profile=profile,
            title="Hill Ride",
            destination="Coorg",
            start_date=today - timedelta(days=6),
            end_date=today - timedelta(days=4),
            budget=9000,
            transport_mode="ride",
        )
        TripLog.objects.create(
            user=self.user,
            travel_plan=plan,
            log_date=today - timedelta(days=5),
            title="Rain highway ghat ride",
            location_name="Coorg ghat",
            notes="Broken road, rain, hill descent and highway return.",
            distance_km=720,
            spend_amount=3400,
        )

        response = self.client.get("/api/mobility/bike-service-dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["route_wear"]["recent_distance_km"], 720)
        self.assertGreater(payload["route_wear"]["wear_index"], 0)
        self.assertIn(payload["route_wear"]["wear_status"], {"watch", "high"})
        self.assertGreater(payload["summary"]["route_adjusted_service_cost"], payload["summary"]["projected_next_service_cost"])
        self.assertGreaterEqual(payload["summary"]["route_service_buffer"], 800)
        self.assertEqual(payload["route_wear"]["signals"]["rain_route_logs"], 1)
        self.assertEqual(payload["route_wear"]["signals"]["hill_route_logs"], 1)
        self.assertTrue(payload["route_wear"]["maintenance_guidance"]["actions"])
        self.assertTrue(payload["route_wear"]["service_cost_guidance"]["cost_factors"])
        action_labels = [item["label"] for item in payload["route_wear"]["maintenance_guidance"]["actions"]]
        self.assertIn("Rough-Road Inspection", action_labels)
        self.assertLess(payload["route_wear"]["maintenance_guidance"]["recommended_interval_km"], profile.service_interval_km)

    def test_catalog_endpoint_filters_models_by_vehicle_type(self):
        response = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=car")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["results"])
        self.assertTrue(all(item["vehicle_type"] == "car" for item in payload["results"]))
        self.assertFalse(any(item["vehicle_type"] == "motorcycle" for item in payload["results"]))

    def test_catalog_endpoint_filters_models_by_make_for_brand_first_picker(self):
        response = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=motorcycle&make=Royal%20Enfield")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["results"])
        self.assertTrue(all(item["vehicle_type"] == "motorcycle" for item in payload["results"]))
        self.assertTrue(all(item["make"] == "Royal Enfield" for item in payload["results"]))
        self.assertTrue(any(item["display_name"] == "Royal Enfield Hunter 350" for item in payload["results"]))
        self.assertFalse(any(item["make"] == "Honda" for item in payload["results"]))
        self.assertIn("manufacturers", payload)
        self.assertTrue(any(item["make"] == "Royal Enfield" and item["model_count"] >= 1 for item in payload["manufacturers"]))

        alias_response = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=scooter&brand=Ola")
        self.assertEqual(alias_response.status_code, 200)
        alias_payload = alias_response.json()
        self.assertTrue(alias_payload["results"])
        self.assertTrue(all(item["make"] == "Ola" and item["vehicle_type"] == "scooter" for item in alias_payload["results"]))

    def test_catalog_and_profile_payload_cover_new_manufacturers_and_model_guidance(self):
        catalog_payload = self.client.get("/api/mobility/bike-models/catalog/").json()
        all_models = catalog_payload["results"]
        coverage = catalog_payload["coverage"]
        manufacturers = catalog_payload["manufacturers"]
        motorcycles = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=motorcycle").json()["results"]
        cars = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=car").json()["results"]

        self.assertTrue(any(item["display_name"] == "KTM Duke 200" for item in motorcycles))
        self.assertTrue(any(item["display_name"] == "Toyota Urban Cruiser Hyryder" for item in cars))
        self.assertTrue(any(item["display_name"] == "MG Comet EV" for item in cars))
        self.assertTrue(any(item["display_name"] == "Honda City" for item in cars))
        self.assertTrue(any(item["display_name"] == "Maruti Suzuki Ertiga" for item in cars))
        self.assertTrue(any(item["display_name"] == "Skoda Kushaq" for item in cars))
        self.assertTrue(any(item["display_name"] == "Volkswagen Taigun" for item in cars))
        self.assertTrue(any(item["display_name"] == "Renault Kiger" for item in cars))
        self.assertTrue(any(item["display_name"] == "Nissan Magnite" for item in cars))
        self.assertTrue(any(item["display_name"] == "BYD ATTO 3" for item in cars))
        self.assertTrue(any(item["display_name"] == "Triumph Speed 400" for item in motorcycles))
        self.assertTrue(any(item["display_name"] == "Ultraviolette F77" for item in motorcycles))
        self.assertTrue(all(item["official_source_url"] for item in all_models))
        self.assertTrue(all(item["maintenance_guidance"] for item in all_models))
        self.assertEqual(len(manufacturers), coverage["manufacturer_count"])
        self.assertTrue(all(item["model_count"] >= 1 for item in manufacturers))
        self.assertEqual(coverage["completion_status"], "complete_current_scope")
        self.assertEqual(coverage["official_source_coverage_pct"], 100)
        self.assertEqual(coverage, catalog_coverage_summary())

        payload = build_profile_payload("Hunter 350", make="Royal Enfield")
        guidance_labels = [item["label"] for item in payload["maintenance_guidance"]]
        self.assertIn("Rear-Shock And Tyre Wear Review", guidance_labels)

        scooters = self.client.get("/api/mobility/bike-models/catalog/?vehicle_type=scooter").json()["results"]
        self.assertTrue(any(item["display_name"] == "Ola S1 Pro" for item in scooters))
        self.assertTrue(any(item["display_name"] == "Simple One" for item in scooters))
        self.assertEqual(next(item for item in scooters if item["display_name"] == "Ola S1 Pro")["fuel_type"], "electric")
