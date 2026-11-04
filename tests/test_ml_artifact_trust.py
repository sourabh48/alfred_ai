"""Real synthetic artifact files: evidence binds the exact bytes and nothing is unpickled."""
from hashlib import sha256
import json
import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ml_engine.core.alfred_registry import AlfredModelRegistry
from apps.ml_engine.core.alfred_router import alfred_router
from apps.ml_engine.inference_adapters.artifacts import (
    ARTIFACT_FORMAT, MAX_ARTIFACT_BYTES, build_artifact_evidence, dump_artifact, load_inference_artifact,
)
from apps.ml_engine.inference_adapters.burnout_rf import BurnoutRF
from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTMAdapter
from apps.ml_engine.inference_adapters.relationship_model import MODEL_PATH, RelationshipModelPredictor
from apps.ml_engine.inference_adapters.risk_classifier import RiskClassifier
from apps.ml_engine.inference_adapters.salary_predictor import SalaryPredictor
from apps.ml_engine.inference_adapters.service_cost_predictor import ServiceCostPredictor
from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.orchestrator import run_training_cycle, serving_readiness_snapshot
from apps.ml_engine.training.simple_models import BinaryLogisticClassifierModel, LinearRegressorModel


NAMES = RelationshipModelPredictor.FEATURE_NAMES
DECLINED = {"status": "unavailable", "task": "relationship", "reason": "model_declined"}


def regressor(intercept, size=len(NAMES)):
    return LinearRegressorModel(coefficients=np.zeros(size), intercept=intercept,
                                feature_mean=np.zeros(size), feature_scale=np.ones(size))


class Explosive:
    """Unpickling this creates the marker folder, proving code ran."""
    def __init__(self, marker):
        self.marker = str(marker)

    def __reduce__(self):
        return os.mkdir, (self.marker,)


class ArtifactTrustTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-artifact-synthetic-")))
        self.enterContext(override_settings(BASE_DIR=self.root))
        with patch.dict("os.environ", {"ALFRED_REGISTRY_PATH": str(self.root / "receipts")}):
            self.registry = AlfredModelRegistry()
        self.enterContext(patch("apps.ml_engine.training.orchestrator.model_registry", self.registry))

    def train(self, key="relationship_model", path=MODEL_PATH, names=NAMES, intercept=61.5, status="ready"):
        def trainer():
            if status == "ready":
                dump_artifact({"model": regressor(intercept, len(names)), "feature_names": names}, path)
            return dict(status=status, sample_count=100, quality_score=80, confidence_estimate=80,
                        artifact_path=path if status == "ready" else "", notes="Synthetic fit.")
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=trainer):
            run_training_cycle(model_keys=[key], force=True, trigger="test")
        return AdaptiveModelState.objects.get(model_key=key)

    def file(self, path=MODEL_PATH):
        return self.root / path

    def test_training_records_evidence_for_the_exact_file_and_serves_it(self):
        state = self.train()
        self.assertEqual(state.artifact_evidence, {
            "role": "relationship_model", "sha256": sha256(self.file().read_bytes()).hexdigest(),
            "format": ARTIFACT_FORMAT, "schema": NAMES, "training_version": state.last_finished_at.isoformat(),
        })
        self.assertEqual(alfred_router.route("relationship", {}), 61.5)
        saved = json.loads((self.root / "receipts" / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["relationship_model"]["metadata"]["artifact_evidence"], state.artifact_evidence)
        self.assertEqual(sorted(p.name for p in self.file().parent.iterdir()), ["model.json"])

    def test_replaced_artifact_is_refused_even_with_identical_size_and_time(self):
        self.train()
        stat = self.file().stat()
        raw = self.file().read_bytes()
        forged = raw.replace(b"61.5", b"99.5")
        self.assertEqual(len(forged), len(raw))
        self.file().write_bytes(forged)
        os.utime(self.file(), ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(alfred_router.route("relationship", {}), DECLINED)

    def test_replaced_salary_artifact_is_not_served_from_an_earlier_load(self):
        names = SalaryPredictor.FEATURE_NAMES
        path = "ml_models/alfred/salary_model/model.json"
        self.train("salary_predictor", path, names, 40000.0)
        adapter = SalaryPredictor()
        self.assertEqual(adapter.predict({}, model_path=path), 40000.0)
        dump_artifact({"model": regressor(90000.0, len(names)), "feature_names": names}, path)
        with self.assertRaisesRegex(ValueError, "no valid evidence"):
            adapter.predict({}, model_path=path)

    def test_each_tampered_evidence_field_is_refused(self):
        state = self.train()
        original = dict(state.artifact_evidence)
        for field, value in (("role", "salary_predictor"), ("sha256", "0" * 64), ("format", "joblib"),
                             ("schema", NAMES[:-1]), ("training_version", "2020-01-01T00:00:00+00:00"),
                             ("training_version", "not-a-time")):
            with self.subTest(field=field, value=value):
                state.artifact_evidence = original | {field: value}
                state.save()
                self.assertIn(alfred_router.route("relationship", {}).get("reason"), {"model_declined", "not_inference_ready"})
        for missing in original:
            with self.subTest(missing=missing):
                state.artifact_evidence = {k: v for k, v in original.items() if k != missing}
                state.save()
                self.assertIn(alfred_router.route("relationship", {}).get("reason"), {"model_declined", "not_inference_ready"})
        state.artifact_evidence = "not-an-object"
        state.save()
        self.assertEqual(alfred_router.route("relationship", {})["reason"], "not_inference_ready")
        state.artifact_evidence = original
        state.save()
        self.assertEqual(alfred_router.route("relationship", {}), 61.5)

    def test_obsolete_schema_is_refused_after_the_code_changes(self):
        names = SalaryPredictor.FEATURE_NAMES + ["income_variability_ratio"]
        self.train("salary_predictor", "ml_models/alfred/salary_model/model.json", names)
        self.assertEqual(alfred_router.route("salary", {})["reason"], "inference_failed")

    def test_revoked_and_failed_retraining_clear_evidence(self):
        self.train()
        state = self.train(status="skipped")
        self.assertEqual(state.artifact_evidence, {})
        self.assertEqual(alfred_router.route("relationship", {})["reason"], "not_inference_ready")
        self.train()
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=lambda: 1 / 0):
            run_training_cycle(model_keys=["relationship_model"], force=True, trigger="test")
        state = AdaptiveModelState.objects.get(model_key="relationship_model")
        self.assertEqual((state.status, state.artifact_evidence), ("failed", {}))
        self.assertEqual(alfred_router.route("relationship", {})["reason"], "not_inference_ready")

    def test_row_without_evidence_reads_nothing_and_readiness_says_so(self):
        legacy = self.root / "ml_models" / "alfred" / "relationship_model" / "model.pkl"
        legacy.parent.mkdir(parents=True)
        marker = self.root / "unpickled"
        legacy.write_bytes(pickle.dumps(Explosive(marker)))
        before = legacy.read_bytes()
        state = self.train()
        state.artifact_path, state.artifact_evidence = str(legacy), {}
        state.save()
        self.assertEqual(alfred_router.route("relationship", {})["reason"], "not_inference_ready")
        readiness = next(item for item in serving_readiness_snapshot()["models"] if item["key"] == "relationship_model")
        self.assertFalse(readiness["registry_eligible"])
        self.assertFalse(marker.exists())
        self.assertEqual(legacy.read_bytes(), before)

    def test_pickle_with_matching_digest_is_never_executed_by_any_loader(self):
        marker = self.root / "unpickled"
        raw = pickle.dumps(Explosive(marker))
        cases = (("relationship_model", "relationship", MODEL_PATH, NAMES),
                 ("salary_predictor", "salary", "ml_models/alfred/salary_model/model.json", SalaryPredictor.FEATURE_NAMES),
                 ("service_cost_predictor", "service-cost", "ml_models/alfred/service_cost_predictor/model.json", ServiceCostPredictor.FEATURE_NAMES),
                 ("expense_forecaster", "expense-forecast", "ml_models/alfred/expense_lstm/model.json", ExpenseLSTMAdapter.FEATURE_NAMES))
        for key, task, path, names in cases:
            with self.subTest(task=task), patch("joblib.load") as load, patch("pickle.loads") as loads:
                state = self.train(key, path, names)
                self.file(path).write_bytes(raw)
                state.artifact_evidence |= {"sha256": sha256(raw).hexdigest()}
                state.save()
                alfred_router.route(task, [1] * 10 if task == "expense-forecast" else {})
                load.assert_not_called()
                loads.assert_not_called()
                self.assertFalse(marker.exists())

    def test_files_outside_the_model_root_or_escaping_it_are_refused(self):
        state = self.train()
        raw = self.file().read_bytes()
        evidence = dict(state.artifact_evidence)
        outside = self.root / "elsewhere" / "model.json"
        outside.parent.mkdir()
        outside.write_bytes(raw)
        for path in (str(outside), "ml_models/alfred/../../elsewhere/model.json", "elsewhere/model.json"):
            with self.subTest(path=path):
                self.assertEqual(build_artifact_evidence("relationship_model", path, evidence["training_version"]), {})
                state.artifact_path = path
                state.save()
                self.assertEqual(alfred_router.route("relationship", {}), DECLINED)

    def link_folder(self, link, target):
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        else:
            os.symlink(target, link, target_is_directory=True)
        self.addCleanup(lambda: os.unlink(link) if os.path.lexists(link) else None)

    def test_folder_link_and_hard_link_are_refused(self):
        state = self.train()
        raw = self.file().read_bytes()
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "model.json").write_bytes(raw)

        linked = self.root / "ml_models" / "alfred" / "linked"
        self.link_folder(linked, outside)
        state.artifact_path = str(linked / "model.json")
        state.save()
        self.assertEqual(alfred_router.route("relationship", {}), DECLINED)

        hard = self.root / "ml_models" / "alfred" / "relationship_model" / "hard.json"
        os.link(outside / "model.json", hard)
        state.artifact_path = str(hard)
        state.save()
        self.assertEqual(alfred_router.route("relationship", {}), DECLINED)

    def test_file_symlink_is_refused(self):
        state = self.train()
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "model.json").write_bytes(self.file().read_bytes())
        symbolic = self.root / "ml_models" / "alfred" / "relationship_model" / "symbolic.json"
        try:
            symbolic.symlink_to(outside / "model.json")
        except OSError:
            self.skipTest("This Windows account may not create file symlinks; the folder link test still ran.")
        state.artifact_path = str(symbolic)
        state.save()
        self.assertEqual(alfred_router.route("relationship", {}), DECLINED)

    def test_malformed_documents_earn_no_evidence_and_never_serve(self):
        good = {"format": ARTIFACT_FORMAT, "feature_names": NAMES, "model": {
            "kind": "linear_regressor", "coefficients": [0.0] * 5, "intercept": 1.0,
            "feature_mean": [0.0] * 5, "feature_scale": [1.0] * 5}}
        model = good["model"]
        documents = [b"{broken", b"[]", b"null", json.dumps(good).replace("1.0", "NaN", 1).encode(),
                     json.dumps(good | {"format": "pickle"}).encode(), json.dumps(good | {"feature_names": []}).encode(),
                     json.dumps(good | {"model": model | {"kind": "__import__"}}).encode(),
                     json.dumps(good | {"model": model | {"coefficients": [0.0] * 4}}).encode(),
                     json.dumps(good | {"model": model | {"coefficients": [[0.0] * 5]}}).encode(),
                     json.dumps(good | {"model": model | {"intercept": [1.0]}}).encode(),
                     json.dumps(good | {"model": model | {"extra": 1}}).encode(),
                     json.dumps(good).encode() + b" " * MAX_ARTIFACT_BYTES]
        state = self.train()
        for raw in documents:
            with self.subTest(raw=raw[:60]):
                self.file().write_bytes(raw)
                self.assertEqual(build_artifact_evidence("relationship_model", MODEL_PATH, "v"), {})
                state.artifact_evidence |= {"sha256": sha256(raw).hexdigest()}
                state.save()
                self.assertIsNone(load_inference_artifact("relationship_model", schema=NAMES))
        self.file().write_bytes(json.dumps(good).encode())
        self.assertTrue(build_artifact_evidence("relationship_model", MODEL_PATH, "v"))

    def test_fresh_instances_after_a_restart_rely_only_on_durable_evidence(self):
        self.train()
        row = AdaptiveModelState.objects.get(model_key="relationship_model")
        self.assertEqual(RelationshipModelPredictor().predict_score({}), 61.5)
        row.refresh_from_db()
        self.file().unlink()
        self.assertIsNone(RelationshipModelPredictor().predict_score({}))
        self.train(intercept=62.5)
        self.assertEqual(RelationshipModelPredictor().predict_score({}), 62.5)

    def test_corrupt_registry_does_not_change_verified_serving(self):
        self.train()
        (self.root / "receipts" / "registry.json").write_text("{broken", encoding="utf-8")
        self.assertEqual(alfred_router.route("relationship", {}), 61.5)

    def test_expense_role_round_trips_real_file_and_falls_back_when_replaced(self):
        names = ExpenseLSTMAdapter.FEATURE_NAMES
        path = "ml_models/alfred/expense_lstm/model.json"

        def trainer():
            dump_artifact({"model": regressor(np.log1p(500.0), len(names)), "feature_names": names, "window_size": 10,
                           "transform": "log1p", "trained_at": timezone.now().isoformat(), "freshness_hours": 12,
                           "sample_count": 100, "quality_score": 80, "confidence_estimate": 80,
                           "evaluation": {"passed": True}}, path)
            return dict(status="ready", sample_count=100, quality_score=80, confidence_estimate=80, artifact_path=path)
        with patch("apps.ml_engine.training.orchestrator._load_trainer", return_value=trainer):
            run_training_cycle(model_keys=["expense_forecaster"], force=True, trigger="test")
        amounts = list(range(1, 11))
        self.assertAlmostEqual(alfred_router.route("expense-forecast", amounts), 500.0)
        self.file(path).write_bytes(self.file(path).read_bytes() + b" ")
        self.assertEqual(alfred_router.route("expense-forecast", amounts), 5.5)

    def test_layoff_risk_stays_off_even_with_valid_evidence_and_no_blockers(self):
        names = RiskClassifier.FEATURE_NAMES
        path = "ml_models/alfred/risk_classifier/model.json"
        size = len(names)
        model = BinaryLogisticClassifierModel(np.zeros(size), 0.0, np.zeros(size), np.ones(size))

        def trainer():
            dump_artifact({"model": model, "feature_names": names}, path)
            return dict(status="ready", sample_count=100, quality_score=80, confidence_estimate=80, artifact_path=path)
        with patch("apps.ml_engine.training.quality.PROXY_TARGET_NOTES", {}), patch(
            "apps.ml_engine.training.orchestrator._load_trainer", return_value=trainer,
        ):
            run_training_cycle(model_keys=["risk_classifier"], force=True, trigger="test")
            state = AdaptiveModelState.objects.get(model_key="risk_classifier")
            self.assertTrue(state.inference_ready)
            self.assertEqual(alfred_router.route("risk", [5, 7, 9]),
                             {"status": "unavailable", "task": "risk", "reason": "not_inference_ready"})

    def test_burnout_serves_only_once_a_future_change_removes_its_proxy_blocker(self):
        names = BurnoutRF.FEATURE_NAMES
        path = "ml_models/alfred/burnout_rf/model.json"
        self.train("burnout_rf", path, names, 4.5)
        self.assertEqual(alfred_router.route("burnout", [5, 7, 9])["reason"], "not_inference_ready")
        with patch("apps.ml_engine.training.quality.PROXY_TARGET_NOTES", {}):
            self.assertEqual(alfred_router.route("burnout", [5, 7, 9]), 4.5)
