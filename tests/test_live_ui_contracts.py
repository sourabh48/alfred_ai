from html.parser import HTMLParser
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client


class _AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.named_controls = []
        self.static_assets = set()
        self.progress_bars = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag in {"input", "select", "textarea"} and attrs.get("name"):
            self.named_controls.append(
                {
                    "tag": tag,
                    "id": attrs.get("id", ""),
                    "name": attrs.get("name", ""),
                    "list": attrs.get("list", ""),
                    "disabled": "disabled" in attrs,
                }
            )
        classes = set(attrs.get("class", "").split())
        if "progress-bar" in classes:
            self.progress_bars.append(attrs)
        for key in ("src", "href"):
            value = attrs.get(key, "")
            if value.startswith("/static/"):
                self.static_assets.add(value.split("?", 1)[0])


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
