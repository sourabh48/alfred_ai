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


class PdfTextLayerTests(SimpleTestCase):
    @staticmethod
    def _pdf(lines):
        import fitz
        document = fitz.open(); page = document.new_page()
        for row, line in enumerate(lines):
            page.insert_text((40, 50 + row * 16), line, fontsize=10)
        return document.tobytes()

    def test_a_soft_hyphen_from_the_font_stays_a_hyphen_before_digits_and_is_dropped_in_words(self):
        from alfred_ai.services.document_extraction import _clean_text
        self.assertEqual(_clean_text("Sanction Date: 02\xad08\xad2023, P&L \xad464.00, pre\xadpayment"),
                         "Sanction Date: 02-08-2023, P&L -464.00, prepayment")

    def test_a_short_readable_text_layer_is_kept_over_ocr_that_scores_only_slightly_higher(self):
        lines = ["Synthetic Lender", "Loan Account No: SYN123456", "EMI Amount: Rs 1,000", "Tenure: 12 Months"]
        layer_with_table_gap = "\n".join(lines).replace(": ", ":  ")  # OCR's double space earns the table bonus
        with patch("alfred_ai.services.document_extraction._extract_pdf_with_ocr",
                   return_value=(layer_with_table_gap, "rapidocr_pdf", [], {})):
            extracted = extract_document_text(self._pdf(lines), "short-statement.pdf")
        self.assertNotEqual(extracted.method, "rapidocr_pdf")
        self.assertIn("Loan Account No: SYN123456", extracted.text)

    def test_ocr_still_replaces_a_text_layer_that_is_clearly_worse(self):
        good = "\n".join(f"Row {n}: Synthetic statement line with an amount Rs 1,{n:03d} on 0{n % 9 + 1}/01/2026" for n in range(12))
        with patch("alfred_ai.services.document_extraction._extract_pdf_with_ocr", return_value=(good, "rapidocr_pdf", [], {})):
            extracted = extract_document_text(self._pdf(["x"]), "scan-with-stub-layer.pdf")
        self.assertEqual(extracted.method, "rapidocr_pdf")
