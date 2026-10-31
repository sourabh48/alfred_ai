"""M14F: synthetic exception and historical diagnostic disclosure regressions."""
import json
from contextlib import redirect_stdout
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from rest_framework.exceptions import APIException

from apps.loans.diagnostics import LOAN_PROCESSING_ERROR, public_payload
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument
from apps.loans.serializers import LoanClosureDocumentSerializer, LoanImportDocumentSerializer
from apps.reports.models import OperationalLog
from alfred_ai.services.upload_limits import UploadFormatError, UploadLimitExceeded, UploadStorageUnavailable, UploadProtectionUnavailable


SECRETS = (r"C:\synthetic-private\temp\loan.pdf", "FAKE-LOAN-9988776655", "7654321.98",
           "OCR PRIVATE SYNTHETIC BORROWER TEXT", "fake-token-M14F-abcdefghijkl", "Traceback (most recent call last)",
           "RAW_UPLOADED_PRIVATE_M14F")
PRIVATE = "; ".join(SECRETS)
PARSED = {"document_type": "loan_statement", "confidence": .8, "extracted_text": "Synthetic source evidence",
          "loans": [{"lender": "Test Bank", "loan_type": "personal", "loan_account_number": "TESTLOAN42",
                     "principal": 1000, "remaining_balance": 500, "emi": 100, "interest_rate": 0,
                     "tenure_months": 10, "start_date": "2026-01-01"}]}


class LoanDiagnosticTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-m14f-"))
        self.directory = Path(directory)
        from alfred_private_storage import private_directory
        private_directory(self.directory)
        limits = private_directory(self.directory / "limits")
        self.enterContext(override_settings(MEDIA_ROOT=directory, FILE_UPLOAD_TEMP_DIR=directory,
                                           ALFRED_ABUSE_THROTTLE_DIR=str(limits),
                                           ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=False))
        self.user = get_user_model().objects.create_user(username="m14f", password="Synthetic-X8!Lantern")
        self.client.force_login(self.user)
        cache.clear()

    def file(self, name="synthetic.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.7 RAW_UPLOADED_PRIVATE_M14F", content_type="application/pdf")

    def loan(self):
        return Loan.objects.create(user=self.user, lender="Test Bank", loan_account_number="TESTLOAN42",
                                   principal=1000, remaining_balance=500, emi=100, interest_rate=0,
                                   tenure_months=10, start_date=date(2026, 1, 1))

    def assert_private_absent(self, value):
        text = json.dumps(value) if not isinstance(value, str) else value
        for marker in SECRETS:
            self.assertNotIn(marker, text)
            self.assertNotIn(json.dumps(marker)[1:-1], text)

    def test_parser_failures_are_reviewable_with_safe_persistence_and_correlated_logs(self):
        for marker in SECRETS:
            with self.subTest(marker=marker), patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=RuntimeError(marker)), self.assertLogs(
                "apps.loans.views", level="ERROR") as logs:
                response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertFalse(data["success"])
            self.assertEqual(data["upload"]["parser_status"], "failed")
            self.assertEqual(data["error"], LOAN_PROCESSING_ERROR)
            UUID(data["error_id"])
            self.assert_private_absent(data)
            self.assertEqual(data["upload"]["extracted_payload"]["error_id"], data["error_id"])
            document = LoanImportDocument.objects.latest("id")
            self.assert_private_absent(document.extracted_payload)
            self.assert_private_absent(document.summary)
            self.assertEqual(document.extracted_text, "")
            self.assertTrue(Path(document.uploaded_file.path).exists())
            event = OperationalLog.objects.get(document_id=document.id, event_type="loan_document_failed")
            self.assert_private_absent(event.payload)
            record = logs.records[0]
            self.assertEqual(record.error_id, data["error_id"])
            self.assertEqual(record.exception_type, "RuntimeError")
            self.assertIsNone(record.exc_info)
            self.assert_private_absent(" ".join(logs.output))
        self.assertEqual(Loan.objects.count(), 0)

    def test_nested_exception_and_unprintable_exception_are_never_formatted(self):
        class UnprintableError(Exception):
            def __str__(self):
                raise AssertionError("Exception text must never be evaluated")
        nested = RuntimeError(PRIVATE)
        nested.__cause__ = OSError(PRIVATE)
        for error in (nested, UnprintableError()):
            with self.subTest(error_type=type(error).__name__), patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=error):
                response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
            self.assertEqual(response.status_code, 201)
            self.assert_private_absent(response.json())

    def test_real_parser_extraction_and_pdf_processing_failures_reach_safe_fallback_without_stdout(self):
        extraction = SimpleNamespace(text="Synthetic loan statement", confidence=.7, notes=[PRIVATE], review_payload={"ocr": PRIVATE})
        for target in ("extract_document_text", "LoanPDFParser._parse_single_loan_statement", "apply_parser_learning"):
            with self.subTest(target=target), patch("apps.loans.services.loan_pdf_parser.extract_document_text", return_value=extraction), patch(
                "apps.loans.services.loan_pdf_parser." + target, side_effect=RuntimeError(PRIVATE)), redirect_stdout(StringIO()) as output:
                response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
            self.assertEqual(response.status_code, 201)
            self.assert_private_absent(response.json())
            self.assert_private_absent(output.getvalue())
            self.assertEqual(response.json()["upload"]["parser_status"], "failed")

    def test_payoff_pdf_image_and_ocr_failures_are_safe_500(self):
        loan = self.loan()
        for name in ("closure.pdf", "closure.png"):
            with self.subTest(name=name), patch("apps.loans.services.loan_closure_parser.extract_document_text", side_effect=RuntimeError(PRIVATE)), self.assertLogs(
                "apps.loans.views", level="ERROR") as logs:
                response = self.client.post(f"/api/loans/{loan.pk}/payoff/", {"file": self.file(name)})
            self.assertEqual(response.status_code, 500)
            self.assert_private_absent(response.json())
            self.assertEqual(logs.records[0].error_id, response.json()["error_id"])
        self.assertEqual(LoanClosureDocument.objects.count(), 0)
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, 500)

    def test_persistence_failure_is_not_misreported_as_reviewable_parser_failure(self):
        with patch("apps.loans.views.loan_pdf_parser.parse_document", return_value=PARSED), patch(
            "apps.loans.views._create_loan_import_document", side_effect=OSError(PRIVATE)):
            response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
        self.assertEqual(response.status_code, 500)
        self.assert_private_absent(response.json())
        self.assertEqual(Loan.objects.count(), 0)
        self.assertEqual(LoanImportDocument.objects.count(), 0)

    def test_fallback_save_failure_is_logged_and_returns_safe_500(self):
        with patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=RuntimeError(PRIVATE)), patch(
            "apps.loans.views._create_loan_import_document", side_effect=OSError(PRIVATE)), self.assertLogs("apps.loans.views", level="ERROR") as logs:
            response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
        self.assertEqual(response.status_code, 500)
        self.assertEqual([record.exception_type for record in logs.records], ["RuntimeError", "OSError"])
        self.assert_private_absent(" ".join(logs.output))
        self.assert_private_absent(response.json())

    def test_resource_statuses_and_generic_api_exception_are_safe(self):
        for exception in (UploadFormatError, UploadLimitExceeded, UploadStorageUnavailable, UploadProtectionUnavailable, APIException):
            with self.subTest(exception=exception.__name__), patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=exception(PRIVATE)):
                response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
            self.assertEqual(response.status_code, exception.status_code)
            self.assert_private_absent(response.json())
        self.assertEqual(LoanImportDocument.objects.count(), 0)

    def test_cleanup_failure_preserves_document_and_logs_safe_reference(self):
        from django.core.files.storage import default_storage
        with override_settings(ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=True), patch(
            "apps.loans.views.loan_pdf_parser.parse_document", return_value=PARSED), patch.object(
            default_storage, "delete", side_effect=OSError(PRIVATE)), self.assertLogs("alfred_ai.services.upload_privacy", level="ERROR") as logs:
            response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        metadata = data["raw_file_retention"]
        self.assertFalse(metadata["deleted"])
        self.assertEqual(logs.records[0].error_id, metadata["error_id"])
        self.assertEqual(logs.records[0].exception_type, "OSError")
        self.assert_private_absent(data)
        self.assert_private_absent(" ".join(logs.output))
        document = LoanImportDocument.objects.get()
        self.assertTrue(Path(document.uploaded_file.path).exists())
        self.assert_private_absent(document.extracted_payload)
        self.assertNotIn("storage_name", document.extracted_payload["raw_file_retention"])
        self.assertNotIn("file_name", document.extracted_payload["raw_file_retention"])

    def test_historical_import_payloads_filtered_on_all_public_routes_without_rewriting(self):
        payload = {"error": PRIVATE, "parser_notes": PRIVATE, "warnings": [PRIVATE], "unknown": {"error": PRIVATE},
                   "raw_text_excerpt": PRIVATE, "extraction_review": {"ocr_pages": [{"preview": PRIVATE}]},
                   "accepted_corrections": {"review_note": PRIVATE}, "background_retry": {"state": "failed", "error": PRIVATE},
                   "raw_file_retention": {"deleted": False, "error": PRIVATE, "storage_name": PRIVATE}, "error_id": "a" * 32}
        document = LoanImportDocument.objects.create(user=self.user, file_name="historical.pdf", uploaded_file=self.file(),
            parser_status="failed", summary=PRIVATE, extracted_text=PRIVATE, extracted_payload=payload)
        OperationalLog.objects.create(user=self.user, module="loans", scope="loan_document", event_type="loan_document_failed",
            severity="error", document_id=document.pk, message=PRIVATE, file_name=PRIVATE, payload=payload)
        self.assert_private_absent(LoanImportDocumentSerializer(document).data)
        for url in ("/api/loans/import-uploads/", "/api/loans/summary/", "/api/documents/review-queue/", "/api/documents/diagnostics/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assert_private_absent(response.json())
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload, payload)
        self.assertEqual(document.summary, PRIVATE)
        self.assertEqual(document.extracted_text, PRIVATE)
        self.assertTrue(Path(document.uploaded_file.path).exists())

    def test_historical_closure_and_nested_settlement_diagnostics_filtered(self):
        loan = self.loan()
        document = LoanClosureDocument.objects.create(loan=loan, uploaded_file=self.file(), file_name="closure.pdf",
            parser_status="failed", verification_status="rejected", verification_notes=PRIVATE, extracted_text=PRIVATE,
            extracted_payload={"error": PRIVATE, "raw_source_amount": PRIVATE, "parser_notes": PRIVATE,
                               "extraction_review": {"ocr": PRIVATE}, "background_retry": {"error": PRIVATE}})
        snapshot = LoanForeclosureSnapshot.objects.create(loan=loan, closure_document=document,
            linkage_notes=PRIVATE, reconciliation_notes=PRIVATE, audit_payload={"settlement_allocation": {
                "payment_total": 500.0, "notes": PRIVATE, "expense_allocations": [{"expense_id": 42, "amount": 500.0, "notes": PRIVATE}],
                "document_components": {"principal_paid": 500.0, "private": PRIVATE}, "unknown": {"raw": PRIVATE}}})
        serialized = LoanClosureDocumentSerializer(document).data
        self.assert_private_absent(serialized)
        self.assertEqual(serialized["foreclosure_snapshot"]["settlement_allocation"]["payment_total"], 500.0)
        for url in ("/api/loans/summary/", f"/api/loans/{loan.pk}/", "/api/documents/review-queue/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assert_private_absent(response.json())
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.reconciliation_notes, PRIVATE)

    def test_historical_malformed_diagnostics_and_poisoned_allowlist_values_fail_closed(self):
        for payload in (None, [], PRIVATE, {"error_id": PRIVATE, "confidence": PRIVATE, "document_type": PRIVATE,
                "raw_file_retention": {"policy": PRIVATE, "reason": PRIVATE, "deleted": PRIVATE}, "background_retry": [PRIVATE]}):
            with self.subTest(payload_type=type(payload).__name__):
                self.assert_private_absent(public_payload(payload))

    def test_successful_import_deduplicates_and_keeps_normal_loan_contract(self):
        for attempt in (1, 2):
            with patch("apps.loans.views.loan_pdf_parser.parse_document", return_value={**PARSED, "parser_notes": PRIVATE,
                       "payload": {"error": PRIVATE, "raw_text_excerpt": PRIVATE}}):
                response = self.client.post("/api/loans/import-pdf/", {"file": self.file()})
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["upload"]["parser_status"], "parsed")
            self.assertEqual(data["loans"][0]["loan_account_number"], "TESTLOAN42")
            self.assertEqual(data["loans"][0]["remaining_balance"], 500.0)
            self.assertTrue(data["upload"]["file_url"])
            self.assert_private_absent(data)
            self.assertEqual(Loan.objects.count(), 1)
            self.assertEqual(LoanImportDocument.objects.count(), attempt)
            self.assert_private_absent(LoanImportDocument.objects.latest("id").extracted_payload)

    def test_successful_real_parsers_do_not_persist_ocr_or_extraction_notes_as_diagnostics(self):
        from apps.loans.services.loan_pdf_parser import loan_pdf_parser
        from apps.loans.services.loan_closure_parser import loan_closure_parser
        text = "HDFC PERSONAL LOAN\nLoan Number TESTLOAN42\nLoan Amount 1000.00\nEMI Amount 100.00\nOutstanding Amount 500.00"
        extraction = SimpleNamespace(text=text, confidence=.8, notes=[PRIVATE], method=PRIVATE, review_payload={"ocr": PRIVATE})
        with patch("apps.loans.services.loan_pdf_parser.extract_document_text", return_value=extraction):
            result = loan_pdf_parser.parse_document(BytesIO(b"synthetic"), filename="synthetic.pdf")
        self.assert_private_absent(result["payload"])
        self.assert_private_absent(result["parser_notes"])
        with patch("apps.loans.services.loan_closure_parser.extract_document_text", return_value=extraction):
            result = loan_closure_parser.parse_document(BytesIO(b"synthetic"), "synthetic.png")
        self.assert_private_absent(result["payload"])
        self.assert_private_absent(result["parser_notes"])

    def test_valid_payoff_evidence_keeps_status_and_balance_behavior(self):
        loan = self.loan()
        file = SimpleUploadedFile("closure.txt", b"Test Bank loan closure letter. Loan account number TESTLOAN42. Foreclosure amount 500.00. Closure date 30/03/2026. No due certificate.")
        response = self.client.post(f"/api/loans/{loan.pk}/payoff/", {"file": file, "final_payment_amount": "500"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["document"]["verification_status"], "verified")
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, 500)
        self.assertEqual(loan.status, "foreclosure_pending")

    def test_loan_retry_exception_is_safe_and_does_not_overwrite_forensic_payload(self):
        document = LoanImportDocument.objects.create(user=self.user, uploaded_file=self.file(), file_name="synthetic.pdf",
            parser_status="failed", extracted_payload={"error": PRIVATE}, extracted_text=PRIVATE)
        with patch("alfred_ai.services.document_review.loan_pdf_parser.parse_document", side_effect=OSError(PRIVATE)):
            response = self.client.post("/api/documents/review-queue/retry/", json.dumps({"scope": "loan_document", "id": document.pk}), content_type="application/json")
        self.assertEqual(response.status_code, 500)
        self.assert_private_absent(response.json())
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload["error"], PRIVATE)
        self.assertEqual(document.extracted_text, PRIVATE)

    def test_read_and_mutation_loan_api_errors_do_not_disclose_internal_exceptions(self):
        for url, target in (("/api/loans/summary/", "_build_loan_summary_payload"),
                            ("/api/loans/metrics/", "loan_intelligence_service.calculate_loan_metrics"),
                            ("/api/loans/networth/", "_build_networth_payload")):
            with self.subTest(url=url), patch("apps.loans.views." + target, side_effect=RuntimeError(PRIVATE)):
                response = self.client.get(url)
            self.assertEqual(response.status_code, 500)
            self.assert_private_absent(response.json())
        with patch("apps.loans.views.loan_intelligence_service.detect_loan_payments", side_effect=RuntimeError(PRIVATE)):
            response = self.client.post("/api/loans/detect-from-expenses/")
        self.assertEqual(response.status_code, 500)
        self.assert_private_absent(response.json())

    def test_authentication_csrf_and_owner_scoping_are_preserved(self):
        with patch("apps.loans.views.loan_pdf_parser.parse_document") as parser:
            self.assertEqual(Client().post("/api/loans/import-pdf/", {"file": self.file()}).status_code, 403)
            csrf_client = Client(enforce_csrf_checks=True)
            csrf_client.force_login(self.user)
            self.assertEqual(csrf_client.post("/api/loans/import-pdf/", {"file": self.file()}).status_code, 403)
            parser.assert_not_called()
        other = get_user_model().objects.create_user(username="m14f-other")
        LoanImportDocument.objects.create(user=other, file_name="other.pdf", parser_status="failed")
        self.assertEqual(self.client.get("/api/loans/import-uploads/").json(), [])

    def test_payoff_validation_exception_keeps_400_without_sensitive_detail(self):
        loan = self.loan()
        with patch("apps.loans.views.loan_closure_parser.parse_document", return_value={"payload": {}}), patch(
            "apps.loans.views.loan_foreclosure_service.process_document", side_effect=ValueError(PRIVATE)):
            response = self.client.post(f"/api/loans/{loan.pk}/payoff/", {"file": self.file()})
        self.assertEqual(response.status_code, 400)
        self.assert_private_absent(response.json())

    def test_closure_retry_and_loan_correction_failures_are_safe(self):
        document = LoanClosureDocument.objects.create(loan=self.loan(), uploaded_file=self.file(), file_name="closure.pdf",
                                                     parser_status="failed")
        with patch("alfred_ai.services.document_review.loan_closure_parser.parse_document", side_effect=UploadLimitExceeded(PRIVATE)):
            response = self.client.post("/api/documents/review-queue/retry/", json.dumps({"scope": "loan_closure_document", "id": document.pk}), content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assert_private_absent(response.json())
        with patch("alfred_ai.views.apply_correction", side_effect=ValueError(PRIVATE)):
            response = self.client.post("/api/documents/review-queue/resolve/", json.dumps({"scope": "loan_closure_document", "id": document.pk, "corrections": {}}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assert_private_absent(response.json())
