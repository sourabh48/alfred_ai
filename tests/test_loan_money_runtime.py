"""Loan register and payment history keep exact cents and numeric APIs."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanPaymentHistory
from apps.loans.services.loan_intelligence import loan_intelligence_service
from apps.loans.services.payment_review import review_loan_payment_match


class LoanMoneyRuntimeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user(username="loan-money-runtime")
        self.other = get_user_model().objects.create_user(username="loan-money-other")
        self.client.force_login(self.user)

    def loan(self, **changes):
        values = dict(
            user=self.user, lender="Example Housing Finance", loan_account_number="HOME123456",
            loan_type="home", principal="1000.10", remaining_balance="999.99", emi="100.20",
            interest_rate=12.0, tenure_months=24, start_date=timezone.localdate() - timedelta(days=60),
            verification_status="confirmed", total_paid="0.10",
        )
        values.update(changes)
        loan = Loan.objects.create(**values)
        loan.refresh_from_db()
        return loan

    def test_detected_float_payment_updates_decimal_register_in_exact_cents(self):
        loan = self.loan()
        expense = Expense.objects.create(
            user=self.user, amount=100.20, direction="debit", classification="loan", category="loan",
            merchant=loan.lender, company_name=loan.lender,
            description="Example Housing Finance EMI HOME123456", external_reference="HOME123456",
            transaction_date=timezone.localdate(),
        )
        result = loan_intelligence_service.detect_loan_payments(self.user, [expense])
        self.assertEqual(result["new_payments"], 1)
        loan.refresh_from_db()
        payment = LoanPaymentHistory.objects.get(expense_reference=expense)
        self.assertTrue(payment.loan_effect_applied)
        self.assertEqual(payment.interest_paid, Decimal("10.00"))
        self.assertEqual(payment.principal_paid, Decimal("90.20"))
        self.assertIsInstance(payment.remaining_balance, Decimal)
        self.assertEqual(loan.remaining_balance, Decimal("909.79"))
        self.assertEqual(loan.total_paid, Decimal("100.30"))

    def reviewed_loan(self, *, applied=False):
        loan = self.loan(remaining_balance="499.90" if applied else "500.10",
                         total_paid="0.30" if applied else "0.10", interest_rate=0)
        LoanPaymentHistory.objects.create(
            loan=loan, payment_date=timezone.localdate() - timedelta(days=1), amount=.1,
            principal_paid=.1, remaining_balance=500.10, match_status="matched", loan_effect_applied=True,
        )
        payment = LoanPaymentHistory.objects.create(
            loan=loan, payment_date=timezone.localdate(), amount=.2, principal_paid=.2,
            remaining_balance=None, match_status="review", loan_effect_applied=applied,
        )
        return loan, payment

    def test_accepting_float_review_payment_keeps_decimal_balance_and_total_exact(self):
        loan, payment = self.reviewed_loan()
        review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="accept")
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("499.90"))
        self.assertEqual(loan.total_paid, Decimal("0.30"))

    def test_rejecting_legacy_applied_review_restores_decimal_cents(self):
        loan, payment = self.reviewed_loan(applied=True)
        review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="reject")
        loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("500.10"))
        self.assertEqual(loan.total_paid, Decimal("0.10"))
        self.assertEqual(payment.match_status, "rejected")
        self.assertFalse(payment.loan_effect_applied)

    def test_legacy_half_cent_review_rounds_each_payment_before_adding_register_total(self):
        loan = self.loan(remaining_balance="500.10", total_paid="0.01", interest_rate=0)
        expense = Expense.objects.create(
            user=self.user, amount=.005, direction="debit",
            transaction_date=timezone.localdate(), description="Legacy half-cent evidence",
        )
        LoanPaymentHistory.objects.create(
            loan=loan, payment_date=timezone.localdate() - timedelta(days=1), amount=.005,
            principal_paid=.005, remaining_balance=500.10, match_status="matched", loan_effect_applied=True,
        )
        payment = LoanPaymentHistory.objects.create(
            loan=loan, payment_date=timezone.localdate(), amount=.005, principal_paid=.005,
            remaining_balance=None, match_status="review", expense_reference=expense,
        )
        review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="accept")
        loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("500.09"))
        self.assertEqual(loan.total_paid, Decimal("0.02"))
        self.assertEqual(payment.amount, Decimal("0.01"))
        self.assertEqual(payment.principal_paid, Decimal("0.01"))
        expense.refresh_from_db()
        self.assertEqual(expense.amount, .005)

    def test_detected_half_cent_amount_keeps_cash_evidence_and_half_up_register_cents(self):
        loan = self.loan(remaining_balance="500.10", total_paid="0.01", emi="0.01", interest_rate=0)
        expense = Expense.objects.create(
            user=self.user, amount=.005, direction="debit", classification="loan", category="loan",
            merchant=loan.lender, company_name=loan.lender,
            description="Example Housing Finance EMI HOME123456", external_reference="HOME123456",
            transaction_date=timezone.localdate(),
        )
        loan_intelligence_service.detect_loan_payments(self.user, [expense])
        loan.refresh_from_db()
        payment = LoanPaymentHistory.objects.get(expense_reference=expense)
        self.assertEqual(loan.remaining_balance, Decimal("500.09"))
        self.assertEqual(loan.total_paid, Decimal("0.02"))
        self.assertEqual(payment.amount, Decimal("0.01"))
        self.assertEqual(payment.principal_paid, Decimal("0.01"))
        expense.refresh_from_db()
        self.assertEqual(expense.amount, .005)

    def terms(self, **changes):
        values = dict(
            lender="Example Housing Finance", loan_type="home", loan_account_number="HOME123456",
            principal="1000.10", remaining_balance="999.99", emi="100.20", interest_rate=12,
            tenure_months=24, start_date=timezone.localdate().isoformat(),
            home_purchase_price="1200.20", home_other_upfront_payments="10.20",
        )
        values.update(changes)
        return values

    def test_api_preserves_numeric_money_and_owned_register_with_exact_home_difference(self):
        response = self.client.post("/api/loans/", self.terms(user=self.other.pk), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        for name in ("principal", "emi", "remaining_balance", "home_purchase_price",
                     "home_down_payment", "home_other_upfront_payments", "home_upfront_cash_invested"):
            self.assertIsInstance(payload[name], (int, float), name)
        loan = Loan.objects.get(pk=payload["id"])
        self.assertEqual(loan.user_id, self.user.pk)
        self.assertEqual(loan.home_down_payment, Decimal("200.10"))
        self.assertEqual(loan.home_other_upfront_payments, Decimal("10.20"))
        summary = self.client.get("/api/loans/summary/")
        self.assertEqual(summary.status_code, 200, summary.content)
        self.assertIsInstance(summary.json()["summary"]["manual_total_emi"], (int, float))
        networth = self.client.get("/api/loans/networth/")
        self.assertEqual(networth.status_code, 200, networth.content)
        self.assertIsInstance(networth.json()["loan_breakdown"]["Home Loan"], (int, float))
        foreign = self.loan(user=self.other)
        denied = self.client.patch(f"/api/loans/{foreign.pk}/", {"remaining_balance": "0.10"},
                                   content_type="application/json")
        self.assertEqual(denied.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.remaining_balance, Decimal("999.99"))

    def test_nullable_balance_stays_null_and_canonical_forecast_accepts_decimal_terms(self):
        loan = self.loan(remaining_balance=None)
        detail = self.client.get(f"/api/loans/{loan.pk}/")
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertIsNone(detail.json()["remaining_balance"])
        summary = self.client.get("/api/loans/summary/")
        self.assertEqual(summary.status_code, 200, summary.content)
        row = summary.json()["summary"]["manual_loans"][0]
        self.assertIsInstance(row["estimated_balance"], (int, float))
        self.assertIsInstance(row["recommended_prepayment"], (int, float))

    def test_consolidation_adds_cents_and_rejects_foreign_source(self):
        first = self.loan(remaining_balance="1000.10")
        second = self.loan(remaining_balance="2000.20", loan_account_number="HOME999999")
        foreign = self.loan(user=self.other)
        options = dict(loan_ids=[first.pk, foreign.pk], lender="Consolidation Bank",
                       emi="100.20", interest_rate=12, tenure_months=36)
        denied = self.client.post("/api/loans/consolidate/", options, content_type="application/json")
        self.assertEqual(denied.status_code, 400, denied.content)
        options["loan_ids"] = [first.pk, second.pk]
        response = self.client.post("/api/loans/consolidate/", options, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()["loan"]
        self.assertEqual(payload["principal"], 3000.30)
        self.assertIsInstance(payload["principal"], (int, float))
        self.assertEqual(Loan.objects.get(pk=payload["id"]).remaining_balance, Decimal("3000.30"))

    def test_api_rejects_currency_outside_precision_without_writing_a_record(self):
        for value in ("1000.001", "1000000000000.00", "NaN", "Infinity"):
            with self.subTest(value=value):
                response = self.client.post("/api/loans/", self.terms(principal=value), content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Loan.objects.filter(user=self.user).exists())
