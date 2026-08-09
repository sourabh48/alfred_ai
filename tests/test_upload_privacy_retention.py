import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction
from apps.career.models import CareerResume
from apps.expenses.models import StatementUpload
from apps.expenses.services.statement_import import StatementParseResult
from apps.integrations.models import CreditReportUpload
from apps.investments.models import InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanImportDocument
from apps.mobility.models import BikeDocument


class UploadPrivacyRetentionTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.override = override_settings(
            MEDIA_ROOT=self.tempdir.name,
            ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=True,
        )
        self.override.enable()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="privacy-user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        self.override.disable()
        self.tempdir.cleanup()

    def test_raw_file_cleanup_removes_saved_document_file_and_records_metadata(self):
        resume = CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.pdf", b"private resume", content_type="application/pdf"),
            file_name="resume.pdf",
            extracted_payload={"role": "Analyst"},
        )
        stored_path = Path(resume.uploaded_file.path)
        self.assertTrue(stored_path.exists())

        metadata = purge_uploaded_file_after_extraction(
            resume,
            "uploaded_file",
            reason="unit_test_cleanup",
        )

        resume.refresh_from_db()
        self.assertTrue(metadata["deleted"])
        self.assertFalse(stored_path.exists())
        self.assertFalse(resume.uploaded_file)
        self.assertEqual(resume.extracted_payload["raw_file_retention"]["policy"], "delete_after_extraction")
        self.assertEqual(resume.extracted_payload["raw_file_retention"]["reason"], "unit_test_cleanup")

    def test_primary_document_models_can_purge_raw_uploads_after_extraction(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Privacy Bank",
            principal=100000,
            interest_rate=10,
            emi=5000,
            tenure_months=24,
            remaining_balance=90000,
            start_date="2026-01-01",
        )
        rows = [
            (
                StatementUpload.objects.create(
                    user=self.user,
                    original_file=SimpleUploadedFile("statement.pdf", b"statement", content_type="application/pdf"),
                    file_name="statement.pdf",
                    extracted_payload={"parser_notes": "ok"},
                ),
                "original_file",
            ),
            (
                CreditReportUpload.objects.create(
                    user=self.user,
                    uploaded_file=SimpleUploadedFile("credit.pdf", b"credit", content_type="application/pdf"),
                    file_name="credit.pdf",
                    extracted_payload={"score": 780},
                ),
                "uploaded_file",
            ),
            (
                InvestmentImportDocument.objects.create(
                    user=self.user,
                    uploaded_file=SimpleUploadedFile("portfolio.pdf", b"portfolio", content_type="application/pdf"),
                    file_name="portfolio.pdf",
                    extracted_payload={"broker": "test"},
                ),
                "uploaded_file",
            ),
            (
                LoanImportDocument.objects.create(
                    user=self.user,
                    uploaded_file=SimpleUploadedFile("loan.pdf", b"loan", content_type="application/pdf"),
                    file_name="loan.pdf",
                    extracted_payload={"document_type": "loan"},
                ),
                "uploaded_file",
            ),
            (
                LoanClosureDocument.objects.create(
                    loan=loan,
                    uploaded_file=SimpleUploadedFile("closure.pdf", b"closure", content_type="application/pdf"),
                    file_name="closure.pdf",
                    extracted_payload={"closure_amount": 90000},
                ),
                "uploaded_file",
            ),
            (
                BikeDocument.objects.create(
                    user=self.user,
                    bike_name="Privacy Bike",
                    document_file=SimpleUploadedFile("invoice.pdf", b"invoice", content_type="application/pdf"),
                    document_title="invoice.pdf",
                    extracted_payload={"amount": 1200},
                ),
                "document_file",
            ),
        ]

        for instance, field_name in rows:
            with self.subTest(model=type(instance).__name__):
                field_file = getattr(instance, field_name)
                stored_path = Path(field_file.path)
                self.assertTrue(stored_path.exists())

                metadata = purge_uploaded_file_after_extraction(
                    instance,
                    field_name,
                    reason="document_family_cleanup",
                )

                instance.refresh_from_db()
                self.assertTrue(metadata["deleted"])
                self.assertFalse(stored_path.exists())
                self.assertFalse(getattr(instance, field_name))
                self.assertTrue(instance.extracted_payload["raw_file_retention"]["deleted"])

    def test_statement_upload_endpoint_deletes_raw_file_and_skips_background_retry_when_enabled(self):
        statement = SimpleUploadedFile("statement.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        parsed_statement = StatementParseResult(
            bank_name="Privacy Bank",
            account_holder="Privacy User",
            account_number="1234567890",
            statement_start=None,
            statement_end=None,
            transactions=[],
            statement_kind="bank_statement",
            parser_status="needs_review",
            confidence=0.58,
            source_text="Statement header only",
            loan_hints={},
            parser_notes="Header-only preview recovered.",
        )
        with patch("apps.expenses.views.parse_bank_statement", return_value=parsed_statement), patch(
            "apps.expenses.views.loan_intelligence_service.detect_loan_payments",
            return_value={"detected_loans": 0, "updated_loans": 0, "new_payments": 0, "review_payments": 0},
        ):
            response = self.client.post("/api/expenses/import-statement/", data={"statement": statement})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        upload = StatementUpload.objects.get(user=self.user)

        self.assertTrue(payload["raw_file_retention"]["deleted"])
        self.assertFalse(upload.original_file)
        self.assertEqual(
            upload.extracted_payload["background_retry"]["state"],
            "not_queued_raw_file_deleted",
        )
        self.assertTrue(upload.extracted_payload["raw_file_retention"]["deleted"])
