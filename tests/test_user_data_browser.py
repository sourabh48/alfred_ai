"""Real-page acceptance of synthetic financial data and its explanations."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import threading
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.handlers.base import BaseHandler
from django.test import override_settings

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
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-invite-limits-"))
        self.enterContext(override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory))
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

    def click_upload_button(self, form_id):
        button = self.browser.find_element(self.By.CSS_SELECTOR, f"#{form_id} button[type=submit]")
        self.browser.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", button)
        self.wait.until(lambda _: button.is_enabled())
        button.click()

    @override_settings(ALFRED_UPLOAD_FILE_BYTES=1024, ALFRED_UPLOAD_REQUEST_BYTES=4096)
    def test_document_size_limit_feedback_then_valid_resume(self):
        from apps.career.models import CareerResume
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-upload-fixture-"))
        oversized = Path(directory) / "oversized.txt"
        valid = Path(directory) / "resume.txt"
        oversized.write_bytes(b"X" * 1025)
        valid.write_text("Synthetic Analyst\nPython SQL\n4 years experience", encoding="utf-8")
        before = CareerResume.objects.count()
        self.login()
        self.browser.get(self.live_server_url + "/documents/")
        field = self.wait.until(lambda driver: driver.find_element(self.By.ID, "documentResumeFile"))
        field.send_keys(str(oversized))
        self.click_upload_button("documentResumeForm")
        self.wait.until(lambda _: "configured" in self.text("documentResumeFeedback"))
        self.assertEqual(CareerResume.objects.count(), before)
        self.capture("upload-size-rejected")
        self.browser.execute_script("document.getElementById('documentResumeFile').value = '';")
        self.browser.find_element(self.By.ID, "documentResumeFile").send_keys(str(valid))
        self.click_upload_button("documentResumeForm")
        self.wait.until(lambda _: CareerResume.objects.count() == before + 1)
        self.wait.until(lambda _: "uploaded" in self.text("documentResumeFeedback").casefold())
        self.capture("upload-valid-resume")

    def test_loan_diagnostics_are_safe_then_real_pdf_import_and_reimport_work(self):
        import fitz
        from apps.loans.models import Loan, LoanImportDocument
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-m14f-browser-"))
        file = Path(directory) / "synthetic-loan.pdf"
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 40), "HDFC PERSONAL LOAN\nLoan Number TESTM14F42\nLoan Amount 1000.00\n"
                             "EMI Amount 100.00\nOutstanding Amount 500.00\nTenure 10 months")
            file.write_bytes(pdf.tobytes())
        owner = get_user_model().objects.get(username="acceptance_demo")
        marker = r"C:\synthetic-private\loan.pdf; fake-token-M14F-browser; OCR PRIVATE LOAN"
        LoanImportDocument.objects.create(user=owner, file_name="historical-loan.pdf", parser_status="failed",
                                         summary=marker, extracted_payload={"error": marker, "raw_text_excerpt": marker})
        self.login()
        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda _: "historical-loan.pdf" in self.text("loanImportHistory"))
        self.assertNotIn(marker, self.browser.page_source)
        self.browser.find_element(self.By.ID, "loanPdfFile").send_keys(str(file))
        button = self.browser.find_element(self.By.ID, "loanImportBtn")
        self.browser.execute_script("arguments[0].scrollIntoView({behavior:'instant', block:'center'});", button)
        self.wait.until(lambda driver: driver.execute_script(
            "const r = document.getElementById('loanImportBtn').getBoundingClientRect(); return r.top >= 78 && r.bottom <= innerHeight;"))
        with patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=RuntimeError(marker)):
            button.click()
            self.wait.until(lambda _: LoanImportDocument.objects.filter(file_name=file.name, parser_status="failed").exists())
            self.wait.until(lambda _: "review" in self.text("loanImportStatus").casefold())
        self.assertNotIn(marker, self.browser.page_source)
        self.capture("loan-safe-parser-failure")
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, "loanImportBtn").is_enabled())
        for attempt in (1, 2):
            self.browser.find_element(self.By.ID, "loanPdfFile").send_keys(str(file))
            self.browser.execute_script("document.getElementById('loanImportBtn').scrollIntoView({behavior:'instant', block:'center'});")
            self.browser.find_element(self.By.ID, "loanImportBtn").click()
            self.wait.until(lambda _: LoanImportDocument.objects.filter(file_name=file.name, parser_status="parsed").count() == attempt)
            self.wait.until(lambda _: self.browser.find_element(self.By.ID, "loanImportBtn").is_enabled())
            rows = list(Loan.objects.filter(user=owner, loan_account_number="TESTM14F42").values_list("pk", "principal", "remaining_balance", "emi"))
            self.assertEqual(len(rows), 1)
            if attempt == 1:
                expected = rows
            else:
                self.assertEqual(rows, expected)
        self.capture("loan-real-pdf-reimport")
        self.browser.get(self.live_server_url + "/documents/")
        self.wait.until(lambda _: "historical-loan.pdf" in self.browser.find_element(self.By.TAG_NAME, "body").text)
        self.assertNotIn(marker, self.browser.page_source)
        self.capture("loan-safe-historical-review")

    def test_statement_real_pdf_reimport_preserves_fingerprints_and_balance(self):
        import fitz
        from apps.expenses.models import BankAccount, StatementUpload
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-statement-fixture-"))
        statement = Path(directory) / "synthetic-statement.pdf"
        header = (f"{'Date':<12}{'Narration':<35}{'Chq./Ref.No.':<18}{'Value Dt':<12}"
                  f"{'Withdrawal Amt.':<20}{'Deposit Amt.':<20}Closing Balance")
        line = (f"{'31/03/26':<12}{'UPI-SYNTHETIC-SHOP':<35}{'123456789012':<18}{'31/03/26':<12}"
                f"{'40.00':>16}    {'':>16}    {'1,210.00':>16}")
        with fitz.open() as pdf:
            page = pdf.new_page(width=1100, height=800)
            for top, text in ((40, "HDFC BANK Statement From: 01/03/2026 To: 31/03/2026"),
                              (55, "Account No: 999988887777"), (70, header), (100, line)):
                page.insert_text((30, top), text, fontname="cour", fontsize=9)
            statement.write_bytes(pdf.tobytes())
        self.login()
        self.browser.get(self.live_server_url + "/documents/")
        self.wait.until(lambda driver: driver.find_element(self.By.ID, "documentStatementFile"))
        for attempt in (1, 2):
            self.browser.execute_script("document.getElementById('documentStatementFile').value = '';")
            self.browser.find_element(self.By.ID, "documentStatementFile").send_keys(str(statement))
            self.click_upload_button("documentStatementForm")
            self.wait.until(lambda _: StatementUpload.objects.filter(file_name=statement.name).count() == attempt)
            self.wait.until(lambda _: "processed" in self.text("documentStatementFeedback").casefold())
            rows = list(Expense.objects.filter(source="bank_statement", bank_account__account_number="999988887777").values_list("transaction_fingerprint", "external_reference", "amount"))
            balances = list(BankAccount.objects.filter(account_number="999988887777").values_list("current_balance", flat=True))
            if attempt == 1:
                self.assertEqual(len(rows), 1)
                expected_rows, expected_balances = rows, balances
            else:
                self.assertEqual(rows, expected_rows)
                self.assertEqual(balances, expected_balances)
        self.capture("upload-statement-deduplication")

    def test_family_invitation_limits_show_safe_feedback_then_allow_valid_acceptance(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.family.models import FamilyAccountLink
        from apps.family.services import create_family_link_invite, family_financial_user_ids
        self.login()
        owner = get_user_model().objects.get(username="acceptance_demo")
        inviter = get_user_model().objects.create_user(username="browser_inviter", password=PASSWORD)
        link, code = create_family_link_invite(inviter)
        now = timezone.now()
        with override_settings(ALFRED_FAMILY_INVITE_CREATE_LIMIT=1, ALFRED_FAMILY_INVITE_CREATE_WINDOW_SECONDS=60,
                               ALFRED_FAMILY_INVITE_ACCEPT_LIMIT=1, ALFRED_FAMILY_INVITE_ACCEPT_WINDOW_SECONDS=60), patch(
                                   "django.utils.timezone.now", side_effect=lambda: now):
            self.browser.get(self.live_server_url + "/settings/")
            self.browser.find_element(self.By.ID, "settingsGenerateInviteBtn").click()
            self.wait.until(lambda _: "code generated" in self.text("settingsLinkFeedback"))
            self.assertTrue(self.text("settingsInviteCode").startswith("ALF-"))
            count = FamilyAccountLink.objects.count()
            self.browser.find_element(self.By.ID, "settingsGenerateInviteBtn").click()
            self.wait.until(lambda _: "throttled" in self.text("settingsLinkFeedback"))
            self.assertEqual(FamilyAccountLink.objects.count(), count)
            self.capture("family-create-throttled")
            field = self.browser.find_element(self.By.ID, "settingsInviteCodeInput")
            submit = self.browser.find_element(self.By.CSS_SELECTOR, '#settingsAcceptInviteForm button[type="submit"]')
            field.send_keys("ALF-AAAA-AAAA")
            submit.click()
            self.wait.until(lambda _: "cannot be accepted" in self.text("settingsLinkFeedback"))
            field.clear()
            field.send_keys(code)
            submit.click()
            self.wait.until(lambda _: "throttled" in self.text("settingsLinkFeedback"))
            link.refresh_from_db()
            self.assertEqual(link.status, "pending")
            self.capture("family-accept-throttled")
            now += timedelta(seconds=60)
            submit.click()
            self.wait.until(lambda _: "account connected" in self.text("settingsLinkFeedback"))
            self.wait.until(lambda _: "browser_inviter" in self.text("settingsLinkedAccountsList"))
            link.refresh_from_db()
            self.assertEqual(link.linked_user_id, owner.pk)
            self.assertEqual(family_financial_user_ids(owner), [owner.pk])
            self.capture("family-accept-after-retry")

    def test_family_growth_failure_shows_safe_message_and_can_recover(self):
        self.login()
        cache.clear()
        marker = "synthetic-private-family-finance-token"
        with patch("apps.family.views._family_growth_payload", side_effect=RuntimeError(marker)):
            self.browser.get(self.live_server_url + "/family/")
            self.wait.until(lambda _: "Family growth is temporarily unavailable. Please try again." in self.text("familyRoot"))
            self.assertNotIn(marker, self.browser.find_element(self.By.TAG_NAME, "body").text)
            self.capture("family-growth-safe-error")
        self.browser.refresh()
        self.wait.until(lambda _: "current net worth" in self.text("familySummaryCards").casefold())
        self.assertNotIn("temporarily unavailable", self.text("familyRoot"))
        self.capture("family-growth-safe-error-recovery")

    def test_family_financial_sharing_requires_owner_opt_in_and_can_be_revoked(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        from apps.family.services import accept_family_link_code, create_family_link_invite, family_financial_user_ids
        owner = get_user_model().objects.get(username="acceptance_demo")
        member = get_user_model().objects.create_user(username="browser_family_member", password=PASSWORD)
        link, code = create_family_link_invite(owner)
        accept_family_link_code(member, code)
        self.login()
        self.browser.get(self.live_server_url + "/settings/")
        selector = f'[data-family-link-action="financial-sharing"][data-family-link-id="{link.pk}"]'
        self.wait.until(lambda driver: driver.find_elements(self.By.CSS_SELECTOR, selector))
        self.assertIn("Share my financial summary", self.text("settingsLinkedAccountsList"))
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.wait.until(lambda driver: driver.switch_to.alert)
        self.assertIn("monthly income", self.browser.switch_to.alert.text)
        self.browser.switch_to.alert.dismiss()
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        self.assertEqual(set(family_financial_user_ids(member)), {owner.pk, member.pk})
        self.assertEqual(family_financial_user_ids(owner), [owner.pk])
        self.browser.refresh()
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        expected_net_worth = resolve_canonical_financial_baseline(owner)["net_worth"]
        self.browser.delete_all_cookies()
        self.login("browser_family_member")
        self.browser.get(self.live_server_url + "/family/")
        expected_text = self.browser.execute_script("return Alfred.formatCurrency(arguments[0]);", float(expected_net_worth))
        self.wait.until(lambda _: self.text("familyNetWorthValue") == expected_text)
        self.browser.delete_all_cookies()
        self.login()
        self.browser.get(self.live_server_url + "/settings/")
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.wait.until(lambda _: "Share my financial summary" in self.text("settingsLinkedAccountsList"))
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.assertIn("Connected", self.text("settingsLinkedAccountsList"))
        self.capture("family-financial-opt-in-revoked")
        self.browser.delete_all_cookies()
        self.login("browser_family_member")
        self.browser.get(self.live_server_url + "/family/")
        private_text = self.browser.execute_script("return Alfred.formatCurrency(0);")
        self.wait.until(lambda _: self.text("familyNetWorthValue") == private_text)

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

    def test_expense_form_preserves_import_identity_and_bank_cents(self):
        from decimal import Decimal
        from types import SimpleNamespace
        from apps.expenses.models import BankAccount
        from apps.expenses.serializers import ExpenseSerializer
        from apps.expenses.services.statement_lifecycle import _import_statement_transactions
        from tests.test_expense_money_identity import parsed_fixture
        from apps.expenses.models import StatementUpload
        from django.utils import timezone

        user = self.scenario["user"]
        account = BankAccount.objects.create(user=user, account_number="TEST0001", current_balance="10.005")
        serializer = ExpenseSerializer(data={"amount": "2.675", "closing_balance": "10.005", "bank_account": account.pk, "transaction_date": timezone.localdate().isoformat(), "source": "bank_statement", "raw_description": "UPI SAMPLE MERCHANT", "description": "UPI SAMPLE MERCHANT", "external_reference": "REF-001", "category": "shopping"}, context={"request": SimpleNamespace(user=user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=user)
        row.refresh_from_db()
        fingerprint, identity = row.transaction_fingerprint, row.transaction_identity
        self.login()
        self.browser.get(self.live_server_url + "/expenses/")
        self.wait.until(lambda driver: driver.execute_script("return expenseIndex.has(arguments[0]);", row.pk))
        self.browser.execute_script("openEditModal(arguments[0]);", row.pk)
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, "expenseSubmitBtn").is_displayed())
        form = self.browser.find_element(self.By.ID, "expenseForm")
        self.assertEqual(form.find_element(self.By.NAME, "amount").get_attribute("value"), "2.68")
        from selenium.webdriver.support.ui import Select
        Select(form.find_element(self.By.NAME, "category")).select_by_value("food")
        self.browser.find_element(self.By.ID, "expenseSubmitBtn").click()
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID, "expenseSubmitBtn").is_displayed())
        row.refresh_from_db()
        account.refresh_from_db()
        self.assertEqual(row.category, "food")
        self.assertEqual((row.transaction_fingerprint, row.transaction_identity), (fingerprint, identity))
        self.assertEqual((row.amount, row.closing_balance, account.current_balance), (Decimal("2.68"), Decimal("10.01"), Decimal("10.01")))
        upload = StatementUpload.objects.create(user=user, bank_account=account, file_name="synthetic.pdf")
        parsed = parsed_fixture(closing=15.005)
        parsed.transactions[0].transaction_date = row.transaction_date
        created, skipped = _import_statement_transactions(user=user, upload=upload, bank_account=account, parsed=parsed)
        self.assertEqual((len(created), skipped), (0, 1))
        payload = self.browser.execute_async_script("const done=arguments[0]; fetch('/api/expenses/').then(r=>r.json()).then(done);")
        rows = payload if isinstance(payload, list) else payload["results"]
        displayed = next(item for item in rows if item["id"] == row.pk)
        self.assertEqual(displayed["amount"], 2.68)
        self.assertEqual(displayed["closing_balance"], 10.01)
        self.capture("expense-money-identity")

    def test_old_transactions_show_their_actual_reporting_month(self):
        Expense.objects.filter(user=self.scenario["user"]).update(transaction_date=month_start(-1))
        cache.clear()
        self.login()
        self.assertIn(month_start(-1).strftime("%B %Y"), self.text("dashboardPeriodNote"))
        self.assertNotIn("Current Month", self.text("dashboardSummaryCards"))
        self.capture("older-history-dashboard")
