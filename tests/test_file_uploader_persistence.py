import fitz

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from unittest.mock import patch

from apps.career.models import CareerResume
from apps.expenses.models import StatementUpload
from apps.expenses.services.statement_import import StatementParseResult
from apps.integrations.models import CreditReportUpload
from apps.loans.models import Loan, LoanImportDocument


class FileUploaderPersistenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="uploader_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_primary_file_uploaders_persist_expected_records(self):
        resume = SimpleUploadedFile(
            "resume.html",
            b"<html><body><h1>Soura Analyst</h1><p>Python SQL 4 years experience</p></body></html>",
            content_type="text/html",
        )
        resume_response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})
        self.assertEqual(resume_response.status_code, 201)
        self.assertEqual(CareerResume.objects.filter(user=self.user).count(), 1)

        statement = SimpleUploadedFile("statement.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        parsed_statement = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Uploader User",
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
            statement_response = self.client.post("/api/expenses/import-statement/", data={"statement": statement})
        self.assertEqual(statement_response.status_code, 201)
        self.assertEqual(StatementUpload.objects.filter(user=self.user).count(), 1)

        credit = SimpleUploadedFile("cibil.pdf", self._build_credit_pdf(), content_type="application/pdf")
        credit_response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": credit, "bureau": "CIBIL"},
        )
        self.assertEqual(credit_response.status_code, 201)
        self.assertEqual(CreditReportUpload.objects.filter(user=self.user).count(), 1)

        loan_pdf = SimpleUploadedFile("sanction-letter.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        with patch(
            "apps.loans.views.loan_pdf_parser.parse_document",
            return_value={
                "document_type": "sanction_letter",
                "confidence": 0.84,
                "extracted_text": "Axis Bank sanction letter",
                "loans": [
                    {
                        "lender": "Axis Bank",
                        "loan_type": "personal",
                        "loan_account_number": "AXIS-PL-001",
                        "principal": 250000,
                        "interest_rate": 11.5,
                        "emi": 8450,
                        "tenure_months": 36,
                        "remaining_balance": 250000,
                        "start_date": "2026-03-30",
                    }
                ],
            },
        ):
            loan_response = self.client.post("/api/loans/import-pdf/", data={"file": loan_pdf})

        self.assertEqual(loan_response.status_code, 201)
        self.assertEqual(LoanImportDocument.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 1)

    def test_loan_upload_is_saved_for_review_when_no_structured_loan_rows_exist(self):
        loan_pdf = SimpleUploadedFile("loan-book.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        with patch(
            "apps.loans.views.loan_pdf_parser.parse_document",
            return_value={
                "document_type": "repayment_schedule",
                "confidence": 0.37,
                "extracted_text": "Repayment schedule header only",
                "loans": [],
            },
        ):
            response = self.client.post("/api/loans/import-pdf/", data={"file": loan_pdf})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["parser_status"], "needs_review")
        self.assertEqual(payload["loans"], [])
        self.assertEqual(LoanImportDocument.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 0)

        upload_list = self.client.get("/api/loans/import-uploads/")
        self.assertEqual(upload_list.status_code, 200)
        self.assertEqual(upload_list.json()[0]["file_name"], "loan-book.pdf")

        summary = self.client.get("/api/loans/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["recent_imports"][0]["file_name"], "loan-book.pdf")

    def test_documents_page_shows_recent_loan_docs_section(self):
        response = self.client.get("/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recent Loan Docs")

    def _build_credit_pdf(self) -> bytes:
        document = fitz.open()
        page = document.new_page()
        point = fitz.Point(72, 72)
        for line in [
            "TransUnion CIBIL Credit Report",
            "Credit Score: 782",
            "Consumer Name: Soura Sarkar",
            "Report Number: CIBIL-2026-001",
            "Report Date: 30/03/2026",
            "Total Accounts: 5",
            "Active Accounts: 4",
            "Closed Accounts: 1",
            "Delinquent Accounts: 0",
            "Credit Utilization: 18%",
            "Total Credit Limit: INR 500000",
        ]:
            page.insert_text(point, line, fontsize=12)
            point = fitz.Point(point.x, point.y + 22)
        return document.tobytes()
