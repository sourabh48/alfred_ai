import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.career.models import CareerResumeLearningMemory
from apps.integrations.models import CreditReportUpload, VerifiedExternalInsight
from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord


class ProjectDetailsLiveTests(TestCase):
    def setUp(self):
        cache.clear()
        self.browser_summary_tempdir = tempfile.TemporaryDirectory()
        self.browser_summary_path = Path(self.browser_summary_tempdir.name) / "browser_regression_summary.json"
        self.browser_summary_env = patch.dict(
            os.environ,
            {"ALFRED_BROWSER_REGRESSION_SUMMARY": str(self.browser_summary_path)},
            clear=False,
        )
        self.browser_summary_env.start()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="project_live_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(username="project_live_admin", password="Pass12345!", email="admin@example.com")
        self.client = Client()

    def tearDown(self):
        self.browser_summary_env.stop()
        self.browser_summary_tempdir.cleanup()
        cache.clear()

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
        for index in range(2):
            BikeIssueReport.objects.create(
                user=self.user,
                bike_profile=profile,
                title=f"Resolved issue {index}",
                system="brakes",
                severity="medium",
                status="resolved",
                symptom="Brake bite changed",
                actual_cost=1400 + index,
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
        self.assertIn("4 open issue reports", tracks_by_title["Vehicle maintenance learning"]["signals"])
        self.assertIn("2 resolved issue outcomes", tracks_by_title["Vehicle maintenance learning"]["signals"])
        self.assertIn("2 costed issue outcomes", tracks_by_title["Vehicle maintenance learning"]["signals"])
        self.assertGreaterEqual(tracks_by_title["Vehicle maintenance learning"]["progress"], 88)
        self.assertLess(tracks_by_title["Vehicle maintenance learning"]["progress"], 100)
        self.assertEqual(tracks_by_title["Vehicle maintenance learning"]["blocker_label"], "Remaining maturity")
        self.assertEqual(tracks_by_title["Vehicle maintenance learning"]["maturity_status"], "Usage-gated")
        self.assertTrue(tracks_by_title["Vehicle maintenance learning"]["blocked_by_real_data"])
        self.assertTrue(
            any(
                "long-tail vehicle models only from real user selections" in action
                for action in tracks_by_title["Vehicle maintenance learning"]["completion_actions"]
            )
        )
        self.assertIn("not exhaustive", tracks_by_title["Vehicle maintenance learning"]["blocker"])
        self.assertIn("costed issue outcomes", tracks_by_title["Vehicle maintenance learning"]["blocker"])
        self.assertIn("Model training lifecycle", tracks_by_title)
        refresh_health = refreshed["guardrails"]["refresh_health"]
        self.assertEqual(refresh_health["active_records"], 1)
        self.assertEqual(refresh_health["fresh_records"], 1)
        self.assertEqual(refresh_health["watchlist_records"], 0)
        self.assertEqual(refresh_health["per_scope"][0]["scope"], "news")
        self.assertEqual(refresh_health["per_scope"][0]["fresh_records"], 1)
        self.assertTrue(refresh_health["last_refresh_success_at"])
        refresh_card = next(item for item in refreshed["summary_cards"] if item["label"] == "Evidence Refresh")
        self.assertEqual(refresh_card["value"], "1/1")

    def test_project_details_page_includes_live_refresh_hook(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/project-details/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="projectDetailsRoot"')
        self.assertContains(response, "/api/project-details/")
        self.assertContains(response, "project_details.js?v=1.8")
        self.assertContains(response, "Verified Complete Checks")
        self.assertContains(response, "Completion actions:")
        self.assertContains(response, "Real-layout gated")
        self.assertContains(response, "Upload and resolve real unknown layouts")
        self.assertContains(response, "Proof Contract Coverage")
        self.assertContains(response, 'id="projectDetailsGuardrailMetrics"')
        self.assertContains(response, 'id="projectDetailsRefreshScopeBlock"')
        self.assertContains(response, 'id="projectDetailsGuardrailFaults"')
        self.assertContains(response, "Refresh health")
        self.assertContains(response, "Watchlist by state")
        self.assertContains(response, "Last refresh attempt")
        self.assertContains(response, "Evidence Refresh By Scope")
        self.assertContains(response, "Cache Health By Namespace")
        self.assertContains(response, "Browser Driver Proof")
        self.assertContains(response, "Browser-driver gated")
        self.assertContains(response, "No driver-backed browser regression summary has been recorded yet")
        self.assertContains(response, "browser_regression_summary.json")
        self.assertContains(response, "login, document-center statement upload, vehicle setup submission, dashboard live refresh")
        self.assertContains(response, "full UI maturity is still not claimed")
        self.assertContains(response, "before new advisory signals ship")
        self.assertContains(response, "Real unknown layouts keep arriving across every document family")
        self.assertContains(response, "Long-tail vehicle models are added from real user demand")
        self.assertContains(response, "The proof contract registry covers every current recommendation and relationship-adjacent surface before new signals are added")
        self.assertContains(response, "Every new recommendation or relationship-adjacent signal ships with required-source proof contracts")
        self.assertContains(response, "Production cache sizing is validated against real payload volume and concurrency")
        self.assertContains(response, "The planned future RL learner remains planned-only")

    def test_project_details_progress_values_are_bounded_integer_percentages(self):
        materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="project-details-cache",
            ttl_seconds=60,
            builder=lambda: {"ok": True},
        )
        materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="project-details-cache",
            ttl_seconds=60,
            builder=lambda: {"ok": False},
        )
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
        self.assertGreaterEqual(payload["learning_snapshot"]["data_gated_tracks"], 1)
        self.assertGreaterEqual(payload["learning_snapshot"]["completion_action_count"], 18)
        self.assertIn("completion actions are listed below", payload["learning_snapshot"]["completion_summary"])
        proof_contract = payload["guardrails"]["proof_contract"]
        self.assertTrue(proof_contract["healthy"])
        self.assertEqual(proof_contract["covered_surface_count"], proof_contract["surface_count"])
        self.assertEqual(proof_contract["scheduled_refresh"], "refresh_due_records")
        self.assertTrue(any(surface["key"] == "relationship_alignment" for surface in proof_contract["surfaces"]))
        learning_by_title = {item["title"]: item for item in payload["learning_snapshot"]["tracks"]}
        in_progress_by_title = {item["title"]: item for item in payload["in_progress_tracks"]}
        document_learning = learning_by_title["Document intelligence"]
        self.assertEqual(document_learning["maturity_status"], "Real-layout gated")
        self.assertTrue(document_learning["blocked_by_real_data"])
        self.assertTrue(
            any(
                "DocumentParserLearningMemory records validated outcomes" in action
                for action in document_learning["completion_actions"]
            )
        )
        scope_card = next(item for item in payload["summary_cards"] if item["label"] == "Scope Completion")
        self.assertTrue(scope_card["value"].endswith("%"))
        in_progress_card = next(item for item in payload["summary_cards"] if item["label"] == "In-Progress Tracks")
        self.assertEqual(in_progress_card["value"], len(payload["in_progress_tracks"]))
        proof_card = next(item for item in payload["summary_cards"] if item["label"] == "Proof Contracts")
        self.assertEqual(proof_card["value"], f"{proof_contract['covered_surface_count']}/{proof_contract['surface_count']}")
        refresh_health = payload["guardrails"]["refresh_health"]
        self.assertIn("active evidence record(s) are fresh", refresh_health["summary"])
        self.assertIn("per_scope", refresh_health)
        self.assertIn("last attempt:", next(signal for signal in in_progress_by_title["Evidence freshness and proof rigor"]["signals"] if signal.startswith("last attempt:")))
        refresh_card = next(item for item in payload["summary_cards"] if item["label"] == "Evidence Refresh")
        self.assertEqual(refresh_card["value"], f"{refresh_health['fresh_records']}/{refresh_health['active_records']}")
        cache_health = payload["cache_health"]
        self.assertGreaterEqual(cache_health["registered_namespace_count"], 20)
        self.assertEqual(cache_health["observed_namespace_count"], 1)
        self.assertEqual(cache_health["hit_rate_pct"], 50.0)
        self.assertFalse(cache_health["production_mature"])
        cache_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Cache Health")
        self.assertEqual(cache_metric["value"], f"{cache_health['observed_namespace_count']}/{cache_health['registered_namespace_count']}")
        self.assertIn("stale regeneration", cache_metric["copy"])
        browser_coverage = payload["browser_coverage"]
        self.assertEqual(browser_coverage["progress"], 70)
        self.assertEqual(browser_coverage["implementation_status"], "Implemented")
        self.assertEqual(browser_coverage["maturity_status"], "Browser-driver gated")
        self.assertFalse(browser_coverage["full_ui_mature"])
        self.assertEqual(browser_coverage["execution_command"], "python scripts/run_browser_regressions.py --browser Chrome --require-browser")
        self.assertEqual(browser_coverage["edge_execution_command"], "python scripts/run_browser_regressions.py --browser Edge --require-browser")
        self.assertEqual(browser_coverage["ci_workflow"], ".github/workflows/browser-regression.yml")
        self.assertEqual(browser_coverage["artifact_dir"], "artifacts/browser")
        self.assertTrue(browser_coverage["summary_artifact"].endswith("browser_regression_summary.json"))
        self.assertIn("zero skipped browser tests", browser_coverage["remaining_gate"])
        browser_health = browser_coverage["driver_run_health"]
        self.assertEqual(browser_health["status"], "not_recorded")
        self.assertFalse(browser_health["maturity_gate_recorded"])
        self.assertEqual(browser_health["summary_filename"], "browser_regression_summary.json")
        self.assertIn("dashboard live refresh", browser_coverage["selenium_workflows"])
        self.assertIn("statement upload selectors and API endpoints", browser_coverage["live_server_contracts"])
        browser_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Browser Coverage")
        self.assertEqual(browser_metric["value"], "70%")
        self.assertIn("run-summary proof", browser_metric["copy"])
        self.assertIn("latest driver status: not_recorded", browser_metric["copy"])
        self.assertIn(
            "Keep source links fresh, add long-tail models from real usage, and collect more condition snapshots plus issue outcomes before treating maintenance learning as mature.",
            payload["next_steps"],
        )
        self.assertIn(
            "Keep supervised artifacts fresh, collect more accepted outcomes, and do not count the planned future RL learner as production-ready ML.",
            payload["next_steps"],
        )

    def test_project_details_surfaces_recorded_driver_backed_browser_run_without_full_ui_maturity(self):
        self.browser_summary_path.write_text(
            json.dumps(
                {
                    "summary_version": 1,
                    "status": "passed",
                    "browser": "Chrome",
                    "run_context": "local",
                    "require_browser": True,
                    "run_browser_tests_env": "true",
                    "runner_return_code": 0,
                    "return_code": 0,
                    "skipped_count": 0,
                    "tests_run_count": 2,
                    "tests_found_count": 2,
                    "driver_backed_success": True,
                    "duration_seconds": 14.8,
                    "finished_at_utc": "2026-08-05T01:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        self.client.force_login(self.superuser)

        payload = self.client.get("/api/project-details/").json()
        browser_coverage = payload["browser_coverage"]
        browser_health = browser_coverage["driver_run_health"]
        in_progress_by_title = {item["title"]: item for item in payload["in_progress_tracks"]}
        browser_track = in_progress_by_title["Browser/UI regression coverage"]
        browser_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Browser Coverage")

        self.assertEqual(browser_coverage["progress"], 72)
        self.assertEqual(browser_coverage["maturity_status"], "Driver proof recorded")
        self.assertFalse(browser_coverage["full_ui_mature"])
        self.assertTrue(browser_health["recorded"])
        self.assertTrue(browser_health["maturity_gate_recorded"])
        self.assertEqual(browser_health["status"], "passed")
        self.assertEqual(browser_health["browser"], "Chrome")
        self.assertEqual(browser_health["run_context"], "local")
        self.assertEqual(browser_health["skipped_count"], 0)
        self.assertEqual(browser_health["runner_return_code"], 0)
        self.assertIn("Driver-backed proof is recorded", browser_health["summary"])
        self.assertEqual(browser_track["progress"], 72)
        self.assertEqual(browser_track["maturity_status"], "Driver proof recorded")
        self.assertTrue(any("latest browser run: passed via local" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("recorded browser skips: 0" in signal for signal in browser_track["signals"]))
        self.assertEqual(browser_metric["value"], "72%")
        self.assertIn("latest driver status: passed", browser_metric["copy"])

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
        self.assertEqual(in_progress_by_title["Browser/UI regression coverage"]["progress"], 70)
        self.assertEqual(in_progress_by_title["Large-data hardening"]["progress"], 88)
        self.assertGreaterEqual(in_progress_by_title["Document OCR and correction maturity"]["progress"], 91)
        browser_track = in_progress_by_title["Browser/UI regression coverage"]
        self.assertIn("Selenium", browser_track["detail"])
        self.assertIn("dashboard live refresh", browser_track["detail"])
        self.assertIn("dedicated Selenium runner", browser_track["detail"])
        self.assertIn("run-summary proof", browser_track["detail"])
        self.assertEqual(browser_track["maturity_status"], "Browser-driver gated")
        self.assertTrue(any("Selenium-gated workflow" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("runner: python scripts/run_browser_regressions.py" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("edge runner: python scripts/run_browser_regressions.py" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("artifacts: artifacts/browser" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("browser_regression_summary.json" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("latest browser run: not_recorded" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("full UI maturity is still not claimed" in signal for signal in browser_track["signals"]))
        self.assertTrue(any("browser_regression_summary.json" in gate for gate in browser_track["maturity_gates"]))
        self.assertTrue(any("no skipped browser tests" in gate for gate in browser_track["maturity_gates"]))
        self.assertTrue(any("fails required-browser jobs" in gate for gate in browser_track["maturity_gates"]))
        self.assertTrue(any("screenshots, page HTML, metadata, and browser logs" in gate for gate in browser_track["maturity_gates"]))
        self.assertIn("cross-family unknown-layout", in_progress_by_title["Document OCR and correction maturity"]["detail"])
        self.assertTrue(
            any(
                "Accepted corrections produce validated parser-learning outcomes" in gate
                for gate in in_progress_by_title["Document OCR and correction maturity"]["maturity_gates"]
            )
        )
        self.assertGreaterEqual(in_progress_by_title["Vehicle catalog and maintenance depth"]["progress"], 88)
        self.assertLess(in_progress_by_title["Vehicle catalog and maintenance depth"]["progress"], 100)
        self.assertIn("2026-07-31", in_progress_by_title["Vehicle catalog and maintenance depth"]["detail"])
        self.assertIn("45-day source refresh policy", in_progress_by_title["Vehicle catalog and maintenance depth"]["detail"])
        self.assertTrue(
            any(
                "real user demand" in gate
                for gate in in_progress_by_title["Vehicle catalog and maintenance depth"]["maturity_gates"]
            )
        )
        self.assertEqual(learning_by_title["Vehicle maintenance learning"]["blocker_label"], "Remaining maturity")
        self.assertIn("salary-bearing accepted/rejected", in_progress_by_title["Career source and compensation breadth"]["detail"])
        self.assertTrue(
            any(
                "Specialty sources are added only after real users expose role or geography gaps" in gate
                for gate in in_progress_by_title["Career source and compensation breadth"]["maturity_gates"]
            )
        )
        self.assertIn("required-source proof contracts", in_progress_by_title["Evidence freshness and proof rigor"]["detail"])
        self.assertIn("registered recommendation or relationship-adjacent surfaces declare the full contract", in_progress_by_title["Evidence freshness and proof rigor"]["detail"])
        self.assertIn("scheduled refresh: refresh_due_records", in_progress_by_title["Evidence freshness and proof rigor"]["signals"])
        self.assertTrue(any("active evidence record(s) are fresh" in signal for signal in in_progress_by_title["Evidence freshness and proof rigor"]["signals"]))
        self.assertTrue(any(signal.startswith("last attempt:") for signal in in_progress_by_title["Evidence freshness and proof rigor"]["signals"]))
        self.assertTrue(any(signal.startswith("last success:") for signal in in_progress_by_title["Evidence freshness and proof rigor"]["signals"]))
        self.assertTrue(
            any(
                "Scheduled refresh keeps active verified evidence inside freshness windows" in gate
                for gate in in_progress_by_title["Evidence freshness and proof rigor"]["maturity_gates"]
            )
        )
        self.assertTrue(
            any(
                "proof contract registry covers every current recommendation and relationship-adjacent surface" in gate
                for gate in in_progress_by_title["Evidence freshness and proof rigor"]["maturity_gates"]
            )
        )
        self.assertTrue(
            any(
                "Cache hit rate" in gate
                for gate in in_progress_by_title["Large-data hardening"]["maturity_gates"]
            )
        )
        self.assertTrue(any("registered materialized namespace" in signal for signal in in_progress_by_title["Large-data hardening"]["signals"]))
        self.assertTrue(any("cache hit rate" in signal for signal in in_progress_by_title["Large-data hardening"]["signals"]))
        self.assertTrue(any("generation latency" in signal for signal in in_progress_by_title["Large-data hardening"]["signals"]))
        self.assertIn("excludes the planned future RL learner", in_progress_by_title["ML maturity and training lifecycle"]["detail"])
        self.assertTrue(
            any(
                "planned-only" in gate
                for gate in in_progress_by_title["ML maturity and training lifecycle"]["maturity_gates"]
            )
        )
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
            "summary": "7/7 production-ready model states are fresh and ready; 0 trainable model state(s) are waiting on data or environment gates, 1 planned future model(s) are excluded from production-ready ML and supervised coverage, and 0 failed recently.",
            "total_models": 8,
            "ready_models": 7,
            "fresh_models": 7,
            "skipped_models": 0,
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
