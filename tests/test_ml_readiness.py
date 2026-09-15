from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import joblib
import numpy as np
import pandas as pd
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTMAdapter
from apps.ml_engine.inference_adapters.salary_predictor import SalaryPredictor
from apps.ml_engine.inference_adapters.parser_confidence_calibrator import ParserConfidenceCalibrator
from apps.ml_engine.inference_adapters.relationship_model import RelationshipModelPredictor
from apps.ml_engine.inference_adapters.service_cost_predictor import ServiceCostPredictor
from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.orchestrator import TRAINING_SPECS, _run_training_spec, run_training_cycle
from apps.ml_engine.training.train_expense_lstm import build_expense_windows, train_expense_lstm


class ExpenseValidationTests(SimpleTestCase):
    def history(self, count=80, constant=False):
        return pd.DataFrame({
            "id": range(count), "user_id": [1] * count,
            "amount": [100.0 if constant else 100.0 + index * 5 for index in range(count)],
            "transaction_date": pd.date_range("2026-01-01", periods=count),
        })

    def test_windows_use_event_dates_and_do_not_cross_users(self):
        first = self.history(15)
        second = self.history(15)
        second["user_id"] = 2
        second["id"] += 100
        second["amount"] += 1000
        source = pd.concat([second, first]).iloc[::-1]
        rows, count = build_expense_windows(source, 10)
        self.assertEqual(count, 30)
        self.assertEqual(len(rows), 10)
        self.assertEqual([row[0] for row in rows], sorted(row[0] for row in rows))
        for _, window, target in rows:
            self.assertTrue(np.all(window < 1000) if target < 1000 else np.all(window > 1000))
            self.assertEqual(target, window[-1] + 5)

    def test_chronological_validation_publishes_only_sufficient_evidence(self):
        with TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.pkl"
            with patch("apps.ml_engine.training.train_expense_lstm.MODEL_PATH", str(model_path)), patch(
                "apps.ml_engine.training.train_expense_lstm.load_user_expense_history", return_value=self.history(),
            ):
                result = train_expense_lstm()
            self.assertEqual(result["status"], "ready")
            evaluation = result["evaluation"]
            self.assertLess(evaluation["training_last_date"], evaluation["holdout_first_date"])
            self.assertLessEqual(evaluation["mae"], evaluation["baseline_mae"] * 0.95)
            self.assertTrue(evaluation["passed"])
            self.assertGreaterEqual(result["confidence_estimate"], 55)
            payload = joblib.load(model_path)
            self.assertEqual(payload["sample_count"], 80)
            with patch("apps.ml_engine.inference_adapters.expense_lstm.MODEL_PATH", str(model_path)):
                adapter = ExpenseLSTMAdapter()
                prediction = adapter.predict(self.history()["amount"].tolist())
            self.assertIsNotNone(adapter.model)
            self.assertGreater(prediction, 0)

    def test_small_or_no_improvement_fit_revokes_previous_artifact(self):
        for history in [self.history(30), self.history(constant=True), self.history(0)]:
            with self.subTest(count=len(history)), TemporaryDirectory() as directory:
                model_path = Path(directory) / "model.pkl"
                model_path.write_bytes(b"previous artifact")
                with patch("apps.ml_engine.training.train_expense_lstm.MODEL_PATH", str(model_path)), patch(
                    "apps.ml_engine.training.train_expense_lstm.load_user_expense_history", return_value=history,
                ):
                    result = train_expense_lstm()
                self.assertEqual(result["status"], "skipped")
                self.assertFalse(model_path.exists())

    def valid_payload(self):
        return {
            "model": Mock(predict=Mock(return_value=[123.0])), "window_size": 10,
            "trained_at": timezone.now().isoformat(), "freshness_hours": 12,
            "evaluation": {"passed": True}, "sample_count": 80,
            "quality_score": 80, "confidence_estimate": 70,
        }

    def test_missing_corrupt_stale_and_underqualified_artifacts_fall_back(self):
        payloads = [
            {}, [], self.valid_payload() | {"sample_count": 20},
            self.valid_payload() | {"confidence_estimate": 30},
            self.valid_payload() | {"trained_at": (timezone.now() - timedelta(hours=13)).isoformat()},
            self.valid_payload() | {"trained_at": (timezone.now() + timedelta(hours=1)).isoformat()},
            self.valid_payload() | {"evaluation": {"passed": False}},
            self.valid_payload() | {"window_size": 0},
        ]
        for payload in payloads:
            with self.subTest(payload=payload), patch(
                "apps.ml_engine.inference_adapters.expense_lstm.joblib.load", return_value=payload,
            ):
                self.assertEqual(ExpenseLSTMAdapter().predict(range(1, 11)), 5.5)
        for error in [FileNotFoundError(), EOFError(), ValueError("corrupt artifact")]:
            with self.subTest(error=error), patch(
                "apps.ml_engine.inference_adapters.expense_lstm.joblib.load", side_effect=error,
            ):
                self.assertEqual(ExpenseLSTMAdapter().predict([None, "bad", np.nan, np.inf, -1, 10, 20]), 15)

    def test_valid_artifact_predicts_but_invalid_model_output_falls_back(self):
        payload = self.valid_payload()
        with patch("apps.ml_engine.inference_adapters.expense_lstm.joblib.load", return_value=payload):
            adapter = ExpenseLSTMAdapter()
            self.assertEqual(adapter.predict(range(1, 11)), 123)
            payload["model"].predict.return_value = [np.nan]
            self.assertEqual(adapter.predict(range(1, 11)), 5.5)

    def test_salary_adapter_rejects_target_leakage_features(self):
        with TemporaryDirectory() as directory:
            model_path = Path(directory) / "salary.pkl"
            model_path.write_bytes(b"artifact")
            with patch("apps.ml_engine.inference_adapters.salary_predictor.joblib.load", return_value={
                "model": Mock(), "feature_names": SalaryPredictor.FEATURE_NAMES + ["income_variability_ratio"],
            }):
                with self.assertRaisesRegex(ValueError, "obsolete"):
                    SalaryPredictor().load(model_path=str(model_path))


class ModelEvidenceTests(TestCase):
    def test_training_cycle_reports_fitting_separately_from_inference_readiness(self):
        outcome = {
            "status": "ready", "sample_count": 9, "quality_score": 90,
            "confidence_estimate": 70, "artifact_path": "README.md",
        }
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=lambda: outcome), patch(
            "apps.ml_engine.training.orchestrator.model_registry",
        ):
            result = run_training_cycle(model_keys=["salary_predictor"], force=True, trigger="test")
        self.assertEqual(result["fitted_count"], 1)
        self.assertEqual(result["ready_count"], 0)
        self.assertEqual(result["average_confidence"], 0)
        self.assertFalse(result["results"][0]["inference_ready"])

    def test_relative_artifact_path_is_resolved_against_project(self):
        state = AdaptiveModelState(
            model_key="salary_predictor", status="ready", sample_count=40,
            quality_score=75, confidence_estimate=70, artifact_path="test-artifact.pkl",
            next_refresh_due_at=timezone.now() + timedelta(hours=12),
        )
        with TemporaryDirectory() as directory, self.settings(BASE_DIR=Path(directory)):
            (Path(directory) / state.artifact_path).write_bytes(b"artifact")
            self.assertTrue(state.inference_ready)
        state.next_refresh_due_at = None
        self.assertFalse(state.inference_ready)

    def test_skipping_fresh_fit_preserves_artifacts_sample_count(self):
        state = AdaptiveModelState.objects.create(
            model_key="salary_predictor", status="ready", sample_count=40,
            quality_score=75, confidence_estimate=70, artifact_path="README.md",
            next_refresh_due_at=timezone.now() + timedelta(hours=12),
        )
        spec = next(item for item in TRAINING_SPECS if item.key == "salary_predictor")
        with patch("apps.ml_engine.training.orchestrator._load_trainer") as trainer:
            result = _run_training_spec(spec, trigger="test", force=False, now=timezone.now())
        self.assertEqual(result["status"], "skipped")
        trainer.assert_not_called()
        state.refresh_from_db()
        self.assertEqual(state.sample_count, 40)
        self.assertTrue(state.inference_ready)

    def test_live_adapters_decline_missing_stale_and_proxy_evidence(self):
        cases = [
            ("parser_confidence_calibrator", ParserConfidenceCalibrator().predict_probability),
            ("relationship_model", RelationshipModelPredictor().predict_score),
            ("service_cost_predictor", ServiceCostPredictor().predict_cost),
        ]
        for key, predict in cases:
            with self.subTest(model=key), patch("apps.ml_engine.inference_adapters.artifacts.joblib.load") as load:
                self.assertIsNone(predict({}))
                state = AdaptiveModelState.objects.create(
                    model_key=key, status="ready", sample_count=100,
                    quality_score=80, confidence_estimate=80, artifact_path="README.md",
                    next_refresh_due_at=timezone.now() - timedelta(hours=1),
                )
                self.assertIsNone(predict({}))
                state.next_refresh_due_at = timezone.now() + timedelta(hours=12)
                state.sample_count = 9
                state.save()
                self.assertIsNone(predict({}))
                if key == "parser_confidence_calibrator":
                    state.sample_count = 100
                    state.save()
                    self.assertIsNone(predict({}))
                load.assert_not_called()

    def test_validated_relationship_and_service_models_reload_then_reject_revoked_state(self):
        cases = [
            ("relationship_model", RelationshipModelPredictor().predict_score),
            ("service_cost_predictor", ServiceCostPredictor().predict_cost),
        ]
        for key, predict in cases:
            with self.subTest(model=key):
                state = AdaptiveModelState.objects.create(
                    model_key=key, status="ready", sample_count=100,
                    quality_score=80, confidence_estimate=80, artifact_path="README.md",
                    next_refresh_due_at=timezone.now() + timedelta(hours=12),
                )
                model = Mock(predict=Mock(return_value=[75]))
                with patch("apps.ml_engine.inference_adapters.artifacts.joblib.load", return_value={"model": model}):
                    self.assertEqual(predict({}), 75)
                    model.predict.return_value = [80]
                    self.assertEqual(predict({}), 80)
                    state.status = "skipped"
                    state.save()
                    self.assertIsNone(predict({}))
