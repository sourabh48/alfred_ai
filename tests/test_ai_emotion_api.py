from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.behavioral.models import BehavioralSignal
from apps.ml_engine.core.alfred_router import alfred_router


class EmotionApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="emotion_user",
            password="Pass12345!",
            monthly_income=90000,
            rent_or_emi=25000,
            city="Bengaluru",
        )
        BehavioralSignal.objects.create(
            user=self.user,
            stress_score=8.2,
            sleep_hours=5.5,
            work_hours=10.5,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_emotion_api_returns_valid_prediction_payload(self):
        response = self.client.post(
            "/api/ai/emotion/",
            data={
                "amount": 4200,
                "category": "shopping",
                "description": "Flash sale Myntra order for premium sneakers",
                "merchant": "Myntra",
                "direction": "debit",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertNotIn("error", payload)
        self.assertTrue(payload["is_emotional"])
        self.assertGreaterEqual(payload["confidence"], 0.65)
        self.assertIn("reason", payload)
        self.assertIn("analysis_source", payload)

    def test_router_accepts_legacy_emotion_task_alias(self):
        result = alfred_router.route(
            "emotion-expense",
            {
                "user": self.user,
                "amount": 2500,
                "category": "food",
                "description": "Late night Swiggy comfort order",
                "merchant": "Swiggy",
                "direction": "debit",
            },
        )

        self.assertNotIn("error", result)
        self.assertIn("is_emotional", result)
        self.assertIn("confidence", result)
