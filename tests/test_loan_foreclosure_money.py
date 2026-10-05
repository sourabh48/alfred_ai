"""Cent conservation and evidence retention at foreclosure posting boundaries."""
import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory
from apps.loans.services.loan_closure_parser import loan_closure_parser
from apps.loans.services.loan_foreclosure_service import (
    SETTLEMENT_COMPONENT_FIELDS,
    _proportional_money_split,
    loan_foreclosure_service,
)


def cents(value):
    return Decimal(str(value))


class ForeclosureAllocationTests(SimpleTestCase):
    def test_largest_remainders_have_stable_ties_and_half_up_total(self):
        self.assertEqual(
            _proportional_money_split("0.005", {"first": 1, "second": 1, "third": 1}, fallback_key="first"),
            {"first": Decimal("0.01"), "second": Decimal("0.00"), "third": Decimal("0.00")},
        )
        self.assertEqual(
            _proportional_money_split("1.01", {"first": 0, "second": None}, fallback_key="second"),
            {"first": Decimal("0.00"), "second": Decimal("1.01")},
        )
        maximum = Decimal("999999999999.99")
        split = _proportional_money_split(maximum * 2, {1: maximum, 2: maximum}, fallback_key=1)
        self.assertEqual(split, {1: maximum, 2: maximum})

    def assert_conserved(self, allocation):
        rows = allocation["expense_allocations"]
        for row in rows:
            self.assertEqual(sum((cents(row[field]) for field in SETTLEMENT_COMPONENT_FIELDS)), cents(row["amount"]))
        for field in SETTLEMENT_COMPONENT_FIELDS:
            self.assertEqual(
                sum((cents(row[field]) for row in rows)), cents(allocation["allocated_components"][field]),
            )
        self.assertEqual(sum((cents(row["amount"]) for row in rows)), cents(allocation["payment_total"]))
        json.dumps(allocation)  # The persistence contract is numeric JSON.

    def test_three_component_cents_and_three_payments_conserve_both_axes(self):
        snapshot = SimpleNamespace(outstanding_principal="0.01", accrued_interest="0.01",
                                   foreclosure_charges="0.01", overdue_charges=0, taxes_gst=0,
                                   total_amount_payable="0.03")
        expenses = [SimpleNamespace(id=index, amount=0.01, transaction_date=timezone.localdate(),
                                    external_reference="") for index in (3, 1, 2)]
        allocation = loan_foreclosure_service._build_settlement_allocation(
            snapshot, matched_expenses=expenses, matched_total=Decimal("0.03"), status="full_match", confidence=0.9,
        )
        self.assert_conserved(allocation)
        self.assertEqual([row["expense_id"] for row in allocation["expense_allocations"]], [1, 2, 3])
        self.assertEqual([row["principal_paid"] for row in allocation["expense_allocations"]], [0.01, 0.0, 0.0])
        self.assertEqual([row["interest_paid"] for row in allocation["expense_allocations"]], [0.0, 0.01, 0.0])
        self.assertEqual([row["charges_paid"] for row in allocation["expense_allocations"]], [0.0, 0.0, 0.01])

    def test_scaled_five_components_and_partial_payments_conserve_residual_cents(self):
        snapshot = SimpleNamespace(outstanding_principal="10.01", accrued_interest="1.01",
                                   foreclosure_charges="0.51", overdue_charges="0.31", taxes_gst="0.21",
                                   total_amount_payable="11.99")
        expenses = [SimpleNamespace(id=index, amount=amount, transaction_date=timezone.localdate(),
                                    external_reference="") for index, amount in enumerate((2.01, 3.02, 2.04), start=1)]
        allocation = loan_foreclosure_service._build_settlement_allocation(
            snapshot, matched_expenses=expenses, matched_total=Decimal("7.07"), status="partial_match", confidence=0.7,
        )
        self.assert_conserved(allocation)
        self.assertEqual(allocation["document_normalization"], "scaled_to_payable_total")
        self.assertEqual(allocation["allocation_status"], "provisional_partial")
        self.assertEqual(sum((cents(value) for value in allocation["document_components"].values())), Decimal("11.99"))
        self.assertEqual(cents(allocation["payment_gap"]), Decimal("4.92"))
        mismatch = loan_foreclosure_service._build_settlement_allocation(
            snapshot, matched_expenses=expenses, matched_total=Decimal("7.07"), status="mismatch", confidence=0.6,
        )
        self.assertEqual(mismatch["allocation_status"], "mismatch_unallocated")
        self.assertEqual(mismatch["expense_allocations"], [])
        self.assertEqual(sum(mismatch["allocated_components"].values()), 0)

    def test_missing_document_components_use_exact_principal_fallback(self):
        snapshot = SimpleNamespace(outstanding_principal=0, accrued_interest=0, foreclosure_charges=0,
                                   overdue_charges=0, taxes_gst=0, total_amount_payable="1.01")
        expenses = [SimpleNamespace(id=1, amount=1.01, transaction_date=timezone.localdate(), external_reference="")]
        allocation = loan_foreclosure_service._build_settlement_allocation(
            snapshot, matched_expenses=expenses, matched_total=Decimal("1.01"), status="full_match", confidence=0.9,
        )
        self.assert_conserved(allocation)
        self.assertEqual(allocation["document_normalization"], "principal_only_fallback")
        self.assertEqual(allocation["allocated_components"]["principal_paid"], 1.01)

    def test_virtual_document_and_payment_totals_can_exceed_a_stored_field_limit(self):
        maximum = Decimal("999999999999.99")
        snapshot = SimpleNamespace(outstanding_principal=maximum, accrued_interest=maximum,
                                   foreclosure_charges=0, overdue_charges=0, taxes_gst=0, total_amount_payable=0)
        expenses = [SimpleNamespace(id=index, amount=maximum, transaction_date=timezone.localdate(),
                                    external_reference="") for index in (1, 2)]
        allocation = loan_foreclosure_service._build_settlement_allocation(
            snapshot, matched_expenses=expenses, matched_total=maximum * 2, status="full_match", confidence=0.9,
        )
        self.assert_conserved(allocation)
        self.assertEqual(cents(allocation["raw_document_total"]), maximum * 2)
        self.assertEqual(cents(allocation["allocated_components"]["principal_paid"]), maximum)
        self.assertEqual(cents(allocation["allocated_components"]["interest_paid"]), maximum)


class ForeclosureMoneyPostingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="foreclosure-cents")
        self.loan = Loan.objects.create(
            user=self.user, loan_type="personal", lender="Axis Bank", loan_account_number="CENT001",
            principal="5000.00", emi="100.00", interest_rate=0, start_date=timezone.localdate(),
            remaining_balance="3000.03", total_paid="0.10", status="foreclosure_pending", is_active=False,
        )

    def make_snapshot(self, total="2000.02", principal="1900.01", interest="100.01"):
        document = LoanClosureDocument.objects.create(
            loan=self.loan, file_name="closure.txt", uploaded_file="closure.txt", closure_amount=total,
            parser_status="parsed", verification_status="verified", extracted_payload={"total_amount_payable": float(total)},
        )
        return LoanForeclosureSnapshot.objects.create(
            loan=self.loan, closure_document=document, total_amount_payable=total,
            outstanding_principal=principal, accrued_interest=interest, lender_name="Axis Bank",
            effective_closure_date=timezone.localdate(),
        )

    def make_expense(self, amount, days=0):
        return Expense.objects.create(
            user=self.user, amount=amount, direction="debit", classification="loan", category="loan",
            merchant="Axis Bank", description="Axis Bank FORECLOSURE CENT001", source="bank_statement",
            transaction_date=timezone.localdate() + timedelta(days=days),
        )

    def test_split_half_cent_source_evidence_posts_once_and_audit_is_numeric(self):
        snapshot = self.make_snapshot()
        expenses = [self.make_expense(1000.005), self.make_expense(1000.005, days=2)]
        self.assertTrue(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=expenses))
        snapshot.refresh_from_db()
        self.loan.refresh_from_db()
        payments = list(LoanPaymentHistory.objects.filter(loan=self.loan).order_by("payment_date", "id"))
        self.assertEqual([payment.amount for payment in payments], [Decimal("1000.01"), Decimal("1000.01")])
        self.assertEqual(self.loan.total_paid, Decimal("2000.12"))
        self.assertEqual(snapshot.matched_payment_total, Decimal("2000.02"))
        for field, expected in (("principal_paid", "1900.01"), ("interest_paid", "100.01")):
            self.assertEqual(sum((getattr(payment, field) for payment in payments)), Decimal(expected))
        for payment in payments:
            self.assertEqual(sum((getattr(payment, field) for field in SETTLEMENT_COMPONENT_FIELDS)), payment.amount)
        before = snapshot.audit_payload.copy()
        json.dumps(before)
        for expense in expenses:
            expense.refresh_from_db()
            self.assertEqual(expense.amount, 1000.005)
        self.assertTrue(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=expenses))
        snapshot.refresh_from_db()
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.total_paid, Decimal("2000.12"))
        self.assertEqual(snapshot.audit_payload, before)
        self.assertEqual(LoanPaymentHistory.objects.filter(loan=self.loan).count(), 2)

    def test_existing_applied_history_is_preserved_without_counting_cash_twice(self):
        snapshot = self.make_snapshot(total="3000.03", principal="2900.02", interest="100.01")
        first, second = self.make_expense(2000.015), self.make_expense(1000.005, days=1)
        self.loan.total_paid = Decimal("2000.02")
        self.loan.save(update_fields=["total_paid"])
        prior = LoanPaymentHistory.objects.create(
            loan=self.loan, expense_reference=first, payment_date=first.transaction_date, amount="2000.02",
            principal_paid="1990.02", interest_paid="10.00", principal_component="1990.02",
            interest_component="10.00", remaining_balance="1000.01", loan_effect_applied=True,
            match_status="matched", detection_reason="Prior allocation remains evidence.",
        )
        before = LoanPaymentHistory.objects.filter(pk=prior.pk).values().get()
        self.assertTrue(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[first, second]))
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.total_paid, Decimal("3000.03"))
        self.assertEqual(before, LoanPaymentHistory.objects.filter(pk=prior.pk).values().get())
        self.assertEqual(LoanPaymentHistory.objects.filter(loan=self.loan).count(), 2)

    def test_register_overflow_rolls_back_the_whole_reconciliation(self):
        snapshot = self.make_snapshot(total="1000.01", principal="1000.01", interest="0.00")
        self.loan.total_paid = Decimal("999999999999.99")
        self.loan.save(update_fields=["total_paid"])
        expense = self.make_expense(1000.01)
        before = LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get()
        with self.assertRaises(ValueError):
            loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[expense])
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.total_paid, Decimal("999999999999.99"))
        self.assertEqual(self.loan.status, "foreclosure_pending")
        self.assertEqual(before, LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get())
        self.assertFalse(LoanPaymentHistory.objects.filter(loan=self.loan).exists())

    def test_parser_preserves_fractional_evidence_and_persistence_normalizes_currency(self):
        text = "Axis Bank FORECLOSURE STATEMENT Loan Account Number: CENT001 Outstanding Principal: 1000.005 Amount Payable: 1000.005"
        extracted = SimpleNamespace(text=text, method="text", notes=[], review_payload={}, confidence=0.9)
        file = SimpleUploadedFile("closure.txt", text.encode(), content_type="text/plain")
        with patch("apps.loans.services.loan_closure_parser.extract_document_text", return_value=extracted), \
                patch("apps.loans.services.loan_closure_parser.apply_parser_learning", return_value=(0.9, [])):
            parsed = loan_closure_parser.parse_document(file, file.name, user=self.user)
        self.assertEqual(parsed["payload"]["outstanding_principal"], 1000.005)
        self.assertEqual(parsed["payload"]["total_amount_payable"], 1000.005)
        result = loan_foreclosure_service.process_document(user=self.user, selected_loan=self.loan, closure_file=file, parsed=parsed)
        self.assertEqual(result.closure_document.closure_amount, Decimal("1000.01"))
        self.assertEqual(result.snapshot.outstanding_principal, Decimal("1000.01"))
        self.assertEqual(result.closure_document.extracted_payload["outstanding_principal"], 1000.005)
        self.assertEqual(result.snapshot.audit_payload["document_payload"]["total_amount_payable"], 1000.005)

    def test_saved_correction_overrides_raw_payable_and_preserves_explicit_zero(self):
        snapshot = self.make_snapshot()
        document = snapshot.closure_document
        for source, expected in (("1234.565", "1234.57"), ("0", "0.00")):
            with self.subTest(source=source):
                document.extracted_payload = {"total_amount_payable": 2000.02, "accepted_corrections": {"closure_amount": source}}
                document.save(update_fields=["extracted_payload"])
                refreshed = loan_foreclosure_service.sync_snapshot_from_document(document)
                refreshed.refresh_from_db()
                self.assertEqual(refreshed.total_amount_payable, Decimal(expected))
                self.assertEqual(refreshed.audit_payload["document_payload"]["total_amount_payable"], 2000.02)
                self.assertEqual(refreshed.audit_payload["document_payload"]["accepted_corrections"]["closure_amount"], source)

    def test_parser_default_zero_falls_back_but_accepted_or_requested_zero_cannot_clear_debt(self):
        snapshot = self.make_snapshot(total="1000.01", principal="1000.01", interest="0.00")
        document = snapshot.closure_document
        document.extracted_payload = {"total_amount_payable": 0, "closure_amount": 0, "outstanding_principal": 1000.01}
        document.save(update_fields=["extracted_payload"])
        snapshot = loan_foreclosure_service.sync_snapshot_from_document(document)
        self.assertEqual(snapshot.total_amount_payable, Decimal("1000.01"))

        document.extracted_payload["accepted_corrections"] = {"closure_amount": "0"}
        document.save(update_fields=["extracted_payload"])
        snapshot = loan_foreclosure_service.sync_snapshot_from_document(document)
        expense = self.make_expense(3000.03)
        self.assertFalse(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[expense]))
        snapshot.refresh_from_db()
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.remaining_balance, Decimal("3000.03"))
        self.assertEqual(self.loan.total_paid, Decimal("0.10"))
        self.assertEqual(snapshot.total_amount_payable, Decimal("0.00"))
        self.assertEqual(snapshot.matched_payment_total, Decimal("0.00"))
        self.assertEqual(snapshot.reconciliation_status, "unmatched")
        self.assertEqual(snapshot.audit_payload["expected_total_amount"], 0.0)
        self.assertEqual(snapshot.audit_payload["settlement_allocation"]["expected_total"], 0.0)
        self.assertFalse(LoanPaymentHistory.objects.filter(loan=self.loan).exists())

        parsed = {"payload": {"total_amount_payable": 3000.03, "outstanding_principal": 3000.03,
                              "loan_account_number": "CENT001", "lender_name": "Axis Bank"},
                  "extracted_text": "Axis Bank FORECLOSURE CENT001", "parser_status": "parsed", "confidence": 0.9}
        file = SimpleUploadedFile("requested-zero.txt", b"foreclosure", content_type="text/plain")
        result = loan_foreclosure_service.process_document(
            user=self.user, selected_loan=self.loan, closure_file=file, parsed=parsed, requested_closure_amount=Decimal("0"),
        )
        self.assertFalse(result.confirmed)
        self.assertEqual(result.closure_document.closure_amount, Decimal("0.00"))
        self.assertEqual(result.snapshot.audit_payload["settlement_allocation"]["expected_total"], 0.0)
        self.assertEqual(result.closure_document.extracted_payload["total_amount_payable"], 3000.03)
        self.assertEqual(result.closure_document.extracted_payload["accepted_corrections"]["closure_amount"], "0")
        self.assertEqual(result.loan.remaining_balance, Decimal("3000.03"))
