import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.behavioral.models import BehavioralSignal
from apps.expenses.models import Expense
from apps.ml_engine.auto_training import bootstrap_startup_training, should_bootstrap_training
from apps.ml_engine.runtime_control import grant_training_consent
from apps.ml_engine.models import AdaptiveModelState, AdaptiveTrainingRun, DocumentParserLearningMemory
from apps.ml_engine.training.orchestrator import run_training_cycle, training_health_snapshot
from apps.ml_engine.training.runtime import training_runtime_status
from apps.mobility.models import BikeProfile, BikeServiceRecord
from apps.relationship.models import RelationshipProfile


ARTIFACT_DIRS = [
    Path("ml_models/alfred/salary_model"),
    Path("ml_models/alfred/expense_lstm"),
    Path("ml_models/alfred/burnout_rf"),
    Path("ml_models/alfred/risk_classifier"),
    Path("ml_models/alfred/parser_confidence"),
    Path("ml_models/alfred/relationship_model"),
    Path("ml_models/alfred/service_cost_predictor"),
]


class MLTrainingOrchestratorTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="ml_primary",
            password="Pass12345!",
            monthly_income=92000,
            variable_income=14000,
            rent_or_emi=26000,
            city="Bengaluru",
        )
        for index in range(11):
            peer = user_model.objects.create_user(
                username=f"ml_user_{index}",
                password="Pass12345!",
                monthly_income=45000 + (index * 6500),
                variable_income=4000 + (index * 500),
                rent_or_emi=12000 + (index * 700),
                city=["Bengaluru", "Mumbai", "Pune", "Hyderabad"][index % 4],
            )
            RelationshipProfile.objects.create(
                user=peer,
                partner_name=f"Partner {index}",
                partner_financial_score=52 + (index * 3),
                partner_savings_habits=2 + (index % 4),
                compatibility_score=48 + (index * 4),
            )
        self.superuser = user_model.objects.create_superuser(
            username="ml_admin",
            password="Pass12345!",
            email="ml-admin@example.com",
        )

        for index in range(24):
            BehavioralSignal.objects.create(
                user=self.user,
                stress_score=4.0 + (index % 5),
                sleep_hours=5.5 + ((index + 1) % 3),
                work_hours=8.0 if index % 2 == 0 else 11.5,
            )

        for index in range(48):
            Expense.objects.create(
                user=self.user,
                amount=300 + (index * 17),
                classification="expense",
                category="food" if index % 3 == 0 else "fuel",
                payment_mode="UPI",
                merchant=f"Merchant {index % 7}",
                description=f"Expense {index}",
                raw_description=f"RAW {index}",
                transaction_date=f"2026-03-{(index % 28) + 1:02d}",
                direction="debit",
                source="manual",
            )

        for index in range(14):
            DocumentParserLearningMemory.objects.create(
                user=self.user,
                scope="statement_document" if index % 2 == 0 else "vehicle_document",
                file_extension=".pdf",
                detected_type="statement" if index % 2 == 0 else "invoice",
                template_signature=f"sig-{index}",
                field_signature=f"field-{index}",
                successful_count=3 + (index % 3) if index % 2 == 0 else 0,
                review_count=1,
                failed_count=0 if index % 2 == 0 else 3,
                correction_count=1 if index % 3 == 0 else 0,
                retry_success_count=1 if index % 2 == 0 else 0,
                retry_failure_count=0 if index % 2 == 0 else 2,
                average_confidence=0.78 if index % 2 == 0 else 0.26,
                observed_fields=["amount", "date", "merchant"] if index % 2 == 0 else ["document_number"],
                observed_keywords=["HDFC", "ACCOUNT"] if index % 2 == 0 else ["INVOICE"],
                accepted_field_hints=["amount", "date"] if index % 2 == 0 else ["document_number"],
                last_resolution="accepted_correction" if index % 3 == 0 else "still_needs_review",
            )

        bike = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            make="Royal Enfield",
            model_name="Hunter 350",
            vehicle_type="motorcycle",
            bike_class="retro",
            engine_cc=349,
            expected_mileage_kmpl=36,
            is_primary=True,
        )
        for index in range(12):
            BikeServiceRecord.objects.create(
                user=self.user,
                bike_profile=bike,
                bike_name=bike.display_name,
                service_date=f"2026-02-{(index % 27) + 1:02d}",
                odometer_km=4200 + (index * 650),
                service_type="routine" if index % 4 else "repair",
                cost=1200 + (index * 145),
                service_center="Jagadamba Automobiles",
                parsed_payload={
                    "service_payload": {
                        "line_item_count": 2 + (index % 3),
                        "parts_items": [{"description": "Consumable"} for _ in range(1 + (index % 2))],
                        "labour_items": [{"description": "Labour"} for _ in range(1 + (index % 3))],
                    }
                },
            )

        self.addCleanup(self._cleanup_artifacts)

    def _cleanup_artifacts(self):
        for directory in ARTIFACT_DIRS:
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)

    def _assert_training_outcome(self, *, state, result_item, minimum_confidence: float, artifact_expected: bool):
        runtime_ready, _ = training_runtime_status()
        if runtime_ready:
            self.assertEqual(state.status, "ready")
            self.assertEqual(result_item["status"], "ready")
            self.assertGreaterEqual(state.confidence_estimate, minimum_confidence)
            if artifact_expected:
                self.assertTrue(Path(state.artifact_path).exists())
        else:
            self.assertEqual(result_item["status"], "skipped")
            self.assertEqual(state.status, "skipped")
            self.assertTrue(
                ("Scikit-learn runtime is unavailable" in result_item["notes"])
                or ("training is unavailable in this environment" in result_item["notes"])
            )

    def test_training_cycle_records_ready_states_for_supported_models(self):
        result = run_training_cycle(
            trigger="manual",
            force=True,
            model_keys=["salary_predictor", "expense_forecaster", "burnout_rf", "risk_classifier"],
        )

        self.assertEqual(result["status"], "completed")
        states = {item.model_key: item for item in AdaptiveModelState.objects.all()}
        results = {item["model_key"]: item for item in result["results"]}
        self._assert_training_outcome(
            state=states["salary_predictor"],
            result_item=results["salary_predictor"],
            minimum_confidence=22,
            artifact_expected=True,
        )
        self._assert_training_outcome(
            state=states["expense_forecaster"],
            result_item=results["expense_forecaster"],
            minimum_confidence=25,
            artifact_expected=True,
        )
        self._assert_training_outcome(
            state=states["burnout_rf"],
            result_item=results["burnout_rf"],
            minimum_confidence=20,
            artifact_expected=True,
        )
        self._assert_training_outcome(
            state=states["risk_classifier"],
            result_item=results["risk_classifier"],
            minimum_confidence=20,
            artifact_expected=True,
        )
        self.assertTrue(
            AdaptiveTrainingRun.objects.filter(
                model_key="risk_classifier",
                status="ready" if training_runtime_status()[0] else "skipped",
            ).exists()
        )

        snapshot = training_health_snapshot()
        self.assertGreaterEqual(snapshot["ready_models"] + snapshot["skipped_models"], 4)
        self.assertGreaterEqual(snapshot["overall_progress"], 0)

    def test_should_bootstrap_training_respects_command_and_flag(self):
        self.assertFalse(should_bootstrap_training(["manage.py", "test"]))
        self.assertFalse(should_bootstrap_training(["manage.py", "migrate"]))
        with patch.dict(os.environ, {"RUN_MAIN": "true"}, clear=False):
            self.assertTrue(should_bootstrap_training(["manage.py", "runserver"]))
        with self.settings(ALFRED_AUTO_TRAIN_ON_STARTUP=False):
            self.assertFalse(should_bootstrap_training(["manage.py", "runserver"]))

    def test_parser_confidence_calibrator_trains_when_parser_memory_exists(self):
        result = run_training_cycle(
            trigger="manual",
            force=True,
            model_keys=["parser_confidence_calibrator"],
        )

        self.assertEqual(result["status"], "completed")
        state = AdaptiveModelState.objects.get(model_key="parser_confidence_calibrator")
        self._assert_training_outcome(
            state=state,
            result_item=result["results"][0],
            minimum_confidence=20,
            artifact_expected=True,
        )

    def test_relationship_model_trains_when_scored_profiles_exist(self):
        result = run_training_cycle(
            trigger="manual",
            force=True,
            model_keys=["relationship_model"],
        )

        self.assertEqual(result["status"], "completed")
        state = AdaptiveModelState.objects.get(model_key="relationship_model")
        self._assert_training_outcome(
            state=state,
            result_item=result["results"][0],
            minimum_confidence=18,
            artifact_expected=True,
        )

    def test_service_cost_predictor_trains_when_service_records_exist(self):
        result = run_training_cycle(
            trigger="manual",
            force=True,
            model_keys=["service_cost_predictor"],
        )

        self.assertEqual(result["status"], "completed")
        state = AdaptiveModelState.objects.get(model_key="service_cost_predictor")
        self._assert_training_outcome(
            state=state,
            result_item=result["results"][0],
            minimum_confidence=18,
            artifact_expected=True,
        )

    def test_training_health_snapshot_does_not_import_trainer_modules(self):
        with patch("apps.ml_engine.training.orchestrator.import_module", side_effect=AssertionError("trainer import not expected")):
            snapshot = training_health_snapshot()

        self.assertIn("overall_progress", snapshot)
        self.assertGreaterEqual(snapshot["total_models"], 1)

    def test_training_cycle_skips_when_trainer_import_is_blocked(self):
        with patch(
            "apps.ml_engine.training.orchestrator.import_module",
            side_effect=ImportError("DLL load failed while importing _libsvm: An Application Control policy has blocked this file."),
        ):
            result = run_training_cycle(
                trigger="manual",
                force=True,
                model_keys=["burnout_rf"],
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["results"][0]["status"], "skipped")
        self.assertIn("Application Control policy has blocked this file", result["results"][0]["notes"])
        state = AdaptiveModelState.objects.get(model_key="burnout_rf")
        self.assertEqual(state.status, "skipped")
        self.assertTrue(
            AdaptiveTrainingRun.objects.filter(model_key="burnout_rf", status="skipped").exists()
        )

    def test_runtime_status_requires_superuser_approval_before_starting_up(self):
        self.client.force_login(self.superuser)

        initial = self.client.get("/api/ai/runtime-status/")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["setup_state"], "awaiting_approval")
        self.assertFalse(initial.json()["approval"]["granted"])

        approved = self.client.post(
            "/api/ai/runtime-control/",
            data=json.dumps({"action": "approve"}),
            content_type="application/json",
        )
        self.assertEqual(approved.status_code, 200)

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.ml_training_consent_granted)
        refreshed = self.client.get("/api/ai/runtime-status/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertTrue(refreshed.json()["approval"]["granted"])
        self.assertIn(refreshed.json()["setup_state"], {"ready", "runtime_blocked"})

    def test_bootstrap_startup_training_runs_only_after_superuser_approval(self):
        cache.clear()

        with patch("apps.ml_engine.auto_training.should_bootstrap_training", return_value=True), patch(
            "apps.ml_engine.auto_training.threading.Thread"
        ) as thread_cls:
            self.assertFalse(bootstrap_startup_training())
            thread_cls.assert_not_called()

            grant_training_consent(self.superuser)
            self.assertTrue(bootstrap_startup_training())
            thread_cls.assert_called_once()
            thread_cls.return_value.start.assert_called_once()
