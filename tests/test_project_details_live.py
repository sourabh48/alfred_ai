from datetime import date, datetime, timedelta

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
        self.assertEqual(refreshed["summary_cards"][1]["label"], "Learning Progress")
        self.assertIn("18 service logs", tracks_by_title["Vehicle maintenance learning"]["signals"])
        self.assertIn("Model training lifecycle", tracks_by_title)

    def test_project_details_page_includes_live_refresh_hook(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/project-details/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="projectDetailsRoot"')
        self.assertContains(response, "/api/project-details/")
        self.assertContains(response, "project_details.js")

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

        self.assertEqual(
            in_progress_by_title["Document correction workflow"]["progress"],
            max(learning_by_title["Document intelligence"]["progress"], 24),
        )
        self.assertEqual(
            in_progress_by_title["Cross-module proof enforcement"]["progress"],
            max(learning_by_title["Verified evidence refresh"]["progress"] - 12, 18),
        )
        self.assertEqual(
            in_progress_by_title["Vehicle catalog and maintenance depth"]["progress"],
            max(learning_by_title["Vehicle maintenance learning"]["progress"] - 8, 20),
        )
        self.assertEqual(
            in_progress_by_title["Career source coverage"]["progress"],
            max(learning_by_title["Career and market intelligence"]["progress"] - 10, 18),
        )
