from datetime import date

import fitz
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from alfred_ai.services import ExtractedDocumentText
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.integrations.models import CreditReportUpload, CreditScore
from apps.loans.models import Loan


class CreditReportUploadTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="credit_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_credit_report_upload_creates_official_score_snapshot(self):
        report = SimpleUploadedFile(
            "cibil-report.pdf",
            self._build_credit_pdf(
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
                Recent Enquiries: 1
                """
            ),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["parser_status"], "parsed")
        self.assertEqual(payload["upload"]["bureau"], "CIBIL")
        self.assertLessEqual(payload["upload"]["parse_confidence"], 0.99)
        self.assertEqual(payload["score"]["source_kind"], "uploaded_report")
        self.assertEqual(payload["score"]["score"], 782)

        stored_upload = CreditReportUpload.objects.get()
        stored_score = CreditScore.objects.get()
        self.assertEqual(stored_upload.parsed_credit_score_id, stored_score.id)
        self.assertEqual(stored_score.score_kind, "official")
        self.assertEqual(stored_score.score, 782)

        dashboard = self.client.get("/api/integrations/credit-score/?bureau=CIBIL")
        self.assertEqual(dashboard.status_code, 200)
        dashboard_payload = dashboard.json()
        self.assertEqual(dashboard_payload["source_kind"], "uploaded_report")
        self.assertEqual(dashboard_payload["source_file_name"], "cibil-report.pdf")

        comprehensive = self.client.get("/api/integrations/credit-score/comprehensive-report/")
        self.assertEqual(comprehensive.status_code, 200)
        comprehensive_payload = comprehensive.json()
        self.assertEqual(comprehensive_payload["bureau_status"], "uploaded_report_active")
        self.assertEqual(comprehensive_payload["active_score_source"]["score"], 782)
        self.assertEqual(comprehensive_payload["factor_analysis"]["source_kind"], "uploaded_report")
        self.assertEqual(comprehensive_payload["peer_comparison"]["comparison_basis"], "official_uploaded_score")

        all_bureaus = self.client.get("/api/integrations/credit-score/all-bureaus/")
        self.assertEqual(all_bureaus.status_code, 200)
        all_bureaus_payload = all_bureaus.json()
        self.assertTrue(all_bureaus_payload["success"])
        self.assertEqual(all_bureaus_payload["scores"]["CIBIL"]["score"], 782)

        refresh = self.client.post("/api/integrations/credit-score/refresh/", data={"bureau": "CIBIL"}, content_type="application/json")
        self.assertEqual(refresh.status_code, 400)
        self.assertIn("uploaded bureau report", refresh.json()["error"])

    def test_unreadable_credit_report_stays_in_review(self):
        report = SimpleUploadedFile(
            "printed-report.pdf",
            b"%PDF-1.4 broken-report",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["parser_status"], "needs_review")
        self.assertIsNone(payload["score"])
        self.assertEqual(CreditScore.objects.count(), 0)
        self.assertEqual(CreditReportUpload.objects.count(), 1)

    @patch("apps.integrations.services.credit_report_parser.extract_document_text")
    def test_scanned_credit_report_ocr_text_creates_official_score(self, mock_extract_document_text):
        mock_extract_document_text.return_value = ExtractedDocumentText(
            text="""
            3/30/26,8:44PM CIBIL Report
            CIBIL
            Part of TransUnion
            CIBIL Score & Report
            ControlNumber:10.76.89.63.216
            Date:30/03/2026
            Hello,SOURABHSARKARSOURABHSARKAR
            YourCIBILScoreis802asofDate:30/03/2026
            300 802 900
            """,
            method="isolated_rapidocr_pdf",
            confidence=0.97,
            notes=["OCR fallback recovered text using isolated_rapidocr_pdf."],
        )
        report = SimpleUploadedFile(
            "scanned-cibil-report.pdf",
            b"%PDF-1.4 scanned-report",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["parser_status"], "parsed")
        self.assertEqual(payload["upload"]["bureau"], "CIBIL")
        self.assertLessEqual(payload["upload"]["parse_confidence"], 0.99)
        self.assertEqual(payload["score"]["score"], 802)
        self.assertEqual(payload["score"]["source_kind"], "uploaded_report")
        self.assertEqual(payload["upload"]["applicant_name"], "SOURABHSARKAR")
        self.assertEqual(payload["upload"]["report_number"], "10.76.89.63.216")

    def test_credit_report_upload_extracts_trade_lines_for_financial_linking(self):
        report = SimpleUploadedFile(
            "cibil-tradelines.pdf",
            self._build_credit_pdf(
                """
                TransUnion CIBIL Credit Report
                Credit Score: 782
                Consumer Name: Soura Sarkar
                Report Number: CIBIL-2026-009
                Report Date: 30/03/2026

                Member Name: Axis Bank
                Account Number: XXXX1234
                Account Type: Personal Loan
                Date Opened: 01/01/2024
                Current Balance: INR 120000
                Sanctioned Amount: INR 250000
                EMI Amount: INR 12500
                Account Status: Active

                Member Name: HDFC Bank
                Account Number: XXXX5678
                Account Type: Credit Card
                Date Opened: 01/06/2023
                Date Closed: 01/02/2026
                Current Balance: INR 0
                Sanctioned Amount: INR 150000
                Account Status: Closed
                """
            ),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["loan_account_overview"]["tracked_accounts"], 2)
        self.assertEqual(payload["upload"]["loan_account_overview"]["active_accounts"], 1)
        self.assertEqual(payload["upload"]["loan_accounts"][0]["lender_name"], "Axis Bank")
        self.assertEqual(payload["upload"]["loan_accounts"][0]["loan_account_number"], "XXXX1234")
        self.assertEqual(payload["upload"]["loan_accounts"][0]["account_type"], "Personal Loan")
        self.assertEqual(payload["upload"]["loan_accounts"][0]["status"].lower(), "active")
        self.assertEqual(payload["upload"]["loan_accounts"][0]["emi_amount"], 12500.0)

    def test_credit_report_upload_updates_matched_active_and_closed_loans(self):
        active_loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS1234",
            principal=250000,
            interest_rate=11,
            emi=12000,
            tenure_months=36,
            remaining_balance=150000,
            start_date=date(2024, 1, 1),
            is_active=True,
            status="active",
        )
        closing_loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="HDFC Bank",
            loan_account_number="HDFC5678",
            principal=150000,
            interest_rate=12,
            emi=7000,
            tenure_months=30,
            remaining_balance=35000,
            start_date=date(2023, 6, 1),
            is_active=True,
            status="active",
        )

        report = SimpleUploadedFile(
            "cibil-loan-sync.pdf",
            self._build_credit_pdf(
                """
                TransUnion CIBIL Credit Report
                Credit Score: 790
                Consumer Name: Soura Sarkar
                Report Number: CIBIL-2026-011
                Report Date: 30/03/2026

                Member Name: Axis Bank
                Account Number: XXXX1234
                Account Type: Personal Loan
                Date Opened: 01/01/2024
                Current Balance: INR 120000
                Sanctioned Amount: INR 250000
                EMI Amount: INR 12500
                Account Status: Active

                Member Name: HDFC Bank
                Account Number: XXXX5678
                Account Type: Personal Loan
                Date Opened: 01/06/2023
                Date Closed: 01/02/2026
                Current Balance: INR 0
                Sanctioned Amount: INR 150000
                EMI Amount: INR 7000
                Account Status: Closed
                """
            ),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["loan_sync"]["processed_accounts"], 2)
        self.assertEqual(payload["loan_sync"]["matched_loans"], 2)
        self.assertGreaterEqual(payload["loan_sync"]["updated_loans"], 1)
        self.assertEqual(payload["loan_sync"]["closed_loans"], 1)

        active_loan.refresh_from_db()
        closing_loan.refresh_from_db()
        self.assertEqual(active_loan.remaining_balance, 120000.0)
        self.assertEqual(closing_loan.status, "closed")
        self.assertFalse(closing_loan.is_active)
        self.assertEqual(closing_loan.remaining_balance, 0.0)
        self.assertEqual(closing_loan.closed_on.isoformat(), "2026-02-01")
        self.assertEqual(closing_loan.closure_reason, "bureau_report_verified")
        self.assertIn("Bureau sync", active_loan.notes)

        intelligence = build_financial_intelligence(self.user)
        self.assertEqual(intelligence["loan_portfolio"]["active_loans"], 1)
        self.assertEqual(intelligence["loan_portfolio"]["manual_total_outstanding"], 120000.0)

    def test_credit_report_upload_creates_missing_active_and_closed_loans_for_insights(self):
        report = SimpleUploadedFile(
            "cibil-new-loans.pdf",
            self._build_credit_pdf(
                """
                TransUnion CIBIL Credit Report
                Credit Score: 775
                Consumer Name: Soura Sarkar
                Report Number: CIBIL-2026-012
                Report Date: 30/03/2026

                Member Name: ICICI Bank
                Account Number: XXXX1111
                Account Type: Home Loan
                Date Opened: 01/01/2025
                Current Balance: INR 1850000
                Sanctioned Amount: INR 2200000
                EMI Amount: INR 24500
                Account Status: Active

                Member Name: SBI
                Account Number: XXXX2222
                Account Type: Car Loan
                Date Opened: 01/01/2022
                Date Closed: 01/12/2025
                Current Balance: INR 0
                Sanctioned Amount: INR 450000
                EMI Amount: INR 9800
                Account Status: Closed
                """
            ),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/integrations/credit-score/upload-report/",
            data={"report": report, "bureau": "CIBIL"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["loan_sync"]["created_loans"], 2)
        self.assertEqual(payload["loan_sync"]["created_active_loans"], 1)
        self.assertEqual(payload["loan_sync"]["created_closed_loans"], 1)

        created_loans = list(Loan.objects.filter(user=self.user).order_by("loan_account_number"))
        self.assertEqual(len(created_loans), 2)
        self.assertTrue(any(loan.loan_type == "home" and loan.is_active for loan in created_loans))
        self.assertTrue(any(loan.loan_type == "car" and not loan.is_active for loan in created_loans))
        self.assertTrue(all(loan.auto_detected for loan in created_loans))

        intelligence = build_financial_intelligence(self.user)
        self.assertEqual(intelligence["loan_portfolio"]["active_loans"], 1)
        self.assertEqual(intelligence["loan_portfolio"]["manual_total_outstanding"], 1850000.0)

    def _build_credit_pdf(self, text: str) -> bytes:
        document = fitz.open()
        page = document.new_page()
        point = fitz.Point(72, 72)
        for line in [item.strip() for item in text.strip().splitlines() if item.strip()]:
            page.insert_text(point, line, fontsize=12)
            point = fitz.Point(point.x, point.y + 22)
        return document.tobytes()
