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
