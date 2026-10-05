"""Bureau balance presence must survive parsing before it can confirm debt."""
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.integrations.models import CreditReportUpload
from apps.integrations.services.credit_loan_sync import sync_credit_report_loans
from apps.integrations.services.credit_report_parser import CreditReportParser
from apps.loans.models import Loan


class BureauBalanceEvidenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="bureau-balance-evidence")
        self.loan = Loan.objects.create(
            user=self.user, lender="Example Housing Finance", loan_account_number="HOME123456",
            loan_type="home", principal=240000, remaining_balance=232000, emi=10000,
            interest_rate=10, tenure_months=24, start_date=timezone.localdate(),
            auto_detected=True, verification_status="estimated", verification_source="emi_pattern",
        )

    def report(self, balance_line="", *, account_number="HOME123456"):
        text = "\n".join([
            "TransUnion CIBIL Credit Report", "Your CIBIL Score: 780",
            "Report Date: 01/10/2026", "Report Number: REPORT123456",
            "Member Name: Example Housing Finance", f"Account Number: {account_number}",
            "Account Type: Home Loan", "Account Status: Active", "Sanctioned Amount: 240000",
            balance_line, "Amount Overdue: 100", "EMI Amount: 9000",
        ])
        payload = CreditReportParser()._extract_payload(text)
        self.assertEqual(len(payload["loan_accounts"]), 1)
        return CreditReportUpload.objects.create(
            user=self.user, file_name="bureau.txt", parser_status="parsed", parse_confidence=.95,
            extracted_text=text, extracted_payload=payload,
        )

    def test_parsed_missing_balance_neither_confirms_nor_erases_existing_debt(self):
        report = self.report()
        account = report.extracted_payload["loan_accounts"][0]
        self.assertEqual(account["current_balance"], 0)
        self.assertFalse(account["balance_reported"])
        for state in ("estimated", "confirmed"):
            with self.subTest(state=state):
                self.loan.verification_status = state
                self.loan.save()
                result = sync_credit_report_loans(user=self.user, report_upload=report)
                self.assertEqual(result["review_items"], 1)
                self.loan.refresh_from_db()
                self.assertEqual(self.loan.verification_status, state)
                self.assertEqual(self.loan.remaining_balance, 232000)
                self.assertEqual(self.loan.emi, 10000)
                self.assertIsNone(self.loan.verified_at)

    def test_parsed_explicit_zero_remains_reported_across_later_lines(self):
        report = self.report("Current Balance: 0")
        account = report.extracted_payload["loan_accounts"][0]
        self.assertTrue(account["balance_reported"])
        self.assertEqual(account["current_balance"], 0)
        result = sync_credit_report_loans(user=self.user, report_upload=report)
        self.assertEqual(result["updated_loans"], 1)
        self.loan.refresh_from_db()
        self.assertTrue(self.loan.is_confirmed)
        self.assertEqual(self.loan.remaining_balance, 0)
        self.assertEqual(self.loan.emi, 9000)
        self.assertEqual(self.loan.interest_rate, 0)

    def test_missing_balance_cannot_create_a_confirmed_bureau_loan(self):
        report = self.report(account_number="OTHER987654")
        result = sync_credit_report_loans(user=self.user, report_upload=report)
        self.assertEqual(result["created_loans"], 0)
        self.assertEqual(result["review_items"], 1)
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 1)

    def test_legacy_default_zero_is_reviewed_but_positive_balance_has_evidence(self):
        for balance in (0, 150000):
            with self.subTest(balance=balance):
                report = self.report(f"Current Balance: {balance}")
                payload = deepcopy(report.extracted_payload)
                del payload["loan_accounts"][0]["balance_reported"]
                report.extracted_payload = payload
                result = sync_credit_report_loans(user=self.user, report_upload=report)
                self.loan.refresh_from_db()
                if balance == 0:
                    self.assertEqual(result["review_items"], 1)
                    self.assertFalse(self.loan.is_confirmed)
                    self.assertEqual(self.loan.remaining_balance, 232000)
                else:
                    self.assertEqual(result["updated_loans"], 1)
                    self.assertTrue(self.loan.is_confirmed)
                    self.assertEqual(self.loan.remaining_balance, balance)
