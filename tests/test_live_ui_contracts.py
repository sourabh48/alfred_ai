from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client


REPO_ROOT = Path(__file__).resolve().parents[1]


class _AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.named_controls = []
        self.forms = []
        self.buttons = []
        self.static_assets = set()
        self.progress_bars = []
        self._current_form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "form":
            form = {
                "id": attrs.get("id", ""),
                "method": attrs.get("method", "").lower(),
                "action": attrs.get("action", ""),
                "enctype": attrs.get("enctype", ""),
                "data_live_refresh_hold": attrs.get("data-live-refresh-hold", ""),
                "controls": [],
                "buttons": [],
            }
            self.forms.append(form)
            self._current_form = form
        if tag in {"input", "select", "textarea"} and attrs.get("name"):
            control = {
                "tag": tag,
                "id": attrs.get("id", ""),
                "name": attrs.get("name", ""),
                "type": attrs.get("type", ""),
                "accept": attrs.get("accept", ""),
                "list": attrs.get("list", ""),
                "disabled": "disabled" in attrs,
                "multiple": "multiple" in attrs,
                "required": "required" in attrs,
            }
            self.named_controls.append(control)
            if self._current_form is not None:
                self._current_form["controls"].append(control)
        if tag == "button":
            button = {
                "id": attrs.get("id", ""),
                "type": attrs.get("type", ""),
            }
            self.buttons.append(button)
            if self._current_form is not None:
                self._current_form["buttons"].append(button)
        classes = set(attrs.get("class", "").split())
        if "progress-bar" in classes:
            self.progress_bars.append(attrs)
        for key in ("src", "href"):
            value = attrs.get(key, "")
            if value.startswith("/static/"):
                self.static_assets.add(value.split("?", 1)[0])

    def handle_endtag(self, tag):
        if tag == "form":
            self._current_form = None


class LiveUIRegressionTests(StaticLiveServerTestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="live_ui_user",
            password="Pass12345!",
            monthly_income=95000,
            rent_or_emi=24000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.session_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.superuser = user_model.objects.create_superuser(
            username="live_ui_admin",
            password="Pass12345!",
            email="live-ui-admin@example.com",
        )

    def test_authenticated_pages_render_over_live_http_with_static_assets(self):
        pages = [
            ("/dashboard/", ["dashboardRoot"]),
            ("/documents/", ["documentCenterRoot"]),
            ("/expenses/", ["expenseRoot"]),
            ("/career/", ["careerRoot"]),
            ("/mobility/", ["mobilityRoot"]),
            ("/bike-service/", ["bikeServiceRoot", "bikeRouteWearPanel"]),
            ("/recommendations/", ["recommendationsRoot"]),
        ]

        checked_assets = set()
        for path, expected_ids in pages:
            with self.subTest(path=path):
                html = self._fetch_text(path)
                parser = _AssetParser()
                parser.feed(html)

                self.assertIn("alfredMainScroll", parser.ids)
                for root_id in expected_ids:
                    self.assertIn(root_id, parser.ids)
                self.assertIn("/static/css/style.css", parser.static_assets)
                self.assertIn("/static/js/app.js", parser.static_assets)
                self.assertNotIn("TemplateDoesNotExist", html)
                self.assertNotIn("Traceback", html)

                for asset_path in sorted(parser.static_assets):
                    if asset_path in checked_assets:
                        continue
                    checked_assets.add(asset_path)
                    asset_body = self._fetch_bytes(asset_path)
                    self.assertGreater(len(asset_body), 20, asset_path)

    def test_project_details_progress_bars_render_over_live_http(self):
        admin_client = Client()
        admin_client.force_login(self.superuser)
        admin_session_cookie = admin_client.cookies[settings.SESSION_COOKIE_NAME].value

        html = self._fetch_text("/project-details/", session_cookie=admin_session_cookie)
        parser = _AssetParser()
        parser.feed(html)

        self.assertIn("projectDetailsRoot", parser.ids)
        self.assertIn("projectDetailsOverallProgressBar", parser.ids)
        self.assertIn("projectDetailsCompletedTracks", parser.ids)
        self.assertIn("/static/js/project_details.js", parser.static_assets)
        self.assertGreaterEqual(len(parser.progress_bars), 1)
        for attrs in parser.progress_bars:
            with self.subTest(attrs=attrs):
                value = int(attrs["aria-valuenow"])
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100)
                self.assertIn(f"width: {value}%", attrs.get("style", ""))

    def test_login_form_contract_is_live_server_rendered(self):
        html = self._fetch_text("/login/", session_cookie="")
        parser = _AssetParser()
        parser.feed(html)

        self.assertIn("id_username", parser.ids)
        self.assertIn("id_password", parser.ids)
        login_form = self._form_with_controls(parser, {"username", "password", "csrfmiddlewaretoken"})
        self.assertEqual(login_form["method"], "post")
        self.assertTrue(any(button["type"] in {"", "submit"} for button in login_form["buttons"]))
        self.assertIn("/static/js/app.js", parser.static_assets)

    def test_dashboard_live_refresh_contract_uses_real_api_and_waitable_root(self):
        html = self._fetch_text("/dashboard/")
        parser = _AssetParser()
        parser.feed(html)

        for element_id in (
            "dashboardRoot",
            "healthScoreRing",
            "dashboardSummaryCards",
            "dashboardRecentTransactions",
        ):
            self.assertIn(element_id, parser.ids)
        self.assertIn("/static/js/dashboard.js", parser.static_assets)

        script = self._fetch_text("/static/js/dashboard.js")
        self.assertIn('Alfred.enableLiveRefresh("dashboard-live", loadDashboard, { rootId: "dashboardRoot" })', script)
        self.assertIn('Alfred.setPageBusy("dashboardRoot", true', script)
        self.assertIn('Alfred.fetchJSON("/api/expenses/dashboard/")', script)

    def test_statement_upload_contracts_cover_documents_and_expenses_paths(self):
        documents_html = self._fetch_text("/documents/")
        documents_parser = _AssetParser()
        documents_parser.feed(documents_html)
        statement_form = self._form_by_id(documents_parser, "documentStatementForm")

        self.assertEqual(statement_form["enctype"], "multipart/form-data")
        self.assertEqual(
            {"statement_kind", "statement"},
            {control["name"] for control in statement_form["controls"]},
        )
        statement_file = self._control_by_name(statement_form, "statement")
        self.assertEqual(statement_file["id"], "documentStatementFile")
        self.assertEqual(statement_file["type"], "file")
        self.assertTrue(statement_file["multiple"])
        self.assertTrue(statement_file["required"])
        self.assertIn("application/pdf", statement_file["accept"])

        documents_script = self._fetch_text("/static/js/documents.js")
        self.assertIn('document.getElementById("documentStatementForm").addEventListener("submit", submitStatementUpload)', documents_script)
        self.assertIn('Alfred.uploadJSON("/api/expenses/import-statement/"', documents_script)
        self.assertIn('Alfred.buildSingleFileFormData(form, fileFieldName, file)', documents_script)

        expenses_html = self._fetch_text("/expenses/")
        expenses_parser = _AssetParser()
        expenses_parser.feed(expenses_html)
        for element_id in ("statementFile", "statementKind", "uploadStatementBtn", "statementUploadStatus"):
            self.assertIn(element_id, expenses_parser.ids)

        expenses_script = self._fetch_text("/static/js/expenses.js")
        self.assertIn('document.getElementById("uploadStatementBtn").addEventListener("click", uploadStatement)', expenses_script)
        self.assertIn('Alfred.uploadJSON("/api/expenses/import-statement/"', expenses_script)
        self.assertIn('formData.append("statement", file)', expenses_script)

    def test_core_form_submission_contracts_pin_expense_document_and_vehicle_workflows(self):
        documents_html = self._fetch_text("/documents/")
        documents_parser = _AssetParser()
        documents_parser.feed(documents_html)
        document_forms = {
            "documentLoanForm": {"file"},
            "documentVehicleForm": {"bike_profile_id", "document_type_override", "document_file"},
            "documentServiceForm": {"bike_profile_id", "service_file"},
            "documentResumeForm": {"resume"},
            "documentCreditForm": {"bureau", "report"},
            "documentChatGPTImportForm": {"title", "import_type", "source_label", "raw_text"},
        }
        for form_id, expected_controls in document_forms.items():
            with self.subTest(form=form_id):
                form = self._form_by_id(documents_parser, form_id)
                self.assertTrue(expected_controls.issubset({control["name"] for control in form["controls"]}))

        documents_script = self._fetch_text("/static/js/documents.js")
        for expected in (
            'document.getElementById("documentLoanForm").addEventListener("submit", submitLoanUpload)',
            'document.getElementById("documentVehicleForm").addEventListener("submit", submitVehicleDocument)',
            'document.getElementById("documentServiceForm").addEventListener("submit", submitServiceDocument)',
            'document.getElementById("documentResumeForm").addEventListener("submit", submitResumeDocument)',
            'document.getElementById("documentCreditForm").addEventListener("submit", submitCreditDocument)',
            'document.getElementById("documentChatGPTImportForm").addEventListener("submit", submitChatGPTImport)',
            'Alfred.uploadJSON("/api/loans/import-pdf/"',
            'Alfred.uploadJSON("/api/mobility/bike-documents/upload/"',
            'Alfred.uploadJSON("/api/mobility/bike-services/import/"',
            'Alfred.uploadJSON("/api/career/resumes/upload/"',
            'Alfred.uploadJSON("/api/integrations/credit-score/upload-report/"',
            'Alfred.fetchJSON("/api/reports/chatgpt-imports/"',
        ):
            self.assertIn(expected, documents_script)

        expenses_html = self._fetch_text("/expenses/")
        expenses_parser = _AssetParser()
        expenses_parser.feed(expenses_html)
        expense_form = self._form_by_id(expenses_parser, "expenseForm")
        timeline_form = self._form_by_id(expenses_parser, "timelineFilterForm")
        self.assertTrue(
            {"transaction_date", "classification", "category", "amount", "direction", "merchant", "source"}.issubset(
                {control["name"] for control in expense_form["controls"]}
            )
        )
        self.assertEqual(timeline_form["data_live_refresh_hold"], "true")
        self.assertTrue({"q", "transaction_id", "classification", "source", "limit"}.issubset({control["name"] for control in timeline_form["controls"]}))

        expenses_script = self._fetch_text("/static/js/expenses.js")
        self.assertIn('document.getElementById("expenseForm").addEventListener("submit", submitExpenseForm)', expenses_script)
        self.assertIn('document.getElementById("timelineFilterForm").addEventListener("submit", applyTimelineFilters)', expenses_script)
        self.assertIn('Alfred.enableLiveRefresh("expenses-live", refreshExpenseWorkspace, { rootId: "expenseRoot" })', expenses_script)
        self.assertIn('const url = expenseId ? `/api/expenses/${expenseId}/` : "/api/expenses/";', expenses_script)

        bike_html = self._fetch_text("/bike-service/")
        bike_parser = _AssetParser()
        bike_parser.feed(bike_html)
        bike_forms = {
            "bikeProfileForm": {"vehicle_type", "make", "display_name", "model_name", "vehicle_number", "bike_class"},
            "bikeServiceRecordForm": {"bike_profile", "bike_name", "vehicle_number", "service_date", "odometer_km", "service_type", "cost"},
            "bikeRefillForm": {"bike_profile", "refill_date", "trip_meter_km", "fuel_liters", "total_cost"},
            "bikeIssueForm": {"title", "system", "severity", "status", "reported_at", "symptom"},
            "bikeDocumentForm": {"bike_profile_id", "document_type_override", "document_file"},
            "bikeConditionForm": {"bike_profile", "captured_at", "engine_status", "brake_status", "tyre_status", "overall_status"},
        }
        for form_id, expected_controls in bike_forms.items():
            with self.subTest(form=form_id):
                form = self._form_by_id(bike_parser, form_id)
                self.assertTrue(expected_controls.issubset({control["name"] for control in form["controls"]}))

        bike_script = self._fetch_text("/static/js/bike_service.js")
        for expected in (
            'document.getElementById("bikeProfileForm").addEventListener("submit", submitBikeProfile)',
            'document.getElementById("bikeServiceRecordForm").addEventListener("submit", submitBikeServiceRecord)',
            'document.getElementById("bikeRefillForm").addEventListener("submit", submitBikeRefill)',
            'document.getElementById("bikeIssueForm").addEventListener("submit", submitBikeIssue)',
            'document.getElementById("bikeDocumentForm").addEventListener("submit", submitBikeDocumentUpload)',
            'document.getElementById("bikeConditionForm").addEventListener("submit", submitBikeCondition)',
            'Alfred.enableLiveRefresh("bike-service-live", loadBikeServiceDashboard, { rootId: "bikeServiceRoot", interactionHoldMs: 4500 })',
            '"/api/mobility/bikes/"',
            'Alfred.fetchJSON("/api/mobility/bike-services/"',
            'Alfred.fetchJSON("/api/mobility/bike-refills/"',
            'Alfred.fetchJSON("/api/mobility/bike-issues/"',
            'Alfred.fetchJSON("/api/mobility/bike-conditions/"',
        ):
            self.assertIn(expected, bike_script)

    def test_browser_regression_runner_and_ci_job_are_wired_to_selenium_suite(self):
        runner = (REPO_ROOT / "scripts" / "run_browser_regressions.py").read_text(encoding="utf-8")
        workflow = (REPO_ROOT / ".github" / "workflows" / "browser-regression.yml").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        browser_tests = (REPO_ROOT / "tests" / "test_document_review_browser.py").read_text(encoding="utf-8")

        self.assertIn('"ALFRED_RUN_BROWSER_TESTS"] = "true"', runner)
        self.assertIn("tests.test_document_review_browser", runner)
        self.assertIn("ALFRED_BROWSER_ARTIFACT_DIR", runner)
        self.assertIn("--require-browser", runner)
        self.assertIn("skipped_count", runner)
        self.assertIn("driver_backed_success", runner)
        self.assertIn("runner_return_code", runner)
        self.assertIn("browser_regression_summary.json", runner)
        self.assertIn("tests_run_count", runner)
        self.assertIn("proof_label", runner)
        self.assertIn("github_actions_metadata", runner)
        self.assertIn("github_actions", runner)
        self.assertIn("artifact_contract", runner)
        self.assertIn("failure_artifact_suffixes", runner)

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn(".github/workflows/browser-regression.yml", workflow)
        self.assertIn("tests/test_browser_regression_runner.py", workflow)
        self.assertIn("scripts/run_browser_regressions.py --browser Chrome --require-browser --proof-label ci-chrome", workflow)
        self.assertIn('ALFRED_RUN_BROWSER_TESTS: "true"', workflow)
        self.assertIn("browser-actions/setup-chrome", workflow)
        self.assertIn("Validate CI browser proof summary", workflow)
        self.assertIn("artifacts/browser/browser_regression_summary.ci-chrome.json", workflow)
        self.assertIn("github.get(\"enabled\") is True", workflow)
        self.assertIn('payload.get("skipped_count") == 0', workflow)
        self.assertIn("actions/upload-artifact", workflow)
        self.assertIn("artifacts/browser", workflow)
        self.assertIn("if-no-files-found: error", workflow)

        self.assertIn("python scripts/run_browser_regressions.py --browser Chrome --require-browser", readme)
        self.assertIn("browser_regression_summary.json", readme)
        self.assertIn("ALFRED_RUN_BROWSER_TESTS=true", readme)
        self.assertIn("ALFRED_BROWSER_ARTIFACT_DIR", browser_tests)
        self.assertIn("save_screenshot", browser_tests)
        self.assertIn(".html", browser_tests)
        self.assertIn(".browser.log", browser_tests)
        self.assertIn('get_log("browser")', browser_tests)

    def test_vehicle_setup_has_single_make_control_and_brand_filtered_model_picker(self):
        html = self._fetch_text("/bike-service/")
        parser = _AssetParser()
        parser.feed(html)

        make_controls = [item for item in parser.named_controls if item["name"] == "make"]
        self.assertEqual(len(make_controls), 1)
        self.assertEqual(make_controls[0]["id"], "bikeCatalogMakeSelect")
        self.assertEqual(make_controls[0]["tag"], "input")
        self.assertEqual(make_controls[0]["list"], "bikeCatalogMakeOptions")
        self.assertIn("bikeCatalogSelect", parser.ids)
        self.assertIn("bikeCatalogMakeOptions", parser.ids)
        self.assertIn("/static/js/bike_service.js", parser.static_assets)

        script = self._fetch_text("/static/js/bike_service.js")
        self.assertIn("BIKE_CATALOG_INTERACTION_HOLD_MS", script)
        self.assertIn("isBikeCatalogInteractionActive", script)
        self.assertIn("bikeCatalogFetchToken", script)
        self.assertIn("profileEditorLocked", script)
        self.assertIn("hydrateModels: false", script)

        dashboard_refresh_block = script[
            script.index("function loadBikeServiceDashboard"):
            script.index("function renderBikeServiceHero")
        ]
        self.assertNotIn("bikeState.catalogRequestKey = \"\";", dashboard_refresh_block)
        self.assertNotIn("bikeState.catalog = data.bike_catalog", dashboard_refresh_block)
        self.assertNotIn("hydrateBikeCatalog(", dashboard_refresh_block)

    def test_document_center_exposes_chatgpt_import_provision(self):
        html = self._fetch_text("/documents/")
        parser = _AssetParser()
        parser.feed(html)

        self.assertIn("documentChatGPTImportForm", parser.ids)
        self.assertIn("documentChatGPTRawText", parser.ids)
        self.assertIn("documentChatGPTImportList", parser.ids)
        self.assertIn("/static/js/documents.js", parser.static_assets)

        script = self._fetch_text("/static/js/documents.js")
        self.assertIn("/api/reports/chatgpt-imports/", script)
        self.assertIn("submitChatGPTImport", script)
        self.assertIn("renderChatGPTImports", script)

    def test_document_review_ui_exposes_ocr_overlay_and_candidate_correction_controls(self):
        html = self._fetch_text("/documents/")
        parser = _AssetParser()
        parser.feed(html)

        self.assertIn("documentReviewQueue", parser.ids)
        self.assertIn("/static/js/documents.js", parser.static_assets)

        script = self._fetch_text("/static/js/documents.js")
        self.assertIn("renderReviewArtifacts", script)
        self.assertIn("renderOcrOverlayPages", script)
        self.assertIn("fillReviewCandidate", script)
        self.assertIn("field_candidates", script)
        self.assertIn("overlay_summary", script)
        self.assertIn("data-field-name", script)
        self.assertIn("data-field-value", script)
        self.assertIn("field_matches", script)
        self.assertIn("low-confidence OCR region", script)
        self.assertIn("<rect", script)

    def _form_by_id(self, parser: _AssetParser, form_id: str) -> dict:
        for form in parser.forms:
            if form["id"] == form_id:
                return form
        self.fail(f"Missing form #{form_id}")

    def _form_with_controls(self, parser: _AssetParser, expected_controls: set[str]) -> dict:
        for form in parser.forms:
            names = {control["name"] for control in form["controls"]}
            if expected_controls.issubset(names):
                return form
        self.fail(f"Missing form with controls {sorted(expected_controls)}")

    def _control_by_name(self, form: dict, name: str) -> dict:
        for control in form["controls"]:
            if control["name"] == name:
                return control
        self.fail(f"Missing control {name} in form {form.get('id')}")

    def _fetch_text(self, path: str, *, session_cookie: str | None = None) -> str:
        return self._fetch_bytes(path, session_cookie=session_cookie).decode("utf-8", errors="replace")

    def _fetch_bytes(self, path: str, *, session_cookie: str | None = None) -> bytes:
        request = Request(
            f"{self.live_server_url}{path}",
            headers={"Cookie": f"{settings.SESSION_COOKIE_NAME}={session_cookie or self.session_cookie}"},
        )
        with urlopen(request, timeout=8) as response:
            self.assertEqual(response.status, 200, path)
            return response.read()
