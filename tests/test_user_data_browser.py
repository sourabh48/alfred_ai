"""Real-page acceptance of synthetic financial data and its explanations."""
import json
import os
from pathlib import Path
import unittest
import threading
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.handlers.base import BaseHandler

from apps.expenses.models import Expense
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests import test_document_review_browser as browser_support
from tests.user_acceptance_scenario import PASSWORD, month_start, seed_acceptance_user


@unittest.skipUnless(browser_support.RUN_BROWSER_TESTS, "Set ALFRED_RUN_BROWSER_TESTS=true to run browser acceptance.")
class UserDataBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        cls.By = By
        cls.active_requests = 0
        cls.request_lock = threading.Lock()
        original_get_response = BaseHandler.get_response

        def tracked_response(handler, request):
            with cls.request_lock:
                cls.active_requests += 1
            try:
                return original_get_response(handler, request)
            finally:
                with cls.request_lock:
                    cls.active_requests -= 1

        tracker = patch.object(BaseHandler, "get_response", tracked_response)
        tracker.start()
        cls.addClassCleanup(tracker.stop)
        cls.browser = browser_support.DocumentReviewBrowserTests._create_driver(webdriver)
        cls.browser.set_window_size(1440, 1200)
        cls.wait = WebDriverWait(cls.browser, 20)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "browser", None):
            cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        self.browser.get("about:blank")
        cache.clear()
        self.offline = _offline_fixture_patches()
        self.addCleanup(self.offline.close)
        self.scenario = seed_acceptance_user(self.client)
        self.browser.delete_all_cookies()
        self.artifacts = Path(os.environ.get("ALFRED_BROWSER_ARTIFACT_DIR", "artifacts/browser")) / "user-data"
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.browser.get("about:blank")
        # Drain real live-server requests before TransactionTestCase flushes
        # users and sessions; navigation can abort a fetch while its server
        # handler is still completing the response.
        self.wait.until(lambda _: self.active_requests == 0)
        super().tearDown()

    def login(self, username="acceptance_demo"):
        self.browser.get(self.live_server_url + "/login/")
        self.browser.find_element(self.By.NAME, "username").send_keys(username)
        self.browser.find_element(self.By.NAME, "password").send_keys(PASSWORD)
        self.browser.find_element(self.By.CSS_SELECTOR, 'button[type="submit"]').click()
        self.wait.until(lambda driver: driver.find_elements(self.By.ID, "dashboardPeriodNote"))
        self.wait.until(lambda driver: self.text("dashboardPeriodNote") and "Loading" not in self.text("dashboardPeriodNote"))
        self.wait.until(lambda driver: self.text("dashboardSummaryCards"))

    def text(self, element_id):
        return self.browser.find_element(self.By.ID, element_id).text

    def capture(self, name):
        self.browser.save_screenshot(str(self.artifacts / f"{name}.png"))
        (self.artifacts / f"{name}.txt").write_text(self.browser.find_element(self.By.TAG_NAME, "body").text, encoding="utf-8")

    def test_tax_planning_uses_selected_year_and_income(self):
        self.login()
        self.browser.get(self.live_server_url + "/tax-optimizer/")
        self.wait.until(lambda _: "Official-source rules verified" in self.text("taxPolicyCopy"))
        self.assertIn("FY 2025-26", self.text("taxPolicyCopy"))
        self.assertIn("AY 2026-27", self.text("taxPolicyCopy"))
        income = self.browser.find_element(self.By.ID, "taxAnnualIncome")
        income.clear()
        income.send_keys("1500000")
        self.browser.find_element(self.By.CSS_SELECTOR, "#taxInputForm button[type=submit]").click()
        self.wait.until(lambda _: "97,500" in self.text("taxAnnualValue"))
        self.assertEqual(self.text("taxRegimeValue"), "NEW")
        self.assertEqual(self.browser.find_element(self.By.ID, "taxFinancialYear").get_attribute("value"), "2025-26")
        self.capture("tax-policy-2025-26")

    def test_inferred_loan_requires_explicit_confirmation_on_real_page(self):
        from django.utils import timezone
        from apps.loans.models import Loan
        from selenium.common.exceptions import StaleElementReferenceException

        user = get_user_model().objects.get(username="acceptance_demo")
        loan = Loan.objects.create(
            user=user, loan_type="personal", lender="Estimated Test Lender",
            principal=240000, remaining_balance=240000, interest_rate=10, emi=10000,
            tenure_months=24, start_date=timezone.localdate(), auto_detected=True,
            verification_status="estimated", verification_source="emi_pattern",
        )
        self.login()
        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda _: "1 estimated loan(s)" in self.text("loanVerificationNotice"))
        self.assertIn("1,00,000", self.text("loanSummaryCards"))
        self.assertNotIn("3,40,000", self.text("loanSummaryCards"))
        self.assertIn("Excluded from financial totals", self.text("loanTableBody"))
        self.capture("loan-estimate-excluded")
        def open_review(driver):
            try:
                driver.find_element(self.By.CSS_SELECTOR, f'button[onclick="editLoan({loan.pk})"]').click()
                return True
            except StaleElementReferenceException:
                # The live summary may replace a row between locating and clicking it.
                return False

        self.wait.until(open_review)
        self.assertFalse(self.browser.find_element(self.By.ID, "loanConfirmEstimate").is_selected())
        for field_id, value in (("manualLoanPrincipal", "200000"), ("manualLoanInterest", "8"),
                                ("manualLoanEmi", "9000"), ("manualLoanBalance", "150000")):
            field = self.browser.find_element(self.By.ID, field_id)
            field.clear()
            field.send_keys(value)
        self.browser.find_element(self.By.ID, "loanConfirmEstimate").click()
        self.browser.execute_script("document.getElementById('loanVerificationFields').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("loan-terms-review")
        self.browser.find_element(self.By.ID, "loanSubmitButton").click()
        self.wait.until(lambda _: "2,50,000" in self.text("loanSummaryCards"))
        self.assertIn("19,000", self.text("loanSummaryCards"))
        self.assertFalse(self.browser.find_element(self.By.ID, "loanVerificationNotice").is_displayed())
        loan.refresh_from_db()
        self.assertEqual(loan.verification_status, "confirmed")
        self.assertEqual(loan.remaining_balance, 150000)
        self.browser.execute_script("document.getElementById('loanSummaryCards').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.wait.until(lambda driver: driver.execute_script(
            "const r = document.getElementById('loanSummaryCards').getBoundingClientRect(); return r.top >= 78 && r.bottom <= innerHeight;"
        ))
        self.capture("loan-estimate-confirmed")

    def test_vehicle_value_and_running_costs_are_separate_on_real_page(self):
        from django.utils import timezone
        from apps.mobility.models import BikeProfile, BikeServiceRecord

        user = get_user_model().objects.get(username="acceptance_demo")
        profile = BikeProfile.objects.create(
            user=user, display_name="Personal Test Scooter", model_name="Test Scooter",
            usage_pattern="personal", estimated_market_value=50000,
        )
        BikeServiceRecord.objects.create(
            user=user, bike_profile=profile, bike_name=profile.display_name,
            service_date=timezone.localdate(), cost=6000,
        )
        self.login()
        self.browser.get(self.live_server_url + "/expenses/")
        self.wait.until(lambda _: "Personal Test Scooter" in self.text("balanceSheetPanel"))
        cards = self.text("balanceSheetCards")
        self.assertIn("2,10,000", cards)
        self.assertIn("1,00,000", cards)
        panel = self.text("balanceSheetPanel")
        self.assertIn("Estimated asset ₹50,000", panel)
        self.assertIn("Recorded running costs ₹6,000", panel)
        self.assertIn("all history", panel)
        self.assertNotIn("Lifestyle vehicle burden", panel)
        self.browser.execute_script("document.getElementById('balanceSheetPanel').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("vehicle-value-and-running-costs")

    def test_investment_projection_starts_with_recorded_value_on_real_page(self):
        self.login()
        self.browser.get(self.live_server_url + "/investments/")
        self.wait.until(lambda _: "1,10,000" in self.text("investmentHeroValue"))
        self.wait.until(lambda driver: driver.execute_script(
            "return Boolean(Chart.getChart(document.getElementById('growthChart')));"
        ))
        chart = self.browser.execute_script(
            "const d = Chart.getChart(document.getElementById('growthChart')).data; "
            "return {labels: d.labels, values: d.datasets[0].data};"
        )
        self.assertEqual(len(chart["labels"]), 13)
        self.assertEqual(len(chart["values"]), 13)
        self.assertEqual(chart["values"][0], 110000)
        self.assertEqual(chart["values"][1], 115766.67)
        factor = 1 + 8 / 1200
        expected_year = 110000 * factor ** 12 + 5000 * factor * (factor ** 12 - 1) / (factor - 1)
        self.assertAlmostEqual(chart["values"][12], expected_year, places=2)
        assumptions = self.text("investmentGrowthAssumptions")
        self.assertIn("Month 0", assumptions)
        self.assertIn("beginning of each month", assumptions)
        (self.artifacts / "investment-growth-values.json").write_text(json.dumps(chart, indent=2), encoding="utf-8")
        self.browser.execute_script("document.getElementById('growthChart').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("investment-month-zero-projection")

    def test_sample_totals_and_explanations_on_real_pages(self):
        self.login()
        summary = self.text("dashboardSummaryCards")
        for expected in ("30,000", "80,000", "47,000", "1,00,000", "Confirmed Outflow"):
            self.assertIn(expected.lower(), summary.lower())
        self.assertIn("33,000", self.text("dashboardFocusStrip"))
        self.assertIn("48.8%", self.text("dashboardFocusStrip"))
        self.assertIn("All recorded months", self.text("dashboardFocusStrip"))
        self.assertIn("60,000", self.text("dashboardReviewNotice"))
        self.assertIn("excluded", self.text("dashboardReviewNotice"))
        self.assertEqual(self.text("healthScoreValue"), "—")
        self.assertIn("Review transactions first", self.text("healthRiskPill"))
        charts = self.browser.execute_script("return Chart.getChart(document.getElementById('dashboardMonthlyChart')).data.datasets.map(d => ({label:d.label, last:d.data.at(-1)}));")
        amounts = {item["label"]: item["last"] for item in charts}
        self.assertEqual(amounts["Card payments"], 2000)
        self.assertEqual(amounts["Investments"], 5000)
        self.assertEqual(sum(amount for label, amount in amounts.items() if label != "Income"), 47000)
        (self.artifacts / "chart-values.json").write_text(json.dumps(amounts, indent=2), encoding="utf-8")
        self.capture("dashboard")

        self.browser.get(self.live_server_url + "/budgets/")
        self.wait.until(lambda driver: "10,000" in self.text("budgetSummaryCards"))
        self.assertIn("30,000", self.text("budgetPlanValue"))
        self.assertIn("20,000", self.text("budgetRemainingValue"))
        self.assertIn("20,000", self.text("budgetAffordabilityPanel"))
        self.assertIn("already reserved", self.text("budgetRoot"))
        self.assertIn("6,000", self.text("budgetCategoryBody"))
        self.assertIn("4,000", self.text("budgetCategoryBody"))
        self.capture("budget")

        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda driver: "1,00,000" in self.text("loanSummaryCards"))
        self.assertIn("10,000", self.text("loanSummaryCards"))
        self.assertIn("Recorded Loan Balance".lower(), self.text("loanSummaryCards").lower())
        self.capture("loans")

        self.browser.get(self.live_server_url + "/investments/")
        self.wait.until(lambda driver: "1,10,000" in self.text("investmentHeroValue"))
        self.assertIn("10,000", self.text("investmentSummaryCards"))
        self.assertIn("unrealized", self.text("investmentSummaryCards").lower())
        self.capture("investments")

    def test_empty_account_displays_missing_history_instead_of_a_bad_score(self):
        get_user_model().objects.create_user(username="empty_acceptance", password=PASSWORD)
        self.login("empty_acceptance")
        self.assertEqual(self.text("healthScoreValue"), "—")
        self.assertIn("No transactions yet", self.text("dashboardPeriodNote"))
        self.assertIn("—", self.text("dashboardFocusStrip"))
        self.capture("empty-dashboard")

    def test_old_transactions_show_their_actual_reporting_month(self):
        Expense.objects.filter(user=self.scenario["user"]).update(transaction_date=month_start(-1))
        cache.clear()
        self.login()
        self.assertIn(month_start(-1).strftime("%B %Y"), self.text("dashboardPeriodNote"))
        self.assertNotIn("Current Month", self.text("dashboardSummaryCards"))
        self.capture("older-history-dashboard")
