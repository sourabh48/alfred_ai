from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.integrations.models import CreditReportUpload
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory


class FinancialRelationshipSynthesisTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="financial_links_user",
            password="Pass12345!",
            monthly_income=120000,
        )

    def test_financial_intelligence_links_transfers_loans_and_bureau_accounts(self):
        primary_account = BankAccount.objects.create(
            user=self.user,
            bank_name="Axis Bank",
            account_number="111122223333",
            account_type="savings",
            current_balance=250000,
        )
        secondary_account = BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC Bank",
            account_number="444455556666",
            account_type="savings",
            current_balance=120000,
        )
        active_loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS1234",
            principal=200000,
            interest_rate=12,
            emi=10000,
            tenure_months=36,
            remaining_balance=120000,
            start_date=timezone.localdate() - timedelta(days=20),
            is_active=True,
            status="active",
        )
        closed_loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS9999",
            principal=150000,
            interest_rate=12,
            emi=9000,
            tenure_months=24,
            remaining_balance=0,
            start_date=timezone.localdate() - timedelta(days=300),
            is_active=False,
            status="foreclosed",
            closed_on=timezone.localdate() - timedelta(days=2),
            closure_reason="foreclosed",
        )

        disbursement = Expense.objects.create(
            user=self.user,
            bank_account=primary_account,
            amount=200000,
            classification="other",
            category="income",
            payment_mode="BANK",
            merchant="Axis Bank",
            description="Axis Bank loan disbursement AXIS1234",
            raw_description="AXIS BANK LOAN DISBURSEMENT AXIS1234",
            transaction_date=active_loan.start_date,
            direction="credit",
            source="bank_statement",
            external_reference="DISB-001",
        )
        transfer_out = Expense.objects.create(
            user=self.user,
            bank_account=primary_account,
            amount=15000,
            classification="other",
            category="transfer",
            payment_mode="BANK",
            merchant="Self Transfer",
            description="Self transfer to HDFC account",
            raw_description="SELF TRANSFER TO OWN ACCOUNT",
            transaction_date=timezone.localdate() - timedelta(days=3),
            direction="debit",
            source="bank_statement",
            external_reference="SELF-001",
        )
        transfer_in = Expense.objects.create(
            user=self.user,
            bank_account=secondary_account,
            amount=15000,
            classification="other",
            category="transfer",
            payment_mode="BANK",
            merchant="Self Transfer",
            description="Self transfer from Axis account",
            raw_description="SELF TRANSFER FROM OWN ACCOUNT",
            transaction_date=timezone.localdate() - timedelta(days=3),
            direction="credit",
            source="bank_statement",
            external_reference="SELF-001",
        )
        regular_repayment = Expense.objects.create(
            user=self.user,
            bank_account=primary_account,
            amount=10000,
            classification="loan",
            category="loan",
            payment_mode="BANK",
            merchant="Axis Bank",
            description="Axis Bank EMI AXIS1234",
            raw_description="AXIS BANK EMI AXIS1234",
            transaction_date=timezone.localdate() - timedelta(days=1),
            direction="debit",
            source="bank_statement",
            external_reference="EMI-001",
        )
        part_payment = Expense.objects.create(
            user=self.user,
            bank_account=primary_account,
            amount=25000,
            classification="loan",
            category="loan",
            payment_mode="BANK",
            merchant="Axis Bank",
            description="Axis Bank part payment AXIS1234",
            raw_description="AXIS BANK PART PAYMENT AXIS1234",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="PART-001",
        )
        closure_payment = Expense.objects.create(
            user=self.user,
            bank_account=primary_account,
            amount=52000,
            classification="loan",
            category="loan",
            payment_mode="BANK",
            merchant="Axis Bank",
            description="Axis Bank foreclosure settlement AXIS9999",
            raw_description="AXIS BANK FORECLOSURE AXIS9999",
            transaction_date=timezone.localdate() - timedelta(days=2),
            direction="debit",
            source="bank_statement",
            external_reference="CLOSE-001",
        )

        LoanPaymentHistory.objects.create(
            loan=active_loan,
            payment_date=regular_repayment.transaction_date,
            amount=10000,
            principal_component=8400,
            interest_component=1600,
            principal_paid=8400,
            interest_paid=1600,
            remaining_balance=111600,
            is_auto_detected=True,
            detection_confidence=89,
            matched_reference="EMI-001",
            match_status="matched",
            expense_reference=regular_repayment,
        )
        LoanPaymentHistory.objects.create(
            loan=active_loan,
            payment_date=part_payment.transaction_date,
            amount=25000,
            principal_component=23200,
            interest_component=1800,
            principal_paid=23200,
            interest_paid=1800,
            remaining_balance=88400,
            is_auto_detected=True,
            detection_confidence=91,
            matched_reference="PART-001",
            match_status="matched",
            expense_reference=part_payment,
        )
        LoanPaymentHistory.objects.create(
            loan=closed_loan,
            payment_date=closure_payment.transaction_date,
            amount=52000,
            principal_component=50000,
            interest_component=1000,
            principal_paid=50000,
            interest_paid=1000,
            charges_paid=500,
            penalties_paid=250,
            tax_paid=250,
            remaining_balance=0,
            is_auto_detected=True,
            detection_confidence=96,
            matched_reference="CLOSE-001",
            match_status="matched",
            expense_reference=closure_payment,
        )

        closure_document = LoanClosureDocument.objects.create(
            loan=closed_loan,
            uploaded_file=SimpleUploadedFile("closure.txt", b"closure", content_type="text/plain"),
            file_name="closure.txt",
            extracted_text="Axis Bank closure letter",
            extracted_payload={"loan_account_number": "AXIS9999"},
            parser_status="parsed",
            parse_confidence=0.91,
            verification_status="verified",
            closure_amount=52000,
            closure_date=closure_payment.transaction_date,
        )
        LoanForeclosureSnapshot.objects.create(
            loan=closed_loan,
            closure_document=closure_document,
            document_type="foreclosure_statement",
            lender_name="Axis Bank",
            borrower_name=self.user.username,
            loan_account_number="AXIS9999",
            statement_date=closure_payment.transaction_date,
            effective_closure_date=closure_payment.transaction_date,
            due_by_date=closure_payment.transaction_date,
            outstanding_principal=50000,
            accrued_interest=1000,
            foreclosure_charges=500,
            overdue_charges=250,
            taxes_gst=250,
            total_amount_payable=52000,
            classification_confidence=0.91,
            linkage_confidence=0.95,
            reconciliation_status="full_match",
            reconciliation_confidence=0.97,
            matched_payment_total=52000,
            matched_closure_transaction_ids=[closure_payment.id],
            audit_payload={},
        )

        CreditReportUpload.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("cibil.pdf", b"credit-data", content_type="application/pdf"),
            file_name="cibil.pdf",
            bureau="CIBIL",
            parser_status="parsed",
            parse_confidence=0.95,
            extracted_payload={
                "loan_accounts": [
                    {
                        "lender_name": "Axis Bank",
                        "loan_account_number": "XXXX1234",
                        "account_type": "Personal Loan",
                        "status": "active",
                        "opened_on": active_loan.start_date.isoformat(),
                        "sanctioned_amount": 200000,
                        "current_balance": 120000,
                        "emi_amount": 10000,
                    },
                    {
                        "lender_name": "Axis Bank",
                        "loan_account_number": "XXXX9999",
                        "account_type": "Personal Loan",
                        "status": "closed",
                        "opened_on": (closed_loan.start_date).isoformat(),
                        "closed_on": closed_loan.closed_on.isoformat(),
                        "sanctioned_amount": 150000,
                        "current_balance": 0,
                        "emi_amount": 9000,
                    },
                ]
            },
            summary="CIBIL report",
        )

        intelligence = build_financial_intelligence(self.user)

        self.assertEqual(intelligence["financial_relationships"]["summary"]["self_transfers"], 1)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["loan_disbursements"], 1)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["loan_repayments"], 1)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["loan_part_payments"], 1)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["loan_closure_payments"], 1)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["bureau_accounts"], 2)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["bureau_accounts_linked"], 2)
        self.assertEqual(len(intelligence["financial_relationships"]["events"]), 5)
        self.assertEqual(
            intelligence["financial_relationships"]["bureau_accounts"][0]["matched_loan_id"],
            active_loan.id,
        )
        recent_by_reference = {
            item["description"]: item
            for item in intelligence["recent_transactions"]
        }
        self.assertIn("loan_disbursement", recent_by_reference[disbursement.description]["relationship_types"])
        self.assertIn("self_transfer", recent_by_reference[transfer_out.description]["relationship_types"])
        self.assertIn("loan_part_payment", recent_by_reference[part_payment.description]["relationship_types"])
        self.assertIn("loan_closure_payment", recent_by_reference[closure_payment.description]["relationship_types"])

    def test_financial_intelligence_falls_back_to_legacy_payment_components(self):
        account = BankAccount.objects.create(
            user=self.user,
            bank_name="Axis Bank",
            account_number="111122223333",
            account_type="savings",
            current_balance=150000,
        )
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS1234",
            principal=200000,
            interest_rate=12,
            emi=10000,
            tenure_months=36,
            remaining_balance=120000,
            start_date=timezone.localdate() - timedelta(days=20),
            is_active=True,
            status="active",
        )
        repayment = Expense.objects.create(
            user=self.user,
            bank_account=account,
            amount=10000,
            classification="loan",
            category="loan",
            payment_mode="BANK",
            merchant="Axis Bank",
            description="Axis Bank EMI AXIS1234",
            raw_description="AXIS BANK EMI AXIS1234",
            transaction_date=timezone.localdate() - timedelta(days=1),
            direction="debit",
            source="bank_statement",
            external_reference="EMI-LEGACY-001",
        )
        legacy_row = {
            "id": 999,
            "loan_id": loan.id,
            "loan__lender": loan.lender,
            "loan__loan_account_number": loan.loan_account_number,
            "loan__emi": loan.emi,
            "expense_reference_id": repayment.id,
            "payment_date": repayment.transaction_date,
            "amount": repayment.amount,
            "principal_component": 8400,
            "interest_component": 1600,
            "remaining_balance": 111600,
            "match_status": "matched",
            "is_auto_detected": True,
            "detection_confidence": 89,
            "detection_reason": "legacy schema",
            "matched_reference": repayment.external_reference,
        }

        with patch(
            "apps.expenses.services.financial_relationships.fetch_payment_history_rows",
            return_value=[legacy_row],
        ), patch(
            "apps.expenses.services.financial_intelligence.fetch_payment_history_rows",
            return_value=[legacy_row],
        ):
            intelligence = build_financial_intelligence(self.user)

        self.assertEqual(intelligence["loan_portfolio"]["payment_component_totals"]["principal_paid"], 8400.0)
        self.assertEqual(intelligence["loan_portfolio"]["payment_component_totals"]["interest_paid"], 1600.0)
        self.assertEqual(intelligence["loan_portfolio"]["payment_component_totals"]["charges_paid"], 0.0)
        self.assertEqual(intelligence["financial_relationships"]["summary"]["loan_repayments"], 1)
        repayment_entry = intelligence["loan_portfolio"]["detected_repayments"][0]
        self.assertEqual(repayment_entry["principal_paid"], 8400.0)
        self.assertEqual(repayment_entry["interest_paid"], 1600.0)
