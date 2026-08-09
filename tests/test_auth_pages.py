import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from alfred_ai.services.logging_filters import sanitize_log_record_value


class AuthPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signin_alias_redirects_to_login(self):
        response = self.client.get("/signin/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_login_page_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Alfred")
        self.assertContains(response, "Create account")

    def test_root_entry_renders_login_without_redirect_for_anonymous_user(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Alfred")
        self.assertContains(response, "Create account")

    def test_root_entry_renders_dashboard_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username="root_user", password="Pass12345!")
        self.client.force_login(user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboardRoot"')
        self.assertContains(response, 'data-home-url="/"')

    def test_root_entry_login_returns_to_index(self):
        get_user_model().objects.create_user(username="root_login_user", password="Pass12345!")

        response = self.client.post(
            "/",
            data={"username": "root_login_user", "password": "Pass12345!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_signup_page_renders(self):
        response = self.client.get("/signup/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your Alfred account")
        self.assertContains(response, "Sign in")

    @override_settings(DEBUG=False)
    def test_not_found_page_offers_route_back_home(self):
        response = self.client.get("/missing-workspace/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "That page does not exist in Alfred.", status_code=404)
        self.assertContains(response, "Go to Home", status_code=404)

    def test_signup_creates_user_and_redirects_to_index(self):
        response = self.client.post(
            "/signup/",
            data={
                "username": "new_user",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "city": "Bengaluru",
                "country": "India",
                "monthly_income": "85000",
                "variable_income": "5000",
                "rent_or_emi": "22000",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

        user = get_user_model().objects.get(username="new_user")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.city, "Bengaluru")
        self.assertEqual(user.monthly_income, 85000)


class SessionSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="session_user", password="Pass12345!")
        self.client = Client()

    def test_authenticated_shell_renders_session_timer_metadata(self):
        self.client.force_login(self.user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="alfredSessionTimer"', count=1)
        self.assertContains(response, 'data-session-ping-url="/api/session/ping/"')
        self.assertContains(response, 'data-login-url="/login/"')
        self.assertContains(response, 'data-logout-url="/logout/"')
        self.assertContains(response, 'data-home-url="/"')
        self.assertContains(response, f'data-session-timeout-seconds="{settings.SESSION_COOKIE_AGE}"')
        self.assertNotContains(response, "requested_path")

    def test_session_ping_requires_authentication_and_returns_timeout_contract(self):
        anonymous_response = self.client.post("/api/session/ping/", data="{}", content_type="application/json")
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertTrue(anonymous_response.headers["Location"].startswith("/login/"))

        self.client.force_login(self.user)
        response = self.client.post("/api/session/ping/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["timeout_seconds"], settings.SESSION_COOKIE_AGE)
        self.assertGreater(payload["timeout_seconds"], 0)
        self.assertGreaterEqual(payload["warning_seconds"], 0)
        self.assertLessEqual(payload["warning_seconds"], payload["timeout_seconds"])

    @override_settings(DEBUG=False)
    def test_not_found_page_does_not_echo_missing_url_path(self):
        response = self.client.get("/private/user/docs/statement.pdf")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "That page does not exist in Alfred.", status_code=404)
        self.assertNotContains(response, "/private/user/docs/statement.pdf", status_code=404)

    def test_client_diagnostics_do_not_collect_browser_route_fields(self):
        script = (Path(__file__).resolve().parents[1] / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("installSessionSecurityTimer", script)
        self.assertIn("page_context", script)
        for forbidden in (
            "page_path",
            "page_url",
            "window.location.pathname",
            "window.location.href",
            "target.src",
            "target.href",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_client_log_endpoint_strips_route_fields_from_stale_clients(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/operational/logs/client/",
            data=json.dumps(
                {
                    "module": "frontend",
                    "category": "visualization",
                    "event_type": "client_issue",
                    "message": "stale client payload",
                    "payload": {
                        "page_path": "/dashboard/",
                        "page_url": "https://alfred.example/dashboard/",
                        "nested": {
                            "href": "/documents/",
                            "src": "/static/js/app.js",
                            "safe": "kept",
                            "unexpected_route_value": "/reports/private/",
                        },
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["result"]["payload"]
        serialized = json.dumps(payload)
        self.assertEqual(payload["nested"]["safe"], "kept")
        self.assertEqual(payload["nested"]["unexpected_route_value"], "[redacted-url]")
        for forbidden in ("page_path", "page_url", "href", "src", "/dashboard/", "/documents/", "/reports/private/"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)

    def test_server_log_route_values_are_redacted_before_emission(self):
        sanitized = sanitize_log_record_value(
            (
                "Not Found: /private/user/docs/statement.pdf",
                {"next": "https://alfred.example.com/dashboard/", "safe": "kept"},
            )
        )

        serialized = json.dumps(sanitized)
        self.assertIn("[redacted-url]", serialized)
        self.assertIn("kept", serialized)
        self.assertNotIn("/private/user/docs/statement.pdf", serialized)
        self.assertNotIn("https://alfred.example.com/dashboard/", serialized)
