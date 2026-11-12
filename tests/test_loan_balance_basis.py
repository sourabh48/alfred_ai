"""A loan balance projected from the EMI schedule is labelled as an estimate; synthetic data only."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.expenses.services.financial_intelligence import (
    SCHEDULE_ESTIMATE_LABEL, _build_balance_sheet, _serialize_loans,
)
from apps.loans.models import Loan


class LoanBalanceBasisTests(TestCase):
    def test_schedule_estimate_is_labelled_and_kept_apart_from_recorded_balances(self):
        user = get_user_model().objects.create_user(username="synthetic-loan-basis-owner")
        terms = dict(user=user, principal="100000.00", emi="5000.00", interest_rate=10, tenure_months=24,
                     start_date=date(2026, 1, 1), verification_status="confirmed")
        recorded = Loan.objects.create(lender="Synthetic Recorded", remaining_balance="40000.00", **terms)
        estimated = Loan.objects.create(lender="Synthetic Estimated", **terms)
        recorded, estimated = Loan.objects.get(pk=recorded.pk), Loan.objects.get(pk=estimated.pk)
        rows = {row["id"]: row for row in _serialize_loans([recorded, estimated], date(2026, 11, 12))}
        self.assertEqual((rows[recorded.id]["balance_basis"], rows[recorded.id]["balance_label"]), ("recorded", None))
        self.assertEqual(rows[estimated.id]["balance_basis"], "estimated_from_schedule")
        self.assertEqual(rows[estimated.id]["balance_label"], SCHEDULE_ESTIMATE_LABEL)
        self.assertIsNone(rows[estimated.id]["remaining_balance"])

        sheet = _build_balance_sheet(user=user, loans=[recorded, estimated])
        self.assertEqual(sheet["loan_liability_recorded"], 40000.0)
        self.assertGreater(sheet["loan_liability_estimated"], 0)
        loan_row = next(row for row in sheet["liabilities"] if row["label"] == "Open loan liabilities")
        self.assertEqual(loan_row["amount"], round(sheet["loan_liability_recorded"] + sheet["loan_liability_estimated"], 2))
        self.assertIn("assumes on-time EMIs", loan_row["note"])
