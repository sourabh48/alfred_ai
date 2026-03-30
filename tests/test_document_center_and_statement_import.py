from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.expenses.models import BankAccount, StatementUpload
from apps.expenses.services.statement_import import StatementParseResult
from apps.loans.models import Loan
from apps.mobility.models import BikeProfile


class DocumentCenterAndStatementImportTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="doc_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_documents_page_renders_for_authenticated_user(self):
        response = self.client.get("/documents/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Central upload hub")
        self.assertContains(response, "Statements")
        self.assertContains(response, "Loan Documents")

    def test_statement_upload_persists_parser_metadata_even_without_transactions(self):
        parsed = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Doc User",
            account_number="1234567890",
            statement_start=None,
            statement_end=None,
            transactions=[],
            statement_kind="credit_card_statement",
            parser_status="needs_review",
            confidence=0.61,
            source_text="Credit card statement. Minimum amount due. Card ending 7890.",
            loan_hints={"loan_type": "credit_card"},
        )
        statement_file = SimpleUploadedFile("credit-card.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch("apps.expenses.views.parse_bank_statement", return_value=parsed), patch(
            "apps.expenses.views.loan_intelligence_service.detect_loan_payments",
            return_value={
                "detected_loans": 0,
                "updated_loans": 0,
                "new_payments": 0,
                "review_payments": 0,
            },
        ):
            response = self.client.post(
                "/api/expenses/import-statement/",
                data={
                    "statement_kind": "credit_card_statement",
                    "statement": statement_file,
                },
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("could not confidently extract transactions yet", payload["detail"])
        self.assertEqual(payload["upload"]["parser_status"], "needs_review")
        self.assertEqual(payload["upload"]["source"], "credit_card_statement")

        upload = StatementUpload.objects.get()
        account = BankAccount.objects.get()
        self.assertEqual(upload.source, "credit_card_statement")
        self.assertEqual(upload.parser_status, "needs_review")
        self.assertAlmostEqual(upload.parse_confidence, 0.61)
        self.assertEqual(upload.bank_account_id, account.id)
        self.assertEqual(account.account_type, "credit")
        self.assertEqual(upload.extracted_payload["loan_hints"]["loan_type"], "credit_card")

    def test_dashboard_returns_balance_sheet_without_expense_history(self):
        BankAccount.objects.create(
            user=self.user,
            bank_name="State Bank of India",
            account_number="SBI123456789",
            account_type="savings",
            current_balance=125000,
            is_primary=True,
        )
        BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa",
            model_name="Activa",
            vehicle_type="scooter",
            bike_class="scooter",
            usage_pattern="personal",
            estimated_market_value=70000,
        )

        response = self.client.get("/api/expenses/dashboard/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["risk_level"], "Limited data")
        self.assertGreater(payload["balance_sheet"]["total_assets"], 0)
        self.assertEqual(len(payload["balance_sheet"]["vehicle_positions"]), 1)
        self.assertEqual(payload["balance_sheet"]["vehicle_positions"][0]["bucket"], "liability")

    def test_loan_import_returns_document_type_and_confidence(self):
        loan_file = SimpleUploadedFile("sanction-letter.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch(
            "apps.loans.views.loan_pdf_parser.parse_document",
            return_value={
                "document_type": "sanction_letter",
                "confidence": 0.84,
                "extracted_text": "Sanction letter",
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
                        "start_date": timezone.localdate(),
                    }
                ],
            },
        ):
            response = self.client.post("/api/loans/import-pdf/", data={"file": loan_file})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_type"], "sanction_letter")
        self.assertAlmostEqual(payload["parse_confidence"], 0.84)
        self.assertEqual(payload["loans"][0]["loan_type"], "personal")
        self.assertTrue(Loan.objects.filter(user=self.user, loan_account_number="AXIS-PL-001").exists())
