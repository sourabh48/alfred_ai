from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image, ImageFilter, ImageOps

from alfred_ai.services.document_extraction import extract_document_text


class _FakeRapidOCR:
    def __call__(self, image):
        return (
            [
                [
                    [[12, 14], [212, 14], [212, 42], [12, 42]],
                    ("SOURABH SARKAR", 0.99),
                ],
                [
                    [[12, 56], [288, 56], [288, 92], [12, 92]],
                    ("JAVA BACKEND DEVELOPER", 0.96),
                ],
            ],
            None,
        )


class DocumentExtractionRecoveryTests(SimpleTestCase):
    @patch("alfred_ai.services.document_extraction.fitz", None)
    @patch("alfred_ai.services.document_extraction._load_ocr_dependencies")
    def test_pdf_extension_with_image_bytes_falls_back_to_image_ocr_with_overlay(self, mock_dependencies):
        image = Image.new("RGB", (420, 220), "white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        raw_bytes = buffer.getvalue()
        mock_dependencies.return_value = (_FakeRapidOCR(), None, Image, ImageOps, ImageFilter)

        extracted = extract_document_text(raw_bytes, "broken-credit-report.pdf")

        self.assertEqual(extracted.method, "rapidocr_image")
        self.assertIn("SOURABH SARKAR", extracted.text)
        self.assertEqual(extracted.review_payload["best_method"], "rapidocr_image")
        self.assertEqual(extracted.review_payload["ocr_pages"][0]["page"], 1)
        self.assertGreater(len(extracted.review_payload["ocr_pages"][0]["regions"]), 0)
        self.assertTrue(
            any(step["step"] == "image_bytes_fallback" and step["status"] == "recovered" for step in extracted.review_payload["recovery_steps"])
        )

    def test_unknown_text_document_exposes_field_candidates_for_review(self):
        extracted = extract_document_text(
            b"""
            Invoice Number INV-90812
            Vehicle KA 01 AB 1234
            Total INR 12,345.50
            Date 2026-04-01
            Email sourabh@example.com
            """,
            "unknown-layout.txt",
        )

        candidates = extracted.review_payload["field_candidates"]
        candidate_types = {item["field_type"] for item in candidates}
        self.assertIn("invoice_number", candidate_types)
        self.assertIn("vehicle_number", candidate_types)
        self.assertIn("amount", candidate_types)
        self.assertIn("date", candidate_types)
        self.assertTrue(any(item["field_name"] == "document_number" for item in candidates))
