"""FIN-02: bank credits count as salary only on real evidence, and unknown income is never read as zero."""
from datetime import date, timedelta
from types import SimpleNamespace
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase
from django.utils import timezone

from apps.career.models import CareerProfile
from apps.career.services.income_intelligence import build_employment_income_signals, is_never_pay
from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence, resolve_canonical_financial_baseline
from apps.integrations.services.credit_score_tracker import CreditScoreTrackerService
from apps.loans.models import Loan
from apps.ml_engine.services.recommendation_engine import FinancialRecommendationEngine
from apps.ml_engine.training.orchestrator import TRAINING_SPECS
from apps.risk.services.risk_intelligence import RiskIntelligenceService


class NeverPayTextTests(SimpleTestCase):
    def never_pay(self, text):
        return is_never_pay(SimpleNamespace(category="income", company_name="", counterparty="", merchant="", description=text, raw_description=""))

    def test_loans_and_investments_that_mention_salary_are_not_pay(self):
        for text in ("NEFT CR SALARY LOAN HDFC", "PAYDAY LOAN XYZ", "LOAN AGAINST SALARY", "LOAN FROM EMPLOYER", "ZERODHA MF PROCEEDS TO SALARY A/C",
                     "HOME LOAN DISBURSAL", "ZERODHA MF PROCEEDS TO SALARY ACCT", "PERSONAL LOAN TO SALARY-A/C", "BAJAJ FINSERV DISBURSAL"):
            with self.subTest(text=text):
                self.assertTrue(self.never_pay(text))

    def test_words_inside_longer_tokens_still_count(self):
        for text in ("SALARY AMT REFUNDED ACME", "NEFT CR AXISMF SWP", "GROWWPAY", "HDFCLOAN", "HOMELOAN", "LOAN_123", "DISBURSEMENT ACME"):
            with self.subTest(text=text):
                self.assertTrue(self.never_pay(text))

    def test_pay_from_lenders_and_payroll_disbursals_still_count(self):
        for text in ("SALARY DISBURSEMENT ACME", "PAYROLL DISBURSED", "SALARY HDFC LOAN SERVICES LTD", "NEFT CR STOCKHOLM TRADING",
                     "NEFT CR SALARY LOANTAP TECHNOLOGIES", "SALARY LOAN RECOVERY ACME", "SALARY - LOAN EMI DEDUCTED",
                     "NEFT CR EPFO PENSION DISBURSEMENT", "COMMISSION DISBURSED"):
            with self.subTest(text=text):
                self.assertFalse(self.never_pay(text))


class SalaryEvidenceBase(TestCase):
    def setUp(self):
        # Rolled-back tests reuse primary keys, and baselines are cached by user.
        cache.clear()

    def user(self, name, amount=0, basis="monthly"):
        return get_user_model().objects.create_user(name, password="Synthetic-Pass-1", monthly_income=amount, monthly_income_basis=basis)

    def credit(self, user, amount, *, months_ago=0, employer="Example Analytics", text="SALARY CREDIT", category="income", days_later=0):
        # Steps of 31 days always land in different calendar months.
        Expense.objects.create(
            user=user, amount=amount, classification="other", category=category, payment_mode="BANK",
            merchant=employer, company_name=employer, counterparty=employer, description=text, raw_description=text,
            transaction_date=timezone.localdate() - timedelta(days=31 * months_ago + 4 - days_later),
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

    def test_a_job_change_uses_the_new_employer_once_the_old_pay_has_stopped(self):
        user = self.user("job_change")
        for month in range(2, 4):
            self.credit(user, 90000, months_ago=month, employer="Oldco Systems")
        self.credit(user, 120000, months_ago=0, employer="Newco Systems")
        signals = self.signals(user)
        self.assertEqual(signals["monthly_cash_income"], 120000.0)
        self.assertEqual(signals["current_employer"], "Newco Systems")

    def test_one_credit_from_a_new_payer_waits_while_recurring_pay_continues(self):
        for name, amount in (("raise", 120000), ("cut", 60000), ("bonus", 300000)):
            with self.subTest(name=name):
                user = self.user(f"lone_{name}")
                for month in range(1, 3):
                    self.credit(user, 90000, months_ago=month, employer="Oldco Systems", text="NEFT OLDCO")
                self.credit(user, amount, months_ago=0, employer="Newco Systems", text="SALARY NEWCO")
                self.assertEqual(self.signals(user)["monthly_cash_income"], 90000.0)

    def test_two_shared_paydays_are_still_a_job_change(self):
        user = self.user("two_shared")
        for month in range(3):
            self.credit(user, 90000, months_ago=month, employer="Oldco Systems", text="SALARY OLDCO")
        for month in range(2):
            self.credit(user, 120000, months_ago=month, employer="Newco Systems", text="SALARY NEWCO")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 120000.0)

    def test_credits_after_the_date_asked_about_are_not_evidence(self):
        future = self.user("future_credit")
        for month in range(3):
            self.credit(future, 80000, months_ago=month)
        Expense.objects.create(user=future, amount=30000, classification="other", category="income", payment_mode="BANK", merchant="Otherco",
                               company_name="Otherco", counterparty="Otherco", description="SALARY OTHERCO", raw_description="SALARY OTHERCO",
                               transaction_date=timezone.localdate() + timedelta(days=200), direction="credit", source="bank_statement")
        self.assertEqual(self.signals(future)["monthly_cash_income"], 80000.0)

        history = self.user("historic_credit")
        for month in range(5, 8):
            self.credit(history, 70000, months_ago=month, employer="Oldco Systems", text="SALARY OLDCO")
        for month in range(3):
            self.credit(history, 120000, months_ago=month, employer="Newco Systems", text="SALARY NEWCO")
        then = timezone.localdate() - timedelta(days=31 * 5)
        past = build_employment_income_signals(user=get_user_model().objects.get(pk=history.pk), today=then)
        self.assertEqual(past["monthly_cash_income"], 70000.0)
        self.assertEqual(past["current_employer"], "Oldco Systems")

    def test_two_employers_paying_together_are_added(self):
        user = self.user("two_jobs")
        for month in range(3):
            self.credit(user, 80000, months_ago=month, employer="First Employer")
            self.credit(user, 30000, months_ago=month, employer="Second Employer")
        signals = self.signals(user)
        self.assertEqual(signals["monthly_cash_income"], 110000.0)
        self.assertEqual(signals["annualized_compensation"], 1320000.0)
        self.assertEqual(signals["salary_signal_count"], 2)

    def test_credits_that_are_never_pay_stay_out_whatever_their_text_says(self):
        for name, category, text in (("loan", "loan", "HDFC LOAN TRANCHE"), ("invest", "investment", "SALARY MF REDEMPTION"), ("card", "credit_card", "SALARY CARD")):
            with self.subTest(name=name):
                user = self.user(f"never_{name}")
                for month in range(2):
                    self.credit(user, 40000, months_ago=month, employer="Lender", text=text, category=category)
                self.assertIsNone(self.signals(user)["salary_credit_signal"])
        # Statement import files every one of these credits under income.
        for name, amount, text in (
            ("refund", 15000, "REFUND TO SALARY A/C"), ("reversed", 50000, "NEFT SALARY REVERSED ACME"),
            ("redemption", 40000, "IMPS CR ZERODHA MF REDEMPTION"), ("advance", 500000, "NEFT CR SALARY ADVANCE LOAN DISBURSAL"),
            ("amc", 40000, "NEFT CR ICICI PRU AMC REDEMPTION"), ("disbursal", 40000, "NEFT CR BAJAJ FINSERV DISBURSAL"),
            ("mf_at_end", 40000, "NEFT CR AXIS MF"),
        ):
            with self.subTest(name=name):
                user = self.user(f"never_income_{name}")
                for month in range(2):
                    self.credit(user, amount, months_ago=month, employer="Acme", text=text)
                self.assertIsNone(self.signals(user)["salary_credit_signal"])
                self.assertEqual(self.baseline(user)["monthly_income"], 0.0)

    def test_people_employed_by_lenders_and_brokers_are_still_paid(self):
        for name, text in (("broker", "SALARY ZERODHA BROKING"), ("recovery", "SALARY LESS LOAN RECOVERY"), ("card", "SALARY HDFC CREDIT CARD DIVISION")):
            with self.subTest(name=name):
                user = self.user(f"lender_staff_{name}")
                for month in range(2):
                    self.credit(user, 40000, months_ago=month, employer="Acme", text=text)
                self.assertEqual(self.signals(user)["monthly_cash_income"], 40000.0)
        for name, text in (("stockholm", "NEFT STOCKHOLM TRADERS"), ("livestock", "NEFT LIVESTOCK TRADERS")):
            with self.subTest(name=name):
                user = self.user(f"lookalike_{name}")
                for month in range(3):
                    self.credit(user, 40000, months_ago=month, employer="Acme", text=text)
                self.assertEqual(self.signals(user)["monthly_cash_income"], 40000.0)

    def test_a_smaller_credit_after_payday_never_displaces_the_salary(self):
        for name, employer, text, recurring in (
            ("tenant", "A Tenant", "NEFT A TENANT", True),
            ("stipend", "Other Payer", "STIPEND", False),
        ):
            with self.subTest(name=name):
                user = self.user(f"after_{name}")
                for month in range(3):
                    self.credit(user, 80000, months_ago=month)
                    if recurring or not month:
                        self.credit(user, 20000, months_ago=month, employer=employer, text=text, days_later=1)
                signals = self.signals(user)
                self.assertEqual(signals["monthly_cash_income"], 80000.0)
                self.assertEqual(signals["current_employer"], "Example Analytics")

    def test_a_larger_recurring_credit_outweighs_one_described_credit(self):
        user = self.user("undescribed_salary")
        for month in range(3):
            self.credit(user, 80000, months_ago=month, employer="Acme Traders", text="NEFT ACME TRADERS")
        self.credit(user, 20000, employer="Other Payer", text="STIPEND", days_later=2)
        self.assertEqual(self.signals(user)["monthly_cash_income"], 80000.0)

    def test_overlapping_paydays_in_a_job_change_are_not_two_jobs(self):
        user = self.user("payday_overlap")
        for month in range(2):
            self.credit(user, 90000, months_ago=month + 1, employer="Oldco Systems", text="SALARY OLDCO")
            self.credit(user, 120000, months_ago=month, employer="Newco Systems", text="SALARY NEWCO")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 120000.0)

    def test_a_pay_cut_at_a_new_employer_takes_over_once_the_old_one_stops(self):
        user = self.user("pay_cut")
        for month in (2, 3):
            self.credit(user, 120000, months_ago=month, employer="Oldco Systems", text="SALARY OLDCO")
        self.credit(user, 90000, employer="Newco Systems", text="SALARY NEWCO")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 90000.0)

    def test_recurring_credits_not_described_as_salary_are_not_added_to_salary(self):
        user = self.user("tenant")
        for month in range(3):
            self.credit(user, 80000, months_ago=month, employer="First Employer")
            self.credit(user, 20000, months_ago=month, employer="A Tenant", text="NEFT A TENANT")
        self.assertEqual(self.signals(user)["monthly_cash_income"], 80000.0)


class IncomeFallbackTests(SalaryEvidenceBase):
    def test_old_income_credits_cannot_return_through_the_fallback(self):
        user = self.user("fallback_stale")
        for month in range(4, 8):
            self.credit(user, 150000, months_ago=month)
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 0.0)
        self.assertEqual(baseline["annual_income"], 0.0)
        self.assertEqual(baseline["income_source"], "not_evidenced")
        self.assertEqual(baseline["metric_states"]["monthly_income"]["status"], "unavailable")

    def test_one_income_credit_is_not_a_monthly_income(self):
        user = self.user("fallback_single")
        self.credit(user, 30000, employer="Acme Traders", text="NEFT ACME TRADERS")
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 0.0)
        self.assertEqual(baseline["income_source"], "not_evidenced")

    def test_small_refunds_do_not_set_income_through_the_fallback(self):
        user = self.user("fallback_refund")
        for month in range(2):
            self.credit(user, 5000, months_ago=month, employer="Amazon", text="AMAZON REFUND")
        self.assertEqual(self.baseline(user)["income_source"], "not_evidenced")

    def test_the_fallback_amount_uses_only_credits_inside_its_window(self):
        user = self.user("fallback_mixed")
        self.credit(user, 150000, months_ago=8, employer="A Family", text="UPI FAMILY SUPPORT")
        for month in range(2):
            self.credit(user, 5000, months_ago=month, employer="A Family", text="UPI FAMILY SUPPORT")
        Expense.objects.create(user=user, amount=1000000, classification="other", category="income", payment_mode="BANK", merchant="Later",
                               description="UPI LATER", raw_description="UPI LATER", transaction_date=timezone.localdate() + timedelta(days=100),
                               direction="credit", source="bank_statement")
        self.assertEqual(self.baseline(user)["monthly_income"], 5000.0)

    def test_an_old_credit_in_the_cutoff_month_does_not_make_one_recent_credit_recur(self):
        user = self.user("fallback_cutoff_month")
        # The window from 31 October opens on 31 July, so 20 July is outside it but in the same month.
        for day in (date(2026, 7, 20), date(2026, 10, 20)):
            Expense.objects.create(user=user, amount=5000, classification="other", category="income", payment_mode="BANK", merchant="A Family",
                                   description="UPI FAMILY", raw_description="UPI FAMILY", transaction_date=day,
                                   direction="credit", source="bank_statement")
        baseline = resolve_canonical_financial_baseline(get_user_model().objects.get(pk=user.pk), reference_date=date(2026, 10, 31))
        self.assertEqual(baseline["income_source"], "not_evidenced")

    def test_recent_recurring_credits_too_small_for_salary_still_count(self):
        user = self.user("fallback_recent")
        for month in range(2):
            self.credit(user, 5000, months_ago=month, employer="A Family", text="UPI FAMILY SUPPORT")
        baseline = self.baseline(user)
        self.assertEqual(baseline["income_source"], "observed_credit_inflow")
        self.assertEqual(baseline["monthly_income"], 5000.0)

    def test_dashboard_and_canonical_baseline_agree_about_old_salary(self):
        user = self.user("dashboard_agrees", 300000, "unconfirmed")
        for month in range(6, 9):
            self.credit(user, 50000, months_ago=month)
        canonical = self.baseline(user)
        dashboard = build_financial_intelligence(get_user_model().objects.get(pk=user.pk))["baseline"]
        self.assertEqual(canonical["income_source"], "reported_income_unconfirmed")
        self.assertEqual((dashboard["income_source"], dashboard["monthly_income"]), (canonical["income_source"], canonical["monthly_income"]))

    def test_a_future_dated_expense_does_not_age_out_current_salary(self):
        user = self.user("future_dated")
        for month in range(2):
            self.credit(user, 50000, months_ago=month)
        Expense.objects.create(user=user, amount=100, classification="expense", category="food", payment_mode="CASH", merchant="Shop",
                               transaction_date=timezone.localdate() + timedelta(days=200), direction="debit", source="manual")
        dashboard = build_financial_intelligence(get_user_model().objects.get(pk=user.pk))["baseline"]
        self.assertEqual(dashboard["income_source"], "salary_credits")


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

    def test_the_agreement_band_edges(self):
        for name, salary, conflict in (("above_edge", 112000, True), ("above_ok", 110000, False), ("below_ok", 56000, False), ("below_edge", 55000, True)):
            with self.subTest(name=name):
                user = self.user(f"band_{name}", 100000, "monthly")
                self.paid(user, salary)
                baseline = self.baseline(user)
                self.assertEqual(bool(baseline["income_conflict"]), conflict)
                self.assertEqual(baseline["monthly_income"], 100000.0 if conflict else float(salary))

    def test_take_home_credits_do_not_replace_an_income_confirmed_per_year(self):
        user = self.user("annual_take_home", Decimal("1000000.00"), "annual")
        self.paid(user, 60000)
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 60000.0)
        self.assertEqual(baseline["annual_income"], 1000000.0)
        self.assertEqual(self.signals(user)["annualized_compensation"], 1000000.0)

    def test_credits_above_an_annual_income_inside_the_band_do_not_raise_it(self):
        user = self.user("annual_above", Decimal("1200000.00"), "annual")
        self.paid(user, 105000)
        baseline = self.baseline(user)
        self.assertEqual(baseline["annual_income"], 1200000.0)
        self.assertEqual(baseline["confirmed_annual_income"], 1200000.0)
        self.assertEqual(self.signals(user)["annualized_compensation"], 1200000.0)

    def test_tax_starts_from_the_confirmed_income_never_take_home(self):
        for name, amount, basis, salary, expected in (
            ("monthly", 100000, "monthly", 80000, 1200000.0),
            ("annual", 1000000, "annual", 60000, 1000000.0),
            ("unconfirmed", 300000, "unconfirmed", 50000, 0.0),
            ("none", 0, "monthly", 50000, 0.0),
            ("career_salary_only", 0, "monthly", 0, 0.0),
        ):
            with self.subTest(name=name):
                user = self.user(f"tax_{name}", amount, basis)
                if name == "career_salary_only":
                    CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=50000)
                else:
                    self.paid(user, salary)
                client = Client()
                client.force_login(user)
                self.assertEqual(float(client.get("/api/integrations/tax/overview/").json()["annual_income"]), expected)

    def test_the_conflict_summary_does_not_also_deny_the_credits_exist(self):
        user = self.user("summary", 300000, "monthly")
        self.paid(user, 50000)
        self.assertNotIn("no recurring salary", self.signals(user)["source_summary"])

    def test_monthly_equivalent_rounds_like_the_stored_decimal(self):
        user = self.user("rounding", Decimal("1200001.50"), "annual")
        self.assertEqual(self.signals(user)["reported_income"]["monthly_equivalent"], float(user.confirmed_monthly_income))

    def test_evidence_for_the_ai_discloses_the_conflict(self):
        from apps.ml_engine.services.canonical_evidence import baseline_source
        user = self.user("evidence", 300000, "monthly")
        self.paid(user, 50000)
        self.assertIn("disagree", str(baseline_source(get_user_model().objects.get(pk=user.pk))))

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
    def test_risk_signals_with_no_data_are_unknown_not_zero(self):
        outlook = RiskIntelligenceService().build_outlook(self.user("risk_blank"))
        signals = outlook["module_signals"]
        self.assertIsNone(signals["emergency_months"])
        self.assertIsNone(signals["average_stress"])
        self.assertIsNone(signals["average_sleep"])
        relocation = next(item for item in outlook["consolidated_risks"] if item["key"] == "relocation")
        self.assertNotIn("rent burden", relocation["note"])

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
        personas = {"spending_categories": {}, "dependents": 0, "age": 35, "savings_rate": 10, "has_investments": True}
        self.assertNotIn("budget_conscious", engine._determine_persona({**personas, "income": 0}))
        self.assertIn("budget_conscious", engine._determine_persona({**personas, "income": 50000}))

    def test_financial_brain_does_not_call_unknown_debt_load_debt_free(self):
        from apps.ml_engine.services.alfred_financial_brain import AlfredFinancialBrain
        brain = AlfredFinancialBrain()
        self.assertTrue(brain._debt_load_unknown({"monthly_income": 0, "fixed_obligations": 20000}))
        self.assertFalse(brain._debt_load_unknown({"monthly_income": 0, "fixed_obligations": 0}))
        self.assertFalse(brain._debt_load_unknown({"monthly_income": 50000, "fixed_obligations": 20000}))
        self.assertFalse(brain._debt_load_unknown({}))
        snapshot = {"financial_baseline": {"monthly_income": 0, "fixed_obligations": 20000, "debt_burden_ratio": 0}}
        factors = brain._calculate_financial_health_score(snapshot)["contributing_factors"]
        self.assertIn("Debt load unknown until income is confirmed", factors)
        self.assertNotIn("Debt-free lifestyle", factors)
        self.assertIn("Confirm Your Income", [item["action"] for item in brain._generate_priority_actions(snapshot)])

    def test_a_projection_on_unknown_income_is_withheld_not_zero(self):
        from apps.career.services.projection_engine import build_projection_simulation, build_salary_projection
        user = self.user("projection_none", 300000, "unconfirmed")
        profile = CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=0)
        projection = build_salary_projection(user, profile, macro={"payload": {"unemployment": {}, "inflation": {}, "market": {}}, "evidence": []})
        self.assertEqual(projection["projections"], [])
        self.assertIn("Confirm your income", projection["message"])
        self.assertEqual(projection["insights"][0], projection["message"])
        macro = {"payload": {"unemployment": {}, "inflation": {}, "market": {}}, "evidence": []}
        simulation = build_projection_simulation(user=user, profile=profile, macro=macro, overrides={"monthly_income": 80000})
        self.assertIsNone(simulation["delta"]["year_5_projected_income"])

    def test_salary_training_count_leaves_out_unconfirmed_income(self):
        self.user("train_unconfirmed", 300000, "unconfirmed")
        self.user("train_monthly", 90000, "monthly")
        spec = next(item for item in TRAINING_SPECS if item.key == "salary_predictor")
        self.assertEqual(spec.sample_counter(), 1)
