"""Synthetic broker-style tables, not authenticated broker or real-account statements."""
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from alfred_ai.services.document_extraction import ExtractedDocumentText
from apps.investments.models import Investment, InvestmentImportDocument
from apps.investments.services.document_evidence import evidence
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service as service


GROWW_TABLE = """Groww synthetic fund statement - not a real account
Statement date: 2026-03-31
Statement type: portfolio holdings
Statement reference: SYNTH-DOCUMENT
Prepared for: synthetic layout owner
Account: SYNTH-A
Fund Name | Units | Current Value | Invested Amount | NAV
Synthetic Alpha Fund | 999.125 | 110.20 | 100.25 | 4.567
Synthetic Beta Fund | 33.875 | 220.40 | 200.50 | 8.123
Total | | 330.60 | 300.75 |
"""
ZERODHA_TABLE = """Zerodha synthetic holdings - not a real account
Statement date: 2026-03-31
Statement type: portfolio holdings
Statement reference: SYNTH-DOCUMENT
Prepared for: synthetic layout owner
Symbol  Account  Quantity  Cost Value  Market Value  LTP
SYNTHA  SYNTH-A  989  2.675  3.075  44.55
SYNTHA  SYNTH-B  123  2.675  3.075  55.66
"""


def table_pdf(text):
    import fitz
    with fitz.open() as pdf:
        page = pdf.new_page(width=1000, height=600)
        for index, line in enumerate(text.splitlines()):
            page.insert_text((32, 40 + index * 20), line, fontsize=10, fontname="cour")
        return pdf.tobytes()


class InvestmentLayoutAcceptanceTests(TestCase):
    def setUp(self):
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.user = get_user_model().objects.create_user(username="synthetic-layout-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-layout-other")
        self.client.force_login(self.user)

    def parse(self, text, *, method="pypdf_text", confidence=.8, review=None):
        extracted = ExtractedDocumentText(text, method, confidence, [], review or {})
        with patch("apps.investments.services.portfolio_intelligence.extract_document_text", return_value=extracted):
            return service.parse_portfolio_document(BytesIO(b"synthetic"), user=self.user, filename="synthetic.pdf")

    def upload(self, text=GROWW_TABLE):
        self.uploaded_pdf = table_pdf(text)
        return self.client.post("/api/investments/import-pdf/", {
            "file": SimpleUploadedFile("synthetic-layout.pdf", self.uploaded_pdf, content_type="application/pdf")})

    def test_labelled_columns_do_not_import_units_prices_metadata_or_totals(self):
        parsed = self.parse(GROWW_TABLE)
        self.assertEqual(parsed["parser_status"], "parsed")
        rows = parsed["investments"]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["current_value"] for r in rows], ["110.20", "220.40"])
        self.assertEqual([r["invested_amount"] for r in rows], ["100.25", "200.50"])
        self.assertEqual({r["account_number"] for r in rows}, {"SYNTH-A"})
        self.assertEqual({r["asset_type"] for r in rows}, {"mutual_fund"})
        self.assertEqual(parsed["payload"]["layout_review"]["status"], "parsed")

    def test_whitespace_symbol_layout_preserves_account_identity_and_raw_decimal(self):
        rows = self.parse(ZERODHA_TABLE)["investments"]
        self.assertEqual([r["asset_name"] for r in rows], ["SYNTHA", "SYNTHA"])
        self.assertEqual([r["account_number"] for r in rows], ["SYNTH-A", "SYNTH-B"])
        self.assertEqual(rows[0]["current_value"], "3.075")

    def test_uncertain_tables_abstain_without_legacy_numeric_fallback(self):
        cases = {
            "missing column": GROWW_TABLE.replace("Invested Amount", "Unidentified Amount"),
            "ambiguous column": GROWW_TABLE.replace("Units", "Market Value"),
            "unknown account": GROWW_TABLE.replace("Account: SYNTH-A\n", ""),
            "conflicting account": GROWW_TABLE.replace("Account: SYNTH-A", "Account: SYNTH-A\nAccount: SYNTH-B"),
            "bad amount": GROWW_TABLE.replace("110.20", "11O.20"),
            "currency cell": GROWW_TABLE.replace("110.20", "USD 110.20"),
            "currency column": GROWW_TABLE.replace("Units", "Currency"),
            "nonfinite": GROWW_TABLE.replace("110.20", "NaN"),
            "overflow": GROWW_TABLE.replace("110.20", "1000000000000.00"),
            "bad grouping": GROWW_TABLE.replace("110.20", "1,10.20"),
            "total mismatch": GROWW_TABLE.replace("330.60", "999.99"),
            "incomplete row": GROWW_TABLE.replace(" | 8.123", ""),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                parsed = self.parse(text)
                self.assertEqual(parsed["investments"], [])
                self.assertEqual(parsed["parser_status"], "needs_review")
                self.assertEqual(parsed["payload"]["layout_review"]["status"], "needs_review")

    def test_duplicates_repeated_headers_and_conflicts(self):
        line = "Synthetic Alpha Fund | 999.125 | 110.20 | 100.25 | 4.567\n"
        self.assertEqual(len(self.parse(GROWW_TABLE.replace(line, line * 2))["investments"]), 2)
        conflict = GROWW_TABLE.replace(line, line + line.replace("110.20", "120.20"))
        self.assertEqual(self.parse(conflict)["investments"], [])
        conflicting_units = GROWW_TABLE.replace(line, line + line.replace("999.125", "888.125"))
        self.assertEqual(self.parse(conflicting_units)["investments"], [])
        header = next(line for line in GROWW_TABLE.splitlines() if line.startswith("Fund Name")) + "\n"
        self.assertEqual(len(self.parse(GROWW_TABLE.replace(line, line + header))["investments"]), 2)

    def test_ocr_provenance_and_confidence_are_retained_but_money_requires_review(self):
        for method, confidence in (("rapidocr_pdf", .25), ("rapidocr_pdf", .95), ("tesseract_pdf", .95)):
            parsed = self.parse(GROWW_TABLE, method=method, confidence=confidence,
                review={"ocr_pages": [{"page": 1, "regions": [{"text": "110.20", "confidence": confidence}]}]})
            self.assertEqual(parsed["investments"], [])
            self.assertEqual(parsed["parser_status"], "needs_review")
            self.assertEqual(parsed["payload"]["extraction_method"], method)
            self.assertEqual(parsed["payload"]["extraction_review"]["ocr_pages"][0]["regions"][0]["confidence"], confidence)
            self.assertIn("OCR", parsed["parser_notes"])

    def test_row_bound_abstains_instead_of_partial_import(self):
        text = "Account: SYNTH-A\nSymbol | Cost Value | Market Value\n" + "\n".join(
            f"SYNTH{i} | 1 | 2" for i in range(31))
        self.assertEqual(self.parse(text)["investments"], [])

    def test_account_labels_do_not_match_portfolio_words_or_cross_newlines(self):
        for text in ("portfolio holdings", "accounting summary", "Account:\nSYMBOL"):
            self.assertEqual(service._extract_account_hint(text), "")
        self.assertEqual(service._extract_account_hint("Account No.: SYNTH-A"), "SYNTH-A")

    def test_damaged_ocr_without_a_recognizable_header_cannot_fall_back_to_money_guesses(self):
        parsed = self.parse("Synthetic Alpha Fund units 999 value 110.20", method="rapidocr_pdf", confidence=.95)
        self.assertEqual(parsed["parser_status"], "needs_review")
        self.assertEqual(parsed["investments"], [])

    def test_unused_ocr_diagnostics_do_not_relabel_selected_digital_text(self):
        parsed = self.parse(GROWW_TABLE, method="pypdf_text", confidence=.5,
            review={"ocr_pages": [{"page": 1, "regions": []}]})
        self.assertEqual(parsed["parser_status"], "parsed")
        self.assertEqual(parsed["payload"]["extraction_method"], "pypdf_text")
        self.assertEqual(parsed["payload"]["account_number"], "SYNTH-A")
        self.assertEqual(self.parse(ZERODHA_TABLE)["payload"]["account_number"], "")

    def test_extraction_text_bound_requires_complete_source_review(self):
        parsed = self.parse(GROWW_TABLE + "\n" * 30000)
        self.assertEqual(parsed["investments"], [])
        self.assertEqual(parsed["parser_status"], "needs_review")

    def test_real_pdf_extraction_reimport_source_receipts_and_owner_boundaries(self):
        foreign = Investment.objects.create(user=self.other, asset_name="Synthetic Alpha Fund",
            institution="Groww", account_number="SYNTH-A", current_value="42.00")
        identities = None
        for _ in range(2):
            response = self.upload()
            self.assertEqual(response.status_code, 201, response.content)
            document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
            self.assertEqual(document.parser_status, "parsed", document.extracted_text)
            rows = list(document.linked_investments.order_by("asset_name"))
            self.assertEqual(len(rows), 2, document.extracted_text)
            self.assertEqual(sum((r.invested_amount for r in rows), Decimal(0)), Decimal("300.75"))
            self.assertEqual(sum((r.current_value for r in rows), Decimal(0)), Decimal("330.60"))
            current_ids = [r.pk for r in rows]
            if identities is not None:
                self.assertEqual(current_ids, identities)
            identities = current_ids
            self.assertIn("NAV", document.extracted_text)
            self.assertTrue(document.uploaded_file)
            detail = evidence(self.user, document.pk, rows[0].pk)
            self.assertEqual(detail["fields"]["current_value"]["original"], "110.20")
            self.assertIsNone(detail["fields"]["current_value"]["currency"])
            source = self.client.get(detail["source_download_url"])
            self.assertEqual(source.status_code, 200)
            self.assertEqual(b"".join(source.streaming_content), self.uploaded_pdf)
            other_client = Client(); other_client.force_login(self.other)
            self.assertEqual(other_client.get(detail["citation_url"]).status_code, 404)
            self.assertEqual(other_client.get(detail["source_download_url"]).status_code, 404)
            denied = other_client.post("/api/documents/review-queue/resolve/", {
                "scope": "investment_document", "id": document.pk, "corrections": {"current_value": "1"}}, content_type="application/json")
            self.assertEqual(denied.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.current_value, Decimal("42.00"))

    def test_real_whitespace_pdf_rounding_correction_retry_and_original_evidence(self):
        response = self.upload(ZERODHA_TABLE)
        self.assertEqual(response.status_code, 201, response.content)
        document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
        rows = list(document.linked_investments.order_by("account_number"))
        self.assertEqual(len(rows), 2, document.extracted_payload)
        self.assertEqual([r.current_value for r in rows], [Decimal("3.08")] * 2)
        row = rows[0]
        for action, extra in (("resolve", {"corrections": {"current_value": "0", "invested_amount": "2.675"}}), ("retry", {})):
            result = self.client.post(f"/api/documents/review-queue/{action}/", {
                "scope": "investment_document", "id": document.pk, **extra}, content_type="application/json")
            self.assertEqual(result.status_code, 200, result.content)
        row.refresh_from_db(); rows[1].refresh_from_db(); document.refresh_from_db()
        self.assertEqual(row.current_value, Decimal("0.00"))
        self.assertEqual(row.invested_amount, Decimal("2.68"))
        self.assertEqual(rows[1].current_value, Decimal("3.08"))
        self.assertEqual(document.linked_investments.count(), 2)
        self.assertIn("3.075", document.extracted_text)
        self.assertEqual(evidence(self.user, document.pk, row.pk)["fields"]["current_value"]["original"], "3.075")

    def test_unsafe_upload_does_not_overwrite_existing_holding_and_can_be_reviewed(self):
        existing = Investment.objects.create(user=self.user, asset_name="Synthetic Alpha Fund", asset_type="mutual_fund",
            institution="Groww", account_number="SYNTH-A", current_value="42.00")
        response = self.upload(GROWW_TABLE.replace("110.20", "11O.20"))
        self.assertEqual(response.status_code, 201, response.content)
        document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
        self.assertEqual(document.parser_status, "needs_review")
        self.assertFalse(document.linked_investments.exists())
        self.assertEqual(Investment.objects.filter(user=self.user).count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.current_value, Decimal("42.00"))
        result = self.client.post("/api/documents/review-queue/resolve/", {
            "scope": "investment_document", "id": document.pk,
            "corrections": {"asset_name": "Synthetic Alpha Fund", "asset_type": "mutual_fund",
                "account_number": "SYNTH-A", "invested_amount": "100.25", "current_value": "110.20"}},
            content_type="application/json")
        self.assertEqual(result.status_code, 200, result.content)
        row = document.linked_investments.get()
        self.assertEqual(row.pk, existing.pk)
        self.assertEqual(row.current_value, Decimal("110.20"))
        document.refresh_from_db()
        self.assertIn("11O.20", document.extracted_text)
        self.assertIsNone(evidence(self.user, document.pk, row.pk)["fields"]["current_value"]["original"])
