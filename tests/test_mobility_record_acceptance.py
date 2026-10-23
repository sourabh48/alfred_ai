from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.mobility.models import BikeProfile, BikeServiceRecord, FuelRefillLog
from apps.mobility.services.bike_service_intelligence import bike_service_intelligence


class MobilityRecordAcceptanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="vehicle_records_owner")
        self.other = get_user_model().objects.create_user(username="vehicle_records_private")
        self.profile = BikeProfile.objects.create(user=self.user, display_name="Recorded Scooter")
        self.private = BikeProfile.objects.create(user=self.other, display_name="PRIVATE-VEHICLE")
        self.client.force_login(self.user)
        self.refill = dict(bike_profile=self.profile.pk, refill_date=timezone.localdate().isoformat(),
                           fuel_liters=5, trip_meter_km=200, total_cost="500.005")

    def test_invalid_measurements_fail_before_create_or_partial_update(self):
        row = FuelRefillLog.objects.create(user=self.user, bike_profile=self.profile, bike_name="Keep", refill_date=timezone.localdate(), fuel_liters=5, trip_meter_km=200, total_cost="500.01")
        for field in ("fuel_liters", "trip_meter_km"):
            for value in ("NaN", "Infinity", "-Infinity", "1e309", True, -1):
                with self.subTest(field=field, value=value):
                    payload = dict(self.refill, **{field:value})
                    response = self.client.post("/api/mobility/bike-refills/", payload, content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    response = self.client.patch(f"/api/mobility/bike-refills/{row.pk}/", {field:value, "total_cost":"1.00"}, content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    row.refresh_from_db()
                    self.assertEqual(row.total_cost, Decimal("500.01"))
        self.assertEqual(FuelRefillLog.objects.count(), 1)

    def test_small_positive_quantity_is_not_clamped_and_prices_keep_cents(self):
        payload = dict(self.refill, fuel_liters=0.005, trip_meter_km=0.2, total_cost="10.005")
        response = self.client.post("/api/mobility/bike-refills/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["total_cost"], 10.01)
        self.assertEqual(data["actual_mileage_kmpl"], 40)
        self.assertEqual(data["fuel_price_per_liter"], 2002)
        row = FuelRefillLog.objects.get(pk=data["id"])
        self.assertEqual(row.fuel_liters, 0.005)
        self.assertEqual(bike_service_intelligence._refill_actual_mileage(row), 40)

    def test_overflowing_derived_measurements_zero_fuel_and_future_dates_are_rejected(self):
        for changes in ({"fuel_liters":0}, {"fuel_liters":1e-308}, {"trip_meter_km":1e308, "fuel_liters":0.1},
                        {"refill_date":(timezone.localdate()+timedelta(days=1)).isoformat()}):
            response = self.client.post("/api/mobility/bike-refills/", dict(self.refill, **changes), content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(FuelRefillLog.objects.exists())

    def test_service_and_fuel_crud_respect_profile_and_record_ownership(self):
        service = dict(bike_profile=self.profile.pk, bike_name="Recorded Scooter", service_date=timezone.localdate().isoformat(), odometer_km=200, cost="2.675")
        for route, payload, model in (("bike-services",service,BikeServiceRecord), ("bike-refills",self.refill,FuelRefillLog)):
            response = self.client.post(f"/api/mobility/{route}/", payload, content_type="application/json")
            self.assertEqual(response.status_code, 201)
            row = model.objects.get(pk=response.json()["id"])
            amount_field = "cost" if route=="bike-services" else "total_cost"
            self.assertEqual(getattr(row,amount_field), Decimal("2.68") if route=="bike-services" else Decimal("500.01"))
            result = self.client.patch(f"/api/mobility/{route}/{row.pk}/", {"bike_profile":self.private.pk}, content_type="application/json")
            self.assertEqual(result.status_code, 400)
            result = self.client.post(f"/api/mobility/{route}/", dict(payload,bike_profile=self.private.pk), content_type="application/json")
            self.assertEqual(result.status_code, 400)
            self.client.force_login(self.other)
            for method in (self.client.get,self.client.patch,self.client.delete):
                result = method(f"/api/mobility/{route}/{row.pk}/", {}, content_type="application/json")
                self.assertEqual(result.status_code,404)
            self.assertNotIn("Recorded Scooter",str(self.client.get(f"/api/mobility/{route}/").json()))
            self.client.force_login(self.user)
            self.assertEqual(self.client.patch(f"/api/mobility/{route}/{row.pk}/", {"notes":"Corrected"}, content_type="application/json").status_code,200)
            row.refresh_from_db()
            self.assertEqual(row.bike_profile_id,self.profile.pk)
            self.assertEqual(self.client.delete(f"/api/mobility/{route}/{row.pk}/").status_code,204)

    def test_service_chronology_and_malformed_refill_preserve_records(self):
        response = self.client.post("/api/mobility/bike-services/", dict(bike_profile=self.profile.pk,
            bike_name="Keep",service_date=timezone.localdate().isoformat(),odometer_km=200,next_service_km=100),content_type="application/json")
        self.assertEqual(response.status_code,400)
        for data in ([], None, "bad"):
            response=self.client.post("/api/mobility/bike-refills/", data, content_type="application/json")
            self.assertEqual(response.status_code,400)
        self.assertFalse(BikeServiceRecord.objects.exists())
        self.assertFalse(FuelRefillLog.objects.exists())

    def test_owner_session_writes_still_require_csrf(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/api/mobility/bike-refills/",self.refill,content_type="application/json").status_code,403)
        self.assertFalse(FuelRefillLog.objects.exists())

    def test_dashboard_reports_server_date_even_when_the_payload_is_cached(self):
        today=timezone.localdate()
        for day in (today,today+timedelta(days=1)):
            with patch("apps.mobility.views.timezone.localdate",return_value=day):
                response=self.client.get("/api/mobility/bike-service-dashboard/")
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()["current_date"],day.isoformat())

    def test_record_corrections_refresh_cached_costs_and_mileage_immediately(self):
        service=BikeServiceRecord.objects.create(user=self.user,bike_profile=self.profile,bike_name="Keep",service_date=timezone.localdate(),cost="1.01")
        refill=FuelRefillLog.objects.create(user=self.user,bike_profile=self.profile,bike_name="Keep",refill_date=timezone.localdate(),fuel_liters=5,trip_meter_km=200,total_cost="500.01")
        before=self.client.get("/api/mobility/bike-service-dashboard/").json()["summary"]
        self.assertEqual(before["total_service_cost"],1.01)
        self.assertEqual(before["average_actual_mileage_kmpl"],40)
        self.assertEqual(self.client.patch(f"/api/mobility/bike-services/{service.pk}/",{"cost":"20.02"},content_type="application/json").status_code,200)
        changed=self.client.get("/api/mobility/bike-service-dashboard/").json()["summary"]
        self.assertEqual(changed["total_service_cost"],20.02)
        self.assertEqual(self.client.patch(f"/api/mobility/bike-refills/{refill.pk}/",{"trip_meter_km":100},content_type="application/json").status_code,200)
        changed=self.client.get("/api/mobility/bike-service-dashboard/").json()["summary"]
        self.assertEqual(changed["average_actual_mileage_kmpl"],20)
