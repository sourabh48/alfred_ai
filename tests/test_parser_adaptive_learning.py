from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from alfred_ai.services.parser_learning import apply_parser_learning, record_parser_learning
from alfred_private_storage import private_directory
from apps.ml_engine.models import DocumentParserLearningMemory


class ParserAdaptiveLearningTests(TestCase):
    def setUp(self):
        limits = self.enterContext(TemporaryDirectory(prefix="alfred-parser-limits-"))
        private_directory(limits)
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=limits))
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="parser_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_parser_learning_service_boosts_confidence_after_similar_successes(self):
        base_text = "TransUnion CIBIL Credit Report Credit Score 782 Consumer Name Soura Sarkar"
        base_fields = ["score", "applicant_name", "report_date"]

        initial_confidence, initial_notes = apply_parser_learning(
            user=self.user,
            scope="credit_report",
            filename="report.pdf",
            detected_type="CIBIL",
            text=base_text,
            field_names=base_fields,
            confidence=0.62,
        )
        self.assertEqual(initial_confidence, 0.62)
        self.assertEqual(initial_notes, [])

        for _ in range(2):
            record_parser_learning(
                user=self.user,
                scope="credit_report",
                filename="report.pdf",
                detected_type="CIBIL",
                text=base_text,
                field_names=base_fields,
                parser_status="parsed",
                confidence=0.84,
            )

        boosted_confidence, boosted_notes = apply_parser_learning(
            user=self.user,
            scope="credit_report",
            filename="report.pdf",
            detected_type="CIBIL",
            text=base_text,
            field_names=base_fields,
            confidence=0.62,
        )
        self.assertGreater(boosted_confidence, 0.62)
        self.assertTrue(boosted_notes)
        self.assertEqual(DocumentParserLearningMemory.objects.count(), 1)
