import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client

from apps.expenses.models import StatementUpload
from apps.ml_engine.models import DocumentParserLearningMemory
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord


RUN_BROWSER_TESTS = os.environ.get("ALFRED_RUN_BROWSER_TESTS", "").lower() in {"1", "true", "yes"}


@unittest.skipUnless(RUN_BROWSER_TESTS, "Set ALFRED_RUN_BROWSER_TESTS=true to run Selenium browser workflow tests.")
class DocumentReviewBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from selenium import webdriver
            from selenium.common.exceptions import WebDriverException
            from selenium.common.exceptions import StaleElementReferenceException
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import Select
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError as exc:
            raise unittest.SkipTest(f"Selenium is not installed: {exc}") from exc

        cls.By = By
        cls.EC = EC
        cls.Select = Select
        cls.StaleElementReferenceException = StaleElementReferenceException
        cls.WebDriverWait = WebDriverWait
        cls.WebDriverException = WebDriverException
        cls.selenium = cls._create_driver(webdriver)
        cls.selenium.set_window_size(1440, 1200)
        cls.selenium.set_script_timeout(18)
        cls.wait = WebDriverWait(cls.selenium, 18)

    @classmethod
    def tearDownClass(cls):
        driver = getattr(cls, "selenium", None)
        if driver:
            driver.quit()
        super().tearDownClass()

    @classmethod
    def _create_driver(cls, webdriver):
        errors = []
        for browser_name, options in cls._browser_options():
            try:
                return getattr(webdriver, browser_name)(options=options)
            except Exception as exc:
                errors.append(f"{browser_name}: {exc}")
        raise unittest.SkipTest(f"No Selenium browser driver available. Tried {'; '.join(errors)}")

    @classmethod
    def _browser_options(cls):
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions

        chrome = ChromeOptions()
        for argument in (
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1440,1200",
        ):
            chrome.add_argument(argument)
        chrome_binary = cls._first_existing(
            os.environ.get("CHROME_BINARY", ""),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        )
        if chrome_binary:
            chrome.binary_location = chrome_binary
        chrome.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        edge = EdgeOptions()
        for argument in (
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1440,1200",
        ):
            edge.add_argument(argument)
        edge_binary = cls._first_existing(
            os.environ.get("EDGE_BINARY", ""),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        )
        if edge_binary:
            edge.binary_location = edge_binary
        edge.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        candidates = (("Chrome", chrome), ("Edge", edge))
        preferred = os.environ.get("ALFRED_BROWSER", "").strip().lower()
        if preferred:
            candidates = tuple((name, options) for name, options in candidates if name.lower() == preferred)
            if not candidates:
                raise unittest.SkipTest("ALFRED_BROWSER must be Chrome or Edge for Selenium browser tests.")
        return candidates

    @staticmethod
    def _first_existing(*paths):
        for path in paths:
            if path and Path(path).exists():
                return path
        return ""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="document_browser_user",
            password="Pass12345!",
            monthly_income=95000,
            rent_or_emi=24000,
            city="Bengaluru",
        )
        self.profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            make="Honda",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA03XY9999",
        )
        self.document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            document_type="invoice",
            document_title="jagadamba-mobile-photo-invoice.png",
            parser_status="needs_review",
            parse_confidence=0.36,
            source_text="\n".join(
                [
                    "JAGADAMBA AUTOMOBILES",
                    "Mobile photo service bill",
                    "DATE 31-03-2026",
                    "KM 26021",
                    "Customer Payable 2432.92",
                ]
            ),
            extracted_payload={
                "extraction_method": "rapidocr_mobile_layout",
                "raw_text_excerpt": "DATE 31-03-2026 KM 26021 Customer Payable 2432.92",
                "invoice_review": {"recovered_edge_rows": 1, "compact_ocr_rows": 2},
                "extraction_review": {
                    "field_candidates": [
                        {
                            "field_type": "grand_total",
                            "field_name": "customer_payable",
                            "label": "Customer Payable",
                            "value": "2432.92",
                            "confidence": 0.93,
                            "source": "mobile_ocr",
                            "context": "Customer Payable 2432.92",
                            "page": 1,
                        },
                        {
                            "field_type": "document_date",
                            "field_name": "service_on",
                            "label": "Service On",
                            "value": "2026-03-31",
                            "confidence": 0.89,
                            "source": "mobile_ocr",
                            "context": "DATE 31-03-2026",
                            "page": 1,
                        },
                        {
                            "field_type": "odometer",
                            "field_name": "km",
                            "label": "KM",
                            "value": "26021",
                            "confidence": 0.87,
                            "source": "mobile_ocr",
                            "context": "KM 26021",
                            "page": 1,
                        },
                        {
                            "field_type": "service_center",
                            "field_name": "service_center",
                            "label": "Service Center",
                            "value": "Jagadamba Automobiles",
                            "confidence": 0.85,
                            "source": "mobile_ocr",
                            "context": "JAGADAMBA AUTOMOBILES",
                            "page": 1,
                        },
                    ],
                    "ocr_pages": [
                        {
                            "page": 1,
                            "width": 1000,
                            "height": 1400,
                            "preview": "DATE 31-03-2026 KM 26021 Customer Payable 2432.92",
                            "variant": "unknown_mobile_layout",
                            "regions": [
                                {
                                    "text": "DATE 31-03-2026 KM 26021",
                                    "confidence": 0.43,
                                    "bbox": [[24, 118], [620, 118], [620, 154], [24, 154]],
                                    "origin": "mobile_photo",
                                },
                                {
                                    "text": "Customer Payable 2432.92",
                                    "confidence": 0.4,
                                    "bbox": [[24, 380], [610, 380], [610, 418], [24, 418]],
                                    "origin": "mobile_photo",
                                },
                            ],
                        }
                    ],
                    "recovery_steps": [{"step": "unknown_layout_alias_review", "status": "mapped"}],
                    "attempts": [{"method": "rapidocr_mobile_layout", "quality": 0.72}],
                },
            },
        )
        self.record = BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=self.profile,
            bike_name=self.profile.display_name,
            vehicle_number=self.profile.vehicle_number,
            service_date=date(2026, 3, 20),
            service_center="Unknown Workshop",
            source_document=self.document,
            source_mode="bill_import",
        )

    def tearDown(self):
        self._disable_live_refresh_timers()
        super().tearDown()

    def run(self, result=None):
        if result is None:
            return super().run(result)
        failures_before = len(result.failures)
        errors_before = len(result.errors)
        super().run(result)
        if len(result.failures) > failures_before or len(result.errors) > errors_before:
            self._capture_browser_artifacts()
        return result

    def test_login_statement_upload_vehicle_setup_and_dashboard_refresh_browser_workflow(self):
        self._login_browser()

        self._prove_dashboard_live_refresh()
        self._upload_statement_from_document_center()
        self._submit_vehicle_setup_form()

    def test_vehicle_invoice_overlay_candidate_buttons_fill_and_save_correction(self):
        self._login_browser()
        self._install_review_queue_harness()

        self.wait.until(self.EC.presence_of_element_located((self.By.ID, "documentCenterRoot")))
        self.wait.until(
            lambda driver: "jagadamba-mobile-photo-invoice.png"
            in driver.find_element(self.By.ID, "documentReviewQueue").text
        )
        self._open_review_summary("Review extraction evidence")
        self._open_review_summary("Accept correction")

        self.wait.until(
            lambda driver: len(driver.find_elements(self.By.CSS_SELECTOR, "#documentReviewQueue svg rect")) >= 3
        )
        for field_name, value in (
            ("cost", "2432.92"),
            ("service_date", "2026-03-31"),
            ("odometer_km", "26021"),
            ("service_center", "Jagadamba Automobiles"),
        ):
            self._click_candidate(field_name, value)
            self.assertEqual(self._review_field(field_name).get_attribute("value"), value)

        submit = self.wait.until(
            self.EC.presence_of_element_located(
                (
                    self.By.XPATH,
                    "//*[@id='documentReviewQueue']//form[contains(@id, 'review-form-vehicle_document')]//button[normalize-space()='Save Correction']",
                )
            )
        )
        self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
        self.selenium.execute_script(
            """
            arguments[0].closest("details").open = true;
            window.submitDocumentCorrection(
                { preventDefault: () => {}, currentTarget: arguments[0].form },
                "vehicle_document",
                arguments[1]
            );
            """,
            submit,
            self.document.pk,
        )

        self.wait.until(
            lambda driver: BikeDocument.objects.get(pk=self.document.pk).parser_status == "parsed"
            or driver.execute_script("return Boolean(window.__lastCorrectionError);")
        )
        correction_error = self.selenium.execute_script("return window.__lastCorrectionError || '';")
        if correction_error:
            correction_request = self.selenium.execute_script("return window.__lastCorrectionRequest || '';")
            correction_result = self.selenium.execute_script("return window.__lastCorrectionResult || null;")
            self.fail(
                f"Correction POST failed: {correction_error}; request={correction_request}; result={correction_result}"
            )
        self.wait.until(
            lambda driver: "No low-confidence uploads are waiting for review right now."
            in driver.find_element(self.By.ID, "documentReviewQueue").text
        )

        self.document.refresh_from_db()
        self.record.refresh_from_db()
        service_payload = self.document.extracted_payload["service_payload"]
        self.assertEqual(service_payload["service_center"], "Jagadamba Automobiles")
        self.assertEqual(service_payload["service_date"], "2026-03-31")
        self.assertEqual(service_payload["odometer_km"], 26021)
        self.assertAlmostEqual(service_payload["cost"], 2432.92)
        self.assertEqual(self.record.service_center, "Jagadamba Automobiles")
        self.assertEqual(str(self.record.service_date), "2026-03-31")
        self.assertEqual(self.record.odometer_km, 26021)
        self.assertAlmostEqual(self.record.cost, 2432.92)
        self.assertEqual(
            self.record.parsed_payload["review_trace"]["accepted_corrections"]["service_center"],
            "Jagadamba Automobiles",
        )

    def test_statement_review_candidate_buttons_fill_and_save_correction(self):
        self.statement_upload = self._create_unknown_statement_upload()
        self._login_browser()
        self._install_review_queue_harness()

        self.wait.until(self.EC.presence_of_element_located((self.By.ID, "documentCenterRoot")))
        self.wait.until(
            lambda driver: "unknown-layout-bank-statement.pdf"
            in driver.find_element(self.By.ID, "documentReviewQueue").text
        )
        self._open_review_summary("Review extraction evidence")
        self._open_review_summary("Accept correction")

        for field_name, value in (
            ("bank_name", "HDFC Bank"),
            ("account_holder", "Selenium User"),
            ("account_number", "50100244137504"),
            ("statement_start", "2026-03-01"),
            ("statement_end", "2026-03-31"),
        ):
            self._click_candidate(field_name, value)
            self.assertEqual(
                self._review_field(field_name, scope="statement_document").get_attribute("value"),
                value,
            )

        submit = self.wait.until(
            self.EC.presence_of_element_located(
                (
                    self.By.XPATH,
                    "//*[@id='documentReviewQueue']//form[contains(@id, 'review-form-statement_document')]//button[normalize-space()='Save Correction']",
                )
            )
        )
        self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
        self.selenium.execute_script(
            """
            arguments[0].closest("details").open = true;
            window.submitDocumentCorrection(
                { preventDefault: () => {}, currentTarget: arguments[0].form },
                "statement_document",
                arguments[1]
            );
            """,
            submit,
            self.statement_upload.pk,
        )

        self.wait.until(
            lambda driver: StatementUpload.objects.get(pk=self.statement_upload.pk).parser_status == "parsed"
            or driver.execute_script("return Boolean(window.__lastCorrectionError);")
        )
        correction_error = self.selenium.execute_script("return window.__lastCorrectionError || '';")
        if correction_error:
            correction_request = self.selenium.execute_script("return window.__lastCorrectionRequest || '';")
            correction_result = self.selenium.execute_script("return window.__lastCorrectionResult || null;")
            self.fail(
                f"Statement correction POST failed: {correction_error}; request={correction_request}; result={correction_result}"
            )

        self.statement_upload.refresh_from_db()
        accepted = self.statement_upload.extracted_payload["accepted_corrections"]
        self.assertEqual(self.statement_upload.bank_name, "HDFC Bank")
        self.assertEqual(self.statement_upload.account_holder, "Selenium User")
        self.assertEqual(self.statement_upload.account_number, "50100244137504")
        self.assertEqual(str(self.statement_upload.statement_start), "2026-03-01")
        self.assertEqual(str(self.statement_upload.statement_end), "2026-03-31")
        self.assertTrue(self.statement_upload.extracted_payload["review_queue_resolved"])
        self.assertEqual(accepted["bank_name"], "HDFC Bank")

        memory = DocumentParserLearningMemory.objects.get(
            scope="statement_document",
            last_resolution="accepted_correction",
        )
        self.assertTrue(
            {"bank_name", "account_holder", "account_number", "statement_start", "statement_end"}.issubset(
                set(memory.accepted_field_hints)
            )
        )

    def _create_unknown_statement_upload(self):
        return StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="unknown-layout-bank-statement.pdf",
            parser_status="needs_review",
            parse_confidence=0.22,
            imported_count=1,
            extracted_payload={
                "extraction_method": "rapidocr_unknown_statement_layout",
                "raw_text_excerpt": (
                    "HDFC Bank Statement Selenium User AC 50100244137504 "
                    "Period 01-03-2026 to 31-03-2026"
                ),
                "extraction_review": {
                    "field_candidates": [
                        {
                            "field_type": "institution",
                            "field_name": "bank",
                            "label": "Institution",
                            "value": "HDFC Bank",
                            "confidence": 0.83,
                            "source": "unknown_statement_ocr",
                            "context": "HDFC Bank Statement",
                            "page": 1,
                        },
                        {
                            "field_type": "holder",
                            "field_name": "holder",
                            "label": "Holder",
                            "value": "Selenium User",
                            "confidence": 0.79,
                            "source": "unknown_statement_ocr",
                            "context": "Statement Selenium User",
                            "page": 1,
                        },
                        {
                            "field_type": "account no",
                            "field_name": "acct-no",
                            "label": "AC",
                            "value": "50100244137504",
                            "confidence": 0.76,
                            "source": "unknown_statement_ocr",
                            "context": "AC 50100244137504",
                            "page": 1,
                        },
                        {
                            "field_type": "from date",
                            "field_name": "period start",
                            "label": "Period Start",
                            "value": "2026-03-01",
                            "confidence": 0.74,
                            "source": "unknown_statement_ocr",
                            "context": "Period 01-03-2026",
                            "page": 1,
                        },
                        {
                            "field_type": "to date",
                            "field_name": "period end",
                            "label": "Period End",
                            "value": "2026-03-31",
                            "confidence": 0.74,
                            "source": "unknown_statement_ocr",
                            "context": "to 31-03-2026",
                            "page": 1,
                        },
                    ],
                    "ocr_pages": [
                        {
                            "page": 1,
                            "width": 1000,
                            "height": 1400,
                            "preview": "HDFC Bank Statement Selenium User AC 50100244137504",
                            "variant": "unknown_statement_layout",
                            "regions": [
                                {
                                    "text": "HDFC Bank Statement Selenium User",
                                    "confidence": 0.42,
                                    "bbox": [[30, 95], [780, 95], [780, 135], [30, 135]],
                                    "origin": "mobile_photo",
                                },
                                {
                                    "text": "AC 50100244137504 Period 01-03-2026 to 31-03-2026",
                                    "confidence": 0.39,
                                    "bbox": [[32, 180], [880, 180], [880, 226], [32, 226]],
                                    "origin": "mobile_photo",
                                },
                            ],
                        }
                    ],
                    "recovery_steps": [{"step": "cross_family_unknown_layout", "status": "mapped"}],
                    "attempts": [{"method": "rapidocr_unknown_statement_layout", "quality": 0.66}],
                },
            },
        )

    def _login_browser(self):
        self.selenium.get(f"{self.live_server_url}/login/")
        self.selenium.delete_all_cookies()
        self.selenium.get(f"{self.live_server_url}/login/?next=/login/")
        self.wait.until(self.EC.presence_of_element_located((self.By.ID, "id_username"))).send_keys(self.user.username)
        self.selenium.find_element(self.By.ID, "id_password").send_keys("Pass12345!")
        self.selenium.find_element(self.By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(lambda driver: driver.execute_script("return document.body.dataset.authenticated") == "true")
        self._install_authenticated_session_cookie()

    def _install_authenticated_session_cookie(self):
        client = Client()
        client.force_login(self.user)
        self.selenium.get(f"{self.live_server_url}/dashboard/")
        self.selenium.add_cookie(
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
                "path": "/",
            }
        )
        self.selenium.get(f"{self.live_server_url}/dashboard/")
        self.wait.until(lambda driver: driver.execute_script("return document.body.dataset.authenticated") == "true")

    def _prove_dashboard_live_refresh(self):
        self.selenium.get(f"{self.live_server_url}/dashboard/")
        self.wait.until(self.EC.presence_of_element_located((self.By.ID, "dashboardRoot")))
        self.wait.until(lambda driver: driver.execute_script("return Boolean(window.Alfred && window.loadDashboard);"))

        result = self.selenium.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            window.Chart = window.Chart || function() {
                this.destroy = function() {};
            };
            const originalFetchJSON = window.Alfred.fetchJSON;
            const urls = [];
            window.Alfred.fetchJSON = function(url, options = {}) {
                urls.push(String(url));
                return originalFetchJSON(url, options);
            };
            Promise.resolve(window.loadDashboard({ live: true }))
                .then(() => done({
                    ok: true,
                    urls,
                    healthScore: document.getElementById("healthScoreValue")?.textContent || "",
                }))
                .catch(error => done({ ok: false, error: error.message || String(error), urls }));
            """
        )
        self.assertTrue(result["ok"], result)
        self.assertIn("/api/expenses/dashboard/", result["urls"])
        self.wait.until(lambda driver: driver.find_element(self.By.ID, "dashboardRoot").is_displayed())

    def _upload_statement_from_document_center(self):
        self._install_statement_upload_harness()

        upload_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as statement:
                statement.write(b"%PDF-1.7 truncated browser statement")
                upload_path = statement.name

            self.Select(self.selenium.find_element(self.By.ID, "documentStatementKind")).select_by_value("bank_statement")
            self.selenium.find_element(self.By.ID, "documentStatementFile").send_keys(upload_path)
            submit = self.selenium.find_element(self.By.CSS_SELECTOR, "#documentStatementForm button[type='submit']")
            self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
            try:
                submit.click()
            except self.WebDriverException:
                self.selenium.execute_script("arguments[0].click();", submit)

            file_name = Path(upload_path).name
            self.wait.until(lambda driver: StatementUpload.objects.filter(user=self.user, file_name=file_name).exists())
            upload = StatementUpload.objects.get(user=self.user, file_name=file_name)
            self.assertIn(upload.parser_status, {"parsed", "needs_review", "failed"})
        finally:
            if upload_path:
                try:
                    Path(upload_path).unlink(missing_ok=True)
                except PermissionError:
                    pass

    def _install_statement_upload_harness(self):
        self.wait.until(lambda driver: driver.execute_script("return Boolean(window.Alfred)"))
        self.selenium.execute_script(
            """
            document.body.innerHTML = `
                <main class="container-fluid alfred-layout">
                    <section id="documentCenterRoot"></section>
                    <form id="documentStatementForm" class="soft-grid" enctype="multipart/form-data">
                        <select id="documentStatementKind" name="statement_kind" class="form-select">
                            <option value="">Auto detect</option>
                            <option value="bank_statement">Bank Statement</option>
                            <option value="credit_card_statement">Credit Card Statement</option>
                            <option value="loan_statement">Loan Statement</option>
                            <option value="investment_statement">Investment Statement</option>
                            <option value="other_statement">Other Statement</option>
                        </select>
                        <input id="documentStatementFile" name="statement" type="file" class="form-control" accept=".pdf,application/pdf" multiple required>
                        <div id="documentStatementFeedback" class="d-none alert mb-0"></div>
                        <button class="btn btn-primary" type="submit">Upload Statements</button>
                    </form>
                </main>
            `;
            window.__statementUploadHarnessReady = false;
            window.__statementUploadHarnessError = "";
            const installHarness = () => {
                try {
                    window.loadDocumentCenter = function() {
                        window.__statementUploadRefreshCalled = true;
                        return Promise.resolve();
                    };
                    const handler = window.submitStatementUpload || submitStatementUpload;
                    document.getElementById("documentStatementForm").addEventListener("submit", handler);
                    window.__statementUploadHarnessReady = true;
                } catch (error) {
                    window.__statementUploadHarnessError = error.message || String(error);
                }
            };
            if (typeof submitStatementUpload === "function") {
                installHarness();
            } else {
                const script = document.createElement("script");
                script.src = "/static/js/documents.js?v=2.3";
                script.onload = installHarness;
                script.onerror = () => { window.__statementUploadHarnessError = "documents.js failed to load"; };
                document.head.appendChild(script);
            }
            """
        )
        self.wait.until(
            lambda driver: driver.execute_script(
                "return window.__statementUploadHarnessReady === true || Boolean(window.__statementUploadHarnessError);"
            )
        )
        error = self.selenium.execute_script("return window.__statementUploadHarnessError || '';")
        if error:
            self.fail(error)

    def _submit_vehicle_setup_form(self):
        self.selenium.get(f"{self.live_server_url}/bike-service/")
        self.wait.until(self.EC.presence_of_element_located((self.By.ID, "bikeProfileForm")))
        self.wait.until(lambda driver: driver.execute_script("return Boolean(window.Alfred && window.submitBikeProfile);"))
        self.selenium.execute_script("window.Alfred.disableLiveRefresh && window.Alfred.disableLiveRefresh('bike-service-live');")

        display_name = "Selenium Honda Dio"
        self.Select(self.selenium.find_element(self.By.ID, "bikeProfileVehicleType")).select_by_value("scooter")
        self._replace_field("bikeCatalogMakeSelect", "Honda")
        self._replace_field("bikeProfileDisplayName", display_name)
        self._replace_field("bikeProfileModelName", "Dio")
        self._replace_field("bikeProfileVehicleNumber", "KA05BR1234")
        self.Select(self.selenium.find_element(self.By.ID, "bikeProfileClass")).select_by_value("scooter")
        self._replace_field("bikeProfileMileage", "48")

        submit = self.selenium.find_element(self.By.ID, "bikeProfileSubmit")
        self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
        try:
            submit.click()
        except self.WebDriverException:
            self.selenium.execute_script("arguments[0].click();", submit)

        self.wait.until(lambda driver: BikeProfile.objects.filter(user=self.user, display_name=display_name).exists())
        profile = BikeProfile.objects.get(user=self.user, display_name=display_name)
        self.assertEqual(profile.make, "Honda")
        self.assertEqual(profile.model_name, "Dio")
        self.assertEqual(profile.vehicle_type, "scooter")

    def _replace_field(self, element_id, value):
        element = self.wait.until(self.EC.presence_of_element_located((self.By.ID, element_id)))
        element.clear()
        element.send_keys(value)

    def _capture_browser_artifacts(self):
        driver = getattr(self, "selenium", None)
        if not driver:
            return

        artifact_dir = Path(os.environ.get("ALFRED_BROWSER_ARTIFACT_DIR", "artifacts/browser"))
        if not artifact_dir.is_absolute():
            artifact_dir = Path.cwd() / artifact_dir
        artifact_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in self.id())[-150:]
        stem = f"{timestamp}-{safe_name}"
        notes = []

        try:
            driver.save_screenshot(str(artifact_dir / f"{stem}.png"))
        except Exception as exc:
            notes.append(f"screenshot failed: {exc}")

        try:
            (artifact_dir / f"{stem}.html").write_text(driver.page_source or "", encoding="utf-8")
        except Exception as exc:
            notes.append(f"page source failed: {exc}")

        try:
            browser_logs = driver.get_log("browser")
            (artifact_dir / f"{stem}.browser.log").write_text(
                "\n".join(json.dumps(item, sort_keys=True) for item in browser_logs),
                encoding="utf-8",
            )
        except Exception as exc:
            notes.append(f"browser log unavailable: {exc}")

        metadata = {
            "test": self.id(),
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "current_url": "",
            "title": "",
            "notes": notes,
        }
        try:
            metadata["current_url"] = driver.current_url
            metadata["title"] = driver.title
        except Exception as exc:
            metadata["notes"].append(f"metadata failed: {exc}")
        try:
            (artifact_dir / f"{stem}.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            return

    def _disable_live_refresh_timers(self):
        driver = getattr(self, "selenium", None)
        if not driver:
            return
        try:
            driver.execute_script(
                """
                if (window.Alfred && window.Alfred.disableLiveRefresh) {
                    [
                        "dashboard-live",
                        "documents-live",
                        "bike-service-live",
                        "project-details-live",
                        "expenses-live",
                    ].forEach(key => window.Alfred.disableLiveRefresh(key));
                }
                """
            )
        except Exception:
            return

    def _install_review_queue_harness(self):
        self.wait.until(lambda driver: driver.execute_script("return Boolean(window.Alfred)"))
        self.selenium.execute_script(
            """
            document.body.innerHTML = `
                <main class="container-fluid alfred-layout">
                    <section id="documentCenterRoot"></section>
                    <section id="documentReviewQueue"></section>
                </main>
            `;
            window.__alfredReviewQueueLoaded = false;
            window.__alfredReviewQueueError = "";
            window.__lastCorrectionRequest = "";
            window.__lastCorrectionResult = null;
            window.__lastCorrectionError = "";
            const originalFetchJSON = window.Alfred.fetchJSON;
            window.Alfred.fetchJSON = function(url, options = {}) {
                const isCorrection = url === "/api/documents/review-queue/resolve/";
                if (isCorrection) {
                    window.__lastCorrectionRequest = options.body || "";
                    window.__lastCorrectionError = "";
                    window.__lastCorrectionResult = null;
                }
                return originalFetchJSON(url, options)
                    .then(data => {
                        if (isCorrection) {
                            window.__lastCorrectionResult = data;
                        }
                        return data;
                    })
                    .catch(error => {
                        if (isCorrection) {
                            window.__lastCorrectionError = error.message || String(error);
                        }
                        throw error;
                    });
            };
            const loadReviewQueueOnly = () => {
                window.loadDocumentCenter = function() {
                    return window.Alfred.fetchJSON("/api/documents/review-queue/")
                        .then(data => {
                            window.renderReviewQueue(data.results || []);
                            return data;
                        });
                };
                window.loadDocumentCenter()
                    .then(() => { window.__alfredReviewQueueLoaded = true; })
                    .catch(error => { window.__alfredReviewQueueError = error.message || String(error); });
            };
            if (window.renderReviewQueue) {
                loadReviewQueueOnly();
            } else {
                const script = document.createElement("script");
                script.src = "/static/js/documents.js?v=2.3";
                script.onload = loadReviewQueueOnly;
                script.onerror = () => { window.__alfredReviewQueueError = "documents.js failed to load"; };
                document.head.appendChild(script);
            }
            """
        )
        self.wait.until(
            lambda driver: driver.execute_script(
                "return window.__alfredReviewQueueLoaded === true || Boolean(window.__alfredReviewQueueError);"
            )
        )
        error = self.selenium.execute_script("return window.__alfredReviewQueueError || '';")
        if error:
            self.fail(error)

    def _open_review_summary(self, label):
        last_error = None
        for _attempt in range(5):
            try:
                summary = self.wait.until(
                    self.EC.presence_of_element_located(
                        (self.By.XPATH, f"//*[@id='documentReviewQueue']//summary[normalize-space()='{label}']")
                    )
                )
                self.selenium.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'}); arguments[0].closest('details').open = true;",
                    summary,
                )
                return
            except (self.StaleElementReferenceException, self.WebDriverException) as exc:
                last_error = exc
        if last_error:
            raise last_error

    def _click_candidate(self, field_name, value):
        last_error = None
        for _attempt in range(5):
            try:
                self.wait.until(
                    lambda driver: len(
                        driver.find_elements(self.By.CSS_SELECTOR, "#documentReviewQueue button[data-field-name]")
                    )
                    > 0
                )
                button = self.selenium.find_element(
                    self.By.CSS_SELECTOR,
                    f'#documentReviewQueue button[data-field-name="{field_name}"][data-field-value="{value}"]',
                )
                self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                try:
                    button.click()
                except self.WebDriverException:
                    self.selenium.execute_script("arguments[0].click();", button)
                return
            except (self.StaleElementReferenceException, self.WebDriverException) as exc:
                last_error = exc
        available = self.selenium.execute_script(
            """
            return Array.from(document.querySelectorAll("#documentReviewQueue button[data-field-name]")).map(button => ({
                field: button.dataset.fieldName,
                value: button.dataset.fieldValue,
                text: button.textContent.trim(),
                visible: Boolean(button.offsetWidth || button.offsetHeight || button.getClientRects().length),
            }));
            """
        )
        if last_error:
            raise AssertionError(
                f"Could not click candidate {field_name}={value}. Available buttons: {available}"
            ) from last_error

    def _review_field(self, field_name, *, scope="vehicle_document"):
        return self.wait.until(
            self.EC.presence_of_element_located(
                (
                    self.By.CSS_SELECTOR,
                    f'#documentReviewQueue form[id^="review-form-{scope}"] [name="{field_name}"]',
                )
            )
        )
