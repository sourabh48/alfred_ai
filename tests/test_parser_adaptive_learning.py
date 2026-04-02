import fitz

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from alfred_ai.services.parser_learning import apply_parser_learning, record_parser_learning
from apps.ml_engine.models import DocumentParserLearningMemory


class ParserAdaptiveLearningTests(TestCase):
    def setUp(self):
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

    def test_repeated_credit_report_uploads_create_learning_memory_and_raise_confidence(self):
        report_bytes = self._build_credit_pdf(
            """
            TransUnion CIBIL Credit Report
            Credit Score: 782
            Consumer Name: Soura Sarkar
            Report Number: CIBIL-2026-001
            Report Date: 30/03/2026
            Total Accounts: 5
            Active Accounts: 4
            Closed Accounts: 1
            Delinquent Accounts: 0
            Credit Utilization: 18%
            Total Credit Limit: INR 500000
            """
        )

        responses = []
        for index in range(3):
            report = SimpleUploadedFile(
                f"cibil-report-{index}.pdf",
                report_bytes,
                content_type="application/pdf",
            )
            response = self.client.post(
                "/api/integrations/credit-score/upload-report/",
                data={"report": report, "bureau": "CIBIL"},
            )
            self.assertEqual(response.status_code, 201)
            responses.append(response.json())

        self.assertEqual(DocumentParserLearningMemory.objects.filter(user=self.user, scope="credit_report").count(), 1)
        self.assertIn("Adaptive parser memory", responses[2]["upload"]["parser_notes"])

    def _build_credit_pdf(self, text: str) -> bytes:
        document = fitz.open()
        page = document.new_page()
        point = fitz.Point(72, 72)
        for line in [item.strip() for item in text.strip().splitlines() if item.strip()]:
            page.insert_text(point, line, fontsize=12)
            point = fitz.Point(point.x, point.y + 22)
        return document.tobytes()
