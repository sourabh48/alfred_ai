from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import OperationalError
from django.test import Client, TestCase
from django.utils import timezone

from apps.expenses.models import BankAccount, Expense, StatementUpload
from datetime import date

from apps.expenses.services.statement_import import (
    ParsedTransaction,
    StatementParseResult,
    _extract_account_holder,
    _extract_account_number,
    classify_transaction_text,
)
from apps.expenses.services.transaction_intelligence import build_user_merchant_profiles, enrich_imported_expense
from alfred_ai.services.pdf_recovery import RecoveredPdf
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

    def test_malformed_statement_pdf_is_stored_for_review_instead_of_crashing(self):
        statement_file = SimpleUploadedFile("hdfc statement.pdf", b"%PDF-1.7 truncated", content_type="application/pdf")

        with patch(
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
                    "statement_kind": "bank_statement",
                    "statement": statement_file,
                },
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("stored for review", payload["detail"])
        self.assertEqual(payload["imported_count"], 0)
        self.assertEqual(payload["upload"]["parser_status"], "failed")
        self.assertIn("PDF reader", payload["parser_notes"])

        upload = StatementUpload.objects.latest("id")
        self.assertEqual(upload.parser_status, "failed")
        self.assertIn("parser_notes", upload.extracted_payload)

    def test_statement_upload_list_exposes_parser_notes_and_transaction_flag(self):
        StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="review.pdf",
            parser_status="needs_review",
            parse_confidence=0.62,
            extracted_payload={"parser_notes": "Recovered metadata only."},
            imported_count=0,
        )

        response = self.client.get("/api/expenses/uploads/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["parser_notes"], "Recovered metadata only.")
        self.assertFalse(payload[0]["has_transactions"])

    def test_parse_bank_statement_uses_repaired_pdf_ocr_preview_for_metadata(self):
        preview_text = """
        HDFC BANK
        Statement of account
        Account No : 50100244137504 PRIME
        MR SOURABH SARKAR
        Statement of accountFrom : 31/03/2025 To : 30/03/2026
        Date Narration Chq./Ref.No. Value Dt Withdrawal Amt. Deposit Amt. Closing Balance
        """

        with patch("apps.expenses.services.statement_import._extract_with_pypdf", return_value=""), patch(
            "apps.expenses.services.statement_import._extract_with_fitz",
            return_value="",
        ), patch(
            "apps.expenses.services.statement_import.rebuild_orphaned_pdf",
            return_value=RecoveredPdf(repaired_bytes=b"%PDF-1.7 repaired", page_count=123),
        ), patch(
            "apps.expenses.services.statement_import._extract_with_ocr",
            return_value=preview_text,
        ):
            from apps.expenses.services.statement_import import parse_bank_statement

            parsed = parse_bank_statement(BytesIO(b"%PDF-1.7 broken"))

        self.assertEqual(parsed.bank_name, "HDFC Bank")
        self.assertEqual(parsed.account_number, "50100244137504 PRIME")
        self.assertEqual(parsed.account_holder, "Sourabh Sarkar")
        self.assertEqual(parsed.statement_kind, "bank_statement")
        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertEqual(parsed.transactions, [])
        self.assertLessEqual(parsed.confidence, 0.62)
        self.assertIn("OCR preview recovered header data", parsed.parser_notes)

    def test_parse_bank_statement_keeps_partial_ocr_transactions_for_repaired_pdf(self):
        preview_text = """
        HDFC BANK
        Statement of account
        Account No : 50100244137504 PRIME
        MR SOURABH SARKAR
        Statement of accountFrom : 31/03/2025 To : 30/03/2026
        Date Narration Chq./Ref.No. Value Dt Withdrawal Amt. Deposit Amt. Closing Balance
        31/03/25 UPI-CAFE LAZY LAD-Q972172493@YBL-YESB0YBLUPI-102441316974-UPI 0000102441316974 01/04/25 560.00 54220.81
        """

        with patch("apps.expenses.services.statement_import._extract_with_pypdf", return_value=""), patch(
            "apps.expenses.services.statement_import._extract_with_fitz",
            return_value="",
        ), patch(
            "apps.expenses.services.statement_import.rebuild_orphaned_pdf",
            return_value=RecoveredPdf(repaired_bytes=b"%PDF-1.7 repaired", page_count=123),
        ), patch(
            "apps.expenses.services.statement_import._extract_with_ocr",
            return_value=preview_text,
        ):
            from apps.expenses.services.statement_import import parse_bank_statement

            parsed = parse_bank_statement(BytesIO(b"%PDF-1.7 broken"))

        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertTrue(parsed.preview_only)
        self.assertEqual(parsed.processed_page_count, 2)
        self.assertEqual(parsed.total_page_count, 123)
        self.assertEqual(parsed.preview_transaction_count, 1)
        self.assertEqual(len(parsed.transactions), 1)
        self.assertIn("partial slice", parsed.parser_notes)

    def test_google_play_mandate_is_classified_as_subscription_not_loan(self):
        details = classify_transaction_text(
            "UPI-GOOGLE PLAY STORE-PLAYSTORE@AXISBANK 0000728141860925 -UTIB0000553-728141860925-MANDATEEXECUTE",
            "debit",
        )

        self.assertEqual(details["classification"], "expense")
        self.assertEqual(details["category"], "subscription")
        self.assertEqual(details["merchant"], "Google Play")
        self.assertEqual(details["company_name"], "Google Play")

    def test_merchant_profiles_reinterpret_legacy_google_play_rows(self):
        for index in range(2):
            Expense.objects.create(
                user=self.user,
                amount=2.0,
                classification="loan",
                category="loan",
                payment_mode="UPI",
                merchant="Google Play Store Mandateexecute",
                description="Auto-classified as loan payment: UPI-GOOGLE PLAY STORE",
                raw_description="UPI-GOOGLE PLAY STORE-PLAYSTORE@AXISBANK-UTIB0000553-MANDATEEXECUTE",
                transaction_date=date(2026, 4, 1),
                direction="debit",
                source="bank_statement",
                external_reference=f"GPAY-{index}",
                counterparty="Google Play Store Mandateexecute",
                company_name="Google Play Store Mandateexecute",
            )

        profiles = build_user_merchant_profiles(user=self.user)

        google_play_profile = profiles.get(("debit", "GOOGLE PLAY"))
        self.assertIsNotNone(google_play_profile)
        self.assertEqual(google_play_profile["classification"], "expense")
        self.assertEqual(google_play_profile["category"], "subscription")

    def test_enrich_imported_expense_reuses_dominant_merchant_history(self):
        for index in range(2):
            Expense.objects.create(
                user=self.user,
                amount=499.0,
                classification="expense",
                category="subscription",
                payment_mode="ACH",
                merchant="Adobe India",
                description="Creative Cloud recurring charge",
                raw_description="ACH D- ADOBE INDIA-IDFCFIRSTBQE",
                transaction_date=date(2026, 4, 1),
                direction="debit",
                source="manual",
                external_reference=f"ADOBE-{index}",
                counterparty="Adobe India",
                company_name="Adobe India",
            )

        enriched = enrich_imported_expense(
            user=self.user,
            amount=499.0,
            classification="expense",
            category="other",
            payment_mode="ACH",
            merchant="Adobe India",
            description="ACH D- ADOBE INDIA-IDFCFIRSTBQE",
            raw_description="ACH D- ADOBE INDIA-IDFCFIRSTBQE",
            direction="debit",
            transaction_date=date(2026, 4, 2),
            external_reference="ADOBE-NEW",
            counterparty="Adobe India",
            company_name="Adobe India",
        )

        self.assertEqual(enriched["classification"], "expense")
        self.assertEqual(enriched["category"], "subscription")
        self.assertEqual(enriched["merchant"], "Adobe India")
        self.assertEqual(enriched["company_name"], "Adobe India")

    def test_partial_ocr_statement_upload_imports_preview_rows_and_tracks_progress(self):
        parsed = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Doc User",
            account_number="1234567890",
            statement_start=date(2025, 3, 31),
            statement_end=date(2026, 3, 30),
            transactions=[
                ParsedTransaction(
                    transaction_date=date(2025, 4, 1),
                    amount=560.0,
                    closing_balance=54220.81,
                    direction="debit",
                    classification="expense",
                    category="food",
                    payment_mode="UPI",
                    merchant="Cafe Lazy Lad",
                    description="Cafe Lazy Lad purchase",
                    raw_description="UPI-CAFE LAZY LAD",
                    external_reference="0000102441316974",
                    counterparty="Cafe Lazy Lad",
                    company_name="Cafe Lazy Lad",
                ),
            ],
            statement_kind="bank_statement",
            parser_status="needs_review",
            confidence=0.64,
            source_text="Recovered OCR preview text",
            loan_hints={},
            parser_notes="OCR preview recovered 1 transaction row from the first repaired pages.",
            preview_only=True,
            processed_page_count=2,
            total_page_count=123,
            preview_transaction_count=1,
        )
        statement_file = SimpleUploadedFile("hdfc-preview.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch("apps.expenses.views.parse_bank_statement", return_value=parsed), patch(
            "apps.expenses.views.loan_intelligence_service.detect_loan_payments",
            return_value={
                "detected_loans": 0,
                "updated_loans": 0,
                "new_payments": 0,
                "review_payments": 0,
            },
        ):
            response = self.client.post("/api/expenses/import-statement/", data={"statement": statement_file})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["imported_count"], 1)
        self.assertIn("OCR-preview transactions", payload["detail"])
        upload = StatementUpload.objects.get(file_name="hdfc-preview.pdf")
        self.assertEqual(upload.parser_status, "needs_review")
        self.assertEqual(upload.imported_count, 1)
        self.assertTrue(upload.extracted_payload["preview_only"])
        self.assertEqual(upload.extracted_payload["ocr_progress"]["processed_pages"], 2)
        self.assertEqual(upload.extracted_payload["ocr_progress"]["total_pages"], 123)

    def test_statement_import_still_succeeds_when_follow_up_loan_detection_hits_locked_database(self):
        parsed = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Doc User",
            account_number="1234567890",
            statement_start=date(2026, 3, 1),
            statement_end=date(2026, 3, 31),
            transactions=[
                ParsedTransaction(
                    transaction_date=date(2026, 3, 15),
                    amount=5200.0,
                    closing_balance=44220.81,
                    direction="debit",
                    classification="loan",
                    category="loan",
                    payment_mode="UPI",
                    merchant="Axis Bank",
                    description="Axis loan payment",
                    raw_description="UPI AXIS LOAN PAYMENT",
                    external_reference="LOCK-TXN-001",
                    counterparty="Axis Bank",
                    company_name="Axis Bank",
                ),
            ],
            statement_kind="bank_statement",
            parser_status="parsed",
            confidence=0.91,
            source_text="Axis loan payment",
            loan_hints={},
            parser_notes="",
        )
        statement_file = SimpleUploadedFile("locked-follow-up.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch("apps.expenses.views.parse_bank_statement", return_value=parsed), patch(
            "apps.expenses.services.statement_lifecycle.loan_intelligence_service.detect_loan_payments",
            side_effect=OperationalError("database is locked"),
        ):
            response = self.client.post("/api/expenses/import-statement/", data={"statement": statement_file})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["imported_count"], 1)
        self.assertEqual(payload["loan_detection"]["new_payments"], 0)
        self.assertTrue(StatementUpload.objects.filter(file_name="locked-follow-up.pdf", imported_count=1).exists())

    def test_account_number_extraction_does_not_confuse_account_branch(self):
        text = """
        HDFC BANK
        Account Branch : PRITECH PARK BENGALURU
        Account No : 50100244137504 PRIME
        """

        self.assertEqual(_extract_account_number(text), "50100244137504 PRIME")

    def test_account_holder_extraction_stops_before_location_tokens(self):
        text = """
        MR SOURABH SARKAR BENGALURU
        KARNATAKA
        """

        self.assertEqual(_extract_account_holder(text), "Sourabh Sarkar")

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

    def test_partial_overlap_statement_still_imports_new_rows_when_reference_repeats(self):
        first = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Doc User",
            account_number="1234567890",
            statement_start=None,
            statement_end=None,
            transactions=[
                ParsedTransaction(
                    transaction_date=date(2026, 3, 2),
                    amount=200.0,
                    closing_balance=800.0,
                    direction="debit",
                    classification="expense",
                    category="shopping",
                    payment_mode="CARD",
                    merchant="Store Alpha",
                    description="Store Alpha purchase",
                    raw_description="CARD STORE ALPHA REF1234567890",
                    external_reference="REF1234567890",
                    counterparty="Store Alpha",
                    company_name="Store Alpha",
                ),
            ],
            statement_kind="bank_statement",
            parser_status="parsed",
            confidence=0.91,
            source_text="first statement",
            loan_hints={},
            parser_notes="",
        )
        second = StatementParseResult(
            bank_name="HDFC Bank",
            account_holder="Doc User",
            account_number="1234567890",
            statement_start=None,
            statement_end=None,
            transactions=[
                ParsedTransaction(
                    transaction_date=date(2026, 3, 2),
                    amount=200.0,
                    closing_balance=800.0,
                    direction="debit",
                    classification="expense",
                    category="shopping",
                    payment_mode="CARD",
                    merchant="Store Alpha",
                    description="Store Alpha purchase",
                    raw_description="CARD STORE ALPHA REF1234567890",
                    external_reference="REF1234567890",
                    counterparty="Store Alpha",
                    company_name="Store Alpha",
                ),
                ParsedTransaction(
                    transaction_date=date(2026, 3, 2),
                    amount=200.0,
                    closing_balance=600.0,
                    direction="debit",
                    classification="expense",
                    category="fuel",
                    payment_mode="UPI",
                    merchant="Fuel Point",
                    description="Fuel refill",
                    raw_description="UPI FUEL POINT REF1234567890",
                    external_reference="REF1234567890",
                    counterparty="Fuel Point",
                    company_name="Fuel Point",
                ),
            ],
            statement_kind="bank_statement",
            parser_status="parsed",
            confidence=0.92,
            source_text="second statement",
            loan_hints={},
            parser_notes="",
        )
        statement_file = SimpleUploadedFile("hdfc-overlap.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch("apps.expenses.views.parse_bank_statement", side_effect=[first, second]), patch(
            "apps.expenses.views.loan_intelligence_service.detect_loan_payments",
            return_value={
                "detected_loans": 0,
                "updated_loans": 0,
                "new_payments": 0,
                "review_payments": 0,
            },
        ):
            first_response = self.client.post("/api/expenses/import-statement/", data={"statement": statement_file})
            second_response = self.client.post(
                "/api/expenses/import-statement/",
                data={"statement": SimpleUploadedFile("hdfc-overlap-2.pdf", b"%PDF-1.4 fake", content_type="application/pdf")},
            )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["imported_count"], 1)
        self.assertEqual(second_response.json()["imported_count"], 1)
        self.assertEqual(second_response.json()["skipped_count"], 1)
        self.assertTrue(
            StatementUpload.objects.filter(file_name="hdfc-overlap-2.pdf", imported_count=1).exists()
        )

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

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["document_type"], "sanction_letter")
        self.assertAlmostEqual(payload["parse_confidence"], 0.84)
        self.assertEqual(payload["loans"][0]["loan_type"], "personal")
        self.assertEqual(payload["upload"]["parser_status"], "parsed")
        self.assertTrue(Loan.objects.filter(user=self.user, loan_account_number="AXIS-PL-001").exists())
