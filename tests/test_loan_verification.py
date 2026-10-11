"""Inferred loan terms must not become confirmed financial positions."""
from datetime import timedelta
from importlib import import_module

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.integrations.models import CreditReportUpload
from apps.integrations.services.credit_loan_sync import sync_credit_report_loans
from apps.loans.models import Loan, LoanPaymentHistory
from apps.loans.services.loan_intelligence import loan_intelligence_service
from apps.loans.services.payment_review import review_loan_payment_match


class LoanVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="loan-verification")
        self.other = get_user_model().objects.create_user(username="other-loan-owner")
        self.client.force_login(self.user)

    def loan(self, **changes):
        values = dict(
            user=self.user, lender="Example Housing Finance", loan_type="home",
            loan_account_number="HOME123456", principal=240000, remaining_balance=240000,
            interest_rate=10, emi=10000, tenure_months=24, start_date=timezone.localdate(),
            auto_detected=True, verification_status="estimated", verification_source="emi_pattern",
        )
        values.update(changes)
        return Loan.objects.create(**values)

    def expense(self, **changes):
        values = dict(
            user=self.user, amount=10000, direction="debit", classification="loan",
            category="loan", merchant="Example Housing Finance", company_name="Example Housing Finance",
            description="Example Housing Finance EMI HOME123456", external_reference="HOME123456",
            transaction_date=timezone.localdate(),
        )
        values.update(changes)
        return Expense.objects.create(**values)

    def confirmation(self, **changes):
        values = dict(
            confirm_estimate=True, principal=200000, interest_rate=8, emi=9000,
            tenure_months=24, remaining_balance=150000, start_date=timezone.localdate().isoformat(),
            lender="Example Housing Finance",
        )
        values.update(changes)
        return values

    def report(self, **changes):
        values = dict(
            user=self.user, file_name="bureau.txt", parser_status="parsed", parse_confidence=.95,
            extracted_payload={"loan_accounts": [{
                "lender_name": "Example Housing Finance", "loan_account_number": "HOME123456",
                "account_type": "Home Loan", "status": "Active", "sanctioned_amount": 200000,
                "current_balance": 150000, "emi_amount": 9000,
                "opened_on": timezone.localdate().isoformat(),
            }]},
        )
        values.update(changes)
        return CreditReportUpload.objects.create(**values)

    def test_repeated_detection_retains_estimate_without_debt_or_payment_effects(self):
        first = self.expense(transaction_date=timezone.localdate() - timedelta(days=30))
        second = self.expense()
        result = loan_intelligence_service.detect_loan_payments(self.user)
        self.assertEqual(result["detected_loans"], 1)
        loan = Loan.objects.get(user=self.user)
        self.assertEqual(loan.verification_status, "estimated")
        self.assertEqual(loan.remaining_balance, 240000)
        self.assertEqual(loan.total_paid, 0)
        self.assertEqual(loan.payment_history.count(), 2)
        self.assertFalse(loan.payment_history.exclude(match_status="review", loan_effect_applied=False).exists())
        self.assertFalse(loan.payment_history.exclude(principal_paid=0, interest_paid=0, remaining_balance=None).exists())
        self.assertEqual(loan_intelligence_service.detect_loan_payments(self.user)["new_payments"], 0)
        self.assertEqual(Expense.objects.filter(pk__in=[first.pk, second.pk]).count(), 2)
        intelligence = build_financial_intelligence(self.user)
        self.assertEqual(intelligence["balance_sheet"]["total_liabilities"], 0)
        self.assertEqual(intelligence["balance_sheet"]["total_assets"], 0)
        self.assertEqual(intelligence["loan_portfolio"]["manual_total_emi"], 0)
        self.assertEqual(intelligence["loan_portfolio"]["unconfirmed_loan_count"], 1)
        self.assertEqual(intelligence["loan_portfolio"]["detected_repayment_total"], 20000)

    def test_unconfirmed_states_are_excluded_across_canonical_apis(self):
        for state in ("estimated", "needs_review"):
            self.loan(verification_status=state)
        confirmed = self.loan(auto_detected=False, loan_type="personal", principal=80000,
                              remaining_balance=60000, emi=4000, verification_status="confirmed")
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        self.assertEqual(summary["manual_total_outstanding"], 60000)
        self.assertEqual(summary["manual_total_emi"], 4000)
        self.assertEqual(summary["active_loans"], 1)
        self.assertEqual(summary["unconfirmed_loan_count"], 2)
        rows = {row["id"]: row for row in summary["manual_loans"]}
        self.assertTrue(rows[confirmed.id]["counts_toward_liabilities"])
        networth = self.client.get("/api/loans/networth/").json()
        self.assertEqual(networth["liabilities"]["total"], 60000)
        self.assertEqual(networth["loan_breakdown"], {"Personal Loan": 60000})
        metrics = loan_intelligence_service.calculate_loan_metrics(self.user)
        self.assertEqual(metrics["monthly_emi_burden"], 4000)
        self.assertEqual(metrics["active_loan_count"], 1)

    def test_confirmation_requires_explicit_terms_and_invalidates_cached_totals(self):
        loan = self.loan()
        self.assertEqual(self.client.get("/api/loans/summary/").json()["summary"]["manual_total_outstanding"], 0)
        url = f"/api/loans/{loan.pk}/"
        self.assertEqual(self.client.patch(url, {"confirm_estimate": True}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"notes": "Checking records"}, content_type="application/json").status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.verification_status, "estimated")
        response = self.client.patch(url, self.confirmation(), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        loan.refresh_from_db()
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.verification_source, "user")
        self.assertIsNotNone(loan.verified_at)
        self.assertEqual(self.client.get("/api/loans/summary/").json()["summary"]["manual_total_outstanding"], 150000)
        self.assertEqual(self.client.patch(url, self.confirmation(), content_type="application/json").status_code, 200)
        self.assertEqual(Loan.objects.get(pk=loan.pk).remaining_balance, 150000)

    def test_confirmation_rejects_invalid_terms_and_status_bypass(self):
        loan = self.loan()
        url = f"/api/loans/{loan.pk}/"
        for invalid in ({"remaining_balance": None}, {"remaining_balance": -1},
                        {"interest_rate": -1}, {"tenure_months": 0}, {"lender": ""}):
            with self.subTest(invalid=invalid):
                response = self.client.patch(url, self.confirmation(**invalid), content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
        self.client.patch(url, {"verification_status": "confirmed"}, content_type="application/json")
        loan.refresh_from_db()
        self.assertFalse(loan.is_confirmed)

    def test_confirmation_and_detection_enforce_ownership(self):
        loan = self.loan(user=self.other)
        response = self.client.patch(f"/api/loans/{loan.pk}/", self.confirmation(), content_type="application/json")
        self.assertEqual(response.status_code, 404)
        other_expense = self.expense(user=self.other)
        result = loan_intelligence_service.detect_loan_payments(self.user, [other_expense])
        self.assertEqual(result["new_payments"], 0)
        self.assertEqual(LoanPaymentHistory.objects.count(), 0)
        with self.assertRaises(ValueError):
            sync_credit_report_loans(user=self.user, report_upload=self.report(user=self.other))

    def test_payment_acceptance_does_not_confirm_terms_or_restore_old_guesses(self):
        loan = self.loan()
        payment = LoanPaymentHistory.objects.create(
            loan=loan, payment_date=timezone.localdate(), amount=10000, match_status="review",
            is_auto_detected=True, principal_paid=8000, interest_paid=2000, remaining_balance=232000,
        )
        with self.assertRaisesMessage(ValueError, "Confirm the loan terms"):
            review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="accept")
        response = self.client.patch(f"/api/loans/{loan.pk}/", self.confirmation(), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        reviewed = review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="accept")
        self.assertEqual(reviewed.match_status, "matched")
        self.assertFalse(reviewed.loan_effect_applied)
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, 150000)
        self.assertEqual(loan.total_paid, 0)

    def test_bureau_new_and_matched_loans_remain_confirmed(self):
        report = self.report()
        first = sync_credit_report_loans(user=self.user, report_upload=report)
        self.assertEqual(first["created_loans"], 1)
        loan = Loan.objects.get(user=self.user)
        self.assertTrue(loan.auto_detected)
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.verification_source, "bureau")
        self.assertEqual(build_financial_intelligence(self.user)["balance_sheet"]["total_liabilities"], 150000)
        loan.verification_status = "estimated"
        loan.remaining_balance = 240000
        loan.save()
        second = sync_credit_report_loans(user=self.user, report_upload=report)
        self.assertEqual(second["created_loans"], 0)
        loan.refresh_from_db()
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.remaining_balance, 150000)

    def test_weak_bureau_report_does_not_confirm_inferred_loan(self):
        loan = self.loan()
        sync_credit_report_loans(user=self.user, report_upload=self.report(parse_confidence=.4))
        loan.refresh_from_db()
        self.assertFalse(loan.is_confirmed)

    def test_bureau_missing_balance_requires_review_and_explicit_zero_is_preserved(self):
        loan = self.loan()
        report = self.report()
        del report.extracted_payload["loan_accounts"][0]["current_balance"]
        result = sync_credit_report_loans(user=self.user, report_upload=report)
        self.assertEqual(result["review_items"], 1)
        loan.refresh_from_db()
        self.assertFalse(loan.is_confirmed)
        report.extracted_payload["loan_accounts"][0]["current_balance"] = 0
        report.extracted_payload["loan_accounts"][0]["balance_reported"] = True
        sync_credit_report_loans(user=self.user, report_upload=report)
        loan.refresh_from_db()
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.remaining_balance, 0)
        self.assertEqual(build_financial_intelligence(self.user)["balance_sheet"]["total_liabilities"], 0)

    def test_late_imported_payment_cannot_reduce_a_confirmed_current_balance(self):
        loan = self.loan()
        response = self.client.patch(f"/api/loans/{loan.pk}/", self.confirmation(), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        expense = self.expense(amount=9000, transaction_date=timezone.localdate() - timedelta(days=30))
        loan_intelligence_service.detect_loan_payments(self.user, [expense])
        payment = LoanPaymentHistory.objects.get(loan=loan)
        self.assertEqual(payment.match_status, "review")
        review_loan_payment_match(user=self.user, payment_id=payment.pk, decision="accept")
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, 150000)

    def test_bureau_balance_confirmation_does_not_confirm_a_guessed_emi(self):
        loan = self.loan(status="foreclosure_pending")
        report = self.report()
        del report.extracted_payload["loan_accounts"][0]["emi_amount"]
        sync_credit_report_loans(user=self.user, report_upload=report)
        loan.refresh_from_db()
        self.assertTrue(loan.is_confirmed)
        self.assertEqual(loan.remaining_balance, 150000)
        self.assertEqual(loan.emi, 0)
        self.assertEqual(loan.interest_rate, 0)
        self.assertEqual(loan.status, "foreclosure_pending")

    def test_confirmed_foreclosure_pending_stays_debt_without_recurring_emi(self):
        self.loan(verification_status="confirmed", status="foreclosure_pending", remaining_balance=75000)
        self.loan(status="foreclosure_pending", remaining_balance=240000)
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        self.assertEqual(summary["manual_total_outstanding"], 75000)
        self.assertEqual(summary["pending_foreclosure_balance"], 75000)
        self.assertEqual(summary["manual_total_emi"], 0)
        metrics = loan_intelligence_service.calculate_loan_metrics(self.user)
        self.assertEqual(metrics["pending_foreclosure_balance"], 75000)


class LoanVerificationMigrationTests(TransactionTestCase):
    """Exercise upgrade/backfill/rollback against an isolated database."""
    migrate_from = ("loans", "0012_loanpaymenthistory_review_state")
    migrate_to = ("loans", "0013_loan_verification")

    def test_backfill_preserves_records_and_requires_owned_bureau_evidence(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        executor.migrate([self.migrate_from])
        previous_leaves = [self.migrate_from if node[0] == "loans" else node for node in leaves]
        old_apps = executor.loader.project_state(previous_leaves).apps
        User = old_apps.get_model("users", "User")
        OldLoan = old_apps.get_model("loans", "Loan")
        Report = old_apps.get_model("integrations", "CreditReportUpload")
        Payment = old_apps.get_model("loans", "LoanPaymentHistory")
        user = User.objects.create(username="migration-loans")
        other = User.objects.create(username="migration-other")

        def make_loan(**changes):
            values = dict(user_id=user.pk, principal=240000, remaining_balance=232000,
                          lender="Example Housing Finance", loan_account_number=f"LOAN{OldLoan.objects.count() + 100000}",
                          emi=10000, interest_rate=10, start_date=timezone.localdate(), auto_detected=True)
            values.update(changes)
            return OldLoan.objects.create(**values)

        manual = make_loan(auto_detected=False)
        inferred = make_loan()
        bureau = make_loan(interest_rate=0)
        foreign = make_loan(interest_rate=0)
        weak = make_loan(interest_rate=0)
        missing_balance = make_loan(interest_rate=0)
        old_default_zero = make_loan(interest_rate=0, remaining_balance=0)
        explicit_zero = make_loan(interest_rate=0, remaining_balance=0, status="closed", is_active=False)
        missing_emi = make_loan(interest_rate=0)
        wrong_loan = make_loan(interest_rate=0)
        guessed_rate = make_loan()
        mismatched_balance = make_loan(interest_rate=0)
        mismatched_principal = make_loan(interest_rate=0)
        closed = make_loan(status="foreclosed", is_active=False, remaining_balance=0)
        payment = Payment.objects.create(loan_id=inferred.pk, payment_date=timezone.localdate(),
                                         amount=10000, match_status="matched", loan_effect_applied=True)

        def report(owner, loan, confidence=.95, **raw_changes):
            raw = dict(
                lender_name=loan.lender, loan_account_number=loan.loan_account_number,
                sanctioned_amount=loan.principal, current_balance=loan.remaining_balance, emi_amount=loan.emi,
            )
            raw.update(raw_changes)
            Report.objects.create(user_id=owner.pk, file_name="report.txt", parser_status="parsed",
                                  parse_confidence=confidence, extracted_payload={"loan_accounts": [raw], "loan_sync": {"accounts": [{
                                      **raw,
                                      "matched_loan_id": loan.pk, "verification_status": "verified",
                                      "action": "created", "match_confidence": .88,
                                  }]}})

        report(user, bureau)
        report(other, foreign)
        report(user, weak, .4)
        report(user, missing_balance, current_balance=None)
        report(user, old_default_zero)
        report(user, explicit_zero, balance_reported=True)
        report(user, missing_emi, emi_amount=0)
        report(user, wrong_loan, loan_account_number="UNRELATED999999")
        report(user, guessed_rate)
        report(user, mismatched_balance, current_balance=150000)
        report(user, mismatched_principal, sanctioned_amount=200000)
        retained_fields = ("pk", "principal", "remaining_balance", "emi", "interest_rate", "total_paid", "status")
        before = list(OldLoan.objects.order_by("pk").values_list(*retained_fields))
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_leaves = [self.migrate_to if node[0] == "loans" else node for node in leaves]
        new_apps = executor.loader.project_state(new_leaves).apps
        NewLoan = new_apps.get_model("loans", "Loan")
        self.assertEqual(NewLoan.objects.get(pk=manual.pk).verification_status, "confirmed")
        self.assertEqual(NewLoan.objects.get(pk=bureau.pk).verification_source, "bureau")
        self.assertEqual(NewLoan.objects.get(pk=explicit_zero.pk).verification_source, "bureau")
        for row in (inferred, foreign, weak, closed, missing_balance, old_default_zero,
                    missing_emi, wrong_loan, guessed_rate, mismatched_balance, mismatched_principal):
            self.assertEqual(NewLoan.objects.get(pk=row.pk).verification_status, "needs_review")
        self.assertEqual(before, list(NewLoan.objects.order_by("pk").values_list(*retained_fields)))
        self.assertTrue(new_apps.get_model("loans", "LoanPaymentHistory").objects.get(pk=payment.pk).loan_effect_applied)
        migration = import_module("apps.loans.migrations.0013_loan_verification")
        snapshot = list(NewLoan.objects.order_by("pk").values_list("pk", "verification_status", "verified_at"))
        with connection.schema_editor() as editor:
            migration.backfill_verification(new_apps, editor)
        self.assertEqual(snapshot, list(NewLoan.objects.order_by("pk").values_list("pk", "verification_status", "verified_at")))
        MigrationExecutor(connection).migrate([self.migrate_from])
        self.assertEqual(before, list(OldLoan.objects.order_by("pk").values_list(*retained_fields)))
