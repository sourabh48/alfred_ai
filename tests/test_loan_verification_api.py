"""User-recorded balances and unknown bureau EMIs keep their evidence boundary."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanPaymentHistory


class LoanVerificationApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="loan-verification-api")
        self.client.force_login(self.user)

    def terms(self, **changes):
        terms = dict(
            lender="Example Housing Finance", loan_type="home", loan_account_number="HOME123456",
            principal=200000, remaining_balance=150000, interest_rate=8, emi=9000,
            tenure_months=24, start_date=(timezone.localdate() - timedelta(days=60)).isoformat(),
        )
        terms.update(changes)
        return terms

    def test_new_user_current_balance_cannot_be_reduced_by_a_late_historical_import(self):
        response = self.client.post("/api/loans/", self.terms(), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        loan = Loan.objects.get(pk=response.json()["id"])
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.verification_source, "user")
        self.assertIsNotNone(loan.verified_at)
        expense = Expense.objects.create(
            user=self.user, amount=9000, direction="debit", category="loan", classification="loan",
            merchant=loan.lender, company_name=loan.lender,
            description="Example Housing Finance EMI HOME123456", external_reference="HOME123456",
            transaction_date=timezone.localdate() - timedelta(days=30),
        )
        detected = self.client.post("/api/loans/detect-from-expenses/")
        self.assertEqual(detected.status_code, 200, detected.content)
        payment = LoanPaymentHistory.objects.get(expense_reference=expense)
        self.assertEqual(payment.match_status, "review")
        self.assertFalse(payment.loan_effect_applied)
        self.assertEqual(payment.principal_paid, 0)
        self.assertEqual(payment.interest_paid, 0)
        reviewed = self.client.post(
            f"/api/loans/payment-history/{payment.pk}/review/",
            {"decision": "accept"}, content_type="application/json",
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.content)
        loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(payment.match_status, "matched")
        self.assertFalse(payment.loan_effect_applied)
        self.assertEqual(loan.remaining_balance, 150000)
        self.assertEqual(loan.total_paid, 0)

    def test_create_without_current_balance_keeps_prior_unstamped_terms(self):
        for explicit_null in (False, True):
            with self.subTest(explicit_null=explicit_null):
                terms = self.terms()
                if explicit_null:
                    terms["remaining_balance"] = None
                else:
                    del terms["remaining_balance"]
                response = self.client.post("/api/loans/", terms, content_type="application/json")
                self.assertEqual(response.status_code, 201, response.content)
                loan = Loan.objects.get(pk=response.json()["id"])
                self.assertTrue(loan.is_confirmed)
                self.assertIsNone(loan.remaining_balance)
                self.assertIsNone(loan.verified_at)

    def test_bureau_unknown_emi_allows_notes_edit_without_fabricating_terms(self):
        verified_at = timezone.now() - timedelta(days=1)
        loan = Loan.objects.create(
            user=self.user, lender="Example Housing Finance", loan_type="home",
            principal=200000, remaining_balance=150000, interest_rate=0, emi=0,
            tenure_months=24, start_date=timezone.localdate(), auto_detected=True,
            verification_status="confirmed", verification_source="bureau", verified_at=verified_at,
        )
        response = self.client.patch(
            f"/api/loans/{loan.pk}/", {"notes": "Checking the next lender statement"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        loan.refresh_from_db()
        self.assertEqual(loan.notes, "Checking the next lender statement")
        self.assertEqual(loan.emi, 0)
        self.assertEqual(loan.remaining_balance, 150000)
        self.assertEqual(loan.verification_status, "confirmed")
        self.assertEqual(loan.verification_source, "bureau")
        self.assertEqual(loan.verified_at, verified_at)

    def test_submitted_zero_emi_is_invalid_for_create_update_and_confirmation(self):
        response = self.client.post("/api/loans/", self.terms(emi=0), content_type="application/json")
        self.assertEqual(response.status_code, 400, response.content)
        loan = Loan.objects.create(
            user=self.user, lender="Example Housing Finance", principal=200000,
            remaining_balance=150000, interest_rate=0, emi=0, start_date=timezone.localdate(),
            auto_detected=True, verification_status="confirmed", verification_source="bureau",
        )
        response = self.client.patch(f"/api/loans/{loan.pk}/", {"emi": 0}, content_type="application/json")
        self.assertEqual(response.status_code, 400, response.content)
        loan.verification_status = "estimated"
        loan.verification_source = "emi_pattern"
        loan.save()
        response = self.client.patch(
            f"/api/loans/{loan.pk}/", self.terms(emi=0, confirm_estimate=True),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        loan.refresh_from_db()
        self.assertEqual(loan.verification_status, "estimated")
        self.assertEqual(loan.emi, 0)
