from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.career.models import CareerResumeLearningMemory
from apps.integrations.models import CreditReportUpload, VerifiedExternalInsight
from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord


class ProjectDetailsLiveTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="project_live_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(username="project_live_admin", password="Pass12345!", email="admin@example.com")
        self.client = Client()

    def test_project_details_api_is_superuser_only(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/project-details/")
        self.assertEqual(response.status_code, 403)

    def test_project_details_api_updates_learning_progress_when_new_data_arrives(self):
        self.client.force_login(self.superuser)
        initial = self.client.get("/api/project-details/").json()

        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="V-Strom SX",
            make="Suzuki",
            model_name="V-Strom SX",
            vehicle_type="motorcycle",
            bike_class="adventure",
            vehicle_number="KA05MN4321",
            is_primary=True,
        )
        for index in range(18):
            BikeServiceRecord.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                service_date=date(2026, 1, 1) + timedelta(days=index),
                odometer_km=1000 + (index * 250),
                service_type="routine",
                cost=950 + index,
            )
        for index in range(6):
            BikeConditionSnapshot.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                captured_at=timezone.make_aware(datetime(2026, 2, 1, 8, 30)) + timedelta(days=index),
                odometer_km=2200 + (index * 250),
                overall_status="good",
                engine_status="good",
                brake_status="watch",
                tyre_status="good",
                battery_status="good",
                body_status="good",
            )
        for index in range(4):
            BikeIssueReport.objects.create(
                user=self.user,
                bike_profile=profile,
                title=f"Open issue {index}",
                system="engine",
                severity="medium",
                status="pending",
                symptom="Engine feels rough",
            )
        for index in range(4):
            BikeDocument.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                document_type="invoice",
                document_number=f"INV-{index}",
                parser_status="parsed",
                parse_confidence=0.9,
                extracted_payload={"service_payload": {"cost": 1200 + index}},
            )
        now = timezone.now()
        VerifiedExternalInsight.objects.create(
            scope="news",
            cache_key="google-news:mobility",
            title="Mobility Feed",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=mobility",
            query="mobility",
            summary="Fresh evidence",
            payload={"items": [{"title": "fresh"}]},
            checksum="fresh-1",
            status="fresh",
            fetched_at=now,
            verified_at=now,
            stale_after=now + timedelta(hours=8),
            is_active=True,
        )

        refreshed = self.client.get("/api/project-details/").json()
        tracks_by_title = {item["title"]: item for item in refreshed["learning_snapshot"]["tracks"]}

        self.assertGreater(refreshed["learning_snapshot"]["overall_progress"], initial["learning_snapshot"]["overall_progress"])
        self.assertEqual(refreshed["summary_cards"][1]["label"], "Scope Completion")
        self.assertEqual(refreshed["summary_cards"][2]["label"], "Learning Maturity")
        self.assertIn("18 service logs", tracks_by_title["Vehicle maintenance learning"]["signals"])
        self.assertGreaterEqual(tracks_by_title["Vehicle maintenance learning"]["progress"], 88)
        self.assertLess(tracks_by_title["Vehicle maintenance learning"]["progress"], 100)
        self.assertEqual(tracks_by_title["Vehicle maintenance learning"]["blocker_label"], "Remaining maturity")
        self.assertIn("not exhaustive", tracks_by_title["Vehicle maintenance learning"]["blocker"])
        self.assertIn("Model training lifecycle", tracks_by_title)

    def test_project_details_page_includes_live_refresh_hook(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/project-details/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="projectDetailsRoot"')
        self.assertContains(response, "/api/project-details/")
        self.assertContains(response, "project_details.js?v=1.4")
        self.assertContains(response, "Verified Complete Checks")

    def test_project_details_progress_values_are_bounded_integer_percentages(self):
        self.client.force_login(self.superuser)
        payload = self.client.get("/api/project-details/").json()

        progress_values = [payload["learning_snapshot"]["overall_progress"]]
        progress_values.extend(item["progress"] for item in payload["learning_snapshot"]["tracks"])
        progress_values.extend(item["progress"] for item in payload["in_progress_tracks"])
        progress_values.extend(item["progress"] for item in payload["completed_tracks"])

        for value in progress_values:
            with self.subTest(value=value):
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100)

        learning_card = next(item for item in payload["summary_cards"] if item["label"] == "Learning Maturity")
        self.assertEqual(learning_card["value"], f"{payload['learning_snapshot']['overall_progress']}%")
        scope_card = next(item for item in payload["summary_cards"] if item["label"] == "Scope Completion")
        self.assertTrue(scope_card["value"].endswith("%"))
        in_progress_card = next(item for item in payload["summary_cards"] if item["label"] == "In-Progress Tracks")
        self.assertEqual(in_progress_card["value"], len(payload["in_progress_tracks"]))

    def test_in_progress_tracks_follow_named_learning_tracks_not_sorted_positions(self):
        self.client.force_login(self.superuser)
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Activa",
            make="Honda",
            model_name="Activa 125",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA03XY9999",
        )
        for index in range(10):
            BikeServiceRecord.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                service_date=date(2026, 1, 10) + timedelta(days=index),
                odometer_km=5000 + (index * 120),
                service_type="routine",
                cost=1200 + index,
            )
        for index in range(3):
            BikeDocument.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                document_type="insurance",
                document_number=f"POL-{index}",
                parser_status="parsed",
                parse_confidence=0.88,
                extracted_payload={"doc": index},
            )
        for index in range(4):
            CareerResumeLearningMemory.objects.create(
                user=self.user,
                file_extension=".pdf",
                role_hint=f"role-{index}",
                skill_signature=f"skill-{index}",
                successful_count=2,
                average_confidence=0.76,
            )
        for index in range(2):
            CreditReportUpload.objects.create(
                user=self.user,
                uploaded_file=f"credit_reports/2026/03/report-{index}.pdf",
                file_name=f"report-{index}.pdf",
                bureau="CIBIL",
                parser_status="parsed",
                parse_confidence=0.81,
            )
        now = timezone.now()
        VerifiedExternalInsight.objects.create(
            scope="macro",
            cache_key="macro:india",
            title="Macro Snapshot",
            source_name="World Bank",
            source_url="https://data.worldbank.org",
            summary="Fresh macro evidence",
            payload={"ok": True},
            checksum="macro-1",
            status="fresh",
            fetched_at=now,
            verified_at=now,
            stale_after=now + timedelta(hours=4),
            is_active=True,
        )

        payload = self.client.get("/api/project-details/").json()
        learning_by_title = {item["title"]: item for item in payload["learning_snapshot"]["tracks"]}
        in_progress_by_title = {item["title"]: item for item in payload["in_progress_tracks"]}
        completed_by_title = {item["title"]: item for item in payload["completed_tracks"]}

        expected_active = {
            "Browser/UI regression coverage",
            "Document OCR and correction maturity",
            "Vehicle catalog and maintenance depth",
            "Career source and compensation breadth",
            "Evidence freshness and proof rigor",
            "Large-data hardening",
            "ML maturity and training lifecycle",
        }
        self.assertTrue(expected_active.issubset(set(in_progress_by_title)))
        self.assertEqual(in_progress_by_title["Browser/UI regression coverage"]["progress"], 45)
        self.assertEqual(in_progress_by_title["Large-data hardening"]["progress"], 84)
        self.assertGreaterEqual(in_progress_by_title["Document OCR and correction maturity"]["progress"], 86)
        self.assertGreaterEqual(in_progress_by_title["Vehicle catalog and maintenance depth"]["progress"], 88)
        self.assertLess(in_progress_by_title["Vehicle catalog and maintenance depth"]["progress"], 100)
        self.assertEqual(learning_by_title["Vehicle maintenance learning"]["blocker_label"], "Remaining maturity")
        self.assertEqual(in_progress_by_title["ML maturity and training lifecycle"]["progress"], round(payload["learning_snapshot"]["model_training"]["overall_progress"]))
        self.assertEqual(completed_by_title["Backend/API regression baseline"]["progress"], 100)
        self.assertEqual(completed_by_title["Vehicle make/model picker fix"]["progress"], 100)
        self.assertNotIn("Vehicle catalog and maintenance depth", completed_by_title)
        self.assertNotIn("Large-data hardening", completed_by_title)
        self.assertNotIn("Career source coverage", completed_by_title)
        if round(payload["learning_snapshot"]["model_training"]["supervised_training_progress"]) >= 100:
            self.assertEqual(completed_by_title["Supervised model refresh"]["progress"], 100)
        else:
            self.assertIn("Supervised model refresh", in_progress_by_title)

    @patch("alfred_ai.project_details.training_health_snapshot")
    def test_completed_supervised_training_moves_auto_training_out_of_active_tracks(self, training_snapshot):
        training_snapshot.return_value = {
            "overall_progress": 75.9,
            "summary": "7/8 model states are fresh and ready; 0 trainable model state(s) are waiting on data or environment gates, 1 planned future model(s) are excluded from supervised coverage, and 0 failed recently.",
            "total_models": 8,
            "ready_models": 7,
            "fresh_models": 7,
            "skipped_models": 1,
            "failed_models": 0,
            "training_models": 0,
            "trainable_models": 7,
            "supervised_ready_models": 7,
            "supervised_fresh_models": 7,
            "supervised_skipped_models": 0,
            "planned_models": 1,
            "supervised_training_progress": 100.0,
            "average_confidence": 58.52,
            "maturity": {},
            "models": [],
        }
        self.client.force_login(self.superuser)

        payload = self.client.get("/api/project-details/").json()
        in_progress_by_title = {item["title"]: item for item in payload["in_progress_tracks"]}
        completed_by_title = {item["title"]: item for item in payload["completed_tracks"]}

        self.assertIn("ML maturity and training lifecycle", in_progress_by_title)
        self.assertEqual(in_progress_by_title["ML maturity and training lifecycle"]["progress"], 76)
        self.assertNotIn("Supervised model refresh", in_progress_by_title)
        self.assertEqual(completed_by_title["Supervised model refresh"]["progress"], 100)
        self.assertIn("7/7 trainable models fresh and ready", completed_by_title["Supervised model refresh"]["detail"])
