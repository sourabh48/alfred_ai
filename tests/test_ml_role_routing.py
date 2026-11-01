"""Router roles obey recorded model evidence; synthetic artifacts only, no real model or provider."""
from datetime import timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from django.test import TestCase
from django.utils import timezone

from apps.ml_engine.core.alfred_registry import AlfredModelRegistry
from apps.ml_engine.core.alfred_router import PLANNED_ROLES, ROLE_MODEL_KEYS, alfred_router
from apps.ml_engine.inference_adapters.emotional_bert import EmotionalBERT
from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTMAdapter
from apps.ml_engine.inference_adapters.salary_predictor import SalaryPredictor
from apps.ml_engine.models import AdaptiveModelState, AdaptiveTrainingRun
from apps.ml_engine.training.orchestrator import TRAINING_SPECS, run_training_cycle
from apps.ml_engine.training.quality import PROXY_TARGET_NOTES


class RoleRoutingTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-role-synthetic-")))
        self.artifact = self.root / "synthetic.pkl"
        self.artifact.write_bytes(b"synthetic")

    def state(self, model_key, **changes):
        values = dict(display_name="Synthetic", status="ready", sample_count=100, quality_score=80,
                      confidence_estimate=80, artifact_path=str(self.artifact),
                      next_refresh_due_at=timezone.now() + timedelta(hours=12))
        values.update(changes)
        return AdaptiveModelState.objects.update_or_create(model_key=model_key, defaults=values)[0]

    def unavailable(self, task, reason):
        return {"status": "unavailable", "task": task, "reason": reason}

    def test_every_training_spec_has_exactly_one_role(self):
        routed = [*ROLE_MODEL_KEYS.values(), *PLANNED_ROLES.values()]
        self.assertEqual(sorted(routed), sorted(spec.key for spec in TRAINING_SPECS))

    def test_learned_roles_without_current_evidence_decline_before_loading_any_file(self):
        cases = (dict(status="failed"), dict(status="skipped"), dict(sample_count=1), dict(quality_score=49),
                 dict(confidence_estimate=54), dict(artifact_path=str(self.root / "missing.pkl")),
                 dict(next_refresh_due_at=timezone.now() - timedelta(seconds=1)))
        for task, key in ROLE_MODEL_KEYS.items():
            if task == "expense-forecast":
                continue
            with self.subTest(task=task, evidence="none"), patch("joblib.load") as load:
                self.assertEqual(alfred_router.route(task, {}), self.unavailable(task, "not_inference_ready"))
                load.assert_not_called()
            for changes in cases:
                with self.subTest(task=task, evidence=sorted(changes)), patch("joblib.load") as load:
                    self.state(key, **changes)
                    self.assertEqual(alfred_router.route(task, {}), self.unavailable(task, "not_inference_ready"))
                    load.assert_not_called()

    def test_proxy_target_roles_never_serve_even_with_perfect_recorded_scores(self):
        roles = {task: key for task, key in ROLE_MODEL_KEYS.items() if key in PROXY_TARGET_NOTES}
        self.assertEqual(set(roles), {"burnout", "risk", "parser-confidence"})
        for task, key in roles.items():
            with self.subTest(task=task), patch("joblib.load") as load:
                self.state(key, quality_score=100, confidence_estimate=100)
                self.assertEqual(alfred_router.route(task, {}), self.unavailable(task, "not_inference_ready"))
                load.assert_not_called()

    def test_planned_role_declines_without_importing_its_unsupported_runtime(self):
        self.state("rl_agent")
        with patch.dict(sys.modules, {"apps.ml_engine.inference_adapters.rl_agent": None, "stable_baselines3": None}):
            self.assertEqual(alfred_router.route("invest-rl", [0.1]), self.unavailable("invest-rl", "planned_not_implemented"))

    def test_relationship_uses_the_trained_gated_model_not_the_untrained_torch_prototype(self):
        self.state("relationship_model")
        model = Mock(predict=Mock(return_value=[72.5]))
        with patch.dict(sys.modules, {"apps.ml_engine.inference_adapters.relationship_siamese": None}), patch(
            "joblib.load", return_value={"model": model},
        ):
            self.assertEqual(alfred_router.route("relationship", {"partner_financial_score": 60}), 72.5)

    def test_service_cost_role_serves_validated_model_and_reports_a_declined_prediction(self):
        self.state("service_cost_predictor")
        model = Mock(predict=Mock(return_value=[1800.0]))
        with patch("joblib.load", return_value={"model": model}):
            self.assertEqual(alfred_router.route("service-cost", {"line_item_count": 2}), 1800.0)
            model.predict.return_value = [float("nan")]
            self.assertEqual(alfred_router.route("service-cost", {}), self.unavailable("service-cost", "model_declined"))

    def salary_artifact(self, name):
        path = self.root / name
        path.write_bytes(b"synthetic")
        self.state("salary_predictor", artifact_path=str(path))
        return path

    def test_salary_role_loads_the_artifact_named_by_its_evidence(self):
        path = self.salary_artifact("evidence-salary.pkl")
        payload = {"model": Mock(predict=Mock(return_value=[52000.0])), "feature_names": SalaryPredictor.FEATURE_NAMES}
        with patch("joblib.load", return_value=payload) as load:
            self.assertEqual(alfred_router.route("salary", {"variable_income": 1000}), 52000.0)
        load.assert_called_once_with(str(path))

    def test_salary_role_reports_corrupt_artifact_bad_input_and_nonfinite_output_as_unavailable(self):
        expected = self.unavailable("salary", "inference_failed")
        self.salary_artifact("corrupt-salary.pkl")
        with patch("joblib.load", side_effect=EOFError("synthetic truncation")):
            self.assertEqual(alfred_router.route("salary", {}), expected)
        self.salary_artifact("usable-salary.pkl")
        model = Mock(predict=Mock(return_value=[float("inf")]))
        with patch("joblib.load", return_value={"model": model, "feature_names": SalaryPredictor.FEATURE_NAMES}):
            self.assertEqual(alfred_router.route("salary", {"variable_income": "not-a-number"}), expected)
            self.assertEqual(alfred_router.route("salary", {}), self.unavailable("salary", "model_declined"))

    def expense_payload(self):
        return dict(model=Mock(predict=Mock(return_value=[321.0])), trained_at=timezone.now().isoformat(),
                    freshness_hours=12, evaluation={"passed": True}, sample_count=80, quality_score=80,
                    confidence_estimate=80, window_size=10)

    def test_expense_role_uses_median_fallback_unless_evidence_and_artifact_both_pass(self):
        amounts = list(range(1, 11))
        with patch("apps.ml_engine.inference_adapters.expense_lstm.joblib.load") as load:
            self.assertEqual(alfred_router.route("expense-forecast", amounts), 5.5)
            self.state("expense_forecaster", status="failed")
            self.assertEqual(alfred_router.route("expense-forecast", amounts), 5.5)
            load.assert_not_called()
            load.return_value = self.expense_payload()
            self.state("expense_forecaster")
            self.assertEqual(alfred_router.route("expense-forecast", amounts), 321.0)
            load.return_value = self.expense_payload() | {"evaluation": {"passed": False}}
            self.assertEqual(alfred_router.route("expense-forecast", amounts), 5.5)

    def test_direct_expense_adapter_can_be_refused_the_learned_model(self):
        with patch("apps.ml_engine.inference_adapters.expense_lstm.joblib.load") as load:
            self.assertEqual(ExpenseLSTMAdapter().predict([10, 20], use_model=False), 15)
        load.assert_not_called()

    def test_emotion_text_model_needs_recorded_evidence_and_is_revocable(self):
        torch = MagicMock()
        torch.softmax.return_value = np.array([[0.1, 0.9]])
        transformers = MagicMock()
        transformers.BertTokenizer.from_pretrained.return_value = Mock(return_value={})
        payload = {"amount": 900, "category": "rent", "description": "synthetic rent bill"}
        adapter = EmotionalBERT()
        with patch("apps.ml_engine.inference_adapters.emotional_bert.os.path.isdir", return_value=True), patch.dict(
            sys.modules, {"torch": torch, "transformers": transformers},
        ):
            adapter.load()
            transformers.BertForSequenceClassification.from_pretrained.assert_not_called()
            self.assertIn("+fallback", adapter.predict(payload)["analysis_source"])

            state = self.state("emotional_bert")
            adapter.load()
            transformers.BertForSequenceClassification.from_pretrained.assert_called_once()
            result = adapter.predict(payload)
            self.assertIn("+text-model", result["analysis_source"])
            self.assertTrue(result["is_emotional"])

            state.status = "skipped"
            state.save()
            adapter.load()
            result = adapter.predict(payload)
            self.assertIn("+fallback", result["analysis_source"])
            self.assertFalse(result["is_emotional"])

    def test_corrupt_registry_receipt_does_not_strand_a_finished_training_run(self):
        outcome = dict(status="ready", sample_count=100, quality_score=80, confidence_estimate=80,
                       artifact_path=str(self.artifact), notes="Synthetic fit.")
        with patch.dict("os.environ", {"ALFRED_REGISTRY_PATH": str(self.root)}):
            registry = AlfredModelRegistry()
        registry_file = self.root / "registry.json"
        registry_file.write_text("{broken", encoding="utf-8")
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=lambda: outcome), patch(
            "apps.ml_engine.training.orchestrator.model_registry", registry,
        ):
            result = run_training_cycle(model_keys=["salary_predictor", "relationship_model"], force=True, trigger="test")
        self.assertEqual([item["status"] for item in result["results"]], ["ready", "ready"])
        state = AdaptiveModelState.objects.get(model_key="salary_predictor")
        self.assertEqual(state.status, "ready")
        self.assertIn("receipt could not be saved", state.notes)
        self.assertFalse(AdaptiveTrainingRun.objects.filter(status="training").exists())
        self.assertEqual(registry_file.read_text(encoding="utf-8"), "{broken")

    def test_nonfinite_evaluation_receipt_is_refused_without_losing_the_prior_receipt(self):
        outcome = dict(status="skipped", sample_count=1, notes="Synthetic skip.", evaluation={"mae": float("nan")})
        with patch.dict("os.environ", {"ALFRED_REGISTRY_PATH": str(self.root)}):
            registry = AlfredModelRegistry()
        registry.update("salary_predictor", "synthetic-v1")
        before = (self.root / "registry.json").read_bytes()
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=lambda: outcome), patch(
            "apps.ml_engine.training.orchestrator.model_registry", registry,
        ):
            result = run_training_cycle(model_keys=["salary_predictor"], force=True, trigger="test")
        self.assertEqual(result["results"][0]["status"], "skipped")
        self.assertEqual((self.root / "registry.json").read_bytes(), before)
        self.assertEqual(json.loads(before)["salary_predictor"]["version"], "synthetic-v1")
