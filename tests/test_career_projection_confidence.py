from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.career.models import CareerResume
from apps.career.services.projection_engine import resolve_salary_model_runtime
from apps.ml_engine.models import AdaptiveModelState


class CareerProjectionConfidenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="career_projection_user",
            password="Pass12345!",
            monthly_income=98000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _macro_payload(self):
        return {
            "payload": {
                "unemployment": {"latest_value": 5.0, "latest_year": 2025},
                "inflation": {"latest_value": 4.7, "latest_year": 2025},
                "market": {"one_month_return_pct": 2.2, "india_vix": 14.0},
            },
            "evidence": [
                {
                    "source_name": "World Bank",
                    "source_url": "https://data.worldbank.org",
                    "verified_at": timezone.now().isoformat(),
                    "summary": "Macro evidence",
                }
            ],
        }

    def _market_payload(self):
        return {
            "risk_score": 28,
            "layoff_news": [],
            "job_market_news": [],
            "macro_context": self._macro_payload()["payload"],
            "insights": ["Market is stable."],
            "evidence": [],
        }

    def test_projection_uses_model_backed_baseline_when_salary_predictor_is_ready_and_loadable(self):
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.html", b"<html></html>", content_type="text/html"),
            file_name="resume.html",
            parser_status="parsed",
            parse_confidence=0.86,
            extracted_payload={"skills": ["Python", "SQL"], "role": "Analyst"},
        )
        AdaptiveModelState.objects.create(
            model_key="salary_predictor",
            display_name="Salary predictor",
            status="ready",
            sample_count=40,
            quality_score=71.4,
            confidence_estimate=68.3,
            artifact_path="ml_models/alfred/salary_model/model.pkl",
            last_finished_at=timezone.now(),
            next_refresh_due_at=timezone.now() + timedelta(hours=12),
        )

        with patch("apps.career.views.verified_intelligence.macro_context", return_value=self._macro_payload()), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value=self._market_payload(),
        ), patch(
            "apps.career.services.projection_engine.resolve_artifact_path",
            return_value=Path(settings.BASE_DIR) / "README.md",
        ), patch(
            "apps.career.services.projection_engine.salary_predictor.predict",
            return_value=120000.0,
        ):
            response = self.client.get("/api/career/projection/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        confidence = payload["projection_confidence"]

        self.assertEqual(payload["projection_mode"], "hybrid_model_backed")
        self.assertEqual(payload["projection_basis"]["baseline_source"], "salary_predictor_model")
        self.assertEqual(payload["projection_basis"]["model_predicted_income"], 120000.0)
        self.assertEqual(confidence["status"], "model_backed_baseline")
        self.assertEqual(confidence["score"], 68.3)
        self.assertEqual(confidence["label"], "Model-backed baseline confidence")
        self.assertIn("not a confidence interval for the full five-year trajectory", confidence["method"].lower())
        self.assertTrue(confidence["model"]["available"])
        self.assertTrue(confidence["model"]["is_fresh"])
        self.assertTrue(confidence["model"]["inference_ready"])
        self.assertEqual(confidence["model"]["inference_reason"], "ok")
        self.assertEqual(confidence["model"]["sample_count"], 40)
        self.assertTrue(confidence["support"]["resume_used"])
        self.assertEqual(confidence["support"]["skills_count"], 2)
        self.assertTrue(all("confidence" not in item for item in payload["projections"]))

    def test_projection_stays_heuristic_when_model_state_exists_but_artifact_is_not_available(self):
        AdaptiveModelState.objects.create(
            model_key="salary_predictor",
            display_name="Salary predictor",
            status="ready",
            sample_count=12,
            quality_score=61.0,
            confidence_estimate=59.0,
            artifact_path="ml_models/alfred/salary_model/model.pkl",
            notes="Artifact is missing on disk.",
        )

        with patch("apps.career.views.verified_intelligence.macro_context", return_value=self._macro_payload()), patch(
            "apps.career.views.job_intelligence.market_outlook",
            return_value=self._market_payload(),
        ), patch(
            "apps.career.services.projection_engine.resolve_artifact_path",
            return_value=Path("F:/ALFRED/ml_models/alfred/missing_salary_model.pkl"),
        ):
            response = self.client.get("/api/career/projection/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        confidence = payload["projection_confidence"]

        self.assertEqual(payload["projection_mode"], "heuristic")
        self.assertEqual(confidence["status"], "unavailable")
        self.assertIsNone(confidence["score"])
        self.assertIn("heuristic", confidence["summary"].lower())
        self.assertIn("no prediction confidence score is attached", confidence["method"].lower())
        self.assertTrue(confidence["model"]["available"])
        self.assertFalse(confidence["model"]["inference_ready"])
        self.assertEqual(confidence["model"]["inference_reason"], "artifact_missing")

    def test_invalid_training_evidence_never_reaches_salary_inference(self):
        state = AdaptiveModelState.objects.create(
            model_key="salary_predictor", display_name="Salary predictor", status="ready",
            sample_count=40, quality_score=75, confidence_estimate=70,
            artifact_path=str(Path(settings.BASE_DIR) / "README.md"),
            next_refresh_due_at=timezone.now() + timedelta(hours=12),
        )
        cases = [
            ({"sample_count": 9}, "validation_blocked"),
            ({"quality_score": 49}, "validation_blocked"),
            ({"confidence_estimate": 54}, "validation_blocked"),
            ({"next_refresh_due_at": None}, "model_stale"),
            ({"next_refresh_due_at": timezone.now() - timedelta(seconds=1)}, "model_stale"),
        ]
        for changes, reason in cases:
            with self.subTest(changes=changes):
                state.sample_count, state.quality_score, state.confidence_estimate = 40, 75, 70
                state.next_refresh_due_at = timezone.now() + timedelta(hours=12)
                for key, value in changes.items():
                    setattr(state, key, value)
                state.save()
                with patch("apps.career.services.projection_engine.salary_predictor.predict") as predict:
                    result = resolve_salary_model_runtime(self.user, {})
                self.assertFalse(result["available"])
                self.assertEqual(result["state"]["inference_reason"], reason)
                predict.assert_not_called()

    def test_nonfinite_salary_predictions_use_heuristic_fallback(self):
        AdaptiveModelState.objects.create(
            model_key="salary_predictor", display_name="Salary predictor", status="ready",
            sample_count=40, quality_score=75, confidence_estimate=70,
            artifact_path=str(Path(settings.BASE_DIR) / "README.md"),
            next_refresh_due_at=timezone.now() + timedelta(hours=12),
        )
        inputs = {"variable_income": 0, "rent_or_emi": 1000, "city": "Pune", "account_age_days": 30}
        for prediction in [float("nan"), float("inf"), -1.0]:
            with self.subTest(prediction=prediction), patch(
                "apps.career.services.projection_engine.salary_predictor.predict", return_value=prediction,
            ):
                result = resolve_salary_model_runtime(self.user, inputs)
            self.assertFalse(result["available"])
            self.assertEqual(result["state"]["inference_reason"], "invalid_prediction")
