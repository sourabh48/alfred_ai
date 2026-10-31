"""FIN-02: bank credits count as salary only on real evidence, and unknown income is never read as zero."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.career.models import CareerProfile
from apps.career.services.income_intelligence import build_employment_income_signals
from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.integrations.services.credit_score_tracker import CreditScoreTrackerService
from apps.loans.models import Loan
from apps.ml_engine.services.recommendation_engine import FinancialRecommendationEngine
from apps.ml_engine.training.orchestrator import TRAINING_SPECS


class SalaryEvidenceBase(TestCase):
    def user(self, name, amount=0, basis="monthly"):
        return get_user_model().objects.create_user(name, password="Synthetic-Pass-1", monthly_income=amount, monthly_income_basis=basis)

    def credit(self, user, amount, *, months_ago=0, employer="Example Analytics", text="SALARY CREDIT", category="income"):
        # Whole 30-day steps keep each credit in its own calendar month closely enough for these fixtures.
        Expense.objects.create(
            user=user, amount=amount, classification="other", category=category, payment_mode="BANK",
            merchant=employer, company_name=employer, counterparty=employer, description=text, raw_description=text,
            transaction_date=timezone.localdate() - timedelta(days=31 * months_ago + 1),
            direction="credit", source="bank_statement",
        )

    def signals(self, user):
        return build_employment_income_signals(user=get_user_model().objects.get(pk=user.pk))

    def baseline(self, user):
        return resolve_canonical_financial_baseline(get_user_model().objects.get(pk=user.pk))


class WhatCountsAsSalaryTests(SalaryEvidenceBase):
    def test_transfer_credits_are_never_salary_even_when_they_recur_or_say_salary(self):
        user = self.user("transfers")
        for month in range(3):
            self.credit(user, 50000, months_ago=month, employer="A Friend", text="SALARY SHARE", category="transfer")
        self.assertIsNone(self.signals(user)["salary_credit_signal"])
        self.assertEqual(self.signals(user)["monthly_cash_income"], 0.0)

    def test_one_credit_needs_its_text_to_say_salary(self):
        unnamed = self.user("one_unnamed")
        self.credit(unnamed, 30000, employer="Acme Traders", text="NEFT ACME TRADERS")
        self.assertIsNone(self.signals(unnamed)["salary_credit_signal"])

        named = self.user("one_named")
        self.credit(named, 30000, employer="Acme Traders", text="SALARY ACME TRADERS")
        self.assertEqual(self.signals(named)["monthly_cash_income"], 30000.0)

    def test_recurring_credits_count_without_the_word_salary(self):
        user = self.user("recurring")
        for month in range(2):
            self.credit(user, 40000, months_ago=month, employer="Acme Traders", text="NEFT ACME TRADERS")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 40000.0)

    def test_old_salary_credits_no_longer_set_income(self):
        user = self.user("ended_job", 60000)
        for month in range(4, 8):
            self.credit(user, 150000, months_ago=month)
        signals = self.signals(user)
        self.assertIsNone(signals["salary_credit_signal"])
        self.assertIsNone(signals["income_conflict"])
        self.assertEqual(signals["monthly_cash_income"], 60000.0)
        self.assertIn("too old", signals["source_summary"])
        self.assertEqual(self.baseline(user)["income_source"], "reported_monthly_income")

    def test_recency_is_judged_at_the_reference_date(self):
        user = self.user("dated")
        self.credit(user, 50000, months_ago=6)
        past = timezone.localdate() - timedelta(days=31 * 6)
        self.assertEqual(build_employment_income_signals(user=user, today=past)["monthly_cash_income"], 50000.0)
        self.assertEqual(build_employment_income_signals(user=user)["monthly_cash_income"], 0.0)

    def test_a_job_change_uses_the_new_employer_even_with_a_shorter_history(self):
        user = self.user("job_change")
        for month in range(1, 3):
            self.credit(user, 90000, months_ago=month, employer="Oldco Systems")
        self.credit(user, 120000, months_ago=0, employer="Newco Systems")
        signals = self.signals(user)
        self.assertEqual(signals["monthly_cash_income"], 120000.0)
        self.assertEqual(signals["current_employer"], "Newco Systems")

    def test_two_employers_paying_together_are_added(self):
        user = self.user("two_jobs")
        for month in range(3):
            self.credit(user, 80000, months_ago=month, employer="First Employer")
            self.credit(user, 30000, months_ago=month, employer="Second Employer")
        signals = self.signals(user)
        self.assertEqual(signals["monthly_cash_income"], 110000.0)
        self.assertEqual(signals["annualized_compensation"], 1320000.0)
        self.assertEqual(signals["salary_signal_count"], 2)

    def test_recurring_credits_not_described_as_salary_are_not_added_to_salary(self):
        user = self.user("tenant")
        for month in range(3):
            self.credit(user, 80000, months_ago=month, employer="First Employer")
            self.credit(user, 20000, months_ago=month, employer="A Tenant", text="NEFT A TENANT")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 80000.0)


class ConfirmedIncomeTests(SalaryEvidenceBase):
    def paid(self, user, amount):
        for month in range(3):
            self.credit(user, amount, months_ago=month)

    def test_salary_that_disagrees_never_replaces_a_confirmed_income(self):
        for name, amount, basis, salary, expected_source in (
            ("much_lower", 300000, "monthly", 50000, "reported_monthly_income"),
            ("much_higher", 50000, "monthly", 300000, "reported_monthly_income"),
            ("annual_low", 600000, "annual", 300000, "reported_annual_ctc"),
        ):
            with self.subTest(name=name):
                user = self.user(name, amount, basis)
                self.paid(user, salary)
                baseline = self.baseline(user)
                expected = float(amount if basis == "monthly" else amount / 12)
                self.assertEqual(baseline["monthly_income"], expected)
                self.assertEqual(baseline["income_source"], expected_source)
                self.assertEqual(baseline["income_conflict"]["salary_monthly"], float(salary))
                self.assertIn("confirmed income", baseline["metric_states"]["monthly_income"]["note"])

    def test_salary_that_agrees_is_used_without_a_conflict(self):
        user = self.user("agrees", 100000, "monthly")
        self.paid(user, 80000)
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 80000.0)
        self.assertEqual(baseline["income_source"], "salary_credits")
        self.assertIsNone(baseline["income_conflict"])

    def test_an_unconfirmed_income_cannot_conflict(self):
        user = self.user("unconfirmed", 300000, "unconfirmed")
        self.paid(user, 50000)
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 50000.0)
        self.assertIsNone(baseline["income_conflict"])
        self.assertTrue(baseline["income_basis_needs_confirmation"])

    def test_annual_income_keeps_its_exact_amount_in_the_baseline(self):
        baseline = self.baseline(self.user("exact", Decimal("1000000.00"), "annual"))
        self.assertEqual(baseline["monthly_income"], 83333.33)
        self.assertEqual(baseline["annual_income"], 1000000.0)

    def test_stored_income_and_credits_are_untouched(self):
        user = self.user("untouched", 300000, "monthly")
        self.paid(user, 50000)
        before = list(Expense.objects.filter(user=user).order_by("pk").values_list("pk", "amount", "category"))
        self.baseline(user)
        user.refresh_from_db()
        self.assertEqual(user.monthly_income, Decimal("300000.00"))
        self.assertEqual(user.monthly_income_basis, "monthly")
        self.assertEqual(list(Expense.objects.filter(user=user).order_by("pk").values_list("pk", "amount", "category")), before)

    def test_settings_shows_the_conflict_only_to_its_owner(self):
        user = self.user("conflict_owner", 300000, "monthly")
        self.paid(user, 50000)
        self.client.force_login(user)
        self.assertContains(self.client.get("/settings/"), 'id="settingsIncomeConflict"')
        self.client.force_login(self.user("conflict_other", 90000, "monthly"))
        self.assertNotContains(self.client.get("/settings/"), 'id="settingsIncomeConflict"')

    def test_settings_names_the_career_income_a_period_would_apply_to(self):
        user = self.user("career_route", 0, "unconfirmed")
        CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=100000)
        self.client.force_login(user)
        response = self.client.get("/settings/")
        self.assertContains(response, 'id="settingsCareerIncomeHint"')
        self.assertContains(response, "100000.00")

        entered = self.user("career_entered", 50000, "monthly")
        CareerProfile.objects.create(user=entered, role="Analyst", experience_years=1, skills="", last_salary=100000)
        self.client.force_login(entered)
        self.assertNotContains(self.client.get("/settings/"), 'id="settingsCareerIncomeHint"')


class UnknownIncomeIsNotZeroTests(SalaryEvidenceBase):
    def with_loan(self, user):
        Loan.objects.create(user=user, loan_type="personal", lender="Synthetic", principal=500000, interest_rate=10,
                            tenure_months=60, emi=20000, remaining_balance=400000, start_date=timezone.localdate() - timedelta(days=60))

    def test_credit_alerts_say_the_ratio_is_unavailable_not_fine(self):
        user = self.user("dti_unknown", 300000, "unconfirmed")
        self.with_loan(user)
        types = {item["type"] for item in CreditScoreTrackerService()._generate_alerts(get_user_model().objects.get(pk=user.pk))}
        self.assertIn("DTI_UNAVAILABLE", types)
        self.assertNotIn("DTI_WARNING", types)

    def test_credit_alerts_still_warn_on_a_known_high_ratio(self):
        user = self.user("dti_high", 30000, "monthly")
        self.with_loan(user)
        types = {item["type"] for item in CreditScoreTrackerService()._generate_alerts(get_user_model().objects.get(pk=user.pk))}
        self.assertIn("DTI_WARNING", types)
        self.assertNotIn("DTI_UNAVAILABLE", types)

    def test_no_debt_means_no_income_alert(self):
        user = self.user("dti_none", 300000, "unconfirmed")
        types = {item["type"] for item in CreditScoreTrackerService()._generate_alerts(get_user_model().objects.get(pk=user.pk))}
        self.assertNotIn("DTI_UNAVAILABLE", types)

    def test_recommendations_do_not_read_unknown_income_as_budget_or_low_debt(self):
        engine = FinancialRecommendationEngine()
        base = {"age": 35, "savings_rate": 10, "has_investments": False, "dti_ratio": 0, "dependents": 0}
        unknown = {**base, "income": 0}
        known = {**base, "income": 50000}
        self.assertEqual(engine._assess_risk_appetite(unknown), "conservative")
        self.assertEqual(engine._assess_risk_appetite(known), "moderate")

    def test_salary_training_count_leaves_out_unconfirmed_income(self):
        self.user("train_unconfirmed", 300000, "unconfirmed")
        self.user("train_monthly", 90000, "monthly")
        spec = next(item for item in TRAINING_SPECS if item.key == "salary_predictor")
        self.assertEqual(spec.sample_counter(), 1)
