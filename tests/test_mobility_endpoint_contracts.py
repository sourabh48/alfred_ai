import json
from datetime import date, datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, FuelRefillLog, TravelPlan, TripLog, TripPhoto
from apps.mobility.services.bike_document_ai import ParsedDocument


class MobilityEndpointContractTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="mobility_contract", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

        self.profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            make="Royal Enfield",
            model_name="Hunter 350",
            vehicle_number="KA01KC6667",
            vehicle_type="motorcycle",
            bike_class="roadster",
            expected_mileage_kmpl=36,
            is_primary=True,
        )
        self.service_record = BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            service_date=date(2026, 3, 10),
            odometer_km=26021,
            service_type="routine",
            cost=2432.92,
            service_center="Jagadamba Automobiles",
            source_mode="bill_import",
            source_document_name="JcPreInvoice.pdf",
            extracted_work_summary="Paid service, oil and brake pad replacement",
            parsed_payload={
                "document_parse": {
                    "document_number": "RJC011402IJ11758",
                    "issuer": "Jagadamba Automobiles",
                },
                "service_payload": {
                    "cost": 2432.92,
                    "parts_items": [{"description": "BRAKE PAD KIT"}],
                    "line_item_count": 7,
                },
            },
        )
        self.refill = FuelRefillLog.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            refill_date=date(2026, 3, 20),
            trip_meter_km=245,
            fuel_liters=5,
            total_cost=540,
            is_full_tank=True,
        )
        self.travel_plan = TravelPlan.objects.create(
            user=self.user,
            vehicle_profile=self.profile,
            title="Darjeeling Ride",
            destination="Darjeeling",
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 14),
            budget=18000,
            transport_mode="ride",
        )
        self.trip_log = TripLog.objects.create(
            user=self.user,
            travel_plan=self.travel_plan,
            log_date=date(2026, 4, 10),
            title="Reached Siliguri",
            location_name="Siliguri",
            distance_km=510,
            spend_amount=2400,
            latitude=26.7271,
            longitude=88.3953,
        )
        self.trip_photo = TripPhoto.objects.create(
            user=self.user,
            travel_plan=self.travel_plan,
            trip_log=self.trip_log,
            image=SimpleUploadedFile("trip.jpg", b"fake-image", content_type="image/jpeg"),
            caption="Tea garden stop",
            location_name="Siliguri",
            taken_at=timezone.make_aware(datetime(2026, 4, 10, 15, 30)),
        )
        self.issue = BikeIssueReport.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_service=self.service_record,
            title="Front brake squeal",
            system="brakes",
            severity="medium",
            status="pending",
            symptom="Front brake squeal after rain",
            probable_cause="Brake pad contamination",
            suggested_action="Inspect brake pads and clean the rotor.",
            service_center_note="Please inspect pad thickness and clean the front brake assembly.",
            projected_cost=900,
        )
        self.document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            document_type="invoice",
            issuer="Jagadamba Automobiles",
            document_number="RJC011402IJ11758",
            parser_status="parsed",
            parse_confidence=0.91,
            extracted_payload={
                "document_number": "RJC011402IJ11758",
                "service_payload": {"cost": 2432.92, "line_item_count": 7},
            },
        )
        self.condition = BikeConditionSnapshot.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            captured_at=timezone.make_aware(datetime(2026, 3, 25, 9, 30)),
            odometer_km=26220,
            overall_status="good",
            engine_status="good",
            brake_status="watch",
            tyre_status="good",
            battery_status="good",
            body_status="good",
        )

    def test_mobility_read_endpoints_return_expected_contracts(self):
        response = self.client.get("/api/mobility/dashboard/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("bike_profiles", payload)
        self.assertEqual(payload["summary"]["trip_logs"], 1)

        response = self.client.get("/api/mobility/bike-service-dashboard/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("charts", payload)
        self.assertEqual(payload["summary"]["service_count"], 1)

        get_cases = [
            ("/api/mobility/bike-models/catalog/", "results"),
            ("/api/mobility/bikes/", None),
            (f"/api/mobility/bikes/{self.profile.id}/", "display_name"),
            ("/api/mobility/bike-services/", None),
            (f"/api/mobility/bike-services/{self.service_record.id}/", "parsed_payload"),
            ("/api/mobility/bike-refills/", None),
            (f"/api/mobility/bike-refills/{self.refill.id}/", "actual_mileage_kmpl"),
            ("/api/mobility/bike-issues/", None),
            (f"/api/mobility/bike-issues/{self.issue.id}/", "probable_cause"),
            ("/api/mobility/bike-documents/", None),
            (f"/api/mobility/bike-documents/{self.document.id}/", "extracted_payload"),
            ("/api/mobility/bike-conditions/", None),
            (f"/api/mobility/bike-conditions/{self.condition.id}/", "overall_status"),
            ("/api/mobility/travel-plans/", None),
            (f"/api/mobility/travel-plans/{self.travel_plan.id}/", "destination"),
            ("/api/mobility/trip-logs/", None),
            (f"/api/mobility/trip-logs/{self.trip_log.id}/", "location_name"),
            ("/api/mobility/trip-photos/", None),
            (f"/api/mobility/trip-photos/{self.trip_photo.id}/", "caption"),
        ]

        for url, key in get_cases:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            payload = response.json()
            if key:
                self.assertIn(key, payload, url)

        with patch("apps.mobility.views.travel_advisor.build_advice", return_value={"destination": "Darjeeling", "feasibility": "good", "proof": []}):
            response = self.client.post(
                "/api/mobility/travel-advisor/preview/",
                data=json.dumps(
                    {
                        "destination": "Darjeeling",
                        "start_date": "2026-04-10",
                        "end_date": "2026-04-14",
                        "budget": 18000,
                        "transport_mode": "ride",
                        "vehicle_profile_id": self.profile.id,
                    }
                ),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["destination"], "Darjeeling")

    def test_service_bill_import_persists_structured_payload_contract(self):
        parsed = ParsedDocument(
            document_type="invoice",
            title="March Service Invoice",
            confidence=0.93,
            fields={
                "vehicle_number": self.profile.vehicle_number,
                "issuer": "Jagadamba Automobiles",
                "document_number": "INV-2026-03",
                "total_customer_amount": 3200.0,
            },
            parser_status="parsed",
            parser_notes="Imported successfully.",
            source_text="invoice text",
            service_payload={
                "service_date": "2026-03-28",
                "odometer_km": 26500,
                "service_type": "repair",
                "cost": 3200.0,
                "service_center": "Jagadamba Automobiles",
                "parts_items": [{"description": "CHAIN KIT"}],
                "line_item_count": 2,
                "extracted_work_summary": "Chain kit replacement",
            },
        )

        with patch("apps.mobility.views.bike_document_ai.parse", return_value=parsed), patch(
            "apps.mobility.views.bike_document_ai.verify_relevance",
            return_value={"accepted": True, "score": 0.98, "reasons": ["Vehicle number matched the uploaded document."]},
        ):
            response = self.client.post(
                "/api/mobility/bike-services/import/",
                data={
                    "bike_profile_id": self.profile.id,
                    "notes": "Imported from service invoice",
                    "service_file": SimpleUploadedFile("service.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
                },
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["document"]["document_number"], "INV-2026-03")
        self.assertEqual(payload["document"]["extracted_payload"]["service_payload"]["line_item_count"], 2)
        self.assertEqual(payload["service_record"]["parsed_payload"]["document_parse"]["issuer"], "Jagadamba Automobiles")
        self.assertEqual(payload["service_record"]["parsed_payload"]["service_payload"]["parts_items"][0]["description"], "CHAIN KIT")

    def test_service_record_patch_merges_existing_parsed_payload_instead_of_overwriting(self):
        response = self.client.patch(
            f"/api/mobility/bike-services/{self.service_record.id}/",
            data=json.dumps(
                {
                    "notes": "Updated after review",
                    "parsed_payload": {
                        "service_payload": {
                            "cost": 2750.0,
                            "next_service_km": 31000,
                        }
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.service_record.refresh_from_db()
        self.assertEqual(self.service_record.notes, "Updated after review")
        self.assertEqual(self.service_record.parsed_payload["document_parse"]["document_number"], "RJC011402IJ11758")
        self.assertEqual(self.service_record.parsed_payload["service_payload"]["line_item_count"], 7)
        self.assertEqual(self.service_record.parsed_payload["service_payload"]["next_service_km"], 31000)
        self.assertEqual(self.service_record.parsed_payload["service_payload"]["cost"], 2750.0)
