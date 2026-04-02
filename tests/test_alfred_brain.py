from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch


class AlfredBrainTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="brain_user",
            password="Pass12345!",
            monthly_income=85000,
            rent_or_emi=22000,
            city="Bengaluru",
        )

    def test_transaction_classifier_falls_back_without_transformers(self):
        from apps.ml_engine.inference_adapters.transaction_classifier import transaction_classifier

        result = transaction_classifier.predict("UPI-SWIGGY-FOOD ORDER-12345", "debit")

        self.assertEqual(result["classification"], "expense")
        self.assertEqual(result["category"], "food")
        self.assertEqual(result["payment_mode"], "UPI")
        self.assertIn("merchant", result)
        self.assertIn("confidence", result)

    def test_alfred_brain_initializes_without_crashing(self):
        from apps.ml_engine.services.alfred_financial_brain import alfred_brain

        alfred_brain.initialize()

        self.assertIsNotNone(alfred_brain.transaction_classifier)

    @patch("apps.ml_engine.inference_adapters.transaction_classifier.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("apps.ml_engine.inference_adapters.transaction_classifier.SentenceTransformer")
    def test_transaction_classifier_does_not_trigger_remote_model_loads_in_tests(self, sentence_transformer):
        from apps.ml_engine.inference_adapters.transaction_classifier import transaction_classifier

        transaction_classifier.load()

        sentence_transformer.assert_not_called()

    def test_comprehensive_snapshot_returns_expected_sections(self):
        from apps.ml_engine.services.alfred_financial_brain import alfred_brain

        snapshot = alfred_brain.get_comprehensive_financial_snapshot(self.user)

        self.assertEqual(snapshot["user"], self.user.username)
        self.assertIn("generated_at", snapshot)
        self.assertIn("accounts", snapshot)
        self.assertIn("loans", snapshot)
        self.assertIn("investments", snapshot)
        self.assertIn("budget", snapshot)
        self.assertIn("daily_affordability", snapshot)
        self.assertIn("forecast", snapshot)
        self.assertIn("health_score", snapshot)
        self.assertIn("priority_actions", snapshot)
        self.assertIn("score", snapshot["health_score"])
